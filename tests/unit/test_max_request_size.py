#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
from unittest.mock import Mock
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import make_config
from litefs.server import HTTPServer, make_environ
from litefs.exceptions import HttpError


class TestMaxRequestSize(unittest.TestCase):
    """测试 max_request_size 配置功能"""

    def test_default_config(self):
        """测试默认配置"""
        config = make_config(webroot='./examples/basic/site')
        
        self.assertEqual(config.max_request_size, 10485760)

    def test_custom_config(self):
        """测试自定义配置"""
        config = make_config(
            webroot='./examples/basic/site',
            max_request_size=5242880
        )
        
        self.assertEqual(config.max_request_size, 5242880)

    def test_httpserver_default(self):
        """测试 HTTPServer 默认值"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        
        self.assertEqual(server.max_request_size, 10485760)

    def test_httpserver_custom(self):
        """测试 HTTPServer 自定义值"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        server.max_request_size = 20971520
        
        self.assertEqual(server.max_request_size, 20971520)

    def test_small_request_accepted(self):
        """测试小请求被接受"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        small_request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n"
        rw = BytesIO(small_request)
        
        environ = make_environ(server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['CONTENT_LENGTH'], 100)

    def test_large_request_rejected(self):
        """测试大请求被拒绝"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        server.max_request_size = 20971520
        large_request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 20971521\r\n\r\n"
        rw = BytesIO(large_request)
        
        with self.assertRaises(HttpError) as context:
            make_environ(server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(context.exception.status_code, 413)

    def test_boundary_request_accepted(self):
        """测试边界请求被接受"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        server.max_request_size = 1024
        boundary_request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1024\r\n\r\n"
        rw = BytesIO(boundary_request)
        
        environ = make_environ(server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['CONTENT_LENGTH'], 1024)

    def test_boundary_request_rejected(self):
        """测试边界请求被拒绝"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        server.max_request_size = 1024
        boundary_request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1025\r\n\r\n"
        rw = BytesIO(boundary_request)
        
        with self.assertRaises(HttpError) as context:
            make_environ(server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(context.exception.status_code, 413)

    def test_no_content_length(self):
        """测试没有 Content-Length 的请求"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        request = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request)
        
        environ = make_environ(server, rw, ('127.0.0.1', 12345))
        
        self.assertNotIn('CONTENT_LENGTH', environ)

    def test_zero_content_length(self):
        """测试 Content-Length 为 0 的请求"""
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n"
        rw = BytesIO(request)
        
        environ = make_environ(server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['CONTENT_LENGTH'], 0)


if __name__ == '__main__':
    unittest.main()
