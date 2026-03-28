#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
首页处理函数
"""

from datetime import datetime


def handler(self):
    """处理首页请求"""
    # 获取会话
    session = self.session
    
    # 增加访问计数
    visit_count = session.get('visit_count', 0) + 1
    session['visit_count'] = visit_count
    
    # 获取当前时间
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 构建响应内容
    content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Litefs Full Stack Example</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <header>
            <h1>Litefs Full Stack Example</h1>
            <nav>
                <ul>
                    <li><a href="/">Home</a></li>
                    <li><a href="/about">About</a></li>
                    <li><a href="/contact">Contact</a></li>
                    <li><a href="/dashboard">Dashboard</a></li>
                </ul>
            </nav>
        </header>
        <main>
            <section class="hero">
                <h2>Welcome to Litefs!</h2>
                <p>A lightweight Python Web framework for building fast and secure web applications.</p>
            </section>
            <section class="info">
                <h3>Application Information</h3>
                <ul>
                    <li><strong>Current Time:</strong> {current_time}</li>
                    <li><strong>Visit Count:</strong> {visit_count}</li>
                    <li><strong>Session ID:</strong> {self.session_id}</li>
                    <li><strong>User Agent:</strong> {self.environ.get('HTTP_USER_AGENT', 'N/A')}</li>
                </ul>
            </section>
            <section class="features">
                <h3>Key Features</h3>
                <div class="feature-grid">
                    <div class="feature-item">
                        <h4>High Performance</h4>
                        <p>Uses epoll and greenlet for high concurrency</p>
                    </div>
                    <div class="feature-item">
                        <h4>WSGI Compatible</h4>
                        <p>Works with Gunicorn, uWSGI, and Waitress</p>
                    </div>
                    <div class="feature-item">
                        <h4>Middleware Support</h4>
                        <p>Extensible middleware system</p>
                    </div>
                    <div class="feature-item">
                        <h4>Session Management</h4>
                        <p>Built-in session support</p>
                    </div>
                    <div class="feature-item">
                        <h4>Caching</h4>
                        <p>Multi-level caching system</p>
                    </div>
                    <div class="feature-item">
                        <h4>Health Checks</h4>
                        <p>Built-in health and readiness checks</p>
                    </div>
                </div>
            </section>
        </main>
        <footer>
            <p>&copy; {datetime.now().year} Litefs Full Stack Example. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    # 设置响应头
    self.start_response(200, [('Content-Type', 'text/html')])
    
    return content
