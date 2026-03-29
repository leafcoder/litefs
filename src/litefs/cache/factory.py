#!/usr/bin/env python
# coding: utf-8

"""
缓存工厂

支持多种缓存后端的工厂模式实现
"""

from typing import Optional, Union

from .cache import MemoryCache, TreeCache
from .redis_cache import RedisCache
from .database_cache import DatabaseCache
from .memcache_cache import MemcacheCache


class CacheBackend:
    """缓存后端类型"""

    MEMORY = "memory"
    TREE = "tree"
    REDIS = "redis"
    DATABASE = "database"
    MEMCACHE = "memcache"


class CacheFactory:
    """
    缓存工厂
    
    根据配置创建不同类型的缓存实例
    """

    @staticmethod
    def create_cache(
        backend: str = CacheBackend.MEMORY,
        **kwargs
    ) -> Union[MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache]:
        """
        创建缓存实例
        
        Args:
            backend: 缓存后端类型（memory, tree, redis, database, memcache）
            **kwargs: 缓存配置参数
        
        Returns:
            缓存实例
        
        Raises:
            ValueError: 不支持的缓存后端
            ImportError: Redis 或 Memcache 包未安装
        """
        backend = backend.lower()

        if backend == CacheBackend.MEMORY:
            max_size = kwargs.get("max_size", 10000)
            return MemoryCache(max_size=max_size)

        elif backend == CacheBackend.TREE:
            clean_period = kwargs.get("clean_period", 60)
            expiration_time = kwargs.get("expiration_time", 3600)
            return TreeCache(clean_period=clean_period, expiration_time=expiration_time)

        elif backend == CacheBackend.REDIS:
            redis_client = kwargs.get("redis_client")
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 6379)
            db = kwargs.get("db", 0)
            password = kwargs.get("password")
            key_prefix = kwargs.get("key_prefix", "litefs:")
            expiration_time = kwargs.get("expiration_time", 3600)

            return RedisCache(
                redis_client=redis_client,
                host=host,
                port=port,
                db=db,
                password=password,
                key_prefix=key_prefix,
                expiration_time=expiration_time,
                **{k: v for k, v in kwargs.items()
                   if k not in ["redis_client", "host", "port", "db", "password", "key_prefix", "expiration_time", "max_size", "clean_period"]}
            )

        elif backend == CacheBackend.DATABASE:
            db_path = kwargs.get("db_path", ":memory:")
            table_name = kwargs.get("table_name", "cache")
            expiration_time = kwargs.get("expiration_time", 3600)

            return DatabaseCache(
                db_path=db_path,
                table_name=table_name,
                expiration_time=expiration_time,
                **{k: v for k, v in kwargs.items()
                   if k not in ["db_path", "table_name", "expiration_time", "max_size", "clean_period"]}
            )

        elif backend == CacheBackend.MEMCACHE:
            memcache_client = kwargs.get("memcache_client")
            servers = kwargs.get("servers", ["localhost:11211"])
            key_prefix = kwargs.get("key_prefix", "litefs:")
            expiration_time = kwargs.get("expiration_time", 3600)

            return MemcacheCache(
                memcache_client=memcache_client,
                servers=servers,
                key_prefix=key_prefix,
                expiration_time=expiration_time,
                **{k: v for k, v in kwargs.items()
                   if k not in ["memcache_client", "servers", "key_prefix", "expiration_time", "max_size", "clean_period"]}
            )

        else:
            raise ValueError(
                f"不支持的缓存后端: {backend}。支持的类型: "
                f"{CacheBackend.MEMORY}, {CacheBackend.TREE}, {CacheBackend.REDIS}, "
                f"{CacheBackend.DATABASE}, {CacheBackend.MEMCACHE}"
            )

    @staticmethod
    def create_from_config(config) -> Union[MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache]:
        """
        从配置对象创建缓存实例
        
        Args:
            config: 配置对象，应包含 cache_backend 和相关配置
        
        Returns:
            缓存实例
        """
        backend = getattr(config, "cache_backend", CacheBackend.MEMORY)

        cache_config = {}
        if backend == CacheBackend.REDIS:
            cache_config = {
                "host": getattr(config, "redis_host", "localhost"),
                "port": getattr(config, "redis_port", 6379),
                "db": getattr(config, "redis_db", 0),
                "password": getattr(config, "redis_password", None),
                "key_prefix": getattr(config, "redis_key_prefix", "litefs:"),
                "expiration_time": getattr(config, "cache_expiration_time", 3600),
            }
        elif backend == CacheBackend.DATABASE:
            cache_config = {
                "db_path": getattr(config, "database_path", ":memory:"),
                "table_name": getattr(config, "database_table", "cache"),
                "expiration_time": getattr(config, "cache_expiration_time", 3600),
            }
        elif backend == CacheBackend.MEMCACHE:
            cache_config = {
                "servers": getattr(config, "memcache_servers", ["localhost:11211"]),
                "key_prefix": getattr(config, "memcache_key_prefix", "litefs:"),
                "expiration_time": getattr(config, "cache_expiration_time", 3600),
            }
        elif backend == CacheBackend.MEMORY:
            cache_config = {
                "max_size": getattr(config, "cache_max_size", 10000),
            }
        elif backend == CacheBackend.TREE:
            cache_config = {
                "clean_period": getattr(config, "cache_clean_period", 60),
                "expiration_time": getattr(config, "cache_expiration_time", 3600),
            }

        return CacheFactory.create_cache(backend, **cache_config)


__all__ = [
    "CacheBackend",
    "CacheFactory",
]
