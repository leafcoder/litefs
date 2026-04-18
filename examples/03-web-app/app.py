#!/usr/bin/env python
# coding: utf-8

"""
Litefs 博客系统

完整的博客系统示例，展示：
- 用户注册与登录
- 密码管理
- 文章发布与管理
- 评论系统
- 访问统计
"""

import sys
import os
import json
import hashlib
import time
from datetime import datetime
from functools import wraps

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs, Response
from litefs.routing import get, post
from litefs.middleware.csrf import CSRFMiddleware
from litefs.middleware.logging import LoggingMiddleware

from models import db
from urllib.parse import parse_qs


def get_query_params(request) -> dict:
    """获取查询参数"""
    query_string = request.query_string if hasattr(request, 'query_string') else ''
    if not query_string:
        return {}
    params = parse_qs(query_string)
    return {k: v[0] if len(v) == 1 else v for k, v in params.items()}


APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Litefs(
    host='0.0.0.0',
    port=8083,
    debug=True,
    secret_key='blog-secret-key-change-in-production'
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))
app.add_middleware(CSRFMiddleware)
app.add_middleware(LoggingMiddleware)

SECRET_KEY = 'blog-secret-key-change-in-production'


def generate_token(user_id: int, username: str) -> str:
    """生成登录令牌"""
    data = f"{user_id}:{username}:{time.time()}:{SECRET_KEY}"
    return hashlib.sha256(data.encode()).hexdigest()


def verify_token(token: str) -> dict:
    """验证令牌（简化版，生产环境应使用 JWT）"""
    return {'valid': bool(token), 'user_id': 1}


def get_current_user(request) -> dict:
    """获取当前登录用户"""
    session = request.cookie.get('session') if request.cookie else None
    if not session:
        return None
    
    token = session.value if hasattr(session, 'value') else None
    if not token:
        return None
    
    parts = token.split(':')
    if len(parts) < 2:
        return None
    
    try:
        user_id = int(parts[0])
        return db.get_user(user_id)
    except (ValueError, TypeError):
        return None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return Response.json({'error': '请先登录'}, status_code=401)
            return Response.redirect('/login')
        return f(request, user, *args, **kwargs)
    return decorated


def admin_required(f):
    """管理员验证装饰器"""
    @wraps(f)
    def decorated(request, *args, **kwargs):
        user = get_current_user(request)
        if not user or not user.is_admin:
            return Response.json({'error': '需要管理员权限'}, status_code=403)
        return f(request, user, *args, **kwargs)
    return decorated


# ==================== 页面路由 ====================

@get('/', name='index')
def index(request):
    """首页"""
    query = get_query_params(request)
    page = int(query.get('page', 1))
    category = query.get('category')
    
    posts = db.get_posts(page=page, per_page=10, category=category)
    stats = db.get_stats()
    user = get_current_user(request)
    
    categories = list(set(p.category for p in db.posts.values()))
    
    return request.render_template('index.html', **{
        'posts': [p.to_dict() for p in posts],
        'stats': stats,
        'categories': categories,
        'current_category': category,
        'page': page,
        'user': user.to_dict() if user else None
    })


@get('/post/{id}', name='post_detail')
def post_detail(request, id):
    """文章详情"""
    post = db.get_post(int(id))
    if not post:
        return Response.json({'error': '文章不存在'}, status_code=404)
    
    db.increment_views(int(id))
    
    user = get_current_user(request)
    author = db.get_user(post.author_id)
    
    return request.render_template('post_detail.html', **{
        'post': post.to_dict(),
        'author': author.to_dict() if author else None,
        'user': user.to_dict() if user else None
    })


@get('/login', name='login')
def login_page(request):
    """登录页面"""
    user = get_current_user(request)
    if user:
        return Response.redirect('/')
    
    return request.render_template('login.html', **{
        'user': None
    })


@get('/register', name='register')
def register_page(request):
    """注册页面"""
    user = get_current_user(request)
    if user:
        return Response.redirect('/')
    
    return request.render_template('register.html', **{
        'user': None
    })


@get('/profile', name='profile')
@login_required
def profile_page(request, user):
    """用户中心"""
    user_posts = [p.to_dict() for p in db.posts.values() if p.author_id == user.id]
    user_posts.sort(key=lambda x: x['created_at'], reverse=True)
    
    return request.render_template('profile.html', **{
        'user': user.to_dict(),
        'posts': user_posts[:10],
        'post_count': len(user_posts)
    })


@get('/settings', name='settings')
@login_required
def settings_page(request, user):
    """设置页面"""
    return request.render_template('settings.html', **{
        'user': user.to_dict()
    })


@get('/admin', name='admin')
@login_required
def admin_page(request, user):
    """管理后台"""
    if not user.is_admin:
        return Response.json({'error': '需要管理员权限'}, status_code=403)
    
    stats = db.get_stats()
    recent_posts = db.get_posts(page=1, per_page=10, status=None)
    users = list(db.users.values())
    
    return request.render_template('admin.html', **{
        'user': user.to_dict(),
        'stats': stats,
        'recent_posts': [p.to_dict() for p in recent_posts],
        'users': [u.to_dict() for u in users]
    })


@get('/editor', name='editor')
@login_required
def editor_page(request, user):
    """文章编辑器"""
    query = get_query_params(request)
    post_id = query.get('id')
    post = None
    if post_id:
        post = db.get_post(int(post_id))
        if post and post.author_id != user.id and not user.is_admin:
            return Response.json({'error': '无权限'}, status_code=403)
    
    return request.render_template('editor.html', **{
        'user': user.to_dict(),
        'post': post.to_dict() if post else None
    })


