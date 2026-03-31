#!/usr/bin/env python
# coding: utf-8

"""
Redis Session 后端

提供基于 Redis 的 Session 实现
"""

import time
import json
from typing import Any, Optional

from .session import Session


class RedisSession:
    """
    Redis Session 实现
    
    使用 Redis 作为 Session 存储，提供高性能的分布式缓存支持
    """

    def __init__(
        self,
        redis_client=None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "litefs:session:",
        expiration_time: int = 3600,
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
            expiration_time: 默认过期时间（秒）
            **kwargs: 其他 Redis 连接参数
        """
        self._key_prefix = key_prefix
        self._expiration_time = expiration_time

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
                "decode_responses": True,
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

    def put(self, session_id: str, session: Session) -> None:
        """
        存储 Session
        
        Args:
            session_id: Session ID
            session: Session 对象
        """
        redis_key = self._make_key(session_id)
        expiration = self._expiration_time
        # 序列化 Session 数据
        try:
            data = json.dumps(dict(session))
        except Exception as e:
            raise ValueError(f"无法序列化 Session 数据: {e}")

        if expiration > 0:
            self._redis.setex(redis_key, expiration, data)
        else:
            self._redis.set(redis_key, data)

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在则返回 None
        """
        redis_key = self._make_key(session_id)
        data_str = self._redis.get(redis_key)
        
        if data_str is None:
            return None
        
        # 反序列化 Session 数据
        try:
            data = json.loads(data_str)
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
        redis_key = self._make_key(session_id)
        self._redis.delete(redis_key)

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的 Session
        
        Args:
            pattern: 键模式
        
        Returns:
            删除的键数量
        """
        redis_pattern = self._make_key(pattern)
        return self._redis.delete(*self._redis.keys(redis_pattern))

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
        设置 Session 过期时间
        
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
        获取 Session 剩余过期时间
        
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
    'RedisSession',
]
