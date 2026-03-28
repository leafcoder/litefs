#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs
from litefs.handlers.request import WSGIRequestHandler


class TestWSGIRequestHandlerPost(unittest.TestCase):
    """测试 WSGIRequestHandler 的 _post 属性"""

    def setUp(self):
        """设置测试环境"""
        self.app = litefs.Litefs(webroot='./examples/basic/site')

    def test_urlencoded_form_post(self):
        """测试 application/x-www-form-urlencoded 表单 POST"""
        form_data = "name=tom&age=25&email=test%40example.com"
        environ = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/test',
            'QUERY_STRING': '',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': str(len(form_data)),
            'wsgi.input': BytesIO(form_data.encode('utf-8')),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }

        handler = WSGIRequestHandler(self.app, environ)

        self.assertEqual(handler.post['name'], 'tom')
        self.assertEqual(handler.post['age'], '25')
        self.assertEqual(handler.post['email'], 'test@example.com')

    def test_urlencoded_form_post_with_special_chars(self):
        """测试包含特殊字符的表单 POST"""
        form_data = "name=%E6%B1%A4%E5%A7%86&value=%E6%9D%B0%E7%91%9E"
        environ = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/test',
            'QUERY_STRING': '',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': str(len(form_data)),
            'wsgi.input': BytesIO(form_data.encode('utf-8')),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }

        handler = WSGIRequestHandler(self.app, environ)

        self.assertEqual(handler.post['name'], '汤姆')
        self.assertEqual(handler.post['value'], '杰瑞')

    def test_urlencoded_form_post_with_array(self):
        """测试包含数组的表单 POST"""
        form_data = "tags[]=python&tags[]=django&tags[]=flask"
        environ = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/test',
            'QUERY_STRING': '',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': str(len(form_data)),
            'wsgi.input': BytesIO(form_data.encode('utf-8')),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }

        handler = WSGIRequestHandler(self.app, environ)

        self.assertIsInstance(handler.post['tags'], list)
        self.assertEqual(handler.post['tags'], ['python', 'django', 'flask'])

    def test_urlencoded_form_post_with_dict(self):
        """测试包含字典的表单 POST"""
        form_data = "user[name]=tom&user[age]=25"
        environ = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/test',
            'QUERY_STRING': '',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': str(len(form_data)),
            'wsgi.input': BytesIO(form_data.encode('utf-8')),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }

        handler = WSGIRequestHandler(self.app, environ)

        self.assertIsInstance(handler.post['user'], dict)
        self.assertEqual(handler.post['user']['name'], 'tom')
        self.assertEqual(handler.post['user']['age'], '25')

    def test_empty_post_body(self):
        """测试空的 POST body"""
        environ = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/test',
            'QUERY_STRING': '',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': '0',
            'wsgi.input': BytesIO(b''),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }

        handler = WSGIRequestHandler(self.app, environ)

        self.assertEqual(handler.post, {})

    def test_get_request_should_not_parse_post(self):
        """测试 GET 请求不应该解析 POST 数据"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/test',
            'QUERY_STRING': 'name=tom',
            'CONTENT_TYPE': 'application/x-www-form-urlencoded',
            'CONTENT_LENGTH': '0',
            'wsgi.input': BytesIO(b''),
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }

        handler = WSGIRequestHandler(self.app, environ)

        self.assertEqual(handler.post, {})
        self.assertEqual(handler.get['name'], 'tom')


if __name__ == '__main__':
    unittest.main()
