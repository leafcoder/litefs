#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import Litefs, make_config


class TestMakeConfig(unittest.TestCase):
    """测试 make_config 函数"""

    def test_default_config(self):
        """测试默认配置"""
        config = make_config()
        
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 9090)
        self.assertEqual(config.debug, False)
        self.assertEqual(config.max_request_size, 10485760)
        self.assertEqual(config.max_upload_size, 52428800)

    def test_custom_config(self):
        """测试自定义配置"""
        config = make_config(
            host='0.0.0.0',
            port=8000,
            debug=True,
            max_request_size=5242880,
            max_upload_size=104857600
        )
        
        self.assertEqual(config.host, '0.0.0.0')
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.debug, True)
        self.assertEqual(config.max_request_size, 5242880)
        self.assertEqual(config.max_upload_size, 104857600)




class TestLitefsInit(unittest.TestCase):
    """测试 Litefs 初始化"""

    def setUp(self):
        """设置测试环境"""
        self.app = Litefs()

    def test_init_default(self):
        """测试默认初始化"""
        self.assertIsNotNone(self.app.config)
        self.assertIsNotNone(self.app.logger)
        self.assertEqual(self.app.host, 'localhost')
        self.assertEqual(self.app.port, 9090)
        self.assertIsNotNone(self.app.sessions)
        self.assertIsNotNone(self.app.caches)
        self.assertIsNotNone(self.app.middleware_manager)

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        app = Litefs(
            host='0.0.0.0',
            port=8000,
            debug=True
        )
        
        self.assertEqual(app.host, '0.0.0.0')
        self.assertEqual(app.port, 8000)
        self.assertEqual(app.config.debug, True)

    def test_sessions_cache(self):
        """测试 sessions 缓存"""
        from litefs.session.session import MemorySessionStore
        
        self.assertIsInstance(self.app.sessions, MemorySessionStore)
        self.assertEqual(len(self.app.sessions), 0)

    def test_caches_tree_cache(self):
        """测试 caches 树缓存"""
        from litefs.cache import TreeCache
        
        self.assertIsInstance(self.app.caches, TreeCache)




class TestLitefsMiddleware(unittest.TestCase):
    """测试 Litefs 中间件管理"""

    def setUp(self):
        """设置测试环境"""
        self.app = Litefs()

    def test_add_middleware(self):
        """测试添加中间件"""
        from litefs.middleware import LoggingMiddleware
        
        self.app.add_middleware(LoggingMiddleware)
        
        self.assertEqual(len(self.app.middleware_manager._middlewares), 1)

    def test_remove_middleware(self):
        """测试移除中间件"""
        from litefs.middleware import LoggingMiddleware, SecurityMiddleware
        
        self.app.add_middleware(LoggingMiddleware)
        self.app.add_middleware(SecurityMiddleware)
        self.app.remove_middleware(LoggingMiddleware)
        
        self.assertEqual(len(self.app.middleware_manager._middlewares), 1)

    def test_clear_middleware(self):
        """测试清空中间件"""
        from litefs.middleware import LoggingMiddleware, SecurityMiddleware
        
        self.app.add_middleware(LoggingMiddleware)
        self.app.add_middleware(SecurityMiddleware)
        self.app.clear_middleware()
        
        self.assertEqual(len(self.app.middleware_manager._middlewares), 0)

    def test_chain_add_middleware(self):
        """测试链式添加中间件"""
        from litefs.middleware import LoggingMiddleware, SecurityMiddleware, CORSMiddleware
        
        app = (
            Litefs()
            .add_middleware(LoggingMiddleware)
            .add_middleware(SecurityMiddleware)
            .add_middleware(CORSMiddleware)
        )
        
        self.assertEqual(len(app.middleware_manager._middlewares), 3)


class TestLitefsWSGI(unittest.TestCase):
    """测试 Litefs WSGI 接口"""

    def setUp(self):
        """设置测试环境"""
        self.app = Litefs()

    def test_wsgi_returns_callable(self):
        """测试 wsgi() 返回可调用对象"""
        application = self.app.wsgi()
        
        self.assertTrue(callable(application))

    def test_wsgi_application_signature(self):
        """测试 WSGI application 签名"""
        application = self.app.wsgi()
        
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        
        def start_response(status, headers):
            pass
        
        result = application(environ, start_response)
        
        self.assertIsNotNone(result)

    def test_wsgi_with_middleware(self):
        """测试带中间件的 WSGI"""
        from litefs.middleware import LoggingMiddleware
        
        self.app.add_middleware(LoggingMiddleware)
        application = self.app.wsgi()
        
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        
        def start_response(status, headers):
            pass
        
        result = application(environ, start_response)
        
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
