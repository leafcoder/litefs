#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
仪表板页面处理函数
"""

from datetime import datetime


def handler(self):
    """处理仪表板页面请求"""
    # 获取会话
    session = self.session
    
    # 检查用户是否已登录（模拟登录状态）
    user = session.get('user', None)
    
    if not user:
        # 模拟用户登录
        user = {
            'id': 1,
            'name': 'John Doe',
            'email': 'john@example.com',
            'role': 'admin'
        }
        session['user'] = user
    
    # 获取访问历史
    visit_history = session.get('visit_history', [])
    current_visit = {
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'path': self.path_info
    }
    visit_history.append(current_visit)
    
    # 只保留最近10次访问
    if len(visit_history) > 10:
        visit_history = visit_history[-10:]
    
    session['visit_history'] = visit_history
    
    # 生成访问历史表格行
    visit_history_rows = ''
    for visit in reversed(visit_history):
        visit_history_rows += f"<tr><td>{visit['time']}</td><td>{visit['path']}</td></tr>"
    
    # 构建响应内容
    content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - Litefs Full Stack Example</title>
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
            <section class="dashboard">
                <h2>User Dashboard</h2>
                
                <div class="user-info">
                    <h3>User Information</h3>
                    <ul>
                        <li><strong>Name:</strong> {user['name']}</li>
                        <li><strong>Email:</strong> {user['email']}</li>
                        <li><strong>Role:</strong> {user['role']}</li>
                        <li><strong>Session ID:</strong> {self.session_id}</li>
                    </ul>
                </div>
                
                <div class="visit-history">
                    <h3>Recent Visits</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Path</th>
                            </tr>
                        </thead>
                        <tbody>
                            {visit_history_rows}
                        </tbody>
                    </table>
                </div>
                
                <div class="session-actions">
                    <h3>Session Actions</h3>
                    <a href="/dashboard/clear" class="button">Clear Visit History</a>
                    <a href="/dashboard/logout" class="button">Logout</a>
                </div>
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
