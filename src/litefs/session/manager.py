#!/usr/bin/env python
# coding: utf-8

"""
Session 管理器

提供全局 Session 实例管理，确保 Session 对象在应用生命周期内常驻内存。
"""

import threading
from typing import Optional, Union

from .session import Session, MemorySessionStore
from .database_session import DatabaseSession
from .redis_session import RedisSession
from .memcache_session import MemcacheSession
from .factory import SessionBackend, SessionFactory


class SessionManager:
    """
    全局 Session 管理器（单例模式）

    确保 Session 对象在应用生命周期内常驻内存，不会因为 Litefs 实例的
    创建和销毁而丢失数据。

    使用示例:
        # 获取 Session 缓存实例（自动创建）
        session_cache = SessionManager.get_session_cache()

        # 获取指定类型的 Session 缓存
        redis_session_cache = SessionManager.get_session_cache(
            backend='redis',
            host='localhost',
            port=6379
        )

        # 重置 Session 缓存（谨慎使用）
        SessionManager.reset_session_cache()
    """

    _instance: Optional['SessionManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'SessionManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            self._session_caches: dict = {}
            self._default_cache_key: str = 'default'
            self._initialized = True

    @classmethod
    def get_session_cache(
        cls,
        backend: str = SessionBackend.MEMORY,
        cache_key: Optional[str] = None,
        **kwargs
    ) -> Union[MemorySessionStore, DatabaseSession, RedisSession, MemcacheSession]:
        """
        获取 Session 缓存实例（单例模式）

        如果 Session 缓存实例不存在，则自动创建。同一 cache_key 的 Session 缓存实例
        在整个应用生命周期内保持唯一。

        Args:
            backend: Session 后端类型
            cache_key: Session 缓存实例标识，None 使用默认缓存
            **kwargs: Session 配置参数

        Returns:
            Session 缓存实例
        """
        manager = cls()
        key = cache_key or manager._default_cache_key

        if key not in manager._session_caches:
            with cls._lock:
                if key not in manager._session_caches:
                    session_cache = SessionFactory.create_session(backend, **kwargs)
                    manager._session_caches[key] = session_cache

        return manager._session_caches[key]

    @classmethod
    def reset_session_cache(cls, cache_key: Optional[str] = None) -> None:
        """
        重置 Session 缓存实例

        谨慎使用！重置后 Session 数据将丢失。

        Args:
            cache_key: 要重置的 Session 缓存标识，None 重置所有 Session 缓存
        """
        manager = cls()

        with cls._lock:
            if cache_key is None:
                manager._session_caches.clear()
            elif cache_key in manager._session_caches:
                del manager._session_caches[cache_key]

    @classmethod
    def has_session_cache(cls, cache_key: str) -> bool:
        """
        检查 Session 缓存实例是否存在

        Args:
            cache_key: Session 缓存标识

        Returns:
            是否存在
        """
        manager = cls()
        return cache_key in manager._session_caches

    @classmethod
    def list_session_caches(cls) -> list:
        """
        获取所有 Session 缓存标识列表

        Returns:
            Session 缓存标识列表
        """
        manager = cls()
        return list(manager._session_caches.keys())


def get_global_session_cache(
    backend: str = SessionBackend.MEMORY,
    **kwargs
) -> Union[MemorySessionStore, DatabaseSession, RedisSession, MemcacheSession]:
    """
    获取全局 Session 缓存实例的便捷函数

    Args:
        backend: Session 后端类型
        **kwargs: Session 配置参数

    Returns:
        Session 缓存实例
    """
    return SessionManager.get_session_cache(backend, **kwargs)


__all__ = [
    'SessionManager',
    'get_global_session_cache',
]
