#!/usr/bin/env python
# coding: utf-8

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.middleware import (
    Middleware,
    MiddlewareManager,
    LoggingMiddleware,
    CORSMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
    ThrottleMiddleware,
)


class TestMiddlewareManager(unittest.TestCase):
    """中间件管理器测试"""

    def test_add_middleware(self):
        """测试添加中间件"""
        manager = MiddlewareManager()
        
        class TestMiddleware(Middleware):
            pass
        
        manager.add(TestMiddleware)
        
        self.assertEqual(len(manager._middlewares), 1)
        middleware_class, kwargs = manager._middlewares[0]
        self.assertEqual(middleware_class, TestMiddleware)
        self.assertEqual(kwargs, {})

    def test_remove_middleware(self):
        """测试移除中间件"""
        manager = MiddlewareManager()
        
        class TestMiddleware(Middleware):
            pass
        
        manager.add(TestMiddleware)
        manager.remove(TestMiddleware)
        
        self.assertEqual(len(manager._middlewares), 0)

    def test_clear_middleware(self):
        """测试清空中间件"""
        manager = MiddlewareManager()
        
        class TestMiddleware1(Middleware):
            pass
        
        class TestMiddleware2(Middleware):
            pass
        
        manager.add(TestMiddleware1)
        manager.add(TestMiddleware2)
        manager.clear()
        
        self.assertEqual(len(manager._middlewares), 0)

    def test_get_middleware_instances(self):
        """测试获取中间件实例"""
        manager = MiddlewareManager()
        
        class TestMiddleware(Middleware):
            def __init__(self, app, param1=None, param2=None):
                super().__init__(app)
                self.app = app
                self.param1 = param1
                self.param2 = param2
        
        manager.add(TestMiddleware, param1='value1', param2='value2')
        app = Mock()
        instances = manager.get_middleware_instances(app)
        
        self.assertEqual(len(instances), 1)
        self.assertIsInstance(instances[0], TestMiddleware)
        self.assertEqual(instances[0].app, app)
        self.assertEqual(instances[0].param1, 'value1')
        self.assertEqual(instances[0].param2, 'value2')

    def test_add_middleware_with_kwargs(self):
        """测试添加带参数的中间件"""
        manager = MiddlewareManager()
        
        class TestMiddleware(Middleware):
            def __init__(self, app, custom_param=None):
                super().__init__(app)
                self.custom_param = custom_param
        
        manager.add(TestMiddleware, custom_param='test_value')
        
        self.assertEqual(len(manager._middlewares), 1)
        middleware_class, kwargs = manager._middlewares[0]
        self.assertEqual(middleware_class, TestMiddleware)
        self.assertEqual(kwargs, {'custom_param': 'test_value'})


