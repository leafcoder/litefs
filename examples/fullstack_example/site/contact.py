#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
联系页面处理函数
"""


def handler(self):
    """处理联系页面请求"""
    # 检查请求方法
    if self.request_method == 'POST':
        # 处理表单提交
        return _handle_form_submission(self)
    else:
        # 显示表单
        return _display_form(self)


def _display_form(self, error_message=None):
    """显示联系表单"""
    # 构建响应内容
    content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contact - Litefs Full Stack Example</title>
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
            <section class="contact">
                <h2>Contact Us</h2>
                {error_message}
                <form method="POST" action="/contact">
                    <div class="form-group">
                        <label for="name">Name:</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    <div class="form-group">
                        <label for="email">Email:</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    <div class="form-group">
                        <label for="subject">Subject:</label>
                        <input type="text" id="subject" name="subject" required>
                    </div>
                    <div class="form-group">
                        <label for="message">Message:</label>
                        <textarea id="message" name="message" rows="5" required></textarea>
                    </div>
                    <div class="form-group">
                        <button type="submit">Send Message</button>
                    </div>
                </form>
            </section>
        </main>
        <footer>
            <p>&copy; 2026 Litefs Full Stack Example. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    # 替换错误信息
    error_html = ''
    if error_message:
        error_html = f'<div class="error-message">{error_message}</div>'
    
    content = content.format(error_message=error_html)
    
    # 设置响应头
    self.start_response(200, [('Content-Type', 'text/html')])
    
    return content


def _handle_form_submission(self):
    """处理表单提交"""
    # 获取表单数据
    form_data = self.form
    
    # 验证表单数据
    name = form_data.get('name', '').strip()
    email = form_data.get('email', '').strip()
    subject = form_data.get('subject', '').strip()
    message = form_data.get('message', '').strip()
    
    # 简单验证
    if not all([name, email, subject, message]):
        return _display_form(self, 'Please fill in all required fields.')
    
    # 模拟发送邮件（实际应用中可以使用邮件库）
    print(f"""
    New contact form submission:
    Name: {name}
    Email: {email}
    Subject: {subject}
    Message: {message}
    """)
    
    # 构建成功响应
    content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Contact - Litefs Full Stack Example</title>
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
            <section class="contact">
                <h2>Message Sent!</h2>
                <div class="success-message">
                    <p>Thank you for your message, {name}!</p>
                    <p>We will get back to you soon.</p>
                </div>
                <a href="/contact" class="button">Send Another Message</a>
            </section>
        </main>
        <footer>
            <p>&copy; 2026 Litefs Full Stack Example. All rights reserved.</p>
        </footer>
    </body>
    </html>
    """
    
    # 替换变量
    content = content.format(name=name)
    
    # 设置响应头
    self.start_response(200, [('Content-Type', 'text/html')])
    
    return content
