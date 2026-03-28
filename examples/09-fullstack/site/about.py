#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
关于页面处理函数
"""


def handler(self):
    """处理关于页面请求"""
    # 构建响应内容
    content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>About - Litefs Full Stack Example</title>
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
            <section class="about">
                <h2>About Litefs</h2>
                <p>Litefs is a lightweight Python Web framework designed for building fast, secure, and flexible web applications. It provides a simple yet powerful API for web development, with features like:</p>
                
                <h3>Core Features</h3>
                <ul>
                    <li>High-performance HTTP server using epoll and greenlet</li>
                    <li>WSGI 1.0 compatible (PEP 3333)</li>
                    <li>Support for Gunicorn, uWSGI, Waitress, and other WSGI servers</li>
                    <li>Static file serving with gzip/deflate compression</li>
                    <li>Mako template engine support</li>
                    <li>CGI script execution (.pl, .py, .php)</li>
                    <li>Session management</li>
                    <li>Multi-level caching system (memory + tree cache + Redis)</li>
                    <li>File monitoring and hot reload</li>
                    <li>Python 2.6-3.14 support</li>
                    <li>Enhanced request processing (separate query and post parameters)</li>
                    <li>Comprehensive form validation system</li>
                    <li>Beautiful error pages, customizable</li>
                    <li>Flexible cache backend options (memory, tree, Redis)</li>
                </ul>
                
                <h3>Design Philosophy</h3>
                <p>Litefs is designed with the following principles in mind:</p>
                <ul>
                    <li><strong>Simplicity:</strong> Keep the API simple and intuitive</li>
                    <li><strong>Performance:</strong> Optimize for speed and concurrency</li>
                    <li><strong>Flexibility:</strong> Provide extensible components</li>
                    <li><strong>Compatibility:</strong> Support multiple Python versions and WSGI servers</li>
                    <li><strong>Security:</strong> Include built-in security features</li>
                </ul>
            </section>
        </main>
        <footer>
            <p>&copy; 2026 Litefs Full Stack Example. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    # 设置响应头
    self.start_response(200, [('Content-Type', 'text/html')])
    
    return content
