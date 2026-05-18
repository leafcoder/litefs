#!/usr/bin/env python
# coding: utf-8

"""
用户模型

提供用户、角色和权限的基础模型，以及可替换的用户存储后端。

默认使用内存存储（MemoryUserStore），适合开发和测试。
生产环境可实现 BaseUserStore 接口对接数据库。
"""

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Dict, List, Optional, Set


@dataclass
class Permission:
    """权限"""
    name: str
    description: str = ''

    # Class-level registry (ClassVar prevents dataclass from treating these as fields)
    _registry: ClassVar[Dict[str, 'Permission']] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __post_init__(self):
        with Permission._registry_lock:
            Permission._registry[self.name] = self

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Permission']:
        """根据名称获取权限"""
        with cls._registry_lock:
            return cls._registry.get(name)

    @classmethod
    def create(cls, name: str, description: str = '') -> 'Permission':
        """创建权限"""
        return cls(name=name, description=description)


@dataclass
class Role:
    """角色"""
    name: str
    description: str = ''
    permissions: List[Permission] = field(default_factory=list)

    # Class-level registry (ClassVar prevents dataclass from treating these as fields)
    _registry: ClassVar[Dict[str, 'Role']] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __post_init__(self):
        with Role._registry_lock:
            Role._registry[self.name] = self

    def add_permission(self, permission: Permission):
        """添加权限"""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: Permission):
        """移除权限"""
        if permission in self.permissions:
            self.permissions.remove(permission)

    def has_permission(self, permission_name: str) -> bool:
        """检查是否有权限"""
        for perm in self.permissions:
            if perm.name == permission_name:
                return True
        return False

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Role']:
        """根据名称获取角色"""
        with cls._registry_lock:
            return cls._registry.get(name)

    @classmethod
    def create(cls, name: str, description: str = '', permissions: List[Permission] = None) -> 'Role':
        """创建角色"""
        return cls(
            name=name,
            description=description,
            permissions=permissions or [],
        )


@dataclass
class User:
    """用户"""
    id: int
    username: str
    password_hash: str
    email: Optional[str] = None
    is_active: bool = True
    roles: List[Role] = field(default_factory=list)

    def add_role(self, role: Role):
        """添加角色"""
        if role not in self.roles:
            self.roles.append(role)

    def remove_role(self, role: Role):
        """移除角色"""
        if role in self.roles:
            self.roles.remove(role)

    def has_role(self, role_name: str) -> bool:
        """检查是否有角色"""
        for role in self.roles:
            if role.name == role_name:
                return True
        return False

    def has_permission(self, permission_name: str) -> bool:
        """检查是否有权限"""
        for role in self.roles:
            if role.has_permission(permission_name):
                return True
        return False


class BaseUserStore(ABC):
    """
    用户存储后端抽象基类

    所有用户存储后端必须实现以下方法：
    - get_by_id(user_id): 根据 ID 获取用户
    - get_by_username(username): 根据用户名获取用户
    - create(username, password_hash, **kwargs): 创建用户
    - delete(user_id): 删除用户
    - list_all(): 获取所有用户
    """

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """根据 ID 获取用户"""
        raise NotImplementedError

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        raise NotImplementedError

    @abstractmethod
    def create(self, username: str, password_hash: str, email: str = None, roles: List[Role] = None) -> User:
        """创建用户"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """删除用户"""
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> List[User]:
        """获取所有用户"""
        raise NotImplementedError


class MemoryUserStore(BaseUserStore):
    """
    内存用户存储（默认后端）

    适合开发和测试环境。重启后数据丢失，多进程/多实例不共享。
    生产环境应使用数据库后端。
    """

    def __init__(self):
        self._users: Dict[int, User] = {}
        self._users_by_username: Dict[str, User] = {}
        self._next_id: int = 1
        self._lock = threading.Lock()

    def get_by_id(self, user_id: int) -> Optional[User]:
        with self._lock:
            return self._users.get(user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        with self._lock:
            return self._users_by_username.get(username)

    def create(self, username: str, password_hash: str, email: str = None, roles: List[Role] = None) -> User:
        with self._lock:
            user_id = self._next_id
            user = User(
                id=user_id,
                username=username,
                password_hash=password_hash,
                email=email,
                roles=roles or [],
            )
            self._users[user_id] = user
            self._users_by_username[username] = user
            self._next_id += 1
            return user

    def delete(self, user_id: int) -> bool:
        with self._lock:
            if user_id in self._users:
                user = self._users[user_id]
                del self._users[user_id]
                self._users_by_username.pop(user.username, None)
                return True
            return False

    def list_all(self) -> List[User]:
        with self._lock:
            return list(self._users.values())


# 全局默认存储实例
_default_store: Optional[BaseUserStore] = None
_default_store_lock = threading.Lock()


def get_user_store() -> BaseUserStore:
    """获取全局用户存储实例"""
    global _default_store
    with _default_store_lock:
        if _default_store is None:
            _default_store = MemoryUserStore()
        return _default_store


def set_user_store(store: BaseUserStore):
    """
    设置全局用户存储实例

    用于切换到数据库后端等持久化存储。

    Args:
        store: BaseUserStore 实例

    使用示例:
        from litefs.auth.models import set_user_store, BaseUserStore

        class DatabaseUserStore(BaseUserStore):
            def __init__(self, db_session):
                self.db = db_session
            # ... 实现抽象方法

        set_user_store(DatabaseUserStore(db_session))
    """
    global _default_store
    with _default_store_lock:
        _default_store = store


def init_default_roles_and_permissions():
    """初始化默认角色和权限"""

    Permission.create('user:read', '查看用户信息')
    Permission.create('user:write', '修改用户信息')
    Permission.create('user:delete', '删除用户')
    Permission.create('admin:access', '访问管理后台')
    Permission.create('admin:manage_users', '管理用户')

    user_role = Role.create('user', '普通用户', [
        Permission.get_by_name('user:read'),
    ])

    admin_role = Role.create('admin', '管理员', [
        Permission.get_by_name('user:read'),
        Permission.get_by_name('user:write'),
        Permission.get_by_name('user:delete'),
        Permission.get_by_name('admin:access'),
        Permission.get_by_name('admin:manage_users'),
    ])

    return user_role, admin_role
