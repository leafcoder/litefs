#!/usr/bin/env python
# coding: utf-8

"""
请求属性测试示例

验证在新的路由系统中，request 对象的各种属性是否正常工作
"""

import litefs
from litefs.routing import get, post

# 创建应用实例
app = litefs.Litefs(
    host='localhost',
    port=9090,
    webroot='./site',
    debug=True
)

@get('/test-request', name='test_request')
def test_request_handler(request):
    """测试请求属性"""
    # 从 environ 中获取头信息
    headers = {}
    for key, value in request.environ.items():
        if key.startswith('HTTP_'):
            headers[key[5:].replace('_', '-').title()] = value
    
    return {
        'method': request.method,
        'path_info': request.path_info,
        'get_params': dict(request.params),
        'post_params': dict(request.data),
        'headers': headers,
        'cookies': dict(request.cookie),
        'session': dict(request.session),
        'route_params': getattr(request, 'route_params', {})
    }

@post('/test-form', name='test_form')
def test_form_handler(request):
    """测试表单提交"""
    return {
        'method': request.method,
        'post_params': dict(request.data),
        'files': {
            key: {
                'name': fp.name,
                'size': len(fp.read()),
                'content_type': getattr(fp, 'content_type', 'unknown')
            }
            for key, fp in request.files.items()
        },
        'body': request.body.decode('utf-8', errors='replace') if request.body else None
    }

@get('/test-path/{id}/{name}', name='test_path_params')
def test_path_params_handler(request, id, name):
    """测试路径参数"""
    return {
        'id': id,
        'name': name,
        'route_params': getattr(request, 'route_params', {})
    }

# 注册路由
app.register_routes(__name__)

if __name__ == '__main__':
    print("Starting request attribute test server...")
    print("Available routes:")
    print("GET  /test-request          - Test request attributes")
    print("POST /test-form             - Test form submission")
    print("GET  /test-path/{id}/{name} - Test path parameters")
    print("\nServer running at http://localhost:9090")
    app.run()