class TestLoggingMiddleware(unittest.TestCase):
    """日志中间件测试"""

    def test_process_request(self):
        """测试请求处理"""
        app = Mock()
        middleware = LoggingMiddleware(app)
        request_handler = Mock()
        request_handler.environ = {
            'REMOTE_ADDR': '127.0.0.1',
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/test',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        
        result = middleware.process_request(request_handler)
        
        self.assertIsNone(result)
        self.assertTrue(hasattr(request_handler, '_start_time'))

    def test_process_response(self):
        """测试响应处理"""
        app = Mock()
        middleware = LoggingMiddleware(app)
        request_handler = Mock()
        request_handler.environ = {
            'REMOTE_ADDR': '127.0.0.1',
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/test',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        request_handler._start_time = 0.0
        
        response = ('200 OK', [], b'content')
        result = middleware.process_response(request_handler, response)
        
        self.assertEqual(result, response)


class TestCORSMiddleware(unittest.TestCase):
    """CORS 中间件测试"""

    def test_process_request_options(self):
        """测试 OPTIONS 请求处理"""
        app = Mock()
        middleware = CORSMiddleware(app)
        request_handler = Mock()
        request_handler.environ = {
            'REQUEST_METHOD': 'OPTIONS',
            'HTTP_ORIGIN': 'http://localhost:3000',
            'HTTP_ACCESS_CONTROL_REQUEST_METHOD': 'POST',
        }
        
        result = middleware.process_request(request_handler)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_process_request_get(self):
        """测试 GET 请求处理"""
        app = Mock()
        middleware = CORSMiddleware(app)
        request_handler = Mock()
        request_handler.environ = {
            'REQUEST_METHOD': 'GET',
            'HTTP_ORIGIN': 'http://localhost:3000',
        }
        
        result = middleware.process_request(request_handler)
        
        self.assertIsNone(result)

    def test_process_response(self):
        """测试响应处理"""
        app = Mock()
        middleware = CORSMiddleware(app)
        request_handler = Mock()
        request_handler.environ = {
            'HTTP_ORIGIN': 'http://localhost:3000',
        }
        
        response = ('200 OK', [], b'content')
        result = middleware.process_response(request_handler, response)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        
        status, headers, content = result
        self.assertEqual(status, '200 OK')
        self.assertEqual(content, b'content')
        
        header_names = [h[0] for h in headers]
        self.assertIn('Access-Control-Allow-Origin', header_names)

    def test_is_origin_allowed(self):
        """测试来源验证"""
        app = Mock()
        middleware = CORSMiddleware(
            app,
            allow_origins=['http://localhost:3000', 'https://example.com']
        )
        
        self.assertTrue(middleware._is_origin_allowed('http://localhost:3000'))
        self.assertTrue(middleware._is_origin_allowed('https://example.com'))
        self.assertFalse(middleware._is_origin_allowed('http://evil.com'))


class TestSecurityMiddleware(unittest.TestCase):
    """安全中间件测试"""

    def test_process_response(self):
        """测试响应处理"""
        app = Mock()
        middleware = SecurityMiddleware(app)
        request_handler = Mock()
        
        response = ('200 OK', [], b'content')
        result = middleware.process_response(request_handler, response)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        
        status, headers, content = result
        self.assertEqual(status, '200 OK')
        self.assertEqual(content, b'content')
        
        header_dict = dict(headers)
        self.assertIn('X-Frame-Options', header_dict)
        self.assertIn('X-Content-Type-Options', header_dict)
        self.assertIn('X-XSS-Protection', header_dict)
        self.assertIn('Referrer-Policy', header_dict)


class TestRateLimitMiddleware(unittest.TestCase):
    """限流中间件测试"""

    def test_process_request_within_limit(self):
        """测试在限流范围内的请求"""
        app = Mock()
        middleware = RateLimitMiddleware(app, max_requests=5, window_seconds=60)
        request_handler = Mock()
        request_handler.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        for i in range(5):
            result = middleware.process_request(request_handler)
            self.assertIsNone(result)

    def test_process_request_exceeds_limit(self):
        """测试超过限流的请求"""
        app = Mock()
        middleware = RateLimitMiddleware(app, max_requests=3, window_seconds=60)
        request_handler = Mock()
        request_handler.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        for i in range(3):
            result = middleware.process_request(request_handler)
            self.assertIsNone(result)
        
        result = middleware.process_request(request_handler)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)
        
        status, headers, content = result
        self.assertEqual(status, '429 Too Many Requests')
        self.assertIn('Retry-After', dict(headers))


class TestThrottleMiddleware(unittest.TestCase):
    """节流中间件测试"""

    def test_process_request_within_interval(self):
        """测试在时间间隔内的请求"""
        app = Mock()
        middleware = ThrottleMiddleware(app, min_interval=0.1)
        request_handler = Mock()
        request_handler.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        result = middleware.process_request(request_handler)
        self.assertIsNone(result)

    def test_process_request_exceeds_interval(self):
        """测试超过时间间隔的请求"""
        app = Mock()
        middleware = ThrottleMiddleware(app, min_interval=1.0)
        request_handler = Mock()
        request_handler.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        result = middleware.process_request(request_handler)
        self.assertIsNone(result)
        
        result = middleware.process_request(request_handler)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, tuple)
        
        status, headers, content = result
        self.assertEqual(status, '429 Too Many Requests')


class TestLitefsMiddlewareIntegration(unittest.TestCase):
    """Litefs 中间件集成测试"""

    def test_add_middleware(self):
        """测试添加中间件到 Litefs"""
        app = Litefs(webroot='./examples/basic/site')
        
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(SecurityMiddleware)
        
        self.assertEqual(len(app.middleware_manager._middlewares), 2)

    def test_remove_middleware(self):
        """测试从 Litefs 移除中间件"""
        app = Litefs(webroot='./examples/basic/site')
        
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(SecurityMiddleware)
        app.remove_middleware(LoggingMiddleware)
        
        self.assertEqual(len(app.middleware_manager._middlewares), 1)
        self.assertNotIn(LoggingMiddleware, app.middleware_manager._middlewares)

    def test_clear_middleware(self):
        """测试清空 Litefs 的中间件"""
        app = Litefs(webroot='./examples/basic/site')
        
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(SecurityMiddleware)
        app.clear_middleware()
        
        self.assertEqual(len(app.middleware_manager._middlewares), 0)

    def test_chain_add_middleware(self):
        """测试链式添加中间件"""
        app = (
            Litefs(webroot='./examples/basic/site')
            .add_middleware(LoggingMiddleware)
            .add_middleware(SecurityMiddleware)
            .add_middleware(CORSMiddleware)
        )
        
        self.assertEqual(len(app.middleware_manager._middlewares), 3)


if __name__ == '__main__':
    unittest.main()
