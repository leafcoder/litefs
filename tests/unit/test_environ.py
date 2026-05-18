#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
from unittest.mock import Mock, MagicMock
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.server import make_environ, HTTPServer
from litefs.exceptions import HttpError


class TestMakeEnviron(unittest.TestCase):
    """测试 make_environ 函数"""

    def setUp(self):
        """设置测试环境"""
        self.server = HTTPServer(('localhost', 9090), lambda *args: None)

    def tearDown(self):
        """清理测试环境"""
        self.server.server_close()

    def test_basic_environ(self):
        """测试基本环境变量"""
        request_line = b"GET /test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['REQUEST_METHOD'], 'GET')
        self.assertEqual(environ['PATH_INFO'], '/test')
        self.assertEqual(environ['SERVER_PROTOCOL'], 'HTTP/1.1')
        self.assertEqual(environ['REMOTE_ADDR'], '127.0.0.1')
        self.assertEqual(environ['REMOTE_HOST'], '127.0.0.1')
        self.assertEqual(environ['REMOTE_PORT'], 12345)

    def test_query_string(self):
        """测试查询字符串"""
        request_line = b"GET /test?name=value&foo=bar HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['QUERY_STRING'], 'name=value&foo=bar')

    def test_url_encoded_path(self):
        """测试 URL 编码的路径"""
        request_line = b"GET /test%20path HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['PATH_INFO'], '/test path')

    def test_content_length(self):
        """测试 Content-Length"""
        request_line = b"POST /test HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['CONTENT_LENGTH'], 100)

    def test_content_type(self):
        """测试 Content-Type"""
        request_line = b"POST /test HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['CONTENT_TYPE'], 'application/json')

    def test_custom_headers(self):
        """测试自定义头部"""
        request_line = b"GET /test HTTP/1.1\r\nHost: localhost\r\nX-Custom-Header: value\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertIn('HTTP_X_CUSTOM_HEADER', environ)
        self.assertEqual(environ['HTTP_X_CUSTOM_HEADER'], 'value')

    def test_connection_header(self):
        """测试 Connection 头部"""
        request_line = b"GET /test HTTP/1.1\r\nHost: localhost\r\nConnection: keep-alive\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertIn('HTTP_CONNECTION', environ)
        self.assertEqual(environ['HTTP_CONNECTION'], 'keep-alive')

    def test_user_agent_header(self):
        """测试 User-Agent 头部"""
        request_line = b"GET /test HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertIn('HTTP_USER_AGENT', environ)
        self.assertEqual(environ['HTTP_USER_AGENT'], 'Mozilla/5.0')

    def test_empty_request(self):
        """测试空请求"""
        request_line = b""
        rw = BytesIO(request_line)
        
        with self.assertRaises(HttpError):
            make_environ(self.server, rw, ('127.0.0.1', 12345))

    def test_request_too_large(self):
        """测试请求过大"""
        self.server.max_request_size = 1024
        request_line = b"POST /test HTTP/1.1\r\nHost: localhost\r\nContent-Length: 2048\r\n\r\n"
        rw = BytesIO(request_line)
        
        with self.assertRaises(HttpError) as context:
            make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(context.exception.status_code, 413)

    def test_script_name_generation(self):
        """测试 SCRIPT_NAME 生成"""
        request_line = b"GET /base/test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['SCRIPT_NAME'], 'base/test')

    def test_index_page(self):
        """测试索引页"""
        request_line = b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['SCRIPT_NAME'], 'index.html')

    def test_multiple_headers_same_name(self):
        """测试同名多个头部"""
        request_line = b"GET /test HTTP/1.1\r\nHost: localhost\r\nX-Custom: value1\r\nX-Custom: value2\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertIn('HTTP_X_CUSTOM', environ)
        self.assertEqual(environ['HTTP_X_CUSTOM'], 'value2')

    def test_post_method(self):
        """测试 POST 方法"""
        request_line = b"POST /test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['REQUEST_METHOD'], 'POST')

    def test_put_method(self):
        """测试 PUT 方法"""
        request_line = b"PUT /test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['REQUEST_METHOD'], 'PUT')

    def test_delete_method(self):
        """测试 DELETE 方法"""
        request_line = b"DELETE /test HTTP/1.1\r\nHost: localhost\r\n\r\n"
        rw = BytesIO(request_line)
        
        environ = make_environ(self.server, rw, ('127.0.0.1', 12345))
        
        self.assertEqual(environ['REQUEST_METHOD'], 'DELETE')


if __name__ == '__main__':
    unittest.main()
