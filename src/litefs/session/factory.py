#!/usr/bin/env python
# coding: utf-8

"""
Session 工厂

支持多种 Session 后端的工厂模式实现
"""

from typing import Optional, Union

from .session import Session, MemorySessionStore
from .db import DatabaseSession
from .redis import RedisSession
from .memcache import MemcacheSession


class SessionBackend:
    """Session 后端类型"""

    MEMORY = "memory"
    DATABASE = "database"
    REDIS = "redis"
    MEMCACHE = "memcache"


class SessionFactory:
    """
    Session 工厂
    
    根据配置创建不同类型的 Session 实例
    """

    @staticmethod
    def create_session(
        backend: str = SessionBackend.MEMORY,
        **kwargs
    ) -> Union[MemorySessionStore, DatabaseSession, RedisSession, MemcacheSession]:
        """
        创建 Session 实例
        
        Args:
            backend: Session 后端类型（memory, database, redis, memcache）
            **kwargs: Session 配置参数
        
        Returns:
            Session 实例
        
        Raises:
            ValueError: 不支持的 Session 后端
            ImportError: Redis 或 Memcache 包未安装
        """
        backend = backend.lower()

        if backend == SessionBackend.MEMORY:
            max_size = kwargs.get("max_size", 1000000)
            return MemorySessionStore(max_size=max_size)

        elif backend == SessionBackend.DATABASE:
            db_path = kwargs.get("db_path", ":memory:")
            table_name = kwargs.get("table_name", "sessions")
            expiration_time = kwargs.get("expiration_time", 3600)

            return DatabaseSession(
                db_path=db_path,
                table_name=table_name,
                expiration_time=expiration_time,
                **{k: v for k, v in kwargs.items()
                   if k not in ["db_path", "table_name", "expiration_time", "max_size"]}
            )

        elif backend == SessionBackend.REDIS:
            redis_client = kwargs.get("redis_client")
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 6379)
            db = kwargs.get("db", 0)
            password = kwargs.get("password")
            key_prefix = kwargs.get("key_prefix", "litefs:session:")
            expiration_time = kwargs.get("expiration_time", 3600)

            return RedisSession(
                redis_client=redis_client,
                host=host,
                port=port,
                db=db,
                password=password,
                key_prefix=key_prefix,
                expiration_time=expiration_time,
                **{k: v for k, v in kwargs.items()
                   if k not in ["redis_client", "host", "port", "db", "password", "key_prefix", "expiration_time", "max_size"]}
            )

        elif backend == SessionBackend.MEMCACHE:
            memcache_client = kwargs.get("memcache_client")
            servers = kwargs.get("servers", ["localhost:11211"])
            key_prefix = kwargs.get("key_prefix", "litefs:session:")
            expiration_time = kwargs.get("expiration_time", 3600)

            return MemcacheSession(
                memcache_client=memcache_client,
                servers=servers,
                key_prefix=key_prefix,
                expiration_time=expiration_time,
                **{k: v for k, v in kwargs.items()
                   if k not in ["memcache_client", "servers", "key_prefix", "expiration_time", "max_size"]}
            )

        else:
            raise ValueError(
                f"不支持的 Session 后端: {backend}。支持的类型: "
                f"{SessionBackend.MEMORY}, {SessionBackend.DATABASE}, "
                f"{SessionBackend.REDIS}, {SessionBackend.MEMCACHE}"
            )

    @staticmethod
    def create_from_config(config) -> Union[MemorySessionStore, DatabaseSession, RedisSession, MemcacheSession]:
        """
        从配置对象创建 Session 实例
        
        Args:
            config: 配置对象，应包含 session_backend 和相关配置
        
        Returns:
            Session 实例
        """
        backend = getattr(config, "session_backend", SessionBackend.MEMORY)

        session_config = {}
        if backend == SessionBackend.REDIS:
            session_config = {
                "host": getattr(config, "redis_host", "localhost"),
                "port": getattr(config, "redis_port", 6379),
                "db": getattr(config, "redis_db", 0),
                "password": getattr(config, "redis_password", None),
                "key_prefix": getattr(config, "redis_session_key_prefix", "litefs:session:"),
                "expiration_time": getattr(config, "session_expiration_time", 3600),
            }
        elif backend == SessionBackend.DATABASE:
            session_config = {
                "db_path": getattr(config, "database_path", ":memory:"),
                "table_name": getattr(config, "database_session_table", "sessions"),
                "expiration_time": getattr(config, "session_expiration_time", 3600),
            }
        elif backend == SessionBackend.MEMCACHE:
            session_config = {
                "servers": getattr(config, "memcache_servers", ["localhost:11211"]),
                "key_prefix": getattr(config, "memcache_session_key_prefix", "litefs:session:"),
                "expiration_time": getattr(config, "session_expiration_time", 3600),
            }
        elif backend == SessionBackend.MEMORY:
            session_config = {
                "max_size": getattr(config, "session_max_size", 1000000),
            }

        return SessionFactory.create_session(backend, **session_config)


__all__ = [
    'SessionBackend',
    'SessionFactory',
]
