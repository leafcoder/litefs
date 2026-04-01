#!/usr/bin/env python
# coding: utf-8

"""
Session 各后端使用示例

演示如何使用 Litefs 的各种 Session 后端
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.session import (
    DatabaseSession, RedisSession, MemcacheSession,
    SessionFactory, SessionBackend
)
from litefs.routing import get

def example_1_database_session_direct():
    """示例 1: 直接使用 Database Session"""
    print("=" * 60)
    print("示例 1: 直接使用 Database Session")
    print("=" * 60)

    try:
        # 创建 Database Session 存储
        session_store = DatabaseSession(
            db_path=":memory:",  # 使用内存数据库
            table_name="sessions",
            expiration_time=3600
        )

        # 创建新 Session
        from litefs.session.session import Session
        import uuid
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        print(f"创建 Session: {session.id}")

        # 设置 Session 数据
        session["user_id"] = 123
        session["username"] = "test_user"
        session["email"] = "test@example.com"
        session["role"] = "admin"
        print("设置 Session 数据: user_id, username, email, role")

        # 保存 Session
        session_store.put(session.id, session)
        print("保存 Session 到数据库")

        # 调试：检查数据库中的数据
        print("调试：检查数据库中的数据")
        conn = session_store._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM sessions WHERE session_id = ?", (session.id,))
        row = cursor.fetchone()
        if row:
            print(f"调试：数据库中存在 Session，data={row['data']}")
        else:
            print("调试：数据库中不存在 Session")

        # 获取 Session
        retrieved_session = session_store.get(session.id)
        if retrieved_session:
            print(f"获取 Session: {retrieved_session.id}")
            print(f"Session 数据: {dict(retrieved_session)}")
        else:
            print("无法获取 Session")

        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")

        # 设置 Session 过期时间
        expire_result = session_store.expire(session.id, 1800)  # 30分钟
        print(f"设置 Session 过期时间: {expire_result}")

        # 获取 Session 剩余过期时间
        ttl = session_store.ttl(session.id)
        print(f"Session 剩余过期时间: {ttl} 秒")

        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")

        # 检查 Session 是否存在
        exists_after_delete = session_store.exists(session.id)
        print(f"删除后 Session 是否存在: {exists_after_delete}")

        # 关闭连接
        session_store.close()
        print("关闭数据库连接")

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_2_redis_session_direct():
    """示例 2: 直接使用 Redis Session"""
    print("=" * 60)
    print("示例 2: 直接使用 Redis Session")
    print("=" * 60)

    try:
        # 创建 Redis Session 存储
        session_store = RedisSession(
            host="localhost",
            port=6379,
            db=0,
            key_prefix="session:",
            expiration_time=3600
        )

        # 创建新 Session
        from litefs.session.session import Session
        import uuid
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        print(f"创建 Session: {session.id}")

        # 设置 Session 数据
        session["user_id"] = 456
        session["username"] = "redis_user"
        session["cart"] = [
            {"id": 1, "name": "商品1", "price": 99.99},
            {"id": 2, "name": "商品2", "price": 199.99}
        ]
        print("设置 Session 数据: user_id, username, cart")

        # 保存 Session
        session_store.put(session.id, session)
        print("保存 Session 到 Redis")

        # 获取 Session
        retrieved_session = session_store.get(session.id)
        if retrieved_session:
            print(f"获取 Session: {retrieved_session.id}")
            print(f"Session 数据: {dict(retrieved_session)}")
        else:
            print("无法获取 Session")

        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")

        # 设置 Session 过期时间
        expire_result = session_store.expire(session.id, 1800)  # 30分钟
        print(f"设置 Session 过期时间: {expire_result}")

        # 获取 Session 剩余过期时间
        ttl = session_store.ttl(session.id)
        print(f"Session 剩余过期时间: {ttl} 秒")

        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")

        # 检查 Session 是否存在
        exists_after_delete = session_store.exists(session.id)
        print(f"删除后 Session 是否存在: {exists_after_delete}")

        # 关闭连接
        session_store.close()
        print("关闭 Redis 连接")

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_3_memcache_session_direct():
    """示例 3: 直接使用 Memcache Session"""
    print("=" * 60)
    print("示例 3: 直接使用 Memcache Session")
    print("=" * 60)

    try:
        # 创建 Memcache Session 存储
        session_store = MemcacheSession(
            servers=["localhost:11211"],
            key_prefix="session:",
            expiration_time=3600
        )

        # 创建新 Session
        from litefs.session.session import Session
        import uuid
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        print(f"创建 Session: {session.id}")

        # 设置 Session 数据
        session["user_id"] = 789
        session["username"] = "memcache_user"
        session["preferences"] = {
            "theme": "dark",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai"
        }
        print("设置 Session 数据: user_id, username, preferences")

        # 保存 Session
        session_store.put(session.id, session)
        print("保存 Session 到 Memcache")

        # 获取 Session
        retrieved_session = session_store.get(session.id)
        if retrieved_session:
            print(f"获取 Session: {retrieved_session.id}")
            print(f"Session 数据: {dict(retrieved_session)}")
        else:
            print("无法获取 Session")

        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")

        # 设置 Session 过期时间
        expire_result = session_store.expire(session.id, 1800)  # 30分钟
        print(f"设置 Session 过期时间: {expire_result}")

        # 获取 Session 剩余过期时间
        ttl = session_store.ttl(session.id)
        print(f"Session 剩余过期时间: {ttl} 秒")

        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")

        # 检查 Session 是否存在
        exists_after_delete = session_store.exists(session.id)
        print(f"删除后 Session 是否存在: {exists_after_delete}")

        # 关闭连接
        session_store.close()
        print("关闭 Memcache 连接")

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_4_session_factory():
    """示例 4: 使用 Session 工厂创建不同后端的 Session"""
    print("=" * 60)
    print("示例 4: 使用 Session 工厂创建不同后端的 Session")
    print("=" * 60)

    try:
        # 使用 Session 工厂创建 Database Session
        print("创建 Database Session...")
        from litefs.session.session import Session
        import uuid
        db_session_store = SessionFactory.create_session(
            backend=SessionBackend.DATABASE,
            db_path=":memory:",
            expiration_time=3600
        )
        session_id = str(uuid.uuid4())
        db_session = Session(session_id)
        db_session["test"] = "database session"
        db_session_store.put(session_id, db_session)
        print(f"Database Session 创建成功: {db_session.id}")
        db_session_store.close()

        # 使用 Session 工厂创建 Redis Session
        print("\n创建 Redis Session...")
        redis_session_store = SessionFactory.create_session(
            backend=SessionBackend.REDIS,
            host="localhost",
            port=6379,
            db=0,
            expiration_time=3600
        )
        session_id = str(uuid.uuid4())
        redis_session = Session(session_id)
        redis_session["test"] = "redis session"
        redis_session_store.put(session_id, redis_session)
        print(f"Redis Session 创建成功: {redis_session.id}")
        redis_session_store.close()

        # 使用 Session 工厂创建 Memcache Session
        print("\n创建 Memcache Session...")
        memcache_session_store = SessionFactory.create_session(
            backend=SessionBackend.MEMCACHE,
            servers=["localhost:11211"],
            expiration_time=3600
        )
        session_id = str(uuid.uuid4())
        memcache_session = Session(session_id)
        memcache_session["test"] = "memcache session"
        memcache_session_store.put(session_id, memcache_session)
        print(f"Memcache Session 创建成功: {memcache_session.id}")
        memcache_session_store.close()

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_5_web_app_session():
    """示例 5: 在 Web 应用中使用 Session"""
    print("=" * 60)
    print("示例 5: 在 Web 应用中使用 Session")
    print("=" * 60)
    print("启动 Web 应用，访问 http://localhost:8085/session-demo")
    print("=" * 60)

    # 创建 Litefs 应用实例
    app = Litefs(
        host='0.0.0.0',
        port=8085,
        debug=True,
        database_path='data.db',
        session_backend='database',
        session_expiration_time=3600
    )

    # 定义 session-demo 路由
    @get('/session-demo')
    def session_demo_handler(self):
        self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
        
        action = self.get.get('action', 'view')
        session_backend = self.get.get('backend', 'default')
        message = ''
        message_type = 'success'
        
        # 根据选择的后端切换 session 存储
        app = self._app
        if session_backend != 'default':
            from litefs.session.manager import SessionManager
            from litefs.session.factory import SessionBackend
            
            try:
                # 保存当前 Session 数据
                current_session_data = dict(self.session)
                current_session_id = self.session.id
                
                if session_backend == 'database':
                    # 使用 Database 后端
                    app.sessions = SessionManager.get_session_cache(
                        backend=SessionBackend.DATABASE,
                        cache_key='sessions_database',
                        db_path='./sessions.db',
                        table_name='sessions'
                    )
                elif session_backend == 'redis':
                    # 使用 Redis 后端
                    app.sessions = SessionManager.get_session_cache(
                        backend=SessionBackend.REDIS,
                        cache_key='sessions_redis',
                        host='localhost',
                        port=6379,
                        db=0
                    )
                elif session_backend == 'memcache':
                    # 使用 Memcache 后端
                    app.sessions = SessionManager.get_session_cache(
                        backend=SessionBackend.MEMCACHE,
                        cache_key='sessions_memcache',
                        servers=['localhost:11211']
                    )
                
                # 重新获取 Session，确保与新的后端关联
                from litefs.session import Session
                session = app.sessions.get(current_session_id)
                if session is None:
                    # 创建 Session 对象时传入存储后端实例
                    session = Session(current_session_id, store=app.sessions)
                    # 恢复 Session 数据
                    session.update(current_session_data)
                    app.sessions.put(current_session_id, session)
                else:
                    # 设置存储后端实例，确保数据修改时自动保存
                    session.store = app.sessions
                
                # 更新请求的 Session 对象
                self._session = session
                self._session_id = current_session_id
                
                message = f"已切换到 {session_backend} Session 后端"
                message_type = 'info'
            except ImportError as e:
                message = f"错误：{e}"
                message_type = 'error'
            except ConnectionError as e:
                message = f"错误：{e}"
                message_type = 'error'
            except Exception as e:
                message = f"错误：{e}"
                message_type = 'error'
        
        # 执行操作
        if action == 'set':
            key = self.get.get('key', 'username')
            value = self.get.get('value', 'guest')
            self.session[key] = value
            # 手动保存 Session 数据
            self.session.save()
            message = f"已设置 Session: {key} = {value}"
        
        elif action == 'delete':
            key = self.get.get('key', 'username')
            if key in self.session:
                del self.session[key]
                # 手动保存 Session 数据
                self.session.save()
                message = f"已删除 Session: {key}"
            else:
                message = f"Session 中不存在: {key}"
                message_type = 'warning'
        
        elif action == 'clear':
            self.session.clear()
            # 手动保存 Session 数据
            self.session.save()
            message = "已清除所有 Session 数据"
        
        elif action == 'set_user':
            self.session['username'] = '张三'
            self.session['user_id'] = '1001'
            self.session['role'] = 'admin'
            self.session['login_time'] = '2024-01-01 12:00:00'
            # 手动保存 Session 数据
            self.session.save()
            message = "已设置用户 Session 信息"
        
        elif action == 'set_cart':
            self.session['cart_items'] = [
                {'id': 1, 'name': '商品A', 'price': 99.99, 'quantity': 2},
                {'id': 2, 'name': '商品B', 'price': 199.99, 'quantity': 1}
            ]
            self.session['cart_total'] = 399.97
            # 手动保存 Session 数据
            self.session.save()
            message = "已设置购物车 Session"
        
        elif action == 'set_pref':
            self.session['theme'] = 'dark'
            self.session['language'] = 'zh-CN'
            self.session['timezone'] = 'Asia/Shanghai'
            # 手动保存 Session 数据
            self.session.save()
            message = "已设置用户偏好 Session"
        
        elif action == 'increment':
            count_key = self.get.get('key', 'visit_count')
            current_count = self.session.get(count_key, 0)
            self.session[count_key] = current_count + 1
            # 手动保存 Session 数据
            self.session.save()
            message = f"{count_key}: {current_count} -> {current_count + 1}"
        
        import json
        import time
        from datetime import datetime
        
        session_data = dict(self.session)
        session_id = self.session.id if hasattr(self.session, 'id') else 'N/A'
        
        # 生成消息样式
        message_styles = {
            'success': 'background: #d4edda; color: #155724; border-left: 4px solid #28a745;',
            'warning': 'background: #fff3cd; color: #856404; border-left: 4px solid #ffc107;',
            'error': 'background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545;',
            'info': 'background: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8;'
        }
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Session 各后端使用示例</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                    overflow: hidden;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }}
                .header h1 {{
                    font-size: 2.5em;
                    margin-bottom: 10px;
                }}
                .header p {{
                    opacity: 0.9;
                    font-size: 1.1em;
                }}
                .content {{
                    padding: 40px;
                }}
                .section {{
                    margin-bottom: 40px;
                }}
                .section h2 {{
                    color: #333;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 3px solid #667eea;
                }}
                .message {{
                    padding: 15px 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    font-weight: 500;
                }}
                .btn-group {{
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin-bottom: 20px;
                }}
                button {{
                    padding: 12px 24px;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: 600;
                    transition: all 0.3s;
                    font-size: 14px;
                }}
                button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }}
                .btn-primary {{
                    background: #667eea;
                    color: white;
                }}
                .btn-primary:hover {{
                    background: #5568d3;
                }}
                .btn-success {{
                    background: #28a745;
                    color: white;
                }}
                .btn-success:hover {{
                    background: #218838;
                }}
                .btn-warning {{
                    background: #ffc107;
                    color: #212529;
                }}
                .btn-warning:hover {{
                    background: #e0a800;
                }}
                .btn-danger {{
                    background: #dc3545;
                    color: white;
                }}
                .btn-danger:hover {{
                    background: #c82333;
                }}
                .btn-info {{
                    background: #17a2b8;
                    color: white;
                }}
                .btn-info:hover {{
                    background: #138496;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                th {{
                    background: #667eea;
                    color: white;
                    padding: 15px;
                    text-align: left;
                    font-weight: 600;
                }}
                td {{
                    padding: 15px;
                    border-bottom: 1px solid #e0e0e0;
                }}
                tr:hover {{
                    background: #f8f9fa;
                }}
                tr:last-child td {{
                    border-bottom: none;
                }}
                code {{
                    background: #f4f4f4;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    color: #e83e8c;
                }}
                .badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    background: #667eea;
                    color: white;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                .empty-session {{
                    text-align: center;
                    padding: 40px;
                    color: #999;
                    font-style: italic;
                }}
                .info-box {{
                    background: #e3f2fd;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                    border-left: 4px solid #2196F3;
                }}
                .info-box h3 {{
                    color: #1976D2;
                    margin-bottom: 10px;
                }}
                .info-box ul {{
                    margin-left: 20px;
                    color: #555;
                }}
                .info-box li {{
                    margin: 8px 0;
                }}
                .session-id {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 8px;
                    font-family: monospace;
                    margin: 10px 0;
                }}
                pre {{
                    background: #f5f5f5;
                    padding: 20px;
                    border-radius: 8px;
                    overflow-x: auto;
                    font-family: 'Courier New', monospace;
                    font-size: 14px;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 Session 各后端使用示例</h1>
                    <p>演示如何在 Web 应用中使用不同后端的 Session 存储</p>
                </div>

                <div class="content">
                    {message_html}

                    <div class="section">
                        <h2>Session 后端选择</h2>
                        <div class="btn-group">
                            <a href="/session-demo?backend=default">
                                <button class="btn-primary">默认 Session</button>
                            </a>
                            <a href="/session-demo?backend=database">
                                <button class="btn-primary">Database Session</button>
                            </a>
                            <a href="/session-demo?backend=redis">
                                <button class="btn-primary">Redis Session</button>
                            </a>
                            <a href="/session-demo?backend=memcache">
                                <button class="btn-primary">Memcache Session</button>
                            </a>
                        </div>
                    </div>

                    <div class="section">
                        <h2>Session 信息</h2>
                        <div class="session-id">
                            <strong>Session ID:</strong> {session_id}
                        </div>
                    </div>

                    <div class="section">
                        <h2>当前 Session 数据</h2>
                        {session_table}
                    </div>

                    <div class="section">
                        <h2>Session 操作</h2>
                        
                        <h3>基本操作</h3>
                        <div class="btn-group">
                            <a href="/session-demo?action=set&key=username&value=张三&backend={session_backend}">
                                <button class="btn-success">设置 username</button>
                            </a>
                            <a href="/session-demo?action=set&key=email&value=test@example.com&backend={session_backend}">
                                <button class="btn-success">设置 email</button>
                            </a>
                            <a href="/session-demo?action=delete&key=username&backend={session_backend}">
                                <button class="btn-danger">删除 username</button>
                            </a>
                            <a href="/session-demo?action=clear&backend={session_backend}" onclick="return confirm('确定要清除所有 Session 数据吗？')">
                                <button class="btn-danger">清除所有 Session</button>
                            </a>
                        </div>
                        
                        <h3>计数器示例</h3>
                        <div class="btn-group">
                            <a href="/session-demo?action=increment&key=visit_count&backend={session_backend}">
                                <button class="btn-info">访问计数 +1</button>
                            </a>
                            <a href="/session-demo?action=increment&key=click_count&backend={session_backend}">
                                <button class="btn-info">点击计数 +1</button>
                            </a>
                        </div>
                        
                        <h3>预设场景</h3>
                        <div class="btn-group">
                            <a href="/session-demo?action=set_user&backend={session_backend}">
                                <button class="btn-success">设置用户登录信息</button>
                            </a>
                            <a href="/session-demo?action=set_cart&backend={session_backend}">
                                <button class="btn-success">设置购物车数据</button>
                            </a>
                            <a href="/session-demo?action=set_pref&backend={session_backend}">
                                <button class="btn-success">设置用户偏好</button>
                            </a>
                        </div>
                    </div>

                    <div class="section">
                        <h2>Session 原始数据</h2>
                        <pre>{session_json}</pre>
                    </div>

                    <div class="section">
                        <div class="info-box">
                            <h3>💡 Session 使用说明</h3>
                            <ul>
                                <li><strong>设置 Session：</strong>使用 <code>self.session[key] = value</code></li>
                                <li><strong>读取 Session：</strong>使用 <code>self.session[key]</code> 或 <code>self.session.get(key, default)</code></li>
                                <li><strong>删除 Session：</strong>使用 <code>del self.session[key]</code></li>
                                <li><strong>清除 Session：</strong>使用 <code>self.session.clear()</code></li>
                                <li><strong>Session ID：</strong>使用 <code>self.session.id</code> 获取唯一标识</li>
                                <li><strong>遍历 Session：</strong>Session 继承自 UserDict，支持字典操作</li>
                            </ul>
                        </div>
                    </div>

                    <div class="section">
                        <div class="info-box">
                            <h3>🔧 Session 后端配置</h3>
                            <ul>
                                <li><strong>默认 Session：</strong>使用内存缓存，适合开发环境</li>
                                <li><strong>Database Session：</strong>使用 SQLite 数据库，支持持久化存储</li>
                                <li><strong>Redis Session：</strong>使用 Redis 存储，支持分布式部署</li>
                                <li><strong>Memcache Session：</strong>使用 Memcache 存储，提供极高性能</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        # 生成消息 HTML
        message_html = f'<div class="message" style="{message_styles[message_type]}">{message}</div>' if message else ''
        
        # 生成 Session 数据表格
        if session_data:
            session_table = """
            <table>
                <thead>
                    <tr>
                        <th>键</th>
                        <th>值</th>
                        <th>类型</th>
                    </tr>
                </thead>
                <tbody>
            """
            for key, value in session_data.items():
                value_type = type(value).__name__
                if value_type == 'str':
                    display_value = value[:100] + '...' if len(value) > 100 else value
                elif value_type == 'list':
                    display_value = f"[{len(value)} items]"
                elif value_type == 'dict':
                    display_value = f"{{{len(value)} keys}}"
                else:
                    display_value = str(value)
                
                session_table += f"""
        <tr>
            <td><code>{key}</code></td>
            <td>{display_value}</td>
            <td><span class="badge">{value_type}</span></td>
        </tr>
            """
            session_table += """
                </tbody>
            </table>
            """
        else:
            session_table = '<p class="empty-session">当前 Session 为空</p>'
        
        # 生成 Session 原始数据 JSON
        session_json = json.dumps(session_data, indent=2, ensure_ascii=False, default=str)
        
        return html.format(
            message_html=message_html,
            session_id=session_id,
            session_table=session_table,
            session_json=session_json,
            session_backend=session_backend
        )

    # 定义 get-put 路由
    @get('/get-put')
    def get_put_handler(self):
        print(self.session_id, self.session.get('name'))
        self.session['name'] = 'Tomy2'
        # 手动保存 Session 数据
        self.session.save()
        return 'get put name'

    # 注册路由
    app.register_routes(session_demo_handler)
    app.register_routes(get_put_handler)

    # 运行应用
    app.run()


def main():
    """主函数"""
    print("Litefs Session 各后端使用示例")
    print("=" * 60)
    print("本示例演示如何使用不同后端的 Session 存储")
    print("包括直接使用和在 Web 应用中使用")
    print("=" * 60)
    print()

    # 运行示例
    example_1_database_session_direct()
    example_2_redis_session_direct()
    example_3_memcache_session_direct()
    example_4_session_factory()
    example_5_web_app_session()


if __name__ == '__main__':
    main()
