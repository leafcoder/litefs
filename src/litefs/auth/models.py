#!/usr/bin/env python
# coding: utf-8

"""
用户模型

提供用户、角色和权限的基础模型。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class Permission:
    """权限"""
    name: str
    description: str = ''
    
    _permissions: Dict[str, 'Permission'] = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        if not hasattr(Permission, '_registry'):
            Permission._registry = {}
        Permission._registry[self.name] = self
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional['Permission']:
        """根据名称获取权限"""
        return cls._registry.get(name) if hasattr(cls, '_registry') else None
    
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
    
    _roles: Dict[str, 'Role'] = field(default_factory=dict, repr=False)
    
    def __post_init__(self):
        if not hasattr(Role, '_registry'):
            Role._registry = {}
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
        return cls._registry.get(name) if hasattr(cls, '_registry') else None
    
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
    
    _users: Dict[int, 'User'] = field(default_factory=dict, repr=False)
    _users_by_username: Dict[str, 'User'] = field(default_factory=dict, repr=False)
    _next_id: int = field(default=1, repr=False)
    
    def __post_init__(self):
        if not hasattr(User, '_registry'):
            User._registry = {}
            User._registry_by_username = {}
            User._next_id = 1
        
        User._registry[self.id] = self
        User._registry_by_username[self.username] = self
        
        if self.id >= User._next_id:
            User._next_id = self.id + 1
    
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
    
    @classmethod
    def get_by_id(cls, user_id: int) -> Optional['User']:
        """根据 ID 获取用户"""
        return cls._registry.get(user_id) if hasattr(cls, '_registry') else None
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """根据用户名获取用户"""
        return cls._registry_by_username.get(username) if hasattr(cls, '_registry_by_username') else None
    
    @classmethod
    def create(cls, username: str, password_hash: str, email: str = None, roles: List[Role] = None) -> 'User':
        """创建用户"""
        user_id = cls._next_id if hasattr(cls, '_next_id') else 1
        
        user = cls(
            id=user_id,
            username=username,
            password_hash=password_hash,
            email=email,
            roles=roles or [],
        )
        
        return user
    
    @classmethod
    def delete(cls, user_id: int) -> bool:
        """删除用户"""
        if user_id in cls._registry:
            user = cls._registry[user_id]
            del cls._registry[user_id]
            if user.username in cls._registry_by_username:
                del cls._registry_by_username[user.username]
            return True
        return False
    
    @classmethod
    def list_all(cls) -> List['User']:
        """获取所有用户"""
        return list(cls._registry.values()) if hasattr(cls, '_registry') else []


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
