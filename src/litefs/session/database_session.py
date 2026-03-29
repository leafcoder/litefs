#!/usr/bin/env python
# coding: utf-8

"""
数据库 Session 后端

提供基于关系数据库的 Session 实现
"""

import sqlite3
import time
import uuid
from typing import Any, Optional, Dict
from .session import Session


class DatabaseSession:
    """
    数据库 Session 实现
    
    使用 SQLite 数据库存储 Session 数据，提供持久化的 Session 支持
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        table_name: str = "sessions",
        session_timeout: int = 3600,
        **kwargs
    ):
        """
        初始化数据库 Session
        
        Args:
            db_path: 数据库文件路径，默认为内存数据库
            table_name: Session 表名
            session_timeout: Session 默认超时时间（秒）
            **kwargs: 其他数据库连接参数
        """
        self._db_path = db_path
        self._table_name = table_name
        self._session_timeout = session_timeout
        self._conn = None
        self._cursor = None
        
        self._initialize_database()

    def _initialize_database(self):
        """初始化数据库和表结构"""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        
        self._cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                session_id TEXT PRIMARY KEY,
                data BLOB,
                timestamp INTEGER,
                expiration INTEGER
            )
        """)
        
        self._cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_expiration 
            ON {self._table_name}(expiration)
        """)
        
        self._conn.commit()

    def _cleanup_expired(self):
        """清理过期的 Session"""
        if self._cursor is None or self._conn is None:
            return
            
        current_time = int(time.time())
        self._cursor.execute(
            f"DELETE FROM {self._table_name} WHERE expiration < ?",
            (current_time,)
        )
        self._conn.commit()

    def create(self) -> Session:
        """
        创建新的 Session
        
        Returns:
            Session 对象
        """
        if self._cursor is None or self._conn is None:
            raise RuntimeError("Database connection not initialized")
            
        session_id = str(uuid.uuid4())
        current_time = int(time.time())
        expire_timestamp = current_time + self._session_timeout
        
        import pickle
        data = pickle.dumps({})
        
        self._cursor.execute(
            f"""
            INSERT INTO {self._table_name} 
            (session_id, data, timestamp, expiration) 
            VALUES (?, ?, ?, ?)
            """,
            (session_id, data, current_time, expire_timestamp)
        )
        self._conn.commit()
        
        session = Session(session_id)
        session.data = {}
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在或已过期则返回 None
        """
        import pickle
        
        if self._cursor is None or self._conn is None:
            return None
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT data FROM {self._table_name} WHERE session_id = ? AND expiration > ?",
            (session_id, int(time.time()))
        )
        result = self._cursor.fetchone()
        
        if result:
            data = pickle.loads(result[0])
            session = Session(session_id)
            session.data = data
            return session
        return None

    def save(self, session: Session) -> None:
        """
        保存 Session
        
        Args:
            session: Session 对象
        """
        import pickle
        
        if self._cursor is None or self._conn is None:
            return
            
        current_time = int(time.time())
        expire_timestamp = current_time + self._session_timeout
        data = pickle.dumps(session.data)
        
        self._cursor.execute(
            f"""
            INSERT OR REPLACE INTO {self._table_name} 
            (session_id, data, timestamp, expiration) 
            VALUES (?, ?, ?, ?)
            """,
            (session.id, data, current_time, expire_timestamp)
        )
        self._conn.commit()

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        if self._cursor is None or self._conn is None:
            return
            
        self._cursor.execute(
            f"DELETE FROM {self._table_name} WHERE session_id = ?",
            (session_id,)
        )
        self._conn.commit()

    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 是否存在且未过期
        """
        if self._cursor is None or self._conn is None:
            return False
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT 1 FROM {self._table_name} WHERE session_id = ? AND expiration > ?",
            (session_id, int(time.time()))
        )
        return self._cursor.fetchone() is not None

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 的过期时间
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        if self._cursor is None or self._conn is None:
            return False
            
        current_time = int(time.time())
        expire_timestamp = current_time + expiration
        
        self._cursor.execute(
            f"UPDATE {self._table_name} SET expiration = ? WHERE session_id = ?",
            (expire_timestamp, session_id)
        )
        self._conn.commit()
        return self._cursor.rowcount > 0

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 的剩余过期时间
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒），如果 Session 不存在或已过期则返回 -2
        """
        if self._cursor is None or self._conn is None:
            return -2
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT expiration FROM {self._table_name} WHERE session_id = ?",
            (session_id,)
        )
        result = self._cursor.fetchone()
        
        if result:
            expiration = result[0]
            if expiration == 0:
                return -1  # 永不过期
            return max(0, expiration - int(time.time()))
        return -2  # Session 不存在

    def clear(self) -> None:
        """
        清空所有 Session
        """
        if self._cursor is None or self._conn is None:
            return
            
        self._cursor.execute(f"DELETE FROM {self._table_name}")
        self._conn.commit()

    def __len__(self) -> int:
        """
        获取 Session 数量
        
        Returns:
            Session 数量
        """
        if self._cursor is None or self._conn is None:
            return 0
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT COUNT(*) FROM {self._table_name}"
        )
        return self._cursor.fetchone()[0]

    def close(self) -> None:
        """
        关闭数据库连接
        """
        if self._cursor:
            self._cursor.close()
        if self._conn:
            self._conn.close()
        
        self._cursor = None
        self._conn = None

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()


__all__ = [
    "DatabaseSession",
]