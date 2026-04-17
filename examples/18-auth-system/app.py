#!/usr/bin/env python
# coding: utf-8

"""
认证授权系统示例

本示例展示如何使用 Litefs 的认证授权功能：
- 用户注册和登录
- JWT Token 认证
- 角色和权限控制
- 受保护的路由

测试步骤：
1. 注册用户: POST /auth/register
2. 登录获取 Token: POST /auth/login
3. 使用 Token 访问受保护路由
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, get, post
from litefs.auth import (
    Auth, login_required, role_required, permission_required,
    User, Role, Permission, hash_password, init_default_roles_and_permissions
)

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)

auth = Auth(
    app,
    secret_key='your-secret-key-change-in-production',
    access_token_expires=3600,
    refresh_token_expires=604800,
)

init_default_roles_and_permissions()

admin_role = Role.get_by_name('admin')
user_role = Role.get_by_name('user')

User.create(
    username='admin',
    password_hash=hash_password('admin123'),
    email='admin@example.com',
    roles=[admin_role],
)

User.create(
    username='user',
    password_hash=hash_password('user123'),
    email='user@example.com',
    roles=[user_role],
)


@get('/', name='index')
def index(request):
    """API 首页"""
    return {
        'message': '认证授权系统示例',
        'endpoints': {
            'auth': {
                'POST /auth/register': '用户注册',
                'POST /auth/login': '用户登录',
                'POST /auth/refresh': '刷新 Token',
                'POST /auth/logout': '用户登出',
            },
            'protected': {
                'GET /profile': '获取用户信息（需要登录）',
                'GET /admin': '管理员页面（需要 admin 角色）',
                'GET /users': '用户列表（需要 admin:manage_users 权限）',
            }
        },
        'test_accounts': {
            'admin': {'username': 'admin', 'password': 'admin123'},
            'user': {'username': 'user', 'password': 'user123'},
        }
    }


@get('/profile', name='profile')
@login_required
def profile(request):
    """用户信息（需要登录）"""
    user = request.user
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'roles': [r.name for r in user.roles],
        'permissions': list(set(
            perm.name for role in user.roles for perm in role.permissions
        ))
    }


@get('/admin', name='admin_panel')
@role_required('admin')
def admin_panel(request):
    """管理员页面（需要 admin 角色）"""
    return {
        'message': '欢迎来到管理后台',
        'user': request.user.username,
    }


@get('/users', name='list_users')
@permission_required('admin:manage_users')
def list_users(request):
    """用户列表（需要 admin:manage_users 权限）"""
    users = User.list_all()
    return {
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'roles': [r.name for r in u.roles],
            }
            for u in users
        ]
    }


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("认证授权系统示例")
    print("=" * 60)
    print()
    print("测试账号：")
    print("  管理员: admin / admin123")
    print("  普通用户: user / user123")
    print()
    print("API 端点：")
    print("  POST /auth/register  - 用户注册")
    print("  POST /auth/login     - 用户登录")
    print("  POST /auth/refresh   - 刷新 Token")
    print("  GET  /profile        - 用户信息（需要登录）")
    print("  GET  /admin          - 管理员页面（需要 admin 角色）")
    print("  GET  /users          - 用户列表（需要权限）")
    print()
    print("测试命令：")
    print("  # 登录")
    print("  curl -X POST http://localhost:8080/auth/login \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"username\": \"admin\", \"password\": \"admin123\"}'")
    print()
    print("  # 使用 Token 访问受保护路由")
    print("  curl http://localhost:8080/profile \\")
    print("       -H 'Authorization: Bearer <your-token>'")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
