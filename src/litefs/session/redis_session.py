#!/usr/bin/env python
# coding: utf-8

"""
Redis Session 后端

提供基于 Redis 的 Session 实现
"""

import time
import uuid
from typing import Any, Optional, Dict
from .session import Session


class RedisSession:
    """
    Redis Session 实现
    
    使用 Redis 存储 Session 数据，提供高性能的分布式 Session 支持
    """

    def __init__(
        self,
        redis_client=None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "session:",
        session_timeout: int = 3600,
        **kwargs
    ):
        """
        初始化 Redis Session
        
        Args:
            redis_client: Redis 客户端实例（如果提供，则忽略其他连接参数）
            host: Redis 服务器地址
            port: Redis 服务器端口
            db: Redis 数据库编号
            password: Redis 密码
            key_prefix: 键前缀
            session_timeout: Session 默认超时时间（秒）
            **kwargs: 其他 Redis 连接参数
        """
        self._key_prefix = key_prefix
        self._session_timeout = session_timeout

        if redis_client is not None:
            self._redis = redis_client
        else:
            try:
                import redis
            except ImportError:
                raise ImportError(
                    "redis-py 包未安装，请使用 pip install redis 安装"
                )

            connection_params = {
                "host": host,
                "port": port,
                "db": db,
                "decode_responses": False,
                **kwargs
            }

            if password:
                connection_params["password"] = password

            self._redis = redis.Redis(**connection_params)

        self._test_connection()

    def _test_connection(self):
        """测试 Redis 连接"""
        try:
            self._redis.ping()
        except Exception as e:
            raise ConnectionError(f"无法连接到 Redis 服务器: {e}")

    def _make_key(self, session_id: str) -> str:
        """生成带前缀的键"""
        return f"{self._key_prefix}{session_id}"

    def create(self) -> Session:
        """
        创建新的 Session
        
        Returns:
            Session 对象
        """
        import pickle
        
        session_id = str(uuid.uuid4())
        redis_key = self._make_key(session_id)
        
        data = pickle.dumps({})
        
        if self._session_timeout > 0:
            self._redis.setex(redis_key, self._session_timeout, data)
        else:
            self._redis.set(redis_key, data)
        
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
        
        redis_key = self._make_key(session_id)
        data = self._redis.get(redis_key)
        
        if data:
            session_data = pickle.loads(data)
            session = Session(session_id)
            session.data = session_data
            return session
        return None

    def save(self, session: Session) -> None:
        """
        保存 Session
        
        Args:
            session: Session 对象
        """
        import pickle
        
        redis_key = self._make_key(session.id)
        data = pickle.dumps(session.data)
        
        if self._session_timeout > 0:
            self._redis.setex(redis_key, self._session_timeout, data)
        else:
            self._redis.set(redis_key, data)

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        redis_key = self._make_key(session_id)
        self._redis.delete(redis_key)

    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 是否存在
        """
        redis_key = self._make_key(session_id)
        return self._redis.exists(redis_key) > 0

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 的过期时间
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        redis_key = self._make_key(session_id)
        return self._redis.expire(redis_key, expiration)

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 的剩余过期时间
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒），如果 Session 不存在则返回 -2
        """
        redis_key = self._make_key(session_id)
        return self._redis.ttl(redis_key)

    def clear(self) -> None:
        """
        清空所有 Session
        
        注意：这会删除所有带前缀的键
        """
        pattern = self._make_key("*")
        keys = self._redis.keys(pattern)
        if keys:
            self._redis.delete(*keys)

    def __len__(self) -> int:
        """
        获取 Session 数量
        
        Returns:
            Session 数量
        """
        pattern = self._make_key("*")
        keys = self._redis.keys(pattern)
        return len(keys) if keys else 0

    def close(self) -> None:
        """
        关闭 Redis 连接
        """
        try:
            self._redis.close()
        except Exception:
            pass

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()


__all__ = [
    "RedisSession",
]