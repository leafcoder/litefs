#!/usr/bin/env python
# coding: utf-8

"""
开发调试工具示例

本示例展示如何使用 Litefs 的开发调试工具：
- 请求/响应检查器
- SQL 查询日志
- 性能分析器
- 错误追踪面板

启用方式：
    export LITEFS_DEBUG=1
    python app.py

测试步骤：
1. 启动服务器（带 LITEFS_DEBUG=1）
2. 访问 http://localhost:8080/
3. 查看终端输出的调试信息
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get, post
from litefs.debug import track_sql, track_performance

os.environ['LITEFS_DEBUG'] = '1'

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)


@get('/', name='index')
def index(request):
    """首页"""
    return {
        'message': 'Welcome to Litefs Debug Demo',
        'endpoints': [
            {'path': '/api/users', 'method': 'GET', 'description': '获取用户列表'},
            {'path': '/api/users/{id}', 'method': 'GET', 'description': '获取用户详情'},
            {'path': '/api/orders', 'method': 'GET', 'description': '获取订单列表（模拟慢查询）'},
            {'path': '/api/error', 'method': 'GET', 'description': '触发错误'},
        ]
    }


@get('/api/users', name='list_users')
def list_users(request):
    """获取用户列表"""
    with track_sql('SELECT * FROM users WHERE status = ?', ('active',)):
        time.sleep(0.005)
    
    with track_sql('SELECT COUNT(*) FROM users'):
        time.sleep(0.002)
    
    return {
        'users': [
            {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
            {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
            {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
        ]
    }


@get('/api/users/{id}', name='get_user')
def get_user(request):
    """获取用户详情"""
    user_id = request.path_params.get('id')
    
    with track_sql('SELECT * FROM users WHERE id = ?', (user_id,)):
        time.sleep(0.003)
    
    with track_sql('SELECT * FROM orders WHERE user_id = ?', (user_id,)):
        time.sleep(0.008)
    
    return {
        'id': user_id,
        'name': f'User {user_id}',
        'email': f'user{user_id}@example.com',
        'orders_count': 5,
    }


@get('/api/orders', name='list_orders')
def list_orders(request):
    """获取订单列表（模拟慢查询）"""
    with track_sql('SELECT * FROM orders WHERE created_at > ? ORDER BY created_at DESC', ('2024-01-01',)):
        time.sleep(0.015)
    
    with track_sql('SELECT * FROM order_items WHERE order_id IN (SELECT id FROM orders)'):
        time.sleep(0.020)
    
    return {
        'orders': [
            {'id': 1, 'total': 99.99, 'status': 'completed'},
            {'id': 2, 'total': 149.99, 'status': 'pending'},
        ]
    }


@get('/api/error', name='trigger_error')
def trigger_error(request):
    """触发错误"""
    raise ValueError('This is a test error for debugging')


@post('/api/data', name='post_data')
def post_data(request):
    """POST 请求示例"""
    body = request.json if hasattr(request, 'json') else {}
    
    with track_sql('INSERT INTO data (key, value) VALUES (?, ?)', ('test', str(body))):
        time.sleep(0.002)
    
    return {
        'status': 'success',
        'received': body,
    }


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("开发调试工具示例")
    print("=" * 60)
    print()
    print("调试模式已启用 (LITEFS_DEBUG=1)")
    print()
    print("测试端点:")
    print("  GET  /              - 首页")
    print("  GET  /api/users     - 用户列表")
    print("  GET  /api/users/1   - 用户详情")
    print("  GET  /api/orders    - 订单列表（慢查询）")
    print("  GET  /api/error     - 触发错误")
    print("  POST /api/data      - POST 请求")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
