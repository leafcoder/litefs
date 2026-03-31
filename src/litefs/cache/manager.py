#!/usr/bin/env python
# coding: utf-8

"""
缓存管理器

提供全局缓存实例管理，确保缓存对象在应用生命周期内常驻内存。
"""

import threading
from typing import Optional, Union

from .cache import MemoryCache, TreeCache
from .redis import RedisCache
from .db import DatabaseCache
from .memcache import MemcacheCache
from .factory import CacheBackend, CacheFactory


class CacheManager:
    """
    全局缓存管理器（单例模式）

    确保缓存对象在应用生命周期内常驻内存，不会因为 Litefs 实例的
    创建和销毁而丢失数据。

    使用示例:
        # 获取缓存实例（自动创建）
        cache = CacheManager.get_cache()

        # 获取指定类型的缓存
        session_cache = CacheManager.get_cache(
            backend='memory',
            max_size=1000000,
            cache_key='sessions'
        )

        # 重置缓存（谨慎使用）
        CacheManager.reset_cache()
    """

    _instance: Optional['CacheManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'CacheManager':
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

            self._caches: dict = {}
            self._default_cache_key: str = 'default'
            self._initialized = True

    @classmethod
    def get_cache(
        cls,
        backend: str = CacheBackend.TREE,
        cache_key: Optional[str] = None,
        **kwargs
    ) -> Union[MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache]:
        """
        获取缓存实例（单例模式）

        如果缓存实例不存在，则自动创建。同一 cache_key 的缓存实例
        在整个应用生命周期内保持唯一。

        Args:
            backend: 缓存后端类型
            cache_key: 缓存实例标识，None 使用默认缓存
            **kwargs: 缓存配置参数

        Returns:
            缓存实例
        """
        manager = cls()
        key = cache_key or manager._default_cache_key

        if key not in manager._caches:
            with cls._lock:
                if key not in manager._caches:
                    cache = CacheFactory.create_cache(backend, **kwargs)
                    manager._caches[key] = cache

        return manager._caches[key]

    @classmethod
    def get_session_cache(cls, **kwargs):
        """
        获取会话缓存实例

        Args:
            **kwargs: 配置参数，支持 max_size

        Returns:
            MemoryCache 实例
        """
        config = {'max_size': 1000000}
        config.update(kwargs)
        return cls.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='sessions',
            **config
        )

    @classmethod
    def get_file_cache(cls, **kwargs):
        """
        获取文件缓存实例

        Args:
            **kwargs: 配置参数，支持 clean_period, expiration_time

        Returns:
            TreeCache 实例
        """
        config = {'clean_period': 60, 'expiration_time': 3600}
        config.update(kwargs)
        return cls.get_cache(
            backend=CacheBackend.TREE,
            cache_key='files',
            **config
        )

    @classmethod
    def reset_cache(cls, cache_key: Optional[str] = None) -> None:
        """
        重置缓存实例

        谨慎使用！重置后缓存数据将丢失。

        Args:
            cache_key: 要重置的缓存标识，None 重置所有缓存
        """
        manager = cls()

        with cls._lock:
            if cache_key is None:
                manager._caches.clear()
            elif cache_key in manager._caches:
                del manager._caches[cache_key]

    @classmethod
    def has_cache(cls, cache_key: str) -> bool:
        """
        检查缓存实例是否存在

        Args:
            cache_key: 缓存标识

        Returns:
            是否存在
        """
        manager = cls()
        return cache_key in manager._caches

    @classmethod
    def list_caches(cls) -> list:
        """
        获取所有缓存标识列表

        Returns:
            缓存标识列表
        """
        manager = cls()
        return list(manager._caches.keys())


def get_global_cache(
    backend: str = CacheBackend.TREE,
    **kwargs
) -> Union[MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache]:
    """
    获取全局缓存实例的便捷函数

    Args:
        backend: 缓存后端类型
        **kwargs: 缓存配置参数

    Returns:
        缓存实例
    """
    return CacheManager.get_cache(backend, **kwargs)
