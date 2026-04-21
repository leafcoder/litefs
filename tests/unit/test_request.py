#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
LiteFS Request 模块测试

测试所有请求处理相关的类和函数
"""

import sys
import os
import unittest
import tempfile
from io import BytesIO
from unittest.mock import Mock, MagicMock, patch
from http.cookies import SimpleCookie

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.handlers import (
    Response,
    BaseRequestHandler,
    WSGIRequestHandler,
    ASGIRequestHandler,
    SocketRequestHandler,
    RequestHandler,
    parse_form,
    parse_header,
    parse_multipart_wsgi,
    parse_multipart_asgi,
    is_bytes,
    imap,
    DEFAULT_STATUS_MESSAGE,
    default_content_type,
    json_content_type,
    server_info,
)


class TestParseHeader(unittest.TestCase):
    """测试 parse_header 函数"""

    def test_simple_content_type(self):
        """测试简单的 Content-Type"""
        content_type, params = parse_header("text/html")
        self.assertEqual(content_type, "text/html")
        self.assertEqual(params, {})

    def test_content_type_with_charset(self):
        """测试带字符集的 Content-Type"""
        content_type, params = parse_header("text/html; charset=utf-8")
        self.assertEqual(content_type, "text/html")
        self.assertEqual(params.get("charset"), "utf-8")

    def test_multipart_boundary(self):
        """测试 multipart 表单的 boundary"""
        content_type, params = parse_header(
            'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW'
        )
        self.assertEqual(content_type, "multipart/form-data")
        self.assertIn("boundary", params)


class TestParseForm(unittest.TestCase):
    """测试 parse_form 函数"""

    def test_simple_form(self):
        """测试简单表单"""
        query_string = "name=tom&value=123"
        form = parse_form(query_string)
        self.assertEqual(form['name'], 'tom')
        self.assertEqual(form['value'], '123')

    def test_url_encoded_form(self):
        """测试 URL 编码的表单"""
        query_string = "name=%E6%B1%A4%E5%A7%86&value=%E6%9D%B0%E7%91%9E"
        form = parse_form(query_string)
        self.assertEqual(form['name'], '汤姆')
        self.assertEqual(form['value'], '杰瑞')

    def test_array_notation(self):
        """测试数组表示法"""
        query_string = "tags[]=tag1&tags[]=tag2&tags[]=tag3"
        form = parse_form(query_string)
        self.assertIsInstance(form['tags'], list)
        self.assertEqual(len(form['tags']), 3)
        self.assertEqual(form['tags'], ['tag1', 'tag2', 'tag3'])

    def test_dict_notation(self):
        """测试字典表示法"""
        query_string = "user[name]=tom&user[age]=25"
        form = parse_form(query_string)
        self.assertIsInstance(form['user'], dict)
        self.assertEqual(form['user']['name'], 'tom')
        self.assertEqual(form['user']['age'], '25')

    def test_empty_value(self):
        """测试空值"""
        query_string = "name=&value=123"
        form = parse_form(query_string)
        self.assertEqual(form['name'], '')
        self.assertEqual(form['value'], '123')

    def test_bytes_input(self):
        """测试字节输入"""
        query_string = b"name=tom&value=123"
        form = parse_form(query_string)
        self.assertEqual(form['name'], 'tom')
        self.assertEqual(form['value'], '123')

    def test_empty_query_string(self):
        """测试空查询字符串"""
        form = parse_form("")
        self.assertEqual(form, {})


class TestResponse(unittest.TestCase):
    """测试 Response 类"""

    def test_basic_response(self):
        """测试基本响应"""
        response = Response("Hello World", 200)
        self.assertEqual(response.content, "Hello World")
        self.assertEqual(response.status_code, 200)

    def test_response_with_headers(self):
        """测试带响应头的响应"""
        headers = [("Content-Type", "text/plain")]
        response = Response("Hello", 200, headers)
        self.assertEqual(len(response.headers), 1)

    def test_json_response(self):
        """测试 JSON 响应"""
        data = {"name": "tom", "age": 25}
        response = Response.json(data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.headers[0][1])

    def test_html_response(self):
        """测试 HTML 响应"""
        response = Response.html("<h1>Hello</h1>")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers[0][1])

    def test_text_response(self):
        """测试纯文本响应"""
        response = Response.text("Hello World")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers[0][1])

    def test_redirect_response(self):
        """测试重定向响应"""
        response = Response.redirect("/login", 302)
        self.assertEqual(response.status_code, 302)
        self.assertIn("Location", [h[0] for h in response.headers])

    def test_error_response(self):
        """测试错误响应"""
        response = Response.error(404, "Page not found")
        self.assertEqual(response.status_code, 404)
        self.assertIn("text/html", response.headers[0][1])

    def test_file_response(self):
        """测试文件响应"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Hello World")
            temp_path = f.name

        try:
            response = Response.file(temp_path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("attachment", response.headers[1][1])
            self.assertIn("Content-Length", [h[0] for h in response.headers])
        finally:
            os.unlink(temp_path)

    def test_file_response_not_found(self):
        """测试文件不存在的响应"""
        response = Response.file("/nonexistent/file.txt")
        self.assertEqual(response.status_code, 404)

    def test_stream_response(self):
        """测试流式响应"""
        def generate():
            yield "chunk1"
            yield "chunk2"

        response = Response.stream(generate())
        self.assertEqual(response.status_code, 200)
        self.assertIn("chunked", [h[1] for h in response.headers if h[0] == "Transfer-Encoding"][0])

    def test_sse_response(self):
        """测试 Server-Sent Events 响应"""
        def generate():
            yield "data: hello\n\n"

        response = Response.sse(generate())
        self.assertEqual(response.status_code, 200)
        content_types = [h[1] for h in response.headers if h[0] == "Content-Type"]
        self.assertIn("text/event-stream", content_types)

    def test_file_stream_response(self):
        """测试流式文件响应"""
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.bin') as f:
            f.write(b"Hello World Binary Data")
            temp_path = f.name

        try:
            response = Response.file_stream(temp_path)
            self.assertEqual(response.status_code, 200)
            self.assertIn("attachment", [h[1] for h in response.headers if h[0] == "Content-Disposition"][0])
        finally:
            os.unlink(temp_path)

    def test_set_cookie(self):
        """测试设置 Cookie"""
        response = Response("Hello")
        response.set_cookie("session_id", "abc123", max_age=3600, path="/", secure=True)
        cookie_headers = [h for h in response.headers if h[0] == "Set-Cookie"]
        self.assertEqual(len(cookie_headers), 1)
        self.assertIn("session_id", cookie_headers[0][1])
        self.assertIn("abc123", cookie_headers[0][1])

    def test_delete_cookie(self):
        """测试删除 Cookie"""
        response = Response("Hello")
        response.delete_cookie("session_id")
        cookie_headers = [h for h in response.headers if h[0] == "Set-Cookie"]
        self.assertEqual(len(cookie_headers), 1)
        self.assertIn("1970", cookie_headers[0][1])


class TestIsBytes(unittest.TestCase):
    """测试 is_bytes 函数"""

    def test_bytes_input(self):
        """测试字节输入"""
        self.assertTrue(is_bytes(b"hello"))

    def test_string_input(self):
        """测试字符串输入"""
        self.assertFalse(is_bytes("hello"))

    def test_int_input(self):
        """测试整数输入"""
        self.assertFalse(is_bytes(123))


class TestImap(unittest.TestCase):
    """测试 imap 函数"""

    def test_basic_imap(self):
        """测试基本功能"""
        result = list(imap(str, [1, 2, 3]))
        self.assertEqual(result, ["1", "2", "3"])


class TestConstants(unittest.TestCase):
    """测试常量定义"""

    def test_default_content_type(self):
        """测试默认 Content-Type"""
        self.assertEqual(default_content_type, "text/html; charset=utf-8")

    def test_json_content_type(self):
        """测试 JSON Content-Type"""
        self.assertEqual(json_content_type, "application/json; charset=utf-8")

    def test_server_info(self):
        """测试服务器信息"""
        self.assertIn("litefs", server_info)
        self.assertIn("python", server_info)

    def test_default_status_message(self):
        """测试默认状态消息模板"""
        self.assertIn("%(code)d", DEFAULT_STATUS_MESSAGE)
        self.assertIn("%(message)s", DEFAULT_STATUS_MESSAGE)


class TestWSGIRequestHandler(unittest.TestCase):
    """测试 WSGIRequestHandler 类"""

    def setUp(self):
        """设置测试环境"""
        self.mock_app = Mock()
        self.mock_app.config = Mock()
        self.mock_app.config.session_name = "session_id"
        self.mock_app.config.session_secure = False
        self.mock_app.config.session_http_only = True
        self.mock_app.config.session_same_site = "Lax"
        self.mock_app.config.max_request_size = 10485760
        self.mock_app.config.max_upload_size = 52428800
        self.mock_app.config.debug = False
        self.mock_app.sessions = Mock()
        self.mock_app.sessions.get = Mock(return_value=None)
        self.mock_app.sessions.put = Mock()
        self.mock_app.middleware_manager = Mock()
        self.mock_app.middleware_manager.process_request = Mock(return_value=None)
        self.mock_app.middleware_manager.process_response = Mock(return_value=None)
        self.mock_app.middleware_manager.process_exception = Mock(return_value=None)
        self.mock_app._get_middleware_instances = Mock(return_value=[])

    def test_environ_normalization(self):
        """测试环境变量规范化"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/test',
            'QUERY_STRING': 'key=value',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        handler = WSGIRequestHandler(self.mock_app, environ)
        self.assertEqual(handler.path_info, '/test')
        self.assertEqual(handler.request_method, 'GET')
        self.assertEqual(handler.query_string, 'key=value')

    def test_query_params(self):
        """测试查询参数解析"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'QUERY_STRING': 'name=tom&age=25',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        handler = WSGIRequestHandler(self.mock_app, environ)
        self.assertEqual(handler.params['name'], 'tom')
        self.assertEqual(handler.params['age'], '25')

    def test_headers_property(self):
        """测试请求头属性"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'HTTP_ACCEPT': 'text/html',
            'HTTP_USER_AGENT': 'TestAgent',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        handler = WSGIRequestHandler(self.mock_app, environ)
        headers = handler.headers
        self.assertEqual(headers.get('accept'), 'text/html')
        self.assertEqual(headers.get('user-agent'), 'TestAgent')

    def test_cookie_property(self):
        """测试 Cookie 属性"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'HTTP_COOKIE': 'session_id=abc123; theme=dark',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        handler = WSGIRequestHandler(self.mock_app, environ)
        cookie = handler.cookie
        self.assertEqual(cookie['session_id'].value, 'abc123')
        self.assertEqual(cookie['theme'].value, 'dark')


class TestASGIRequestHandler(unittest.TestCase):
    """测试 ASGIRequestHandler 类"""

    def setUp(self):
        """设置测试环境"""
        self.mock_app = Mock()
        self.mock_app.config = Mock()
        self.mock_app.config.session_name = "session_id"
        self.mock_app.config.session_secure = False
        self.mock_app.config.session_http_only = True
        self.mock_app.config.session_same_site = "Lax"
        self.mock_app.config.max_request_size = 10485760
        self.mock_app.config.max_upload_size = 52428800
        self.mock_app.config.debug = False
        self.mock_app.sessions = Mock()
        self.mock_app.sessions.get = Mock(return_value=None)
        self.mock_app.sessions.put = Mock()
        self.mock_app.middleware_manager = Mock()
        self.mock_app.middleware_manager.process_request = Mock(return_value=None)
        self.mock_app.middleware_manager.process_response = Mock(return_value=None)
        self.mock_app.middleware_manager.process_exception = Mock(return_value=None)
        self.mock_app._get_middleware_instances = Mock(return_value=[])

    def test_scope_parsing(self):
        """测试 ASGI scope 解析"""
        scope = {
            'method': 'GET',
            'path': '/test',
            'query_string': b'name=value',
            'server': ('localhost', 8000),
            'client': ('127.0.0.1', 12345),
            'http_version': '1.1',
            'headers': [
                (b'accept', b'text/html'),
                (b'user-agent', b'TestAgent'),
            ],
        }

        handler = ASGIRequestHandler(self.mock_app, scope, Mock(), Mock())

        self.assertEqual(handler.path_info, '/test')
        self.assertEqual(handler.request_method, 'GET')
        self.assertEqual(handler.query_string, 'name=value')

    def test_headers_parsing(self):
        """测试请求头解析"""
        scope = {
            'method': 'GET',
            'path': '/',
            'query_string': b'',
            'server': ('localhost', 8000),
            'client': ('127.0.0.1', 12345),
            'http_version': '1.1',
            'headers': [
                (b'content-type', b'application/json'),
                (b'content-length', b'100'),
            ],
        }

        handler = ASGIRequestHandler(self.mock_app, scope, Mock(), Mock())
        self.assertEqual(handler.content_type, 'application/json')


class TestSocketRequestHandler(unittest.TestCase):
    """测试 SocketRequestHandler 类"""

    def setUp(self):
        """设置测试环境"""
        self.mock_app = Mock()
        self.mock_app.config = Mock()
        self.mock_app.config.session_name = "session_id"
        self.mock_app.config.session_secure = False
        self.mock_app.config.session_http_only = True
        self.mock_app.config.session_same_site = "Lax"
        self.mock_app.config.max_request_size = 10485760
        self.mock_app.config.max_upload_size = 52428800
        self.mock_app.config.debug = False
        self.mock_app.sessions = Mock()
        self.mock_app.sessions.get = Mock(return_value=None)
        self.mock_app.sessions.put = Mock()
        self.mock_app.middleware_manager = Mock()
        self.mock_app.middleware_manager.process_request = Mock(return_value=None)
        self.mock_app.middleware_manager.process_response = Mock(return_value=None)
        self.mock_app.middleware_manager.process_exception = Mock(return_value=None)
        self.mock_app._get_middleware_instances = Mock(return_value=[])

    def test_basic_environ(self):
        """测试基本环境变量"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/test',
            'QUERY_STRING': 'name=tom',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        mock_rw = Mock()

        handler = SocketRequestHandler(self.mock_app, mock_rw, environ, Mock())
        self.assertEqual(handler.path_info, '/test')
        self.assertEqual(handler.request_method, 'GET')

    def test_cast_string(self):
        """测试字符串类型转换"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        mock_rw = Mock()
        handler = SocketRequestHandler(self.mock_app, mock_rw, environ, Mock())
        result = handler._cast("Hello World")
        self.assertEqual(result, [b"Hello World"])

    def test_cast_bytes(self):
        """测试字节类型转换"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        mock_rw = Mock()
        handler = SocketRequestHandler(self.mock_app, mock_rw, environ, Mock())
        result = handler._cast(b"Hello World")
        self.assertEqual(result, [b"Hello World"])

    def test_cast_dict(self):
        """测试字典类型转换"""
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        mock_rw = Mock()
        handler = SocketRequestHandler(self.mock_app, mock_rw, environ, Mock())
        handler._response_headers["Content-Type"] = "application/json"
        result = handler._cast({"name": "tom"})
        self.assertEqual(result, [b'{"name": "tom"}'])


class TestBaseRequestHandler(unittest.TestCase):
    """测试 BaseRequestHandler 基类"""

    def setUp(self):
        """设置测试环境"""
        self.mock_app = Mock()
        self.mock_app.config = Mock()
        self.mock_app.config.template_dir = 'templates'

    def test_basic_initialization(self):
        """测试基本初始化"""

        class TestHandler(BaseRequestHandler):
            def _add_header(self, key, value):
                self._headers.append((key, value))

        environ = {'PATH_INFO': '/'}
        handler = TestHandler(self.mock_app, environ)

        self.assertEqual(handler._status_code, 200)
        self.assertEqual(handler.get, {})
        self.assertEqual(handler.post, {})

    def test_properties(self):
        """测试属性访问"""

        class TestHandler(BaseRequestHandler):
            def _add_header(self, key, value):
                pass

        environ = {'PATH_INFO': '/'}
        handler = TestHandler(self.mock_app, environ)
        handler._session = Mock()
        handler._session_id = "test_session"

        self.assertEqual(handler.session_id, "test_session")
        self.assertEqual(handler.session, handler._session)


class TestResponseIntegration(unittest.TestCase):
    """测试 Response 与请求处理器的集成"""

    def test_response_with_wsgi_handler(self):
        """测试 Response 与 WSGI 处理器配合使用"""
        mock_app = Mock()
        mock_app.config = Mock()
        mock_app.config.session_name = "session_id"
        mock_app.config.session_secure = False
        mock_app.config.session_http_only = True
        mock_app.config.session_same_site = "Lax"
        mock_app.config.max_request_size = 10485760
        mock_app.config.max_upload_size = 52428800
        mock_app.config.debug = False
        mock_app.sessions = Mock()
        mock_app.sessions.get = Mock(return_value=None)
        mock_app.sessions.put = Mock()
        mock_app.middleware_manager = Mock()
        mock_app.middleware_manager.process_request = Mock(return_value=None)
        mock_app.middleware_manager.process_response = Mock(return_value="handled")
        mock_app.middleware_manager.process_exception = Mock(return_value=None)
        mock_app._get_middleware_instances = Mock(return_value=[])

        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_LENGTH': '0',
            'CONTENT_TYPE': '',
        }

        handler = WSGIRequestHandler(mock_app, environ)

        # 创建 Response 对象
        response = Response.json({"success": True})
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/json", response.headers[0][1])


if __name__ == '__main__':
    unittest.main()
