#!/usr/bin/env python
# coding: utf-8

"""
REST API 示例

展示 Litefs 的 API 开发特性：
- RESTful 路由
- JWT 认证
- OpenAPI 文档
- 请求验证
- 流式响应
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get, post, put, delete
from litefs.auth import Auth, init_default_roles_and_permissions
from litefs.auth.models import User, Role
from litefs.auth.password import hash_password
from litefs.auth.middleware import login_required, role_required
from litefs.openapi import OpenAPI

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)

auth = Auth(app, secret_key='your-secret-key-change-in-production')

init_default_roles_and_permissions()

admin_role = Role.get_by_name('admin')
User.create(
    username='admin',
    password_hash=hash_password('admin123'),
    roles=[admin_role],
)

openapi = OpenAPI(app, title='Litefs API', version='1.0.0')

ITEMS = [
    {'id': 1, 'name': 'Item 1', 'price': 100},
    {'id': 2, 'name': 'Item 2', 'price': 200},
    {'id': 3, 'name': 'Item 3', 'price': 300},
]


@get('/', name='index')
def index(request):
    """API 首页"""
    return {
        'name': 'Litefs REST API',
        'version': '1.0.0',
        'endpoints': [
            {'method': 'GET', 'path': '/api/items', 'desc': '获取列表'},
            {'method': 'GET', 'path': '/api/items/{id}', 'desc': '获取详情'},
            {'method': 'POST', 'path': '/api/items', 'desc': '创建项目'},
            {'method': 'PUT', 'path': '/api/items/{id}', 'desc': '更新项目'},
            {'method': 'DELETE', 'path': '/api/items/{id}', 'desc': '删除项目'},
            {'method': 'GET', 'path': '/api/stream', 'desc': '流式响应'},
            {'method': 'GET', 'path': '/openapi.json', 'desc': 'OpenAPI 文档'},
            {'method': 'GET', 'path': '/docs', 'desc': 'Swagger UI'},
        ]
    }


@get('/api/items', name='list_items')
def list_items(request):
    """获取项目列表"""
    return {'items': ITEMS, 'total': len(ITEMS)}


@get('/api/items/{id}', name='get_item')
def get_item(request, id):
    """获取项目详情"""
    item_id = int(id)
    for item in ITEMS:
        if item['id'] == item_id:
            return {'item': item}
    return {'error': 'Not found'}, 404


@post('/api/items', name='create_item')
@login_required
def create_item(request):
    """创建项目"""
    data = request.json if hasattr(request, 'json') else {}
    new_item = {
        'id': len(ITEMS) + 1,
        'name': data.get('name', 'New Item'),
        'price': data.get('price', 0),
    }
    ITEMS.append(new_item)
    return {'item': new_item}, 201


@put('/api/items/{id}', name='update_item')
@login_required
def update_item(request, id):
    """更新项目"""
    item_id = int(id)
    data = request.json if hasattr(request, 'json') else {}

    for item in ITEMS:
        if item['id'] == item_id:
            item['name'] = data.get('name', item['name'])
            item['price'] = data.get('price', item['price'])
            return {'item': item}

    return {'error': 'Not found'}, 404


@delete('/api/items/{id}', name='delete_item')
@role_required('admin')
def delete_item(request, id):
    """删除项目（需要管理员权限）"""
    global ITEMS
    item_id = int(id)
    ITEMS = [i for i in ITEMS if i['id'] != item_id]
    return {'status': 'deleted'}


@get('/api/stream', name='stream_data')
def stream_data(request):
    """流式响应示例"""
    def generate():
        for i in range(10):
            yield json.dumps({'index': i, 'data': f'Chunk {i}'}) + '\n'
    return generate(), {'Content-Type': 'application/x-ndjson'}


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs REST API 示例")
    print("=" * 60)
    print()
    print("展示特性:")
    print("  - RESTful 路由")
    print("  - JWT 认证")
    print("  - 角色权限控制")
    print("  - OpenAPI 文档")
    print("  - 流式响应")
    print()
    print("测试账号: admin / admin123")
    print("API 文档: http://localhost:8080/docs")
    print("=" * 60)

    app.run()
