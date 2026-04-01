#!/usr/bin/env python
# coding: utf-8

"""
路由系统示例

演示如何使用 Litefs 新的路由系统
"""

import litefs
from litefs.routing import get, post, put, delete

# 创建应用实例
app = litefs.Litefs(
    host='localhost',
    port=9090,
    webroot='./site',
    debug=True
)

# 方法 1: 使用装饰器定义路由
@get('/hello', name='hello')
def hello_handler(request):
    """简单的 GET 请求处理"""
    return {
        'message': 'Hello, World!',
        'method': request.method,
        'path': request.path_info
    }

@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    """带路径参数的 GET 请求处理"""
    return {
        'user_id': id,
        'message': f'User details for ID {id}'
    }

@post('/user', name='create_user')
def create_user_handler(request):
    """POST 请求处理"""
    return {
        'message': 'User created successfully',
        'data': request.post
    }

@put('/user/{id}', name='update_user')
def update_user_handler(request, id):
    """PUT 请求处理"""
    return {
        'user_id': id,
        'message': f'User {id} updated successfully',
        'data': request.post
    }

@delete('/user/{id}', name='delete_user')
def delete_user_handler(request, id):
    """DELETE 请求处理"""
    return {
        'user_id': id,
        'message': f'User {id} deleted successfully'
    }

# 方法 2: 使用方法链添加路由
@app.add_get('/api/status', name='api_status')
def api_status_handler(request):
    """API 状态检查"""
    return {
        'status': 'ok',
        'timestamp': litefs.utils.gmt_date()
    }

# 注册路由装饰器定义的路由
app.register_routes(__name__)

if __name__ == '__main__':
    print("Starting server with new routing system...")
    print("Available routes:")
    print("GET  /hello              - Hello World")
    print("GET  /user/{id}          - User details")
    print("POST /user               - Create user")
    print("PUT  /user/{id}          - Update user")
    print("DELETE /user/{id}       - Delete user")
    print("GET  /api/status         - API status")
    
    # 调试：打印已注册的路由
    print("\nDebug: Registered routes:")
    for i, route in enumerate(app.router.routes):
        print(f"{i+1}. {route.methods} {route.path} - {route.name}")
    
    print("\nServer running at http://localhost:9090")
    app.run()
