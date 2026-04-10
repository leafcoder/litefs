#!/usr/bin/env python
# coding: utf-8

"""
表单数据缓存模块

提供高效的表单数据缓存机制，避免重复解析
"""

from collections import OrderedDict
from time import time
from typing import Dict, Optional, Any


class FormCache:
    """
    表单数据缓存
    
    使用 LRU (Least Recently Used) 策略管理缓存
    支持自动过期和容量限制
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
    ):
        """
        初始化表单缓存
        
        Args:
            max_size: 最大缓存数量
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._access_time: Dict[str, float] = {}
        self._expire_time: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的表单数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的表单数据，如果不存在或已过期则返回 None
        """
        if key not in self._cache:
            return None
        
        # 检查是否过期
        if key in self._expire_time and time() > self._expire_time[key]:
            self._remove(key)
            return None
        
        # 更新访问时间并移动到末尾（LRU）
        self._access_time[key] = time()
        self._cache.move_to_end(key)
        
        return self._cache[key]
    
    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        设置缓存的表单数据
        
        Args:
            key: 缓存键
            value: 表单数据
            ttl: 过期时间（秒），None 使用默认值
        """
        if ttl is None:
            ttl = self.default_ttl
        
        # 如果键已存在，先删除
        if key in self._cache:
            self._remove(key)
        
        # 如果缓存已满，移除最久未使用的项
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._remove(oldest_key)
        
        # 添加新项
        self._cache[key] = value
        self._access_time[key] = time()
        self._expire_time[key] = time() + ttl
    
    def delete(self, key: str) -> bool:
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if key in self._cache:
            self._remove(key)
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._access_time.clear()
        self._expire_time.clear()
    
    def cleanup_expired(self) -> int:
        """
        清理过期的缓存项
        
        Returns:
            清理的项数
        """
        current_time = time()
        expired_keys = [
            key for key, expire_time in self._expire_time.items()
            if current_time > expire_time
        ]
        
        for key in expired_keys:
            self._remove(key)
        
        return len(expired_keys)
    
    def _remove(self, key: str) -> None:
        """
        移除缓存项
        
        Args:
            key: 缓存键
        """
        if key in self._cache:
            del self._cache[key]
        if key in self._access_time:
            del self._access_time[key]
        if key in self._expire_time:
            del self._expire_time[key]
    
    def __len__(self) -> int:
        """返回缓存大小"""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否在缓存中"""
        return key in self._cache
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl,
        }
