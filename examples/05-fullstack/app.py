#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全栈应用示例 - 综合展示 Litefs 所有功能

这个示例是一个完整的 Web 应用，综合展示了 Litefs 的所有核心功能：
- 现代路由系统（装饰器 + 方法链）
- 会话管理（用户认证）
- 缓存使用（内存缓存）
- 中间件集成（日志、安全、CORS、限流）
- 静态文件服务
- 表单处理
- 错误处理
- 健康检查
"""

import sys
import os
import json
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.routing import get, post
from litefs.middleware import (
    LoggingMiddleware,
    SecurityMiddleware,
    CORSMiddleware,
    RateLimitMiddleware,
    HealthCheck
)
from litefs.cache import MemoryCache

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    log='./app.log',
    session_backend='memory',
    session_expiration_time=3600,
    cache_backend='memory',
    max_request_size=20971520,
    max_upload_size=52428800
)

# 初始化缓存
cache = MemoryCache(max_size=10000)

# 挂载静态文件
app.add_static('/static', 'static')

# ==================== 数据存储 ====================

# 用户数据
users_db = {
    1: {'id': 1, 'username': 'admin', 'name': 'Administrator', 'role': 'admin'},
    2: {'id': 2, 'username': 'user1', 'name': 'User One', 'role': 'user'},
}

user_passwords = {
    'admin': 'admin123',
    'user1': 'user123',
}

# 文章数据
posts_db = [
    {'id': 1, 'title': 'Litefs 入门指南', 'content': 'Litefs 是一个轻量级的 Python Web 框架...', 'author_id': 1, 'created_at': '2024-01-01'},
    {'id': 2, 'title': 'Web 开发最佳实践', 'content': '构建高质量的 Web 应用需要注意...', 'author_id': 1, 'created_at': '2024-01-02'},
    {'id': 3, 'title': 'Python 性能优化', 'content': '优化 Python 应用的几个技巧...', 'author_id': 2, 'created_at': '2024-01-03'},
]

# 访问统计
visit_stats = {
    'total_visits': 0,
    'unique_visitors': set(),
    'page_views': {}
}


# ==================== HTML 渲染辅助函数 ====================

def render_page(content, title='Litefs Fullstack', user=None):
    """渲染完整页面"""
    user_section = ''
    if user:
        user_section = f'''
        <div class="user-menu">
            <span>欢迎, {user['name']}</span>
            <a href="/dashboard">控制台</a>
            <a href="/logout">退出</a>
        </div>
        '''
    else:
        user_section = '<div class="user-menu"><a href="/login">登录</a></div>'
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <header>
        <nav class="navbar">
            <div class="container">
                <a href="/" class="logo">Litefs Fullstack</a>
                <div class="nav-links">
                    <a href="/">首页</a>
                    <a href="/posts">文章</a>
                    <a href="/about">关于</a>
                    <a href="/api/docs">API</a>
                </div>
                {user_section}
            </div>
        </nav>
    </header>
    <main class="container">
        {content}
    </main>
    <footer>
        <div class="container">
            <p>&copy; 2024 Litefs Fullstack Demo. Built with Litefs Framework.</p>
        </div>
    </footer>
    <script src="/static/js/app.js"></script>
</body>
</html>'''


# ==================== 路由定义 ====================

# 首页
@app.add_get('/', name='home')
def home_handler(request):
    """首页"""
    # 统计访问
    visit_stats['total_visits'] += 1
    
    # 获取最新文章
    latest_posts = sorted(posts_db, key=lambda x: x['created_at'], reverse=True)[:3]
    
    posts_html = ''
    for post in latest_posts:
        author = users_db.get(post['author_id'], {})
        posts_html += f'''
        <article class="post-card">
            <h3><a href="/posts/{post['id']}">{post['title']}</a></h3>
            <div class="meta">
                <span>作者: {author.get('name', 'Unknown')}</span>
                <span>时间: {post['created_at']}</span>
            </div>
            <p>{post['content'][:100]}...</p>
        </article>
        '''
    
    content = f'''
    <section class="hero">
        <h1>Litefs 全栈应用示例</h1>
        <p>一个综合展示 Litefs 所有功能的完整 Web 应用</p>
        <div class="features">
            <div class="feature">
                <h3>🚀 现代路由</h3>
                <p>装饰器和方法链两种风格</p>
            </div>
            <div class="feature">
                <h3>🔐 会话管理</h3>
                <p>完整的用户认证系统</p>
            </div>
            <div class="feature">
                <h3>⚡ 缓存支持</h3>
                <p>高性能数据缓存</p>
            </div>
            <div class="feature">
                <h3>🛡️ 中间件</h3>
                <p>日志、安全、限流等</p>
            </div>
        </div>
    </section>
    <section class="latest-posts">
        <h2>最新文章</h2>
        <div class="posts-grid">
            {posts_html}
        </div>
        <div class="text-center">
            <a href="/posts" class="btn btn-primary">查看所有文章</a>
        </div>
    </section>
    '''
    
    user = None
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id:
            user = users_db.get(user_id)
    
    html = render_page(content, user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# 文章列表
@app.add_get('/posts', name='posts')
def posts_handler(request):
    """文章列表"""
    # 检查缓存
    cache_key = 'posts_list'
    cached = cache.get(cache_key)
    if cached:
        posts_html = cached
    else:
        posts_html = ''
        for post in sorted(posts_db, key=lambda x: x['created_at'], reverse=True):
            author = users_db.get(post['author_id'], {})
            posts_html += f'''
            <article class="post-item">
                <h3><a href="/posts/{post['id']}">{post['title']}</a></h3>
                <div class="meta">
                    <span>作者: {author.get('name', 'Unknown')}</span>
                    <span>时间: {post['created_at']}</span>
                </div>
                <p>{post['content'][:150]}...</p>
                <a href="/posts/{post['id']}" class="read-more">阅读全文 →</a>
            </article>
            '''
        # 缓存 5 分钟
        cache.put(cache_key, posts_html, ttl=300)
    
    content = f'''
    <section class="posts-section">
        <h1>所有文章</h1>
        <div class="posts-list">
            {posts_html}
        </div>
    </section>
    '''
    
    user = None
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id:
            user = users_db.get(user_id)
    
    html = render_page(content, title='文章列表 - Litefs Fullstack', user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# 文章详情
@app.add_get('/posts/{id}', name='post_detail')
def post_detail_handler(request, id):
    """文章详情"""
    post = next((p for p in posts_db if str(p['id']) == id), None)
    
    if not post:
        content = '<h1>文章未找到</h1><p>该文章不存在或已被删除。</p>'
        html = render_page(content, title='404 - Litefs Fullstack')
        request.start_response(404, [('Content-Type', 'text/html; charset=utf-8')])
        return html
    
    author = users_db.get(post['author_id'], {})
    
    content = f'''
    <article class="post-detail">
        <h1>{post['title']}</h1>
        <div class="meta">
            <span>作者: {author.get('name', 'Unknown')}</span>
            <span>时间: {post['created_at']}</span>
        </div>
        <div class="content">
            {post['content']}
        </div>
        <div class="actions">
            <a href="/posts" class="btn">← 返回列表</a>
        </div>
    </article>
    '''
    
    user = None
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id:
            user = users_db.get(user_id)
    
    html = render_page(content, title=post['title'], user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# 关于页面
@app.add_get('/about', name='about')
def about_handler(request):
    """关于页面"""
    content = '''
    <section class="about-section">
        <h1>关于 Litefs Fullstack</h1>
        <p>这是一个综合展示 Litefs 框架所有功能的完整 Web 应用示例。</p>
        
        <h2>功能特性</h2>
        <ul class="feature-list">
            <li><strong>现代路由系统</strong> - 支持装饰器和方法链两种风格</li>
            <li><strong>会话管理</strong> - 完整的用户认证和会话管理</li>
            <li><strong>缓存支持</strong> - 内存缓存提高性能</li>
            <li><strong>中间件集成</strong> - 日志、安全、CORS、限流等中间件</li>
            <li><strong>静态文件服务</strong> - 自动处理静态资源</li>
            <li><strong>健康检查</strong> - 应用健康状态监控</li>
        </ul>
        
        <h2>技术栈</h2>
        <ul class="tech-stack">
            <li>Python 3.8+</li>
            <li>Litefs Framework</li>
            <li>HTML5 / CSS3</li>
            <li>Vanilla JavaScript</li>
        </ul>
    </section>
    '''
    
    user = None
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id:
            user = users_db.get(user_id)
    
    html = render_page(content, title='关于 - Litefs Fullstack', user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# 登录页面
@app.add_get('/login', name='login')
def login_handler(request):
    """登录页面"""
    content = '''
    <section class="auth-section">
        <div class="auth-form">
            <h1>用户登录</h1>
            <form method="post" action="/login" id="loginForm">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <div id="error" class="error-message"></div>
                <button type="submit" class="btn btn-primary btn-block">登录</button>
            </form>
            <div class="auth-info">
                <p>默认账号：</p>
                <ul>
                    <li>admin / admin123</li>
                    <li>user1 / user123</li>
                </ul>
            </div>
        </div>
    </section>
    '''
    
    html = render_page(content, title='登录 - Litefs Fullstack')
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# 处理登录
@app.add_post('/login', name='login_post')
def login_post_handler(request):
    """处理登录"""
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    
    # 验证用户
    if username in user_passwords and user_passwords[username] == password:
        user = next((u for u in users_db.values() if u['username'] == username), None)
        if user and hasattr(request, 'session'):
            request.session['user_id'] = user['id']
            request.session['username'] = user['username']
            request.session.save()
        
        request.start_response(302, [('Location', '/')])
        return ''
    
    # 登录失败
    content = '''
    <section class="auth-section">
        <div class="auth-form">
            <h1>用户登录</h1>
            <div class="alert alert-error">用户名或密码错误</div>
            <form method="post" action="/login">
                <div class="form-group">
                    <label for="username">用户名</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">密码</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">登录</button>
            </form>
        </div>
    </section>
    '''
    
    html = render_page(content, title='登录 - Litefs Fullstack')
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# 退出登录
@app.add_get('/logout', name='logout')
def logout_handler(request):
    """退出登录"""
    if hasattr(request, 'session'):
        request.session.clear()
    request.start_response(302, [('Location', '/')])
    return ''


# 用户控制台
@app.add_get('/dashboard', name='dashboard')
def dashboard_handler(request):
    """用户控制台"""
    # 检查登录
    user = None
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id:
            user = users_db.get(user_id)
    
    if not user:
        request.start_response(302, [('Location', '/login')])
        return ''
    
    # 获取用户文章
    user_posts = [p for p in posts_db if p['author_id'] == user['id']]
    
    posts_html = ''
    for post in user_posts:
        posts_html += f'''
        <tr>
            <td>{post['title']}</td>
            <td>{post['created_at']}</td>
            <td>
                <a href="/posts/{post['id']}" class="btn btn-sm">查看</a>
            </td>
        </tr>
        '''
    
    content = f'''
    <section class="dashboard">
        <h1>用户控制台</h1>
        <div class="user-info">
            <h2>欢迎, {user['name']}</h2>
            <p>角色: {user['role']}</p>
        </div>
        <div class="user-posts">
            <h3>我的文章</h3>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>标题</th>
                        <th>发布时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    {posts_html if posts_html else '<tr><td colspan="3">暂无文章</td></tr>'}
                </tbody>
            </table>
        </div>
    </section>
    '''
    
    html = render_page(content, title='控制台 - Litefs Fullstack', user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# API 文档
@app.add_get('/api/docs', name='api_docs')
def api_docs_handler(request):
    """API 文档"""
    content = '''
    <section class="api-docs">
        <h1>API 文档</h1>
        <p>Litefs Fullstack 提供以下 API 端点：</p>
        
        <h2>文章 API</h2>
        <table class="api-table">
            <thead>
                <tr>
                    <th>方法</th>
                    <th>端点</th>
                    <th>描述</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>GET</td>
                    <td>/api/posts</td>
                    <td>获取文章列表</td>
                </tr>
                <tr>
                    <td>GET</td>
                    <td>/api/posts/{id}</td>
                    <td>获取文章详情</td>
                </tr>
            </tbody>
        </table>
        
        <h2>示例</h2>
        <pre><code>curl http://localhost:8080/api/posts</code></pre>
    </section>
    '''
    
    user = None
    if hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        if user_id:
            user = users_db.get(user_id)
    
    html = render_page(content, title='API 文档 - Litefs Fullstack', user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


# API: 获取文章列表
@app.add_get('/api/posts', name='api_posts')
def api_posts_handler(request):
    """API: 获取文章列表"""
    posts = []
    for post in sorted(posts_db, key=lambda x: x['created_at'], reverse=True):
        author = users_db.get(post['author_id'], {})
        posts.append({
            'id': post['id'],
            'title': post['title'],
            'excerpt': post['content'][:100] + '...',
            'author': author.get('name', 'Unknown'),
            'created_at': post['created_at']
        })
    
    return {'posts': posts}


# API: 获取文章详情
@app.add_get('/api/posts/{id}', name='api_post_detail')
def api_post_detail_handler(request, id):
    """API: 获取文章详情"""
    post = next((p for p in posts_db if str(p['id']) == id), None)
    
    if not post:
        request.start_response(404, [('Content-Type', 'application/json')])
        return {'error': 'Post not found'}
    
    author = users_db.get(post['author_id'], {})
    
    return {
        'id': post['id'],
        'title': post['title'],
        'content': post['content'],
        'author': author.get('name', 'Unknown'),
        'created_at': post['created_at']
    }


# ==================== 配置中间件 ====================

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 添加安全中间件
app.add_middleware(SecurityMiddleware)

# 添加 CORS 中间件
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_methods=["GET", "POST", "PUT", "DELETE"],
                   allow_headers=["Content-Type", "Authorization"])

# 添加限流中间件
app.add_middleware(RateLimitMiddleware,
                   max_requests=100,
                   window_seconds=60,
                   block_duration=120)

# 添加健康检查中间件
app.add_middleware(HealthCheck,
                   path='/health',
                   ready_path='/health/ready')


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs Fullstack Application")
    print("=" * 60)
    print("访问地址: http://localhost:8080")
    print("=" * 60)
    print("默认账号:")
    print("  admin / admin123")
    print("  user1 / user123")
    print("=" * 60)
    print("健康检查: http://localhost:8080/health")
    print("=" * 60)
    
    app.run()
