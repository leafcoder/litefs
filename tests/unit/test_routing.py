#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import Litefs
from litefs.routing import Router, Route, route, get, post, put, delete


class TestRoute(unittest.TestCase):
    """测试 Route 类"""

    def test_route_creation(self):
        """测试创建 Route 对象"""
        def handler(request):
            pass

        route = Route('/hello', ['GET'], handler, name='hello')
        self.assertEqual(route.path, '/hello')
        self.assertEqual(route.methods, ['GET'])
        self.assertEqual(route.handler, handler)
        self.assertEqual(route.name, 'hello')

    def test_route_match_exact(self):
        """测试精确路径匹配"""
        def handler(request):
            pass

        route = Route('/hello', ['GET'], handler)
        params = route.match('/hello', 'GET')
        self.assertIsNotNone(params)
        self.assertEqual(params, {})

    def test_route_match_with_params(self):
        """测试带路径参数的匹配"""
        def handler(request):
            pass

        route = Route('/user/{id}', ['GET'], handler)
        params = route.match('/user/123', 'GET')
        self.assertIsNotNone(params)
        self.assertEqual(params, {'id': '123'})

    def test_route_match_no_match(self):
        """测试路径不匹配"""
        def handler(request):
            pass

        route = Route('/hello', ['GET'], handler)
        params = route.match('/world', 'GET')
        self.assertIsNone(params)

    def test_route_match_method_no_match(self):
        """测试方法不匹配"""
        def handler(request):
            pass

        route = Route('/hello', ['GET'], handler)
        params = route.match('/hello', 'POST')
        self.assertIsNone(params)


