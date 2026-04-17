#!/usr/bin/env python
# coding: utf-8

"""
OpenAPI/Swagger 文档自动生成示例

本示例展示如何使用 Litefs 的 OpenAPI 文档自动生成功能：
- 自动从路由生成 API 文档
- 使用装饰器添加详细的 API 信息
- Swagger UI 界面
- 认证配置
- Schema 定义

访问文档：
http://localhost:8080/docs
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, get, post, put, delete
from litefs.openapi import OpenAPI

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)

openapi = OpenAPI(
    app,
    title='用户管理 API',
    version='1.0.0',
    description='一个简单的用户管理 REST API 示例',
)

openapi.add_tag('users', '用户管理')
openapi.add_tag('health', '健康检查')

openapi.add_server('http://localhost:8080', '开发服务器')

openapi.add_security_scheme('bearerAuth', {
    'type': 'http',
    'scheme': 'bearer',
    'bearerFormat': 'JWT',
})


@openapi.schema('User')
class User:
    id: int
    name: str
    email: str
    age: int = 0


@openapi.schema('CreateUser')
class CreateUser:
    name: str
    email: str
    age: int = 0


users_db = {
    1: {'id': 1, 'name': 'Alice', 'email': 'alice@example.com', 'age': 25},
    2: {'id': 2, 'name': 'Bob', 'email': 'bob@example.com', 'age': 30},
}


@get('/', name='index')
def index(request):
    """API 首页"""
    return {
        'message': '用户管理 API',
        'docs': '/docs',
        'openapi': '/openapi.json',
    }


@get('/users', name='list_users')
@openapi.doc(
    summary='获取用户列表',
    description='获取所有用户的列表',
    tags=['users'],
    response={
        'description': '用户列表',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'users': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/User'}
                        }
                    }
                }
            }
        }
    }
)
def list_users(request):
    """获取用户列表"""
    return {'users': list(users_db.values())}


@get('/users/{user_id}', name='get_user')
@openapi.doc(
    summary='获取用户详情',
    description='根据 ID 获取单个用户的详细信息',
    tags=['users'],
    parameters=[
        {
            'name': 'user_id',
            'in': 'path',
            'required': True,
            'description': '用户 ID',
            'schema': {'type': 'integer'}
        }
    ],
    response={
        'description': '用户详情',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/User'}
            }
        }
    }
)
def get_user(request, user_id: int):
    """获取用户详情"""
    user = users_db.get(int(user_id))
    if not user:
        return {'error': '用户不存在'}, 404
    return user


@post('/users', name='create_user')
@openapi.doc(
    summary='创建用户',
    description='创建一个新用户',
    tags=['users'],
    request_body={
        'required': True,
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/CreateUser'}
            }
        }
    },
    response={
        'description': '创建的用户',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/User'}
            }
        }
    }
)
def create_user(request):
    """创建用户"""
    data = request.json or {}
    
    new_id = max(users_db.keys()) + 1 if users_db else 1
    user = {
        'id': new_id,
        'name': data.get('name', ''),
        'email': data.get('email', ''),
        'age': data.get('age', 0),
    }
    users_db[new_id] = user
    
    return user


@put('/users/{user_id}', name='update_user')
@openapi.doc(
    summary='更新用户',
    description='更新指定用户的信息',
    tags=['users'],
    parameters=[
        {
            'name': 'user_id',
            'in': 'path',
            'required': True,
            'description': '用户 ID',
            'schema': {'type': 'integer'}
        }
    ],
    request_body={
        'required': True,
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/CreateUser'}
            }
        }
    },
    response={
        'description': '更新后的用户',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/User'}
            }
        }
    }
)
def update_user(request, user_id: int):
    """更新用户"""
    uid = int(user_id)
    if uid not in users_db:
        return {'error': '用户不存在'}, 404
    
    data = request.json or {}
    user = users_db[uid]
    user.update({
        'name': data.get('name', user['name']),
        'email': data.get('email', user['email']),
        'age': data.get('age', user['age']),
    })
    
    return user


@delete('/users/{user_id}', name='delete_user')
@openapi.doc(
    summary='删除用户',
    description='删除指定用户',
    tags=['users'],
    parameters=[
        {
            'name': 'user_id',
            'in': 'path',
            'required': True,
            'description': '用户 ID',
            'schema': {'type': 'integer'}
        }
    ],
    response={
        'description': '删除结果',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string'}
                    }
                }
            }
        }
    }
)
def delete_user(request, user_id: int):
    """删除用户"""
    uid = int(user_id)
    if uid not in users_db:
        return {'error': '用户不存在'}, 404
    
    del users_db[uid]
    return {'message': '用户已删除'}


@get('/health', name='health_check')
@openapi.doc(
    summary='健康检查',
    description='检查服务是否正常运行',
    tags=['health'],
    response={
        'description': '健康状态',
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'status': {'type': 'string'},
                        'message': {'type': 'string'}
                    }
                }
            }
        }
    }
)
def health_check(request):
    """健康检查"""
    return {'status': 'ok', 'message': '服务正常运行'}


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("OpenAPI/Swagger 文档自动生成示例")
    print("=" * 60)
    print()
    print("API 文档地址：")
    print("  Swagger UI:  http://localhost:8080/docs")
    print("  OpenAPI JSON: http://localhost:8080/openapi.json")
    print()
    print("API 端点：")
    print("  GET    /              - API 首页")
    print("  GET    /users         - 获取用户列表")
    print("  GET    /users/{id}    - 获取用户详情")
    print("  POST   /users         - 创建用户")
    print("  PUT    /users/{id}    - 更新用户")
    print("  DELETE /users/{id}    - 删除用户")
    print("  GET    /health        - 健康检查")
    print()
    print("测试命令：")
    print("  # 获取用户列表")
    print("  curl http://localhost:8080/users")
    print()
    print("  # 创建用户")
    print("  curl -X POST http://localhost:8080/users \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"name\": \"Charlie\", \"email\": \"charlie@example.com\"}'")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
