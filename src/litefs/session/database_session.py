#!/usr/bin/env python
# coding: utf-8

"""
Database Session 后端

提供基于 SQLite 数据库的 Session 实现
"""

from multiprocessing import current_process
import sqlite3
import time
import json
from typing import Any, Optional

from .session import Session


class DatabaseSession:
    """
    数据库 Session 实现
    
    使用 SQLite 数据库作为 Session 存储，支持持久化存储
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        table_name: str = "sessions",
        expiration_time: int = 3600,
        **kwargs
    ):
        """
        初始化 Database Session
        
        Args:
            db_path: 数据库文件路径，默认为内存数据库
            table_name: Session 表名
            expiration_time: 默认过期时间（秒）
            **kwargs: 其他配置参数
        """
        self._db_path = db_path
        self._table_name = table_name
        self._expiration_time = expiration_time
        self._conn = None
        self._create_table()
        print(f"调试：数据库路径: {self._db_path}")

    def _connect(self):
        """连接数据库"""
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _create_table(self):
        """创建 Session 表"""
        conn = self._connect()
        cursor = conn.cursor()
        # 只在表不存在时创建表
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        conn.commit()
        # 调试：打印表结构
        cursor.execute(f"PRAGMA table_info({self._table_name})")
        columns = cursor.fetchall()
        print(f"调试：表 {self._table_name} 的结构：")
        for column in columns:
            print(f"  {column[1]}: {column[2]}")

    def _make_key(self, key: str) -> str:
        """生成键"""
        return key

    def put(self, session_id: str, session: Session) -> None:
        """
        存储 Session
        
        Args:
            session_id: Session ID
            session: Session 对象
        """
        conn = self._connect()
        cursor = conn.cursor()
        print(f"调试：存储 Session: {session_id} {session.data}")
        
        # 序列化 Session 数据
        try:
            data = json.dumps(dict(session))
        except Exception as e:
            raise ValueError(f"无法序列化 Session 数据: {e}")
        
        created_at = int(time.time())
        expires_at = created_at + self._expiration_time
        
        # 插入或更新 Session
        cursor.execute(f"""
            INSERT OR REPLACE INTO {self._table_name} 
            (session_id, data, created_at, expires_at) 
            VALUES (?, ?, ?, ?)
        """, (session_id, data, created_at, expires_at))
        conn.commit()
        cursor = conn.cursor()
        ret = cursor.execute(f"""
            SELECT * FROM {self._table_name} 
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        print(row.keys())
        print(f"调试：查询 Session: {session_id} 结果: {row if row else '无'}")

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在或已过期则返回 None
        """
        conn = self._connect()
        cursor = conn.cursor()
        # 查询 Session
        cursor.execute(f"""
            SELECT data, expires_at FROM {self._table_name} 
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        # 检查是否过期
        expires_at = row['expires_at']
        if int(time.time()) > expires_at:
            # 删除过期 Session
            self.delete(session_id)
            return None
        
        # 反序列化 Session 数据
        try:
            data = json.loads(row['data'])
        except Exception as e:
            # 如果反序列化失败，删除损坏的 Session
            self.delete(session_id)
            return None
        
        # 创建 Session 对象
        session = Session(session_id)
        session.update(data)
        return session

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"""
            DELETE FROM {self._table_name} 
            WHERE session_id = ?
        """, (session_id,))
        conn.commit()

    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 是否存在且未过期
        """
        conn = self._connect()
        cursor = conn.cursor()
        
        # 查询 Session
        cursor.execute(f"""
            SELECT expires_at FROM {self._table_name} 
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        
        if row is None:
            return False
        
        # 检查是否过期
        expires_at = row['expires_at']
        return int(time.time()) <= expires_at

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 过期时间
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        conn = self._connect()
        cursor = conn.cursor()
        
        # 检查 Session 是否存在
        if not self.exists(session_id):
            return False
        
        # 更新过期时间
        expires_at = int(time.time()) + expiration
        cursor.execute(f"""
            UPDATE {self._table_name} 
            SET expires_at = ? 
            WHERE session_id = ?
        """, (expires_at, session_id))
        conn.commit()
        return True

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 剩余过期时间
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒），如果 Session 不存在则返回 -2，已过期则返回 -1
        """
        conn = self._connect()
        cursor = conn.cursor()
        
        # 查询 Session
        cursor.execute(f"""
            SELECT expires_at FROM {self._table_name} 
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        
        if row is None:
            return -2
        
        # 计算剩余过期时间
        expires_at = row['expires_at']
        current_time = int(time.time())
        ttl = expires_at - current_time
        
        if ttl <= 0:
            # 删除过期 Session
            self.delete(session_id)
            return -1
        
        return ttl

    def clear(self) -> None:
        """
        清空所有 Session
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {self._table_name}")
        conn.commit()

    def __len__(self) -> int:
        """
        获取 Session 数量
        
        Returns:
            Session 数量
        """
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self._table_name}")
        return cursor.fetchone()[0]

    def close(self) -> None:
        """
        关闭数据库连接
        """
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()


__all__ = [
    'DatabaseSession',
]
