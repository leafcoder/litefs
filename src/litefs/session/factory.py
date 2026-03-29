#!/usr/bin/env python
# coding: utf-8

"""
Session 工厂

支持多种 Session 后端的工厂模式实现
"""

from typing import Optional, Union

from .session import Session
from .database_session import DatabaseSession
from .redis_session import RedisSession
from .memcache_session import MemcacheSession


class SessionBackend:
    """Session 后端类型"""

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
        backend: str = SessionBackend.DATABASE,
        **kwargs
    ) -> Union[DatabaseSession, RedisSession, MemcacheSession]:
        """
        创建 Session 实例
        
        Args:
            backend: Session 后端类型（database, redis, memcache）
            **kwargs: Session 配置参数
        
        Returns:
            Session 实例
        
        Raises:
            ValueError: 不支持的 Session 后端
            ImportError: Redis 或 Memcache 包未安装
        """
        backend = backend.lower()

        if backend == SessionBackend.DATABASE:
            db_path = kwargs.get("db_path", ":memory:")
            table_name = kwargs.get("table_name", "sessions")
            session_timeout = kwargs.get("session_timeout", 3600)

            return DatabaseSession(
                db_path=db_path,
                table_name=table_name,
                session_timeout=session_timeout,
                **{k: v for k, v in kwargs.items()
                   if k not in ["db_path", "table_name", "session_timeout"]}
            )

        elif backend == SessionBackend.REDIS:
            redis_client = kwargs.get("redis_client")
            host = kwargs.get("host", "localhost")
            port = kwargs.get("port", 6379)
            db = kwargs.get("db", 0)
            password = kwargs.get("password")
            key_prefix = kwargs.get("key_prefix", "session:")
            session_timeout = kwargs.get("session_timeout", 3600)

            return RedisSession(
                redis_client=redis_client,
                host=host,
                port=port,
                db=db,
                password=password,
                key_prefix=key_prefix,
                session_timeout=session_timeout,
                **{k: v for k, v in kwargs.items()
                   if k not in ["redis_client", "host", "port", "db", "password", "key_prefix", "session_timeout"]}
            )

        elif backend == SessionBackend.MEMCACHE:
            memcache_client = kwargs.get("memcache_client")
            servers = kwargs.get("servers", ["localhost:11211"])
            key_prefix = kwargs.get("key_prefix", "session:")
            session_timeout = kwargs.get("session_timeout", 3600)

            return MemcacheSession(
                memcache_client=memcache_client,
                servers=servers,
                key_prefix=key_prefix,
                session_timeout=session_timeout,
                **{k: v for k, v in kwargs.items()
                   if k not in ["memcache_client", "servers", "key_prefix", "session_timeout"]}
            )

        else:
            raise ValueError(
                f"不支持的 Session 后端: {backend}。支持的类型: "
                f"{SessionBackend.DATABASE}, {SessionBackend.REDIS}, {SessionBackend.MEMCACHE}"
            )

    @staticmethod
    def create_from_config(config) -> Union[DatabaseSession, RedisSession, MemcacheSession]:
        """
        从配置对象创建 Session 实例
        
        Args:
            config: 配置对象，应包含 session_backend 和相关配置
        
        Returns:
            Session 实例
        """
        backend = getattr(config, "session_backend", SessionBackend.DATABASE)

        session_config = {}
        if backend == SessionBackend.REDIS:
            session_config = {
                "host": getattr(config, "redis_host", "localhost"),
                "port": getattr(config, "redis_port", 6379),
                "db": getattr(config, "redis_db", 0),
                "password": getattr(config, "redis_password", None),
                "key_prefix": getattr(config, "redis_key_prefix", "session:"),
                "session_timeout": getattr(config, "session_timeout", 3600),
            }
        elif backend == SessionBackend.MEMCACHE:
            session_config = {
                "servers": getattr(config, "memcache_servers", ["localhost:11211"]),
                "key_prefix": getattr(config, "memcache_key_prefix", "session:"),
                "session_timeout": getattr(config, "session_timeout", 3600),
            }
        elif backend == SessionBackend.DATABASE:
            session_config = {
                "db_path": getattr(config, "database_path", ":memory:"),
                "table_name": getattr(config, "database_table", "sessions"),
                "session_timeout": getattr(config, "session_timeout", 3600),
            }

        return SessionFactory.create_session(backend, **session_config)


__all__ = [
    "SessionBackend",
    "SessionFactory",
]