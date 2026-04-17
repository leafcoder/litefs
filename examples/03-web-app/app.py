#!/usr/bin/env python
# coding: utf-8

"""
Web 应用示例

展示 Litefs 的 Web 开发特性：
- 模板渲染
- 表单处理
- CSRF 保护
- 缓存系统
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get, post
from litefs.cache import MemoryCache
from litefs.middleware.csrf import CSRFMiddleware

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)

app.add_static('/static', 'static')

app.add_middleware(CSRFMiddleware)

cache = MemoryCache()


POSTS = [
    {'id': 1, 'title': '第一篇文章', 'content': '这是文章内容', 'created_at': '2024-01-01'},
    {'id': 2, 'title': '第二篇文章', 'content': '更多内容', 'created_at': '2024-01-02'},
]


@get('/', name='index')
def index(request):
    """首页 - 文章列表"""
    posts = cache.get('posts')
    if posts is None:
        posts = POSTS
        cache.put('posts', posts)

    return request.render_template('index.html', **{
        'title': '博客首页',
        'posts': posts,
    })


@get('/post/{id}', name='post_detail')
def post_detail(request, id):
    """文章详情"""
    post_id = int(id)
    post = next((p for p in POSTS if p['id'] == post_id), None)

    if not post:
        return {'error': '文章不存在'}, 404

    return request.render_template('post.html', **{
        'title': post['title'],
        'post': post,
    })


@get('/login', name='login_form')
def login_form(request):
    """登录表单"""
    return request.render_template('login.html', **{
        'title': '登录',
    })


@post('/login', name='login')
def login(request):
    """登录处理"""
    data = request.json if hasattr(request, 'json') else {}
    username = data.get('username', '')
    password = data.get('password', '')

    if username == 'admin' and password == 'admin123':
        return {'status': 'success', 'message': '登录成功'}

    return {'status': 'error', 'message': '用户名或密码错误'}, 401


@get('/logout', name='logout')
def logout(request):
    """登出"""
    return {'status': 'success', 'message': '已登出'}


@get('/profile', name='profile')
def profile(request):
    """用户中心"""
    return request.render_template('profile.html', **{
        'title': '用户中心',
        'user': {'username': 'guest'},
    })


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs Web 应用示例")
    print("=" * 60)
    print()
    print("展示特性:")
    print("  - 模板渲染")
    print("  - 表单处理")
    print("  - CSRF 保护")
    print("  - 缓存系统")
    print()
    print("测试账号: admin / admin123")
    print("访问地址: http://localhost:8080")
    print("=" * 60)

    app.run()
