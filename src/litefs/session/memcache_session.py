#!/usr/bin/env python
# coding: utf-8

"""
Memcache Session 后端

提供基于 Memcache 的 Session 实现
"""

import time
import uuid
from typing import Any, Optional, Dict
from .session import Session


class MemcacheSession:
    """
    Memcache Session 实现
    
    使用 Memcache 存储 Session 数据，提供高性能的分布式 Session 支持
    """

    def __init__(
        self,
        memcache_client=None,
        servers: list = ["localhost:11211"],
        key_prefix: str = "session:",
        session_timeout: int = 3600,
        **kwargs
    ):
        """
        初始化 Memcache Session
        
        Args:
            memcache_client: Memcache 客户端实例（如果提供，则忽略其他连接参数）
            servers: Memcache 服务器列表
            key_prefix: 键前缀
            session_timeout: Session 默认超时时间（秒）
            **kwargs: 其他 Memcache 连接参数
        """
        self._key_prefix = key_prefix
        self._session_timeout = session_timeout

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

    def create(self) -> Session:
        """
        创建新的 Session
        
        Returns:
            Session 对象
        """
        import pickle
        
        session_id = str(uuid.uuid4())
        memcache_key = self._make_key(session_id)
        
        data = pickle.dumps({})
        
        if self._use_pymemcache:
            self._mc.set(memcache_key, data, expire=self._session_timeout if self._session_timeout > 0 else 0)
        else:
            self._mc.set(memcache_key, data, time=self._session_timeout)
        
        session = Session(session_id)
        session.data = {}
        return session

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在或已过期则返回 None
        """
        import pickle
        
        memcache_key = self._make_key(session_id)
        data = self._mc.get(memcache_key)
        
        if data:
            session_data = pickle.loads(data)
            session = Session(session_id)
            session.data = session_data
            return session
        return None

    def save(self, session: Session) -> None:
        """
        保存 Session
        
        Args:
            session: Session 对象
        """
        import pickle
        
        memcache_key = self._make_key(session.id)
        data = pickle.dumps(session.data)
        
        if self._use_pymemcache:
            self._mc.set(memcache_key, data, expire=self._session_timeout if self._session_timeout > 0 else 0)
        else:
            self._mc.set(memcache_key, data, time=self._session_timeout)

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        memcache_key = self._make_key(session_id)
        self._mc.delete(memcache_key)

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
        设置 Session 的过期时间
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        memcache_key = self._make_key(session_id)
        data = self._mc.get(memcache_key)
        
        if data is None:
            return False
        
        if self._use_pymemcache:
            self._mc.set(memcache_key, data, expire=expiration if expiration > 0 else 0)
        else:
            self._mc.set(memcache_key, data, time=expiration)
        
        return True

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 的剩余过期时间
        
        注意：Memcache 不支持 TTL 查询，此方法返回 -1
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒），如果 Session 不存在则返回 -2，否则返回 -1（不支持查询）
        """
        memcache_key = self._make_key(session_id)
        if self._mc.get(memcache_key) is None:
            return -2
        return -1

    def clear(self) -> None:
        """
        清空所有 Session
        
        注意：此方法仅删除带前缀的键，需要遍历所有键
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
        """支持上下文管理器"""
        self.close()


__all__ = [
    "MemcacheSession",
]