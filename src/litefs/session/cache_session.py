#!/usr/bin/env python
# coding: utf-8

"""
带缓存的 Session 存储

为 DatabaseSession 添加缓存层，提高 Session 查找性能
"""

from typing import Optional

from .session import Session


class CachedSessionStore:
    """
    带缓存的 Session 存储
    
    在 DatabaseSession 前面添加缓存层，减少数据库查询
    """

    def __init__(self, store, cache, cache_key_prefix: str = "session:"):
        """
        初始化 CachedSessionStore
        
        Args:
            store: 底层 Session 存储（如 DatabaseSession）
            cache: 缓存存储（如 MemoryCache）
            cache_key_prefix: 缓存键前缀
        """
        self.store = store
        self.cache = cache
        self.cache_key_prefix = cache_key_prefix

    def put(self, session_id: str, session: Session) -> None:
        """
        存储 Session
        
        Args:
            session_id: Session ID
            session: Session 对象
        """
        # 先存储到底层
        self.store.put(session_id, session)
        
        # 再写入缓存
        cache_key = f"{self.cache_key_prefix}{session_id}"
        self.cache.put(cache_key, session)

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在则返回 None
        """
        # 先查缓存
        cache_key = f"{self.cache_key_prefix}{session_id}"
        session = self.cache.get(cache_key)
        
        if session is not None:
            return session
        
        # 缓存未命中，查底层存储
        session = self.store.get(session_id)
        
        if session is not None:
            # 写入缓存
            self.cache.put(cache_key, session)
        
        return session

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        # 删除底层存储
        self.store.delete(session_id)
        
        # 删除缓存
        cache_key = f"{self.cache_key_prefix}{session_id}"
        self.cache.delete(cache_key)

    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 是否存在
        """
        return self.store.exists(session_id)

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 过期时间
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        return self.store.expire(session_id, expiration)

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 剩余过期时间
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒）
        """
        return self.store.ttl(session_id)

    def clear(self) -> None:
        """
        清空所有 Session
        """
        self.store.clear()

    def __len__(self) -> int:
        """
        获取 Session 数量
        
        Returns:
            Session 数量
        """
        return self.store.__len__()

    def create(self) -> Session:
        """
        创建新的 Session 对象
        
        Returns:
            Session 对象
        """
        return self.store.create()

    def save(self, session: Session) -> None:
        """
        保存 Session 数据
        
        Args:
            session: Session 对象
        """
        self.put(session.id, session)
