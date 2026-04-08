#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
博客系统示例 - 可视化 Web 应用

这个示例展示了如何构建一个完整的博客系统，包括：
- HTML 模板渲染
- 静态文件服务
- 会话管理（用户登录）
- 表单处理
- 文章 CRUD 操作
"""

import sys
import os
import json
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.routing import get, post
from litefs.middleware import LoggingMiddleware


# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    session_backend='memory',
    session_expiration_time=3600
).add_middleware(LoggingMiddleware)

# 挂载静态文件
app.add_static('/static', 'static')

# 模拟数据库 - 文章存储
posts_db = [
    {
        'id': 1,
        'title': '欢迎使用 Litefs',
        'content': 'Litefs 是一个轻量级的 Python Web 框架，简单易用，功能强大。',
        'author': 'Admin',
        'created_at': '2024-01-01 10:00:00',
        'views': 128
    },
    {
        'id': 2,
        'title': 'Python Web 开发入门',
        'content': 'Python 是进行 Web 开发的绝佳选择，拥有丰富的框架和库。',
        'author': 'Admin',
        'created_at': '2024-01-02 14:30:00',
        'views': 85
    }
]

# 模拟用户数据库
users_db = {
    'admin': {'password': 'admin123', 'name': 'Administrator'}
}


# ==================== 页面渲染函数 ====================

def render_template(template_name, **kwargs):
    """渲染 HTML 模板"""
    template_path = os.path.join('templates', template_name)
    if not os.path.exists(template_path):
        return f"<h1>Template {template_name} not found</h1>"
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 简单的模板变量替换
    for key, value in kwargs.items():
        content = content.replace(f'{{{{ {key} }}}}', str(value))
    
    return content


def render_base(content, title='Litefs Blog', user=None):
    """渲染基础页面框架"""
    user_info = f'<span class="user">{user}</span>' if user else '<a href="/login">登录</a>'
    
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <nav class="navbar">
        <div class="container">
            <a href="/" class="logo">Litefs Blog</a>
            <div class="nav-links">
                <a href="/">首页</a>
                <a href="/posts">文章</a>
                {('<a href="/posts/new">写文章</a>' if user else '')}
                {user_info}
            </div>
        </div>
    </nav>
    <main class="container">
        {content}
    </main>
    <footer>
        <div class="container">
            <p>&copy; 2024 Litefs Blog. Powered by Litefs Framework.</p>
        </div>
    </footer>
</body>
</html>'''


# ==================== 路由处理函数 ====================

@app.add_get('/', name='home')
def home_handler(request):
    """首页 - 显示最新文章"""
    # 获取最新3篇文章
    latest_posts = sorted(posts_db, key=lambda x: x['created_at'], reverse=True)[:3]
    
    posts_html = ''
    for post in latest_posts:
        posts_html += f'''
        <article class="post-card">
            <h2><a href="/posts/{post['id']}">{post['title']}</a></h2>
            <div class="meta">
                <span>作者: {post['author']}</span>
                <span>时间: {post['created_at']}</span>
                <span>阅读: {post['views']}</span>
            </div>
            <p class="excerpt">{post['content'][:100]}...</p>
            <a href="/posts/{post['id']}" class="read-more">阅读更多</a>
        </article>
        '''
    
    content = f'''
    <div class="hero">
        <h1>欢迎来到 Litefs Blog</h1>
        <p>一个使用 Litefs 框架构建的简单博客系统</p>
    </div>
    <section class="latest-posts">
        <h2>最新文章</h2>
        {posts_html}
    </section>
    '''
    
    user = request.session.get('username') if hasattr(request, 'session') else None
    html = render_base(content, user=user)
    
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


@app.add_get('/posts', name='post_list')
def post_list_handler(request):
    """文章列表页"""
    posts_html = ''
    for post in sorted(posts_db, key=lambda x: x['created_at'], reverse=True):
        posts_html += f'''
        <article class="post-item">
            <h2><a href="/posts/{post['id']}">{post['title']}</a></h2>
            <div class="meta">
                <span>作者: {post['author']}</span>
                <span>时间: {post['created_at']}</span>
                <span>阅读: {post['views']}</span>
            </div>
            <p>{post['content'][:150]}...</p>
        </article>
        '''
    
    content = f'''
    <h1>所有文章</h1>
    <div class="post-list">
        {posts_html}
    </div>
    '''
    
    user = request.session.get('username') if hasattr(request, 'session') else None
    html = render_base(content, user=user)
    
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html

@app.add_get('/posts/new', name='post_new')
def post_new_handler(request):
    """新建文章页面"""
    # 检查登录状态
    user = request.session.get('username') if hasattr(request, 'session') else None
    if not user:
        request.start_response(302, [('Location', '/login')])
        return ''
    
    content = '''
    <h1>写文章</h1>
    <form method="post" action="/posts" class="post-form">
        <div class="form-group">
            <label>标题</label>
            <input type="text" name="title" required>
        </div>
        <div class="form-group">
            <label>内容</label>
            <textarea name="content" rows="10" required></textarea>
        </div>
        <button type="submit" class="btn btn-primary">发布</button>
        <a href="/posts" class="btn">取消</a>
    </form>
    '''
    
    html = render_base(content, title='写文章', user=user)
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


@app.add_get('/posts/{id}', name='post_detail')
def post_detail_handler(request, id):
    """文章详情页"""
    post = next((p for p in posts_db if str(p['id']) == id), None)
    
    if not post:
        request.start_response(404, [('Content-Type', 'text/html; charset=utf-8')])
        return render_base('<h1>文章未找到</h1><p>该文章不存在或已被删除。</p>')
    
    # 增加阅读数
    post['views'] += 1
    
    content = f'''
    <article class="post-detail">
        <h1>{post['title']}</h1>
        <div class="meta">
            <span>作者: {post['author']}</span>
            <span>时间: {post['created_at']}</span>
            <span>阅读: {post['views']}</span>
        </div>
        <div class="content">
            {post['content']}
        </div>
    </article>
    <div class="actions">
        <a href="/posts" class="btn">返回列表</a>
    </div>
    '''
    
    user = request.session.get('username') if hasattr(request, 'session') else None
    html = render_base(content, title=post['title'], user=user)
    
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


@app.add_post('/posts', name='post_create')
def post_create_handler(request):
    """创建文章"""
    # 检查登录状态
    user = request.session.get('username') if hasattr(request, 'session') else None
    if not user:
        request.start_response(302, [('Location', '/login')])
        return ''
    
    title = request.data.get('title', '')
    content = request.data.get('content', '')
    
    if not title or not content:
        request.start_response(400, [('Content-Type', 'text/html; charset=utf-8')])
        return render_base('<h1>错误</h1><p>标题和内容不能为空。</p>', user=user)
    
    # 创建新文章
    new_post = {
        'id': len(posts_db) + 1,
        'title': title,
        'content': content,
        'author': user,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'views': 0
    }
    posts_db.append(new_post)
    
    request.start_response(302, [('Location', f'/posts/{new_post["id"]}')])
    return ''


@app.add_get('/login', name='login')
def login_handler(request):
    """登录页面"""
    content = '''
    <div class="auth-form">
        <h1>登录</h1>
        <form method="post" action="/login">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary">登录</button>
        </form>
        <p class="hint">默认账号: admin / admin123</p>
    </div>
    '''
    
    html = render_base(content, title='登录')
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return html


@app.add_post('/login', name='login_post')
def login_post_handler(request):
    """处理登录"""
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    
    user = users_db.get(username)
    if user and user['password'] == password:
        request.session['username'] = username
        request.session['name'] = user['name']
        request.session.save()
        request.start_response(302, [('Location', '/')])
        return ''
    else:
        content = '''
        <div class="auth-form">
            <h1>登录</h1>
            <p class="error">用户名或密码错误</p>
            <form method="post" action="/login">
                <div class="form-group">
                    <label>用户名</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>密码</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary">登录</button>
            </form>
        </div>
        '''
        html = render_base(content, title='登录')
        request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
        return html


@app.add_get('/logout', name='logout')
def logout_handler(request):
    """退出登录"""
    request.session.clear()
    request.start_response(302, [('Location', '/')])
    return ''


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs Blog Demo")
    print("=" * 60)
    print("访问地址: http://localhost:8080")
    print("=" * 60)
    print("默认账号: admin / admin123")
    print("=" * 60)
    
    app.run(processes=6)
