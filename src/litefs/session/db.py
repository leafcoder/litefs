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

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import QueuePool, StaticPool
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

from .base import SessionStoreBase
from .session import Session


class DatabaseSession(SessionStoreBase):
    """
    数据库 Session 实现
    
    使用 SQLite 数据库作为 Session 存储，支持持久化存储
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        table_name: str = "sessions",
        expiration_time: int = 3600,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        use_pool: bool = True,
        **kwargs
    ):
        """
        初始化 Database Session
        
        Args:
            db_path: 数据库文件路径，默认为内存数据库
            table_name: Session 表名
            expiration_time: 默认过期时间（秒）
            pool_size: 连接池大小（默认5）
            max_overflow: 连接池最大溢出数（默认10）
            pool_timeout: 连接池超时时间（秒，默认30）
            pool_recycle: 连接回收时间（秒，默认3600）
            use_pool: 是否使用连接池（默认True）
            **kwargs: 其他配置参数
        """
        self._db_path = db_path
        self._table_name = table_name
        self._expiration_time = expiration_time
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._pool_timeout = pool_timeout
        self._pool_recycle = pool_recycle
        self._use_pool = use_pool and SQLALCHEMY_AVAILABLE
        
        self._engine = None
        self._conn = None
        
        if self._use_pool:
            self._initialize_pool()
        else:
            self._create_table()

    def _initialize_pool(self):
        """初始化SQLAlchemy连接池"""
        if not SQLALCHEMY_AVAILABLE:
            raise ImportError("SQLAlchemy未安装，无法使用连接池功能")
        
        # 对于内存数据库，使用StaticPool
        if self._db_path == ":memory:":
            self._engine = create_engine(
                f"sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:
            # 对于文件数据库，使用QueuePool
            self._engine = create_engine(
                f"sqlite:///{self._db_path}",
                poolclass=QueuePool,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                pool_timeout=self._pool_timeout,
                pool_recycle=self._pool_recycle,
                connect_args={"check_same_thread": False},
                echo=False
            )
        
        # 创建表
        with self._engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
            """))
            conn.commit()

    def _connect(self):
        """连接数据库"""
        if self._use_pool:
            # 使用连接池时，返回引擎
            return self._engine
        else:
            # 不使用连接池时，使用传统的sqlite3连接
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
        # 序列化 Session 数据
        try:
            data = json.dumps(dict(session))
        except Exception as e:
            raise ValueError(f"无法序列化 Session 数据: {e}")
        
        created_at = int(time.time())
        expires_at = created_at + self._expiration_time
        
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                conn.execute(text(f"""
                    INSERT OR REPLACE INTO {self._table_name} 
                    (session_id, data, created_at, expires_at) 
                    VALUES (:session_id, :data, :created_at, :expires_at)
                """), {
                    'session_id': session_id,
                    'data': data,
                    'created_at': created_at,
                    'expires_at': expires_at
                })
                conn.commit()
        else:
            # 不使用连接池
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT OR REPLACE INTO {self._table_name} 
                (session_id, data, created_at, expires_at) 
                VALUES (?, ?, ?, ?)
            """, (session_id, data, created_at, expires_at))
            conn.commit()

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在或已过期则返回 None
        """
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT data, expires_at FROM {self._table_name} 
                    WHERE session_id = :session_id
                """), {'session_id': session_id})
                row = result.fetchone()
        else:
            # 不使用连接池
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT data, expires_at FROM {self._table_name} 
                WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
        
        if row is None:
            return None
        
        # 检查是否过期
        if self._use_pool:
            expires_at = row[1]
        else:
            expires_at = row['expires_at']
        
        if int(time.time()) > expires_at:
            # 删除过期 Session
            self.delete(session_id)
            return None
        
        # 反序列化 Session 数据
        try:
            if self._use_pool:
                data = json.loads(row[0])
            else:
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
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                conn.execute(text(f"""
                    DELETE FROM {self._table_name} 
                    WHERE session_id = :session_id
                """), {'session_id': session_id})
                conn.commit()
        else:
            # 不使用连接池
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
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT expires_at FROM {self._table_name} 
                    WHERE session_id = :session_id
                """), {'session_id': session_id})
                row = result.fetchone()
        else:
            # 不使用连接池
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT expires_at FROM {self._table_name} 
                WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
        
        if row is None:
            return False
        
        # 检查是否过期
        if self._use_pool:
            expires_at = row[0]
        else:
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
        # 检查 Session 是否存在
        if not self.exists(session_id):
            return False
        
        # 更新过期时间
        expires_at = int(time.time()) + expiration
        
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                conn.execute(text(f"""
                    UPDATE {self._table_name} 
                    SET expires_at = :expires_at 
                    WHERE session_id = :session_id
                """), {
                    'expires_at': expires_at,
                    'session_id': session_id
                })
                conn.commit()
        else:
            # 不使用连接池
            conn = self._connect()
            cursor = conn.cursor()
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
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT expires_at FROM {self._table_name} 
                    WHERE session_id = :session_id
                """), {'session_id': session_id})
                row = result.fetchone()
        else:
            # 不使用连接池
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT expires_at FROM {self._table_name} 
                WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
        
        if row is None:
            return -2
        
        # 计算剩余过期时间
        if self._use_pool:
            expires_at = row[0]
        else:
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
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                conn.execute(text(f"DELETE FROM {self._table_name}"))
                conn.commit()
        else:
            # 不使用连接池
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
        if self._use_pool:
            # 使用连接池
            with self._engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {self._table_name}"))
                return result.fetchone()[0]
        else:
            # 不使用连接池
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self._table_name}")
            return cursor.fetchone()[0]

    def close(self) -> None:
        """
        关闭数据库连接
        """
        if self._use_pool:
            # 关闭连接池
            if self._engine is not None:
                try:
                    self._engine.dispose()
                except Exception:
                    pass
                self._engine = None
        else:
            # 关闭传统连接
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

    def create(self) -> Session:
        """
        创建新的 Session 对象
        
        Returns:
            Session 对象
        """
        session = Session(store=self)
        return session

    def save(self, session: Session) -> None:
        """
        保存 Session 数据
        
        Args:
            session: Session 对象
        """
        self.put(session.id, session)


__all__ = [
    'DatabaseSession',
]
