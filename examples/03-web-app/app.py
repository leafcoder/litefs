#!/usr/bin/env python
# coding: utf-8

"""
Litefs 博客系统

完整的博客系统示例，展示：
- 用户注册与登录
- OAuth2 社交登录（GitHub、Google）
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

from litefs.core import Litefs
from litefs.handlers import Response
from litefs.routing import get, post
from litefs.middleware.csrf import CSRFMiddleware
from litefs.middleware.logging import LoggingMiddleware
from litefs.auth import OAuth2, OAuth2UserInfo

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

oauth = OAuth2(app)

GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID', '')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET', '')

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    oauth.register(
        name='github',
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
        redirect_uri='http://localhost:8083/auth/github/callback',
        scope='user:email'
    )

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri='http://localhost:8083/auth/google/callback',
        scope='openid email profile'
    )


def generate_token(user_id: int, username: str) -> str:
    """生成登录令牌"""
    data = f"{user_id}:{username}:{time.time()}:{SECRET_KEY}"
    return hashlib.sha256(data.encode()).hexdigest()


def verify_token(token: str) -> dict:
    """验证令牌（简化版，生产环境应使用 JWT）"""
    return {'valid': bool(token), 'user_id': 1}


def get_current_user(request) -> dict:
    """获取当前登录用户"""
    try:
        session = request.cookie.get('session') if request.cookie else None
        if not session:
            return None
        
        token = session.value if hasattr(session, 'value') else None
        if not token:
            return None
        
        parts = token.split(':')
        if len(parts) < 2:
            return None
        
        user_id = int(parts[0])
        user = db.get_user(user_id)
        if not user:
            return None
        return user
    except Exception as e:
        print(f"get_current_user exception: {e}")
        return None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated(request, *args, **kwargs):
        try:
            user = get_current_user(request)
        except Exception as e:
            print(f"get_current_user error: {e}")
            user = None
        
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
    
    user_dict = user.to_dict() if user and hasattr(user, 'to_dict') else None
    
    return request.render_template('index.html',
        posts=[p.to_dict() for p in posts],
        stats=stats,
        categories=categories,
        current_category=category,
        page=page,
        user=user_dict
    )


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
    if not user or not hasattr(user, 'id'):
        return Response.redirect('/login')
    
    user_posts = [p.to_dict() for p in db.posts.values() if p.author_id == user.id]
    user_posts.sort(key=lambda x: x['created_at'], reverse=True)
    
    # 计算统计
    total_views = sum(p.get('views', 0) for p in user_posts)
    total_likes = sum(p.get('likes', 0) for p in user_posts)
    
    user_dict = user.to_dict() if hasattr(user, 'to_dict') else user
    return request.render_template('profile.html',
        title='用户中心',
        user=user_dict,
        posts=user_posts[:10],
        post_count=len(user_posts),
        total_views=total_views,
        total_likes=total_likes
    )


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
        'title': '编辑文章' if post else '写新文章',
        'post_id': post.id if post else None,
        'post_title': post.title if post else '',
        'post_content': post.content if post else '',
        'post_summary': post.summary if post else '',
        'post_category': post.category if post else '默认',
        'post_status': post.status if post else 'published',
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


# ==================== OAuth2 路由 ====================

@get('/auth/github', name='auth_github')
def auth_github(request):
    """GitHub OAuth 登录"""
    if not oauth.get_provider('github'):
        return Response.json({'error': 'GitHub OAuth 未配置'}, status_code=400)
    return oauth.authorize_redirect(request, 'github')


@get('/auth/github/callback', name='auth_github_callback')
def auth_github_callback(request):
    """GitHub OAuth 回调"""
    user_info = oauth.authorize_user(request, 'github')
    if not user_info:
        return Response.redirect('/login?error=oauth_failed')
    
    user = db.get_user_by_oauth('github', user_info.provider_user_id)
    
    if not user:
        user = db.create_oauth_user(
            provider='github',
            oauth_user_id=user_info.provider_user_id,
            username=user_info.username,
            email=user_info.email or '',
            nickname=user_info.name or user_info.username,
            avatar=user_info.avatar_url or ''
        )
    
    token = f"{user.id}:{user.username}:{generate_token(user.id, user.username)}"
    
    response = Response.redirect('/profile')
    response.set_cookie('session', token, max_age=7 * 24 * 3600, httponly=True)
    return response


@get('/auth/google', name='auth_google')
def auth_google(request):
    """Google OAuth 登录"""
    if not oauth.get_provider('google'):
        return Response.json({'error': 'Google OAuth 未配置'}, status_code=400)
    return oauth.authorize_redirect(request, 'google')


@get('/auth/google/callback', name='auth_google_callback')
def auth_google_callback(request):
    """Google OAuth 回调"""
    user_info = oauth.authorize_user(request, 'google')
    if not user_info:
        return Response.redirect('/login?error=oauth_failed')
    
    user = db.get_user_by_oauth('google', user_info.provider_user_id)
    
    if not user:
        user = db.create_oauth_user(
            provider='google',
            oauth_user_id=user_info.provider_user_id,
            username=user_info.username,
            email=user_info.email or '',
            nickname=user_info.name or user_info.username,
            avatar=user_info.avatar_url or ''
        )
    
    token = f"{user.id}:{user.username}:{generate_token(user.id, user.username)}"
    
    response = Response.redirect('/profile')
    response.set_cookie('session', token, max_age=7 * 24 * 3600, httponly=True)
    return response


@get('/auth/link/github', name='auth_link_github')
@login_required
def auth_link_github(request, user):
    """关联 GitHub 账号"""
    if not oauth.get_provider('github'):
        return Response.json({'error': 'GitHub OAuth 未配置'}, status_code=400)
    
    request._oauth_link_user_id = user.id
    return oauth.authorize_redirect(request, 'github', callback_url='/auth/link/github/callback')


@get('/auth/link/github/callback', name='auth_link_github_callback')
@login_required
def auth_link_github_callback(request, user):
    """关联 GitHub 账号回调"""
    user_info = oauth.authorize_user(request, 'github')
    if not user_info:
        return Response.redirect('/settings?error=link_failed')
    
    existing_user = db.get_user_by_oauth('github', user_info.provider_user_id)
    if existing_user and existing_user.id != user.id:
        return Response.redirect('/settings?error=already_linked')
    
    db.link_oauth(user.id, 'github', user_info.provider_user_id)
    
    if user_info.avatar_url and not user.avatar:
        db.update_user(user.id, avatar=user_info.avatar_url)
    
    return Response.redirect('/settings?success=github_linked')


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 博客系统")
    print("=" * 60)
    print()
    print("功能:")
    print("  - 用户注册与登录")
    print("  - OAuth2 社交登录 (GitHub/Google)")
    print("  - 密码管理")
    print("  - 文章发布与管理")
    print("  - 访问统计")
    print()
    print("默认管理员: admin / admin123")
    print("访问地址: http://localhost:8083")
    print()
    print("OAuth2 配置:")
    if GITHUB_CLIENT_ID:
        print("  - GitHub: 已配置")
    else:
        print("  - GitHub: 未配置 (设置 GITHUB_CLIENT_ID 和 GITHUB_CLIENT_SECRET)")
    if GOOGLE_CLIENT_ID:
        print("  - Google: 已配置")
    else:
        print("  - Google: 未配置 (设置 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET)")
    print("=" * 60)
    
    app.run()
