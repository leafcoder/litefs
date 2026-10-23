#!/usr/bin/env python
# coding: utf-8

"""
Memcache 缓存后端

提供基于 Memcache 的缓存实现
"""

from typing import Any, Optional

from .._json import dumps_ascii, loads
from .base import CacheBackendBase


class MemcacheCache(CacheBackendBase):
    """
    Memcache 缓存实现

    使用 Memcache 作为缓存后端，提供高性能的分布式缓存支持
    """

    def __init__(
        self,
        memcache_client=None,
        servers: list = ["localhost:11211"],
        key_prefix: str = "litefs:",
        expiration_time: int = 3600,
        **kwargs
    ):
        """
        初始化 Memcache 缓存

        Args:
            memcache_client: Memcache 客户端实例（如果提供，则忽略其他连接参数）
            servers: Memcache 服务器列表
            key_prefix: 键前缀
            expiration_time: 默认过期时间（秒）
            **kwargs: 其他 Memcache 连接参数
        """
        self._key_prefix = key_prefix
        self._expiration_time = expiration_time

        if memcache_client is not None:
            self._mc = memcache_client
            # 按客户端类型判定调用约定：pymemcache 的 set 带 expire= 参数，
            # python-memcached 带 time= 参数。依据客户端所属模块判定，
            # 未标注模块的客户端（如测试 Mock）按 python-memcached 分支处理
            self._use_pymemcache = (
                type(memcache_client).__module__.split(".")[0] == "pymemcache"
            )
        else:
            try:
                import pymemcache  # noqa: F401  # 仅用于探测 pymemcache 是否可用
                from pymemcache.client.base import Client
            except ImportError:
                try:
                    import memcache  # noqa: F401  # 仅用于探测 python-memcached 是否可用
                except ImportError:
                    raise ImportError(
                        "pymemcache 或 python-memcached 包未安装，"
                        "请使用 pip install pymemcache 或 pip install python-memcached 安装"
                    )

            self._use_pymemcache = True
            self._mc = Client(servers[0] if isinstance(servers, list) else servers, **kwargs)

        self._test_connection()

    def _test_connection(self):
        """测试 Memcache 连接"""
        try:
            if hasattr(self._mc, 'stats'):
                self._mc.stats()
            else:
                self._mc.set('_litefs_test', '1')
                self._mc.delete('_litefs_test')
        except Exception as e:
            raise ConnectionError(f"无法连接到 Memcache 服务器: {e}")

    def _make_key(self, key: str) -> str:
        """生成带前缀的键"""
        return f"{self._key_prefix}{key}"

    def put(self, key: str, val: Any, expiration: Optional[int] = None) -> None:
        """
        存储值到缓存

        Args:
            key: 缓存键
            val: 缓存值
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        memcache_key = self._make_key(key)
        expiration = expiration if expiration is not None else self._expiration_time

        # 序列化值
        try:
            # 使用 ASCII 安全序列化：pymemcache 客户端默认按 ASCII 编码值，
            # 非 ASCII 内容会直接写入失败
            val_str = dumps_ascii(val)
        except Exception as e:
            raise ValueError(f"无法序列化值: {e}")

        if self._use_pymemcache:
            self._mc.set(memcache_key, val_str, expire=expiration if expiration > 0 else 0)
        else:
            self._mc.set(memcache_key, val_str, time=expiration)

    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在则返回 None
        """
        memcache_key = self._make_key(key)
        val_str = self._mc.get(memcache_key)

        if val_str is None:
            self.stats.record_miss()
            return None

        # 反序列化值
        try:
            value = loads(val_str)
        except Exception:
            # 如果反序列化失败，返回原始字符串
            value = val_str

        self.stats.record_hit()
        return value

    def delete(self, key: str) -> None:
        """
        从缓存删除值

        Args:
            key: 缓存键
        """
        memcache_key = self._make_key(key)
        self._mc.delete(memcache_key)

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的键

        注意：Memcache 不支持模式匹配，此方法仅返回 0

        Args:
            pattern: 键模式

        Returns:
            删除的键数量（始终为 0）
        """
        return 0

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 缓存键

        Returns:
            键是否存在
        """
        memcache_key = self._make_key(key)
        return self._mc.get(memcache_key) is not None

    def expire(self, key: str, expiration: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 缓存键
            expiration: 过期时间（秒）

        Returns:
            是否设置成功
        """
        memcache_key = self._make_key(key)
        value = self._mc.get(memcache_key)

        if value is None:
            return False

        if self._use_pymemcache:
            self._mc.set(memcache_key, value, expire=expiration if expiration > 0 else 0)
        else:
            self._mc.set(memcache_key, value, time=expiration)

        return True

    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        注意：Memcache 不支持 TTL 查询，此方法返回 -1

        Args:
            key: 缓存键

        Returns:
            剩余过期时间（秒），如果键不存在则返回 -2，否则返回 -1（不支持查询）
        """
        memcache_key = self._make_key(key)
        if self._mc.get(memcache_key) is None:
            return -2
        return -1

    def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        原子递增计数器

        基于 memcached 原生 ``incr`` 命令，要求缓存值为数字字符串。
        经由 :meth:`put` 存储的整数会序列化为 ``"42"`` 这类数字字符串，
        与原生命令天然兼容；递增后 :meth:`get` 仍能正确反序列化为整数。

        Args:
            key: 缓存键
            delta: 递增步长

        Returns:
            递增后的新值，键不存在时返回 None
        """
        memcache_key = self._make_key(key)
        if self._use_pymemcache:
            # pymemcache 默认 noreply=True 会导致拿不到返回值，须显式关闭
            result = self._mc.incr(memcache_key, delta, noreply=False)
        else:
            result = self._mc.incr(memcache_key, delta)
        return result if isinstance(result, int) else None

    def decr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        原子递减计数器

        基于 memcached 原生 ``decr`` 命令，要求缓存值为数字字符串。
        memcached 保证计数不会递减至 0 以下（下限钳位为 0）。

        Args:
            key: 缓存键
            delta: 递减步长

        Returns:
            递减后的新值，键不存在时返回 None
        """
        memcache_key = self._make_key(key)
        if self._use_pymemcache:
            # pymemcache 默认 noreply=True 会导致拿不到返回值，须显式关闭
            result = self._mc.decr(memcache_key, delta, noreply=False)
        else:
            result = self._mc.decr(memcache_key, delta)
        return result if isinstance(result, int) else None

    def clear(self) -> None:
        """
        清空所有缓存

        注意：此方法仅删除带前缀的键，需要遍历所有键
        """
        pass

    def __len__(self) -> int:
        """
        获取缓存中的键数量

        注意：Memcache 不支持统计键数量，此方法返回 0

        Returns:
            键数量（始终为 0）
        """
        return 0

    def get_many(self, keys: list) -> dict:
        """
        批量获取值

        Args:
            keys: 缓存键列表

        Returns:
            键值字典
        """
        if not keys:
            return {}

        memcache_keys = [self._make_key(key) for key in keys]

        if self._use_pymemcache:
            values = self._mc.get_many(memcache_keys)
            result = {}
            for memcache_key, val_str in values.items():
                original_key = memcache_key.replace(self._key_prefix, '', 1)
                if val_str is not None:
                    # 反序列化值
                    try:
                        result[original_key] = loads(val_str)
                    except Exception:
                        # 如果反序列化失败，返回原始字符串
                        result[original_key] = val_str
            return result
        else:
            values = self._mc.get_multi(memcache_keys)
            result = {}
            for memcache_key, val_str in values.items():
                original_key = memcache_key.replace(self._key_prefix, '', 1)
                if val_str is not None:
                    # 反序列化值
                    try:
                        result[original_key] = loads(val_str)
                    except Exception:
                        # 如果反序列化失败，返回原始字符串
                        result[original_key] = val_str
            return result

    def set_many(self, mapping: dict, expiration: Optional[int] = None) -> None:
        """
        批量存储值

        Args:
            mapping: 键值字典
            expiration: 过期时间（秒），如果为 None 则使用默认过期时间
        """
        if not mapping:
            return

        expiration = expiration if expiration is not None else self._expiration_time

        memcache_mapping = {}
        for key, value in mapping.items():
            # 序列化值
            try:
                # 使用 ASCII 安全序列化：pymemcache 客户端默认按 ASCII 编码值，
                # 非 ASCII 内容会直接写入失败
                val_str = dumps_ascii(value)
            except Exception as e:
                raise ValueError(f"无法序列化值: {e}")

            memcache_key = self._make_key(key)
            memcache_mapping[memcache_key] = val_str

        if self._use_pymemcache:
            self._mc.set_many(memcache_mapping, expire=expiration if expiration > 0 else 0)
        else:
            self._mc.set_multi(memcache_mapping, time=expiration)

    def delete_many(self, keys: list) -> None:
        """
        批量删除键

        Args:
            keys: 缓存键列表
        """
        if not keys:
            return

        memcache_keys = [self._make_key(key) for key in keys]

        if self._use_pymemcache:
            self._mc.delete_many(memcache_keys)
        else:
            self._mc.delete_multi(memcache_keys)

    def close(self) -> None:
        """
        关闭 Memcache 连接
        """
        try:
            if hasattr(self._mc, 'close'):
                self._mc.close()
        except Exception:
            pass

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()


__all__ = [
    "MemcacheCache",
]
