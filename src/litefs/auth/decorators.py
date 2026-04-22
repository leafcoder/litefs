#!/usr/bin/env python
# coding: utf-8

"""
权限装饰器

提供权限验证和用户信息获取的装饰器。
"""

import functools
from typing import Callable, Optional


def permission_required(*permissions: str) -> Callable:
    """
    权限验证装饰器

    Args:
        *permissions: 需要的权限列表

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or request.user is None:
                from ..exceptions import Unauthorized
                raise Unauthorized(message='Authentication required')

            user_permissions = set()

            roles = getattr(request.user, 'roles', [])
            for role in roles:
                role_perms = getattr(role, 'permissions', [])
                for perm in role_perms:
                    perm_name = perm.name if hasattr(perm, 'name') else str(perm)
                    user_permissions.add(perm_name)

            for perm in permissions:
                if perm not in user_permissions:
                    from ..exceptions import Forbidden
                    raise Forbidden(message='Insufficient permissions')

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def current_user(func: Callable) -> Callable:
    """
    当前用户装饰器

    将当前用户作为第一个参数传递给处理函数。

    Args:
        func: 处理函数

    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        user = getattr(request, 'user', None)
        return func(user, request, *args, **kwargs)
    return wrapper


def admin_required(func: Callable) -> Callable:
    """
    管理员权限装饰器

    Args:
        func: 处理函数

    Returns:
        装饰后的函数
    """
    from .middleware import role_required
    return role_required('admin')(func)


def owner_or_admin_required(get_owner_id: Callable) -> Callable:
    """
    所有者或管理员权限装饰器

    Args:
        get_owner_id: 获取所有者 ID 的函数

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or request.user is None:
                from ..exceptions import Unauthorized
                raise Unauthorized(message='Authentication required')

            user = request.user
            user_roles = getattr(user, 'roles', [])
            user_role_names = [r.name if hasattr(r, 'name') else str(r) for r in user_roles]

            if 'admin' in user_role_names:
                return func(request, *args, **kwargs)

            owner_id = get_owner_id(request, *args, **kwargs)

            if str(user.id) == str(owner_id):
                return func(request, *args, **kwargs)

            from ..exceptions import Forbidden
            raise Forbidden(message='Insufficient permissions')
        return wrapper
    return decorator
