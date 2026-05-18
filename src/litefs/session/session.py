#!/usr/bin/env python
# coding: utf-8

from collections import UserDict
from typing import Any, Optional

from .base import SessionStoreBase


class Session(UserDict):
    """
    Session 数据对象
    
    继承自 UserDict，用于存储单个 Session 的数据
    """

    def __init__(self, session_id=None, store=None):
        """
        初始化 Session
        
        Args:
            session_id: Session ID（如果为 None，则会在创建时生成）
            store: Session 存储后端实例，用于手动保存数据
        """
        import uuid
        self.id = session_id or str(uuid.uuid4())
        self.data = {}
        self.store = store

    def __str__(self):
        return "<Session Id=%s>" % self.id

    def save(self):
        """
        手动保存 Session 数据到存储后端
        """
        if self.store is not None:
            self.store.put(self.id, self)
            return True
        return False


class MemorySessionStore(SessionStoreBase):
    """
    内存 Session 存储
    
    使用内存作为 Session 存储，适合开发环境
    """

    def __init__(self, max_size: int = 1000000):
        """
        初始化 MemorySessionStore
        
        Args:
            max_size: 最大 Session 数量
        """
        self._max_size = max_size
        self._sessions = {}

    def put(self, session_id: str, session: Session) -> None:
        """
        存储 Session
        
        Args:
            session_id: Session ID
            session: Session 对象
        """
        if len(self._sessions) >= self._max_size:
            # 简单的 LRU 策略：删除最早的 Session
            oldest_session_id = next(iter(self._sessions))
            del self._sessions[oldest_session_id]
        self._sessions[session_id] = session

    def get(self, session_id: str) -> Optional[Session]:
        """
        获取 Session
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 对象，如果不存在则返回 None
        """
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        """
        删除 Session
        
        Args:
            session_id: Session ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]

    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在
        
        Args:
            session_id: Session ID
        
        Returns:
            Session 是否存在
        """
        return session_id in self._sessions

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 过期时间
        
        注意：内存 Session 不支持过期时间，此方法始终返回 False
        
        Args:
            session_id: Session ID
            expiration: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        return False

    def ttl(self, session_id: str) -> int:
        """
        获取 Session 剩余过期时间
        
        注意：内存 Session 不支持过期时间，此方法始终返回 -1
        
        Args:
            session_id: Session ID
        
        Returns:
            剩余过期时间（秒），如果 Session 不存在则返回 -2，否则返回 -1（不支持查询）
        """
        if session_id not in self._sessions:
            return -2
        return -1

    def clear(self) -> None:
        """
        清空所有 Session
        """
        self._sessions.clear()

    def __len__(self) -> int:
        """
        获取 Session 数量
        
        Returns:
            Session 数量
        """
        return len(self._sessions)

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
    'Session',
    'MemorySessionStore',
]

