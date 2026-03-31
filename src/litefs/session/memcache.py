#!/usr/bin/env python
# coding: utf-8

"""
Memcache Session 后端

提供基于 Memcache 的 Session 实现
"""

import time
import json
from typing import Any, Optional

from .session import Session


class MemcacheSession:
    """
    Memcache Session 实现
    
    使用 Memcache 作为 Session 存储，提供高性能的分布式缓存支持
    """

    def __init__(
        self,
        memcache_client=None,
        servers: list = ["localhost:11211"],
        key_prefix: str = "litefs:session:",
        expiration_time: int = 3600,
        **kwargs
    ):
        """
        初始化 Memcache Session
        
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
        else:
            try:
                import pymemcache
                from pymemcache.client.base import Client
            except ImportError:
                try:
                    import memcache
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

    def _make_key(self, session_id: str) -> str:
        """生成带前缀的键"""
        return f"{self._key_prefix}{session_id}"

    def put(self, session_id: str, session: Session) -> None:
        """
        存储 Session
        
        Args:
            session_id: Session ID
            session: Session 对象
        """
        memcache_key = self._make_key(session_id)
        expiration = self._expiration_time

        # 序列化 Session 数据
        try:
            data = json.dumps(dict(session))
        except Exception as e:
            raise ValueError(f"无法序列化 Session 数据: {e}")

        if self._use_pymemcache:
            self._mc.set(memcache_key, data, expire=expiration if expiration > 0 else 0)
        else:
            self._mc.set(memcache_key, data, time=expiration)

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在则返回 None
        """
        memcache_key = self._make_key(session_id)
        data_str = self._mc.get(memcache_key)
        
        if data_str is None:
            return None
        
        # 反序列化 Session 数据
        try:
            data = json.loads(data_str)
        except Exception as e:
            # 如果反序列化失败，删除损坏的 Session
            self.delete(session_id)
            return None
        
        # 创建 Session 对象
        session = Session(session_id)
        session.update(data)
        return session

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        memcache_key = self._make_key(session_id)
        self._mc.delete(memcache_key)

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的 Session
        
        注意：Memcache 不支持模式匹配，此方法仅返回 0
        
        Args:
            pattern: 键模式
        
        Returns:
            删除的键数量（始终为 0）
        """
        return 0

    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 是否存在
        """
        memcache_key = self._make_key(session_id)
        return self._mc.get(memcache_key) is not None

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 过期时间
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        memcache_key = self._make_key(session_id)
        session = self.get(session_id)
        
        if session is None:
            return False
        
        # 重新存储 Session 以更新过期时间
        self.put(session_id, session)
        return True

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 剩余过期时间
        
        注意：Memcache 不支持 TTL 查询，此方法返回 -1
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒），如果 Session 不存在则返回 -2，否则返回 -1（不支持查询）
        """
        if not self.exists(session_id):
            return -2
        return -1

    def clear(self) -> None:
        """
        清空所有 Session
        
        注意：Memcache 不支持清空指定前缀的键，此方法不执行任何操作
        """
        pass

    def __len__(self) -> int:
        """
        获取 Session 数量
        
        注意：Memcache 不支持统计键数量，此方法返回 0
        
        Returns:
            Session 数量（始终为 0）
        """
        return 0

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
        """
        支持上下文管理器
        """
        self.close()

    def create(self) -> Session:
        """
        创建新的 Session 对象
        
        Returns:
            Session 对象
        """
        session = Session(store=self)
        return session

    def save(self, session: Session) -> None:
        """
        保存 Session 数据
        
        Args:
            session: Session 对象
        """
        self.put(session.id, session)


__all__ = [
    'MemcacheSession',
]
