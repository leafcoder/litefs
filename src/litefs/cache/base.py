#!/usr/bin/env python
# coding: utf-8

"""
缓存后端抽象基类

定义所有缓存后端必须实现的接口，强制接口一致性。
"""

from abc import ABC, abstractmethod
from threading import Lock
from typing import Any, Dict, Optional


class CacheStats:
    """
    缓存统计计数器

    记录缓存后端的读写次数，供监控指标采集使用。
    内部使用互斥锁保证多线程环境下的计数准确性。
    """

    def __init__(self) -> None:
        """初始化统计计数器"""
        self._lock = Lock()
        self._counters: Dict[str, int] = {
            "hit": 0,
            "miss": 0,
            "set": 0,
            "delete": 0,
        }

    def record_hit(self) -> None:
        """记录一次缓存命中"""
        self._increment("hit")

    def record_miss(self) -> None:
        """记录一次缓存未命中"""
        self._increment("miss")

    def record_set(self) -> None:
        """记录一次缓存写入"""
        self._increment("set")

    def record_delete(self) -> None:
        """记录一次缓存删除"""
        self._increment("delete")

    def _increment(self, name: str) -> None:
        """
        递增指定计数器

        Args:
            name: 计数器名称
        """
        with self._lock:
            self._counters[name] += 1

    def snapshot(self) -> Dict[str, int]:
        """
        获取当前统计快照

        Returns:
            各计数器的当前值
        """
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """重置全部计数器"""
        with self._lock:
            for name in self._counters:
                self._counters[name] = 0


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

    @property
    def stats(self) -> CacheStats:
        """
        缓存统计计数器

        所有子类均未调用 ``super().__init__()``，因此这里采用懒加载方式
        创建统计对象，避免要求子类显式初始化。

        Returns:
            CacheStats 实例
        """
        stats = getattr(self, "_cache_stats", None)
        if stats is None:
            stats = CacheStats()
            self._cache_stats = stats
        return stats

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