# ==================== API 路由 ====================

@post('/api/register', name='api_register')
def api_register(request):
    """用户注册"""
    data = request.json if hasattr(request, 'json') else {}
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    email = data.get('email', '').strip()
    nickname = data.get('nickname', '').strip() or username
    
    if not username or not password:
        return Response.json({'error': '用户名和密码不能为空'}, status_code=400)
    
    if len(username) < 3:
        return Response.json({'error': '用户名至少3个字符'}, status_code=400)
    
    if len(password) < 6:
        return Response.json({'error': '密码至少6个字符'}, status_code=400)
    
    user = db.create_user(username, password, email, nickname)
    if not user:
        return Response.json({'error': '用户名已存在'}, status_code=400)
    
    return Response.json({
        'success': True,
        'message': '注册成功',
        'user': {'id': user.id, 'username': user.username, 'nickname': user.nickname}
    })


@post('/api/login', name='api_login')
def api_login(request):
    """用户登录"""
    data = request.json if hasattr(request, 'json') else {}
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    user = db.verify_user(username, password)
    if not user:
        return Response.json({'error': '用户名或密码错误'}, status_code=401)
    
    token = f"{user.id}:{user.username}:{generate_token(user.id, user.username)}"
    
    response = Response.json({
        'success': True,
        'message': '登录成功',
        'user': {'id': user.id, 'username': user.username, 'nickname': user.nickname, 'is_admin': user.is_admin}
    })
    
    response.set_cookie('session', token, max_age=7 * 24 * 3600, httponly=True)
    return response


@post('/api/logout', name='api_logout')
def api_logout(request):
    """用户登出"""
    response = Response.json({'success': True, 'message': '已登出'})
    response.delete_cookie('session')
    return response


@post('/api/password', name='api_password')
@login_required
def api_change_password(request, user):
    """修改密码"""
    data = request.json if hasattr(request, 'json') else {}
    
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    
    if not old_password or not new_password:
        return Response.json({'error': '请填写完整'}, status_code=400)
    
    if len(new_password) < 6:
        return Response.json({'error': '新密码至少6个字符'}, status_code=400)
    
    from models import verify_password
    if not verify_password(old_password, user.password_hash, user.password_salt):
        return Response.json({'error': '原密码错误'}, status_code=400)
    
    db.update_password(user.id, new_password)
    return Response.json({'success': True, 'message': '密码修改成功'})


@post('/api/profile', name='api_profile')
@login_required
def api_update_profile(request, user):
    """更新资料"""
    data = request.json if hasattr(request, 'json') else {}
    
    nickname = data.get('nickname', '').strip()
    email = data.get('email', '').strip()
    bio = data.get('bio', '').strip()
    
    updated_user = db.update_user(user.id, nickname=nickname, email=email, bio=bio)
    
    return Response.json({
        'success': True,
        'message': '资料更新成功',
        'user': updated_user.to_dict()
    })


@get('/api/user', name='api_user')
def api_get_user(request):
    """获取当前用户"""
    user = get_current_user(request)
    if user:
        return Response.json({'user': user.to_dict()})
    return Response.json({'user': None})


@post('/api/posts', name='api_create_post')
@login_required
def api_create_post(request, user):
    """创建文章"""
    data = request.json if hasattr(request, 'json') else {}
    
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    category = data.get('category', '默认').strip()
    summary = data.get('summary', '').strip()
    tags = data.get('tags', [])
    
    if not title or not content:
        return Response.json({'error': '标题和内容不能为空'}, status_code=400)
    
    post = db.create_post(
        title=title,
        content=content,
        author_id=user.id,
        author_name=user.nickname or user.username,
        category=category,
        tags=tags,
        summary=summary
    )
    
    return Response.json({
        'success': True,
        'message': '文章发布成功',
        'post': post.to_dict()
    })


@post('/api/posts/{id}', name='api_update_post')
@login_required
def api_update_post(request, user, id):
    """更新文章"""
    post = db.get_post(int(id))
    if not post:
        return Response.json({'error': '文章不存在'}, status_code=404)
    
    if post.author_id != user.id and not user.is_admin:
        return Response.json({'error': '无权限'}, status_code=403)
    
    data = request.json if hasattr(request, 'json') else {}
    
    updated_post = db.update_post(int(id), **{
        'title': data.get('title', post.title),
        'content': data.get('content', post.content),
        'category': data.get('category', post.category),
        'summary': data.get('summary', post.summary),
        'tags': data.get('tags', post.tags),
        'status': data.get('status', post.status)
    })
    
    return Response.json({
        'success': True,
        'message': '文章更新成功',
        'post': updated_post.to_dict()
    })


@post('/api/posts/{id}/delete', name='api_delete_post')
@login_required
def api_delete_post(request, user, id):
    """删除文章"""
    post = db.get_post(int(id))
    if not post:
        return Response.json({'error': '文章不存在'}, status_code=404)
    
    if post.author_id != user.id and not user.is_admin:
        return Response.json({'error': '无权限'}, status_code=403)
    
    db.delete_post(int(id))
    return Response.json({'success': True, 'message': '文章已删除'})


@get('/api/stats', name='api_stats')
def api_stats(request):
    """获取统计数据"""
    return Response.json(db.get_stats())


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 博客系统")
    print("=" * 60)
    print()
    print("功能:")
    print("  - 用户注册与登录")
    print("  - 密码管理")
    print("  - 文章发布与管理")
    print("  - 访问统计")
    print()
    print("默认管理员: admin / admin123")
    print("访问地址: http://localhost:8083")
    print("=" * 60)
    
    app.run()
