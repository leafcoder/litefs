#!/usr/bin/env python
# coding: utf-8

"""
增强的缓存装饰器

提供灵活的缓存机制，支持函数缓存、响应缓存等。

缓存后端委托给 litefs.cache.MemoryCache，统一缓存基础设施。
"""

import hashlib
import pickle
import threading
import time
from typing import Any, Callable, Optional, Dict, Union
from functools import wraps
from datetime import timedelta


class MemoryCacheStore:
    """
    内存缓存存储

    委托给 litefs.cache.MemoryCache 作为底层存储，
    在其之上添加 TTL 过期管理能力。
    """

    def __init__(self, max_size: int = 1000):
        from .cache import MemoryCache as _MemoryCache

        self.max_size = max_size
        self._cache = _MemoryCache(max_size=max_size)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int):
        with self._lock:
            self._cache.put(key, value, expiration=ttl)

    def delete(self, key: str):
        with self._lock:
            self._cache.delete(key)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> dict:
        with self._lock:
            return {
                'total_entries': len(self._cache),
                'max_size': self.max_size
            }


# 全局缓存存储
_global_cache_store: Optional[MemoryCacheStore] = None


def get_cache_store() -> MemoryCacheStore:
    """
    获取全局缓存存储
    
    Returns:
        MemoryCacheStore 实例
    """
    global _global_cache_store
    if _global_cache_store is None:
        _global_cache_store = MemoryCacheStore()
    return _global_cache_store


def _generate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: Optional[str] = None
) -> str:
    """
    生成缓存键
    
    Args:
        func: 函数
        args: 位置参数
        kwargs: 关键字参数
        key_prefix: 键前缀
        
    Returns:
        缓存键字符串
    """
    # 基础键：函数名
    key_parts = [func.__module__, func.__name__]
    
    # 添加前缀
    if key_prefix:
        key_parts.insert(0, key_prefix)
    
    # 序列化参数
    try:
        args_hash = hashlib.md5(
            pickle.dumps((args, kwargs))
        ).hexdigest()
        key_parts.append(args_hash)
    except Exception:
        # 如果参数无法序列化，使用字符串表示
        key_parts.append(str((args, kwargs)))
    
    return ':'.join(key_parts)


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    cache_store: Optional[MemoryCacheStore] = None,
    skip_cache_func: Optional[Callable] = None
):
    """
    函数缓存装饰器
    
    Args:
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
        cache_store: 缓存存储实例
        skip_cache_func: 判断是否跳过缓存的函数
        
    Returns:
        装饰器函数
        
    使用示例:
        @cached(ttl=60, key_prefix='user')
        def get_user(user_id):
            return db.query(User).get(user_id)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 检查是否跳过缓存
            if skip_cache_func and skip_cache_func(*args, **kwargs):
                return func(*args, **kwargs)
            
            # 获取缓存存储
            store = cache_store or get_cache_store()
            
            # 生成缓存键
            cache_key = _generate_cache_key(func, args, kwargs, key_prefix)
            
            # 尝试从缓存获取
            cached_value = store.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            store.set(cache_key, result, ttl)
            
            return result
        
        # 添加缓存控制方法
        wrapper.cache_clear = lambda: (store or get_cache_store()).delete(
            _generate_cache_key(func, (), {}, key_prefix)
        )
        
        return wrapper
    return decorator


def cache_response(
    ttl: int = 300,
    vary_on: Optional[list] = None,
    key_prefix: str = 'response'
):
    """
    响应缓存装饰器
    
    用于缓存视图函数的响应
    
    Args:
        ttl: 缓存过期时间（秒）
        vary_on: 响应变化的请求头列表
        key_prefix: 缓存键前缀
        
    Returns:
        装饰器函数
        
    使用示例:
        @cache_response(ttl=60, vary_on=['Accept-Encoding'])
        def api_endpoint(request):
            return {'data': 'value'}
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request_handler, *args, **kwargs):
            store = get_cache_store()
            
            # 生成缓存键
            cache_key_parts = [
                key_prefix,
                request_handler.environ.get('PATH_INFO', '/'),
                request_handler.environ.get('REQUEST_METHOD', 'GET')
            ]
            
            # 添加变化的请求头
            if vary_on:
                for header in vary_on:
                    header_value = request_handler.environ.get(f'HTTP_{header.upper().replace("-", "_")}', '')
                    cache_key_parts.append(f"{header}={header_value}")
            
            cache_key = ':'.join(cache_key_parts)
            
            # 尝试从缓存获取
            cached_response = store.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # 执行函数
            response = func(request_handler, *args, **kwargs)
            
            # 存入缓存
            store.set(cache_key, response, ttl)
            
            return response
        
        return wrapper
    return decorator


def cache_method(ttl: int = 300):
    """
    方法缓存装饰器
    
    用于缓存类方法的结果
    
    Args:
        ttl: 缓存过期时间（秒）
        
    Returns:
        装饰器函数
        
    使用示例:
        class UserService:
            @cache_method(ttl=60)
            def get_user(self, user_id):
                return db.query(User).get(user_id)
    """
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # 获取缓存存储
            store = get_cache_store()
            
            # 生成缓存键（包含 self）
            cache_key = _generate_cache_key(
                method,
                (id(self),) + args,
                kwargs,
                key_prefix=method.__name__
            )
            
            # 尝试从缓存获取
            cached_value = store.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行方法
            result = method(self, *args, **kwargs)
            
            # 存入缓存
            store.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_property(ttl: int = 300):
    """
    属性缓存装饰器
    
    用于缓存类属性的计算结果
    
    Args:
        ttl: 缓存过期时间（秒）
        
    Returns:
        装饰器函数
        
    使用示例:
        class User:
            def __init__(self, user_id):
                self.user_id = user_id
            
            @cache_property(ttl=60)
            def profile(self):
                return db.query(Profile).filter_by(user_id=self.user_id).first()
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self):
            # 获取缓存存储
            store = get_cache_store()
            
            # 生成缓存键
            cache_key = f"property:{func.__name__}:{id(self)}"
            
            # 尝试从缓存获取
            cached_value = store.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 计算属性值
            result = func(self)
            
            # 存入缓存
            store.set(cache_key, result, ttl)
            
            return result
        
        return property(wrapper)
    return decorator


# 便捷函数
def clear_all_cache():
    """清空所有缓存"""
    get_cache_store().clear()


def get_cache_stats() -> dict:
    """
    获取缓存统计信息
    
    Returns:
        统计信息字典
    """
    return get_cache_store().get_stats()
