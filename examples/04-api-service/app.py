#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RESTful API 服务示例

这个示例展示了如何使用 Litefs 构建一个完整的 RESTful API 服务，包括：
- 用户管理 API
- 文章管理 API
- 认证和授权
- 请求验证
- 分页和过滤
- 统一的 API 响应格式
"""

import sys
import os
import secrets
from datetime import datetime, timedelta

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))  # noqa: E402

from litefs import Litefs  # noqa: E402

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    session_backend='memory',
    session_expiration_time=3600
)

# ==================== 数据存储（模拟数据库）====================

# 用户数据
users_db = {
    1: {'id': 1, 'username': 'admin', 'email': 'admin@example.com', 'role': 'admin'},
    2: {'id': 2, 'username': 'john', 'email': 'john@example.com', 'role': 'user'},
    3: {'id': 3, 'username': 'jane', 'email': 'jane@example.com', 'role': 'user'},
}

# 用户密码（实际应用中应该使用哈希存储）
user_passwords = {
    'admin': 'admin123',
    'john': 'john123',
    'jane': 'jane123',
}

# 文章数据
posts_db = {
    1: {'id': 1, 'title': 'First Post', 'content': 'This is the first post', 'author_id': 1, 'created_at': '2024-01-01T10:00:00', 'updated_at': '2024-01-01T10:00:00'},
    2: {'id': 2, 'title': 'Second Post', 'content': 'This is the second post', 'author_id': 2, 'created_at': '2024-01-02T14:30:00', 'updated_at': '2024-01-02T14:30:00'},
    3: {'id': 3, 'title': 'Third Post', 'content': 'This is the third post', 'author_id': 1, 'created_at': '2024-01-03T09:15:00', 'updated_at': '2024-01-03T09:15:00'},
}

# API Token 存储
api_tokens = {}


# ==================== 辅助函数 ====================

def json_response(data, status=200):
    """返回统一的 JSON 响应"""
    response = {
        'success': status < 400,
        'data': data if status < 400 else None,
        'error': data if status >= 400 else None,
        'timestamp': datetime.now().isoformat()
    }
    return response


def require_auth(request):
    """验证用户是否已登录"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # 检查 session
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id and user_id in users_db:
            return users_db[user_id]
    
    # 检查 API token
    if token and token in api_tokens:
        user_id = api_tokens[token]['user_id']
        if user_id in users_db:
            return users_db[user_id]
    
    return None


def require_admin(request):
    """验证用户是否为管理员"""
    user = require_auth(request)
    if user and user['role'] == 'admin':
        return user
    return None


# ==================== API 路由 ====================

# 首页/API 文档
@app.add_get('/', name='api_docs')
def api_docs_handler(request):
    """API 文档"""
    return json_response({
        'name': 'Litefs API Service',
        'version': '1.0.0',
        'description': 'A RESTful API service built with Litefs',
        'endpoints': {
            'auth': {
                'POST /api/auth/login': '用户登录',
                'POST /api/auth/logout': '用户登出',
                'GET /api/auth/me': '获取当前用户信息',
            },
            'users': {
                'GET /api/users': '获取用户列表（管理员）',
                'GET /api/users/{id}': '获取用户详情',
                'POST /api/users': '创建用户（管理员）',
                'PUT /api/users/{id}': '更新用户',
                'DELETE /api/users/{id}': '删除用户（管理员）',
            },
            'posts': {
                'GET /api/posts': '获取文章列表',
                'GET /api/posts/{id}': '获取文章详情',
                'POST /api/posts': '创建文章',
                'PUT /api/posts/{id}': '更新文章',
                'DELETE /api/posts/{id}': '删除文章',
            }
        },
        'authentication': {
            'type': 'Bearer Token',
            'header': 'Authorization: Bearer <token>',
            'alternative': 'Session Cookie'
        }
    })


# ==================== 认证 API ====================

