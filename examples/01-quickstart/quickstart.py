#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs
from litefs.routing import get, post


@get('/hello', name='hello')
def hello_handler(request):
    """Hello World 处理函数"""
    return {
        'message': 'Hello, World!',
        'method': request.method,
        'path': request.path_info
    }


@get('/user/{id}', name='user_detail')
def user_handler(request, id):
    """用户详情处理函数"""
    return {
        'user_id': id,
        'message': f'User details for ID {id}'
    }


@post('/form', name='form_submit')
def form_handler(request):
    """表单处理函数"""
    return {
        'message': 'Form submitted successfully',
        'data': request.data
    }

def main():
    """快速入门示例 - 最简单的 Litefs 应用"""
    app = litefs.Litefs(
        host='0.0.0.0',
        port=8080,
        debug=True
    )
    
    # 使用新的路由系统（方法链风格）
    @app.add_get('/hello_route', name='hello_route')
    def hello_route_handler(request):
        return {'message': 'Hello from route!'}
    
    # 注册装饰器定义的路由
    app.register_routes(__name__)
    
    print("=" * 60)
    print("Litefs Quick Start Example")
    print("=" * 60)
    print(f"Version: {litefs.__version__}")
    print(f"访问地址: http://localhost:8080")
    print("=" * 60)
    print("路由系统示例:")
    print("  GET  /hello          - Hello World 路由（装饰器风格）")
    print("  GET  /user/{id}      - 用户详情路由")
    print("  POST /form           - 表单提交路由")
    print("  GET  /hello_route    - Hello World 路由（方法链风格）")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
