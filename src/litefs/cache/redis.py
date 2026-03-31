#!/usr/bin/env python
# coding: utf-8

"""
Redis 缓存后端

提供基于 Redis 的缓存实现
"""

import time
import json
from typing import Any, Optional


class RedisCache:
    """
    Redis 缓存实现
    
    使用 Redis 作为缓存后端，提供高性能的分布式缓存支持
    """

    def __init__(
        self,
        redis_client=None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "litefs:",
        expiration_time: int = 3600,
        **kwargs
    ):
        """
        初始化 Redis 缓存
        
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

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self._key_prefix}{key}"

    def put(self, key: str, val: Any, expiration: Optional[int] = None) -> None:
        """
        存储值到缓存
        
        Args:
            key: 缓存键
            val: 缓存值
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        redis_key = self._make_key(key)
        expiration = expiration if expiration is not None else self._expiration_time

        # 序列化值
        try:
            val_str = json.dumps(val)
        except Exception as e:
            raise ValueError(f"无法序列化值: {e}")

        if expiration > 0:
            self._redis.setex(redis_key, expiration, val_str)
        else:
            self._redis.set(redis_key, val_str)

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值
        
        Args:
            key: 缓存键
        
        Returns:
            缓存值，如果不存在则返回 None
        """
        redis_key = self._make_key(key)
        val_str = self._redis.get(redis_key)
        
        if val_str is None:
            return None
        
        # 反序列化值
        try:
            return json.loads(val_str)
        except Exception as e:
            # 如果反序列化失败，返回原始字符串
            return val_str

    def delete(self, key: str) -> None:
        """
        从缓存删除值
        
        Args:
            key: 缓存键
        """
        redis_key = self._make_key(key)
        self._redis.delete(redis_key)

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的键
        
        Args:
            pattern: 键模式
        
        Returns:
            删除的键数量
        """
        redis_pattern = self._make_key(pattern)
        return self._redis.delete(*self._redis.keys(redis_pattern))

    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            键是否存在
        """
        redis_key = self._make_key(key)
        return self._redis.exists(redis_key) > 0

    def expire(self, key: str, expiration: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 缓存键
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        redis_key = self._make_key(key)
        return self._redis.expire(redis_key, expiration)

    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间
        
        Args:
            key: 缓存键
        
        Returns:
            剩余过期时间（秒），如果键不存在则返回 -2
        """
        redis_key = self._make_key(key)
        return self._redis.ttl(redis_key)

    def clear(self) -> None:
        """
        清空所有缓存
        
        注意：这会删除所有带前缀的键
        """
        pattern = self._make_key("*")
        keys = self._redis.keys(pattern)
        if keys:
            self._redis.delete(*keys)

    def __len__(self) -> int:
        """
        获取缓存中的键数量
        
        Returns:
            键数量
        """
        pattern = self._make_key("*")
        keys = self._redis.keys(pattern)
        return len(keys) if keys else 0

    def get_many(self, keys: list) -> dict:
        """
        批量获取值
        
        Args:
            keys: 缓存键列表
        
        Returns:
            键值字典
        """
        if not keys:
            return {}

        redis_keys = [self._make_key(key) for key in keys]
        values = self._redis.mget(redis_keys)

        result = {}
        for i, key in enumerate(keys):
            val_str = values[i]
            if val_str is not None:
                # 反序列化值
                try:
                    result[key] = json.loads(val_str)
                except Exception:
                    # 如果反序列化失败，返回原始字符串
                    result[key] = val_str

        return result

    def set_many(self, mapping: dict, expiration: Optional[int] = None) -> None:
        """
        批量存储值
        
        Args:
            mapping: 键值字典
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        if not mapping:
            return

        expiration = expiration if expiration is not None else self._expiration_time

        pipe = self._redis.pipeline()
        for key, value in mapping.items():
            # 序列化值
            try:
                val_str = json.dumps(value)
            except Exception as e:
                raise ValueError(f"无法序列化值: {e}")
            
            redis_key = self._make_key(key)
            if expiration > 0:
                pipe.setex(redis_key, expiration, val_str)
            else:
                pipe.set(redis_key, val_str)

        pipe.execute()

    def delete_many(self, keys: list) -> None:
        """
        批量删除键
        
        Args:
            keys: 缓存键列表
        """
        if not keys:
            return

        redis_keys = [self._make_key(key) for key in keys]
        if redis_keys:
            self._redis.delete(*redis_keys)

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
    "RedisCache",
]
