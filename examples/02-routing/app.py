#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
路由系统示例 - 展示 Litefs 的各种路由功能

这个示例展示了 Litefs 路由系统的完整功能，包括：
- 装饰器路由
- 方法链路由
- 路径参数
- 各种 HTTP 方法
- 请求参数处理
"""

import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))  # noqa: E402

from litefs import Litefs  # noqa: E402
from litefs.routing import get, post, put, delete  # noqa: E402

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

# ==================== 方法 1: 使用装饰器定义路由 ====================

@get('/', name='index')
def index_handler(request):
    """首页"""
    return {
        'message': 'Welcome to Litefs Routing Demo',
        'available_endpoints': [
            '/users - GET 获取所有用户',
            '/users - POST 创建用户',
            '/users/{id} - GET 获取用户详情',
            '/users/{id} - PUT 更新用户',
            '/users/{id} - DELETE 删除用户',
            '/search?q=keyword - 搜索',
        ]
    }


@get('/users', name='user_list')
def user_list_handler(request):
    """获取用户列表"""
    # 获取查询参数
    page = int(request.params.get('page', 1))
    limit = int(request.params.get('limit', 10))
    
    # 模拟用户数据
    users = [
        {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
        {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
        {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
    ]
    
    return {
        'users': users,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': len(users)
        }
    }


@post('/users', name='create_user')
def create_user_handler(request):
    """创建用户"""
    # 获取 POST 数据
    name = request.data.get('name')
    email = request.data.get('email')
    
    if not name or not email:
        request.start_response(400, [('Content-Type', 'application/json')])
        return {'error': 'Name and email are required'}
    
    return {
        'message': 'User created successfully',
        'user': {
            'id': 4,
            'name': name,
            'email': email
        }
    }


@get('/users/{id}', name='user_detail')
def user_detail_handler(request, id):
    """获取用户详情 - 带路径参数"""
    # 模拟用户数据
    users = {
        '1': {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
        '2': {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
        '3': {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
    }
    
    user = users.get(id)
    if not user:
        request.start_response(404, [('Content-Type', 'application/json')])
        return {'error': f'User {id} not found'}
    
    return {'user': user}


@put('/users/{id}', name='update_user')
def update_user_handler(request, id):
    """更新用户"""
    name = request.data.get('name')
    email = request.data.get('email')
    
    return {
        'message': f'User {id} updated successfully',
        'user': {
            'id': id,
            'name': name,
            'email': email
        }
    }


@delete('/users/{id}', name='delete_user')
def delete_user_handler(request, id):
    """删除用户"""
    return {
        'message': f'User {id} deleted successfully'
    }


# ==================== 方法 2: 使用方法链添加路由 ====================

@app.add_get('/search', name='search')
def search_handler(request):
    """搜索功能 - 演示查询参数"""
    query = request.params.get('q', '')
    category = request.params.get('category', 'all')
    
    # 模拟搜索结果
    results = [
        {'id': 1, 'title': f'Result for {query} 1', 'category': category},
        {'id': 2, 'title': f'Result for {query} 2', 'category': category},
    ]
    
    return {
        'query': query,
        'category': category,
        'results': results,
        'total': len(results)
    }


@app.add_get('/products/{category}/{id}', name='product_detail')
def product_detail_handler(request, category, id):
    """产品详情 - 多个路径参数"""
    return {
        'category': category,
        'product_id': id,
        'name': f'Product {id} in {category}',
        'price': 99.99
    }


# 注册装饰器定义的路由
app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs Routing System Demo")
    print("=" * 60)
    print("访问地址: http://localhost:8080")
    print("=" * 60)
    print("可用路由:")
    print("  GET    /                    - 首页")
    print("  GET    /users               - 获取用户列表")
    print("  POST   /users               - 创建用户")
    print("  GET    /users/{id}          - 获取用户详情")
    print("  PUT    /users/{id}          - 更新用户")
    print("  DELETE /users/{id}          - 删除用户")
    print("  GET    /search?q=keyword    - 搜索")
    print("  GET    /products/{cat}/{id} - 产品详情")
    print("=" * 60)
    
    app.run()
