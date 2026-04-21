#!/usr/bin/env python
# coding: utf-8

"""
缓存后端抽象基类

定义所有缓存后端必须实现的接口，强制接口一致性。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheBackendBase(ABC):
    """
    缓存后端抽象基类

    所有缓存后端必须实现以下方法：
    - put(key, val, expiration): 存储值
    - get(key): 获取值
    - delete(key): 删除值
    - exists(key): 检查键是否存在
    - clear(): 清空所有缓存
    - __len__(): 获取缓存数量
    - close(): 关闭连接

    可选方法（子类按需实现）：
    - delete_pattern(pattern): 删除匹配模式的键
    - expire(key, expiration): 设置过期时间
    - ttl(key): 获取剩余过期时间
    - get_many(keys): 批量获取
    - set_many(mapping): 批量存储
    - delete_many(keys): 批量删除
    """

    @abstractmethod
    def put(self, key: str, val: Any, expiration: Optional[int] = None) -> None:
        """
        存储值到缓存

        Args:
            key: 缓存键
            val: 缓存值
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """
        从缓存删除值

        Args:
            key: 缓存键
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 缓存键

        Returns:
            键是否存在
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存"""
        raise NotImplementedError

    @abstractmethod
    def __len__(self) -> int:
        """获取缓存中的键数量"""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        raise NotImplementedError

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的键

        Args:
            pattern: 键模式

        Returns:
            删除的键数量（不支持时返回 0）
        """
        return 0

    def expire(self, key: str, expiration: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 缓存键
            expiration: 过期时间（秒）

        Returns:
            是否设置成功
        """
        return False

    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Args:
            key: 缓存键

        Returns:
            剩余过期时间（秒），不支持返回 -1，键不存在返回 -2
        """
        return -1

    def get_many(self, keys: list) -> dict:
        """
        批量获取值（默认实现：逐个获取）

        Args:
            keys: 缓存键列表

        Returns:
            键值字典
        """
        result = {}
        for key in keys:
            val = self.get(key)
            if val is not None:
                result[key] = val
        return result

    def set_many(self, mapping: dict, expiration: Optional[int] = None) -> None:
        """
        批量存储值（默认实现：逐个存储）

        Args:
            mapping: 键值字典
            expiration: 过期时间（秒）
        """
        for key, value in mapping.items():
            self.put(key, value, expiration=expiration)

    def delete_many(self, keys: list) -> None:
        """
        批量删除键（默认实现：逐个删除）

        Args:
            keys: 缓存键列表
        """
        for key in keys:
            self.delete(key)

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()