@app.add_post('/api/auth/login', name='login')
def login_handler(request):
    """用户登录"""
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    
    if not username or not password:
        request.start_response(400, [('Content-Type', 'application/json')])
        return json_response('Username and password are required', 400)
    
    # 验证密码
    if username not in user_passwords or user_passwords[username] != password:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Invalid username or password', 401)
    
    # 查找用户
    user = next((u for u in users_db.values() if u['username'] == username), None)
    if not user:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('User not found', 401)
    
    # 生成 API token
    token = secrets.token_urlsafe(32)
    api_tokens[token] = {
        'user_id': user['id'],
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
    }
    
    # 设置 session
    if hasattr(request, 'session'):
        request.session['user_id'] = user['id']
        request.session['username'] = user['username']
    
    return json_response({
        'token': token,
        'user': user,
        'expires_at': api_tokens[token]['expires_at']
    })


@app.add_post('/api/auth/logout', name='logout')
def logout_handler(request):
    """用户登出"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # 删除 token
    if token in api_tokens:
        del api_tokens[token]
    
    # 清除 session
    if hasattr(request, 'session'):
        request.session.clear()
    
    return json_response({'message': 'Logged out successfully'})


@app.add_get('/api/auth/me', name='current_user')
def current_user_handler(request):
    """获取当前用户信息"""
    user = require_auth(request)
    
    if not user:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Authentication required', 401)
    
    return json_response(user)


# ==================== 用户 API ====================

@app.add_get('/api/users', name='user_list')
def user_list_handler(request):
    """获取用户列表（仅管理员）"""
    # 验证管理员权限
    if not require_admin(request):
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Admin access required', 403)
    
    # 分页参数
    page = int(request.params.get('page', 1))
    limit = int(request.params.get('limit', 10))
    
    # 获取用户列表
    users = list(users_db.values())
    total = len(users)
    
    # 分页
    start = (page - 1) * limit
    end = start + limit
    users = users[start:end]
    
    return json_response({
        'users': users,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit
        }
    })


@app.add_get('/api/users/{id}', name='user_detail')
def user_detail_handler(request, id):
    """获取用户详情"""
    user_id = int(id)
    
    # 验证权限（只能查看自己或管理员查看所有人）
    current = require_auth(request)
    if not current:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Authentication required', 401)
    
    if current['id'] != user_id and current['role'] != 'admin':
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Access denied', 403)
    
    user = users_db.get(user_id)
    if not user:
        request.start_response(404, [('Content-Type', 'application/json')])
        return json_response(f'User {id} not found', 404)
    
    return json_response(user)


@app.add_post('/api/users', name='create_user')
def create_user_handler(request):
    """创建用户（仅管理员）"""
    # 验证管理员权限
    if not require_admin(request):
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Admin access required', 403)
    
    username = request.data.get('username', '')
    email = request.data.get('email', '')
    password = request.data.get('password', '')
    role = request.data.get('role', 'user')
    
    # 验证必填字段
    if not username or not email or not password:
        request.start_response(400, [('Content-Type', 'application/json')])
        return json_response('Username, email and password are required', 400)
    
    # 检查用户名是否已存在
    if any(u['username'] == username for u in users_db.values()):
        request.start_response(400, [('Content-Type', 'application/json')])
        return json_response('Username already exists', 400)
    
    # 创建用户
    new_id = max(users_db.keys()) + 1 if users_db else 1
    new_user = {
        'id': new_id,
        'username': username,
        'email': email,
        'role': role
    }
    users_db[new_id] = new_user
    user_passwords[username] = password
    
    return json_response(new_user)


@app.add_put('/api/users/{id}', name='update_user')
def update_user_handler(request, id):
    """更新用户"""
    user_id = int(id)
    
    # 验证权限
    current = require_auth(request)
    if not current:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Authentication required', 401)
    
    if current['id'] != user_id and current['role'] != 'admin':
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Access denied', 403)
    
    user = users_db.get(user_id)
    if not user:
        request.start_response(404, [('Content-Type', 'application/json')])
        return json_response(f'User {id} not found', 404)
    
    # 更新字段
    if 'email' in request.data:
        user['email'] = request.data['email']
    
    # 只有管理员可以修改角色
    if 'role' in request.data and current['role'] == 'admin':
        user['role'] = request.data['role']
    
    return json_response(user)


@app.add_delete('/api/users/{id}', name='delete_user')
def delete_user_handler(request, id):
    """删除用户（仅管理员）"""
    # 验证管理员权限
    if not require_admin(request):
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Admin access required', 403)
    
    user_id = int(id)
    user = users_db.get(user_id)
    
    if not user:
        request.start_response(404, [('Content-Type', 'application/json')])
        return json_response(f'User {id} not found', 404)
    
    # 删除用户
    del users_db[user_id]
    if user['username'] in user_passwords:
        del user_passwords[user['username']]
    
    return json_response({'message': f'User {id} deleted successfully'})


# ==================== 文章 API ====================

@app.add_get('/api/posts', name='post_list')
def post_list_handler(request):
    """获取文章列表"""
    # 分页参数
    page = int(request.params.get('page', 1))
    limit = int(request.params.get('limit', 10))
    author_id = request.params.get('author_id')
    
    # 过滤文章
    posts = list(posts_db.values())
    if author_id:
        posts = [p for p in posts if p['author_id'] == int(author_id)]
    
    total = len(posts)
    
    # 分页
    start = (page - 1) * limit
    end = start + limit
    posts = posts[start:end]
    
    # 添加作者信息
    for post in posts:
        author = users_db.get(post['author_id'])
        post['author'] = author['username'] if author else 'Unknown'
    
    return json_response({
        'posts': posts,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit
        }
    })


@app.add_get('/api/posts/{id}', name='post_detail')
def post_detail_handler(request, id):
    """获取文章详情"""
    post_id = int(id)
    post = posts_db.get(post_id)
    
    if not post:
        request.start_response(404, [('Content-Type', 'application/json')])
        return json_response(f'Post {id} not found', 404)
    
    # 添加作者信息
    author = users_db.get(post['author_id'])
    post['author'] = author['username'] if author else 'Unknown'
    
    return json_response(post)


@app.add_post('/api/posts', name='create_post')
def create_post_handler(request):
    """创建文章"""
    # 验证登录
    user = require_auth(request)
    if not user:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Authentication required', 401)
    
    title = request.data.get('title', '')
    content = request.data.get('content', '')
    
    if not title or not content:
        request.start_response(400, [('Content-Type', 'application/json')])
        return json_response('Title and content are required', 400)
    
    # 创建文章
    new_id = max(posts_db.keys()) + 1 if posts_db else 1
    now = datetime.now().isoformat()
    new_post = {
        'id': new_id,
        'title': title,
        'content': content,
        'author_id': user['id'],
        'created_at': now,
        'updated_at': now
    }
    posts_db[new_id] = new_post
    
    return json_response(new_post)


@app.add_put('/api/posts/{id}', name='update_post')
def update_post_handler(request, id):
    """更新文章"""
    post_id = int(id)
    
    # 验证登录
    user = require_auth(request)
    if not user:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Authentication required', 401)
    
    post = posts_db.get(post_id)
    if not post:
        request.start_response(404, [('Content-Type', 'application/json')])
        return json_response(f'Post {id} not found', 404)
    
    # 验证权限（只能修改自己的文章，管理员可以修改所有）
    if post['author_id'] != user['id'] and user['role'] != 'admin':
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Access denied', 403)
    
    # 更新字段
    if 'title' in request.data:
        post['title'] = request.data['title']
    if 'content' in request.data:
        post['content'] = request.data['content']
    post['updated_at'] = datetime.now().isoformat()
    
    return json_response(post)


@app.add_delete('/api/posts/{id}', name='delete_post')
def delete_post_handler(request, id):
    """删除文章"""
    post_id = int(id)
    
    # 验证登录
    user = require_auth(request)
    if not user:
        request.start_response(401, [('Content-Type', 'application/json')])
        return json_response('Authentication required', 401)
    
    post = posts_db.get(post_id)
    if not post:
        request.start_response(404, [('Content-Type', 'application/json')])
        return json_response(f'Post {id} not found', 404)
    
    # 验证权限（只能删除自己的文章，管理员可以删除所有）
    if post['author_id'] != user['id'] and user['role'] != 'admin':
        request.start_response(403, [('Content-Type', 'application/json')])
        return json_response('Access denied', 403)
    
    del posts_db[post_id]
    
    return json_response({'message': f'Post {id} deleted successfully'})


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs RESTful API Service")
    print("=" * 60)
    print("访问地址: http://localhost:8080")
    print("=" * 60)
    print("默认账号:")
    print("  admin / admin123 (管理员)")
    print("  john  / john123  (普通用户)")
    print("  jane  / jane123  (普通用户)")
    print("=" * 60)
    print("API 文档: http://localhost:8080/")
    print("=" * 60)
    
    app.run()
