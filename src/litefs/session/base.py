#!/usr/bin/env python
# coding: utf-8

"""
Session 后端抽象基类

定义所有 Session 后端必须实现的接口，强制接口一致性。
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .session import Session


class SessionStoreBase(ABC):
    """
    Session 存储后端抽象基类

    所有 Session 后端必须实现以下方法：
    - put(session_id, session): 存储 Session
    - get(session_id): 获取 Session
    - delete(session_id): 删除 Session
    - exists(session_id): 检查 Session 是否存在
    - clear(): 清空所有 Session
    - __len__(): 获取 Session 数量
    - create(): 创建新 Session 对象
    - save(session): 保存 Session
    - close(): 关闭连接

    可选方法（子类按需实现）：
    - expire(session_id, expiration): 设置过期时间
    - ttl(session_id): 获取剩余过期时间
    - delete_pattern(pattern): 删除匹配模式的 Session
    """

    @abstractmethod
    def put(self, session_id: str, session: 'Session') -> None:
        """
        存储 Session

        Args:
            session_id: Session ID
            session: Session 对象
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, session_id: str) -> Optional['Session']:
        """
        获取 Session

        Args:
            session_id: Session ID

        Returns:
            Session 对象，如果不存在则返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """
        删除 Session

        Args:
            session_id: Session ID
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, session_id: str) -> bool:
        """
        检查 Session 是否存在

        Args:
            session_id: Session ID

        Returns:
            Session 是否存在
        """
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """清空所有 Session"""
        raise NotImplementedError

    @abstractmethod
    def __len__(self) -> int:
        """获取 Session 数量"""
        raise NotImplementedError

    @abstractmethod
    def create(self) -> 'Session':
        """
        创建新的 Session 对象

        Returns:
            Session 对象
        """
        raise NotImplementedError

    def save(self, session: 'Session') -> None:
        """
        保存 Session 数据

        Args:
            session: Session 对象
        """
        self.put(session.id, session)

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的 Session

        Args:
            pattern: 键模式

        Returns:
            删除的键数量（不支持时返回 0）
        """
        return 0

    def expire(self, session_id: str, expiration: int) -> bool:
        """
        设置 Session 过期时间

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

        Args:
            session_id: Session ID

        Returns:
            剩余过期时间（秒），不支持返回 -1，Session 不存在返回 -2
        """
        return -1

    def close(self) -> None:
        """关闭连接"""
        pass

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持上下文管理器"""
        self.close()
