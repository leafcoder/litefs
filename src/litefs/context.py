#!/usr/bin/env python
# coding: utf-8

"""
请求上下文管理

提供请求上下文管理功能，类似 Flask 的 g 对象
"""

import threading
from typing import Any, Optional, Dict
from datetime import datetime


class RequestContextData:
    """
    请求数据容器
    
    用于存储请求生命周期内的数据
    """
    
    def __init__(self, request):
        """
        初始化请求数据容器
        
        Args:
            request: 请求对象
        """
        self.request = request
        self._data: Dict[str, Any] = {}
        self.created_at = datetime.now()
        self._start_time = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取数据
        
        Args:
            key: 数据键
            default: 默认值
            
        Returns:
            数据值
        """
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self._data[key] = value
    
    def delete(self, key: str) -> None:
        """
        删除数据
        
        Args:
            key: 数据键
        """
        if key in self._data:
            del self._data[key]
    
    def clear(self) -> None:
        """清空所有数据"""
        self._data.clear()
    
    def keys(self):
        """获取所有键"""
        return self._data.keys()
    
    def values(self):
        """获取所有值"""
        return self._data.values()
    
    def items(self):
        """获取所有键值对"""
        return self._data.items()
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._data
    
    def __getitem__(self, key: str) -> Any:
        """通过键获取值"""
        return self._data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """通过键设置值"""
        self._data[key] = value
    
    def __delitem__(self, key: str) -> None:
        """通过键删除值"""
        del self._data[key]
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"<RequestContextData {self._data}>"


class RequestContext:
    """
    请求上下文管理器
    
    使用线程本地存储管理请求上下文
    """
    
    _local = threading.local()
    
    @classmethod
    def push(cls, request) -> RequestContextData:
        """
        压入请求上下文
        
        Args:
            request: 请求对象
            
        Returns:
            请求数据容器
        """
        context_data = RequestContextData(request)
        cls._local.context = context_data
        return context_data
    
    @classmethod
    def pop(cls) -> None:
        """弹出请求上下文"""
        if hasattr(cls._local, 'context'):
            delattr(cls._local, 'context')
    
    @classmethod
    def get_current(cls) -> Optional[RequestContextData]:
        """
        获取当前请求上下文
        
        Returns:
            请求数据容器，如果没有则返回 None
        """
        return getattr(cls._local, 'context', None)
    
    @classmethod
    def has_context(cls) -> bool:
        """
        检查是否存在请求上下文
        
        Returns:
            是否存在请求上下文
        """
        return hasattr(cls._local, 'context')


class G:
    """
    全局请求上下文对象
    
    类似 Flask 的 g 对象，用于在请求生命周期内存储数据
    
    使用示例:
        from litefs.context import g
        
        # 设置数据
        g.user = current_user
        g.db_session = db_session
        
        # 获取数据
        user = g.user
        db = g.db_session
        
        # 检查是否存在
        if 'user' in g:
            print(g.user)
    """
    
    def __getattr__(self, name: str) -> Any:
        """
        获取属性
        
        Args:
            name: 属性名
            
        Returns:
            属性值
            
        Raises:
            AttributeError: 如果上下文不存在或属性不存在
        """
        context = RequestContext.get_current()
        if context is None:
            raise AttributeError(
                f"Working outside of request context. "
                f"This typically means that you attempted to use '{name}' "
                f"outside of a request handler."
            )
        
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        return context.get(name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """
        设置属性
        
        Args:
            name: 属性名
            value: 属性值
            
        Raises:
            AttributeError: 如果上下文不存在
        """
        if name.startswith('_'):
            super().__setattr__(name, value)
            return
        
        context = RequestContext.get_current()
        if context is None:
            raise AttributeError(
                f"Working outside of request context. "
                f"This typically means that you attempted to set '{name}' "
                f"outside of a request handler."
            )
        
        context.set(name, value)
    
    def __delattr__(self, name: str) -> None:
        """
        删除属性
        
        Args:
            name: 属性名
            
        Raises:
            AttributeError: 如果上下文不存在或属性不存在
        """
        if name.startswith('_'):
            super().__delattr__(name)
            return
        
        context = RequestContext.get_current()
        if context is None:
            raise AttributeError(
                f"Working outside of request context. "
                f"This typically means that you attempted to delete '{name}' "
                f"outside of a request handler."
            )
        
        context.delete(name)
    
    def __contains__(self, name: str) -> bool:
        """
        检查属性是否存在
        
        Args:
            name: 属性名
            
        Returns:
            是否存在
        """
        context = RequestContext.get_current()
        if context is None:
            return False
        
        return name in context
    
    def get(self, name: str, default: Any = None) -> Any:
        """
        获取属性值
        
        Args:
            name: 属性名
            default: 默认值
            
        Returns:
            属性值
        """
        context = RequestContext.get_current()
        if context is None:
            return default
        
        return context.get(name, default)
    
    def pop(self, name: str, default: Any = None) -> Any:
        """
        弹出属性值
        
        Args:
            name: 属性名
            default: 默认值
            
        Returns:
            属性值
        """
        context = RequestContext.get_current()
        if context is None:
            return default
        
        value = context.get(name, default)
        if name in context:
            context.delete(name)
        
        return value
    
    def clear(self) -> None:
        """清空所有属性"""
        context = RequestContext.get_current()
        if context is not None:
            context.clear()
    
    def __repr__(self) -> str:
        """字符串表示"""
        context = RequestContext.get_current()
        if context is None:
            return "<g (no context)>"
        
        return f"<g {dict(context.items())}>"


# 全局请求上下文对象实例
g = G()


def has_request_context() -> bool:
    """
    检查是否存在请求上下文
    
    Returns:
        是否存在请求上下文
    """
    return RequestContext.has_context()


def get_current_request():
    """
    获取当前请求对象
    
    Returns:
        当前请求对象，如果没有则返回 None
    """
    context = RequestContext.get_current()
    if context is None:
        return None
    
    return context.request


class RequestContextManager:
    """
    请求上下文管理器
    
    用于在请求处理前后自动管理上下文
    """
    
    def __init__(self, request):
        """
        初始化上下文管理器
        
        Args:
            request: 请求对象
        """
        self.request = request
    
    def __enter__(self):
        """进入上下文"""
        return RequestContext.push(self.request)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        RequestContext.pop()
        return False


def with_request_context(func):
    """
    请求上下文装饰器
    
    为函数自动添加请求上下文
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    def wrapper(*args, **kwargs):
        # 如果已经有上下文，直接执行
        if has_request_context():
            return func(*args, **kwargs)
        
        # 否则创建一个假的上下文
        from unittest.mock import Mock
        mock_request = Mock()
        
        with RequestContextManager(mock_request):
            return func(*args, **kwargs)
    
    return wrapper
