#!/usr/bin/env python
# coding: utf-8

"""
数据库缓存后端

提供基于关系数据库的缓存实现
"""

import json
import random
import sqlite3
import time
import zlib
from typing import Any, Optional


class DatabaseCache:
    """
    数据库缓存实现
    
    使用 SQLite 数据库作为缓存后端，提供持久化的缓存支持
    使用 JSON 序列化替代 pickle，避免反序列化安全风险
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        table_name: str = "cache",
        expiration_time: int = 3600,
        cleanup_probability: float = 0.01,
        cleanup_threshold: int = 1000,
        **kwargs
    ):
        """
        初始化数据库缓存
        
        Args:
            db_path: 数据库文件路径，默认为内存数据库
            table_name: 缓存表名
            expiration_time: 默认过期时间（秒）
            cleanup_probability: 清理概率（0-1之间，默认0.01即1%概率）
            cleanup_threshold: 触发强制清理的过期条目阈值（默认1000）
            **kwargs: 其他数据库连接参数
        """
        self._db_path = db_path
        self._table_name = table_name
        self._expiration_time = expiration_time
        self._cleanup_probability = cleanup_probability
        self._cleanup_threshold = cleanup_threshold
        self._conn = None
        self._cursor = None
        self._operation_count = 0
        
        self._initialize_database()

    def _initialize_database(self):
        """初始化数据库和表结构"""
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._cursor = self._conn.cursor()
        
        self._cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self._table_name} (
                key TEXT PRIMARY KEY,
                value TEXT,
                timestamp INTEGER,
                expiration INTEGER
            )
        """)
        
        self._cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_expiration 
            ON {self._table_name}(expiration)
        """)
        
        self._conn.commit()

    def _cleanup_expired(self, force: bool = False):
        """
        清理过期的缓存条目
        
        使用概率性清理策略：
        1. 每次操作有小概率触发清理（默认1%）
        2. 当操作计数达到阈值时强制清理
        3. 可通过force参数强制执行清理
        
        Args:
            force: 是否强制执行清理
        """
        if self._cursor is None:
            return
        
        self._operation_count += 1
        
        # 判断是否需要执行清理
        should_cleanup = force
        
        # 概率性清理
        if not should_cleanup and self._cleanup_probability > 0:
            should_cleanup = random.random() < self._cleanup_probability
        
        # 阈值触发清理
        if not should_cleanup and self._cleanup_threshold > 0:
            if self._operation_count >= self._cleanup_threshold:
                should_cleanup = True
                self._operation_count = 0
        
        if should_cleanup:
            current_time = int(time.time())
            self._cursor.execute(
                f"DELETE FROM {self._table_name} WHERE expiration < ?",
                (current_time,)
            )
            self._conn.commit()

    def _serialize(self, value: Any) -> str:
        """
        安全序列化：使用 JSON + zlib 压缩
        
        Args:
            value: 要序列化的值
            
        Returns:
            序列化后的字符串
            
        Raises:
            TypeError: 如果值包含 JSON 不支持的类型
        """
        json_str = json.dumps(value, ensure_ascii=False, default=str)
        compressed = zlib.compress(json_str.encode("utf-8"))
        import base64
        return base64.b64encode(compressed).decode("ascii")

    def _deserialize(self, data: str) -> Any:
        """
        安全反序列化：使用 zlib 解压 + JSON 解析
        
        Args:
            data: 序列化的字符串
            
        Returns:
            反序列化后的值
            
        Raises:
            ValueError: 如果数据损坏或格式无效
        """
        import base64
        try:
            compressed = base64.b64decode(data.encode("ascii"))
            json_str = zlib.decompress(compressed).decode("utf-8")
            return json.loads(json_str)
        except (json.JSONDecodeError, zlib.error, Exception) as e:
            raise ValueError(f"缓存数据反序列化失败: {e}")

    def put(self, key: str, val: Any, expiration: Optional[int] = None) -> None:
        """
        存储值到缓存
        
        Args:
            key: 缓存键
            val: 缓存值
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        if self._cursor is None:
            return
            
        current_time = int(time.time())
        expiration_time = expiration if expiration is not None else self._expiration_time
        expire_timestamp = current_time + expiration_time if expiration_time > 0 else 0
        
        serialized_value = self._serialize(val)
        
        self._cursor.execute(
            f"""
            INSERT OR REPLACE INTO {self._table_name} 
            (key, value, timestamp, expiration) 
            VALUES (?, ?, ?, ?)
            """,
            (key, serialized_value, current_time, expire_timestamp)
        )
        self._conn.commit()

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        if self._cursor is None:
            return None
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT value FROM {self._table_name} WHERE key = ? AND expiration > ?",
            (key, int(time.time()))
        )
        result = self._cursor.fetchone()
        
        if result:
            try:
                return self._deserialize(result[0])
            except ValueError:
                # 损坏的缓存数据，删除并返回 None
                self.delete(key)
                return None
        return None

    def delete(self, key: str) -> None:
        """
        从缓存删除值
        
        Args:
            key: 缓存键
        """
        if self._cursor is None:
            return
            
        self._cursor.execute(
            f"DELETE FROM {self._table_name} WHERE key = ?",
            (key,)
        )
        self._conn.commit()

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的键
        
        Args:
            pattern: 键模式（支持 SQL LIKE 语法）
        
        Returns:
            删除的键数量
        """
        if self._cursor is None:
            return 0
            
        self._cursor.execute(
            f"DELETE FROM {self._table_name} WHERE key LIKE ?",
            (pattern,)
        )
        self._conn.commit()
        return self._cursor.rowcount

    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            键是否存在且未过期
        """
        if self._cursor is None:
            return False
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT 1 FROM {self._table_name} WHERE key = ? AND expiration > ?",
            (key, int(time.time()))
        )
        return self._cursor.fetchone() is not None

    def expire(self, key: str, expiration: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 缓存键
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        if self._cursor is None:
            return False
            
        current_time = int(time.time())
        expire_timestamp = current_time + expiration
        
        self._cursor.execute(
            f"UPDATE {self._table_name} SET expiration = ? WHERE key = ?",
            (expire_timestamp, key)
        )
        self._conn.commit()
        return self._cursor.rowcount > 0

    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间
        
        Args:
            key: 缓存键
        
        Returns:
            剩余过期时间（秒），如果键不存在或已过期则返回 -2
        """
        if self._cursor is None:
            return -2
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT expiration FROM {self._table_name} WHERE key = ?",
            (key,)
        )
        result = self._cursor.fetchone()
        
        if result:
            expiration = result[0]
            if expiration == 0:
                return -1  # 永不过期
            return max(0, expiration - int(time.time()))
        return -2  # 键不存在

    def clear(self) -> None:
        """
        清空所有缓存
        """
        if self._cursor is None:
            return
            
        self._cursor.execute(f"DELETE FROM {self._table_name}")
        self._conn.commit()
        self._operation_count = 0

    def __len__(self) -> int:
        """
        获取缓存中的键数量
        
        Returns:
            键数量
        """
        if self._cursor is None:
            return 0
            
        self._cleanup_expired()
        
        self._cursor.execute(
            f"SELECT COUNT(*) FROM {self._table_name}"
        )
        return self._cursor.fetchone()[0]

    def get_many(self, keys: list) -> dict:
        """
        批量获取值
        
        Args:
            keys: 缓存键列表
        
        Returns:
            键值字典
        """
        if self._cursor is None or not keys:
            return {}
        
        self._cleanup_expired()
        
        placeholders = ','.join(['?' for _ in keys])
        self._cursor.execute(
            f"SELECT key, value FROM {self._table_name} WHERE key IN ({placeholders}) AND expiration > ?",
            keys + [int(time.time())]
        )
        results = self._cursor.fetchall()
        
        result = {}
        for key, value in results:
            try:
                result[key] = self._deserialize(value)
            except ValueError:
                # 损坏的数据跳过
                self.delete(key)
        
        return result

    def set_many(self, mapping: dict, expiration: Optional[int] = None) -> None:
        """
        批量存储值
        
        Args:
            mapping: 键值字典
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        if self._cursor is None or not mapping:
            return
        
        current_time = int(time.time())
        expiration_time = expiration if expiration is not None else self._expiration_time
        expire_timestamp = current_time + expiration_time if expiration_time > 0 else 0
        
        data = []
        for key, value in mapping.items():
            serialized_value = self._serialize(value)
            data.append((key, serialized_value, current_time, expire_timestamp))
        
        self._cursor.executemany(
            f"""
            INSERT OR REPLACE INTO {self._table_name} 
            (key, value, timestamp, expiration) 
            VALUES (?, ?, ?, ?)
            """,
            data
        )
        self._conn.commit()

    def delete_many(self, keys: list) -> None:
        """
        批量删除键
        
        Args:
            keys: 缓存键列表
        """
        if self._cursor is None or not keys:
            return
        
        placeholders = ','.join(['?' for _ in keys])
        self._cursor.execute(
            f"DELETE FROM {self._table_name} WHERE key IN ({placeholders})",
            keys
        )
        self._conn.commit()

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
    "DatabaseCache",
]