class TestRouter(unittest.TestCase):
    """测试 Router 类"""

    def setUp(self):
        """设置测试环境"""
        self.router = Router()

    def test_add_route(self):
        """测试添加路由"""
        def handler(request):
            pass

        self.router.add_route('/hello', ['GET'], handler, name='hello')
        self.assertEqual(len(self.router.routes), 1)

    def test_add_get(self):
        """测试添加 GET 路由"""
        def handler(request):
            pass

        self.router.add_get('/hello', handler, name='hello')
        self.assertEqual(len(self.router.routes), 1)
        self.assertEqual(self.router.routes[0].methods, ['GET'])

    def test_add_post(self):
        """测试添加 POST 路由"""
        def handler(request):
            pass

        self.router.add_post('/hello', handler, name='hello')
        self.assertEqual(len(self.router.routes), 1)
        self.assertEqual(self.router.routes[0].methods, ['POST'])

    def test_match_route(self):
        """测试匹配路由"""
        def handler(request):
            pass

        self.router.add_get('/hello', handler, name='hello')
        self.router.add_get('/user/{id}', handler, name='user_detail')

        # 测试精确匹配
        route_match = self.router.match('/hello', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(params, {})

        # 测试路径参数匹配
        route_match = self.router.match('/user/123', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(params, {'id': '123'})

    def test_match_route_not_found(self):
        """测试路由未找到"""
        def handler(request):
            pass

        self.router.add_get('/hello', handler, name='hello')

        route_match = self.router.match('/world', 'GET')
        self.assertIsNone(route_match)

    def test_url_for(self):
        """测试 URL 反向生成"""
        def handler(request):
            pass

        self.router.add_get('/user/{id}', handler, name='user_detail')
        url = self.router.url_for('user_detail', id=123)
        self.assertEqual(url, '/user/123')

    def test_url_for_with_multiple_params(self):
        """测试带多个参数的 URL 反向生成"""
        def handler(request):
            pass

        self.router.add_get('/user/{id}/posts/{post_id}', handler, name='user_post')
        url = self.router.url_for('user_post', id=123, post_id=456)
        self.assertEqual(url, '/user/123/posts/456')


class TestRouteDecorators(unittest.TestCase):
    """测试路由装饰器"""

    def test_route_decorator(self):
        """测试 route 装饰器"""
        router = Router()

        @route('/hello', ['GET'], name='hello')
        def hello_handler(request):
            return 'Hello, World!'

        # 手动添加路由到路由器
        router.add_route('/hello', ['GET'], hello_handler, name='hello')

        route_match = router.match('/hello', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(handler, hello_handler)

    def test_get_decorator(self):
        """测试 get 装饰器"""
        router = Router()

        @get('/hello', name='hello')
        def hello_handler(request):
            return 'Hello, World!'

        # 手动添加路由到路由器
        router.add_route('/hello', ['GET'], hello_handler, name='hello')

        route_match = router.match('/hello', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(handler, hello_handler)

    def test_post_decorator(self):
        """测试 post 装饰器"""
        router = Router()

        @post('/form', name='form')
        def form_handler(request):
            return {'status': 'success'}

        # 手动添加路由到路由器
        router.add_route('/form', ['POST'], form_handler, name='form')

        route_match = router.match('/form', 'POST')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(handler, form_handler)


class TestLitefsRouting(unittest.TestCase):
    """测试 Litefs 路由集成"""

    def setUp(self):
        """设置测试环境"""
        self.app = Litefs(webroot='./site')

    def test_add_get_route(self):
        """测试添加 GET 路由"""
        def handler(request):
            return 'Hello, World!'

        self.app.add_get('/hello', handler, name='hello')
        self.assertEqual(len(self.app.router.routes), 1)

    def test_add_post_route(self):
        """测试添加 POST 路由"""
        def handler(request):
            return {'status': 'success'}

        self.app.add_post('/form', handler, name='form')
        self.assertEqual(len(self.app.router.routes), 1)

    def test_register_routes(self):
        """测试注册路由"""
        # 创建一个包含路由的模块
        import types
        routes_module = types.ModuleType('routes_module')

        @get('/hello', name='hello')
        def hello_handler(request):
            return 'Hello, World!'

        @post('/form', name='form')
        def form_handler(request):
            return {'status': 'success'}

        routes_module.hello_handler = hello_handler
        routes_module.form_handler = form_handler

        # 注册路由
        self.app.register_routes(routes_module)
        self.assertEqual(len(self.app.router.routes), 2)

    def test_router_integration(self):
        """测试路由系统集成"""
        # 定义路由处理函数
        def hello_handler(request):
            return 'Hello, World!'

        def user_detail_handler(request, id):
            return f'User: {id}'

        # 使用方法链添加路由
        self.app.add_get('/hello', hello_handler, name='hello')
        self.app.add_get('/user/{id}', user_detail_handler, name='user_detail')

        # 测试路由匹配
        route_match = self.app.router.match('/hello', 'GET')
        self.assertIsNotNone(route_match)

        route_match = self.app.router.match('/user/123', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(params, {'id': '123'})


class TestStaticRouting(unittest.TestCase):
    """测试静态文件路由"""

    def setUp(self):
        """设置测试环境"""
        self.app = Litefs(webroot='./site')
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, 'test.txt')
        with open(self.temp_file, 'w') as f:
            f.write('Hello, World!')

    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_add_static_route(self):
        """测试添加静态文件路由"""
        self.app.add_static('/static', self.temp_dir, name='static')
        self.assertEqual(len(self.app.router.routes), 1)
        self.assertEqual(self.app.router.static_prefix, '/static')
        self.assertEqual(self.app.router.static_directory, self.temp_dir)

    def test_static_route_match(self):
        """测试静态文件路由匹配"""
        self.app.add_static('/static', self.temp_dir, name='static')
        
        route_match = self.app.router.match('/static/test.txt', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(params, {'file_path': 'test.txt'})

    def test_static_route_with_subpath(self):
        """测试带子路径的静态文件路由匹配"""
        sub_dir = os.path.join(self.temp_dir, 'subdir')
        os.makedirs(sub_dir)
        sub_file = os.path.join(sub_dir, 'test.txt')
        with open(sub_file, 'w') as f:
            f.write('Hello, Subdir!')

        self.app.add_static('/static', self.temp_dir, name='static')
        
        route_match = self.app.router.match('/static/subdir/test.txt', 'GET')
        self.assertIsNotNone(route_match)
        handler, params = route_match
        self.assertEqual(params, {'file_path': 'subdir/test.txt'})

        # 清理
        os.remove(sub_file)
        os.rmdir(sub_dir)

    def test_static_route_handler(self):
        """测试静态文件路由处理函数"""
        self.app.add_static('/static', self.temp_dir, name='static')
        
        route_match = self.app.router.match('/static/test.txt', 'GET')
        handler, params = route_match
        
        # 模拟请求处理器
        mock_request = MagicMock()
        mock_request.start_response = MagicMock()
        
        result = handler(mock_request, file_path='test.txt')
        
        # 验证响应
        self.assertIsNotNone(result)
        self.assertEqual(mock_request.start_response.call_count, 1)
        call_args = mock_request.start_response.call_args[0]
        self.assertEqual(call_args[0], 200)
        
        # 验证响应头
        headers = call_args[1]
        content_type = [h[1] for h in headers if h[0] == 'Content-Type'][0]
        self.assertIn('text/plain', content_type)


if __name__ == '__main__':
    unittest.main()
