#!/usr/bin/env python
# coding: utf-8

"""
拆分行为快照测试

v0.10.0 结构重构前建立的行为基线快照，覆盖将被拆分的 5 个大文件：

- ``handlers/socket.py``  → socket_request / socket_response / socket_multipart
- ``server/greenlet.py``  → greenlet_request / greenlet_worker
- ``error_pages.py``      → templates/error/*.html
- ``handlers/base.py``    → handlers/properties
- ``config.py``           → config/env

本模块只断言「对外可观察行为」，不依赖任何内部实现结构，
因此拆分前后均应保持通过。

约定
----
1. 快照记录的是**当前实际行为**，包括已知的实现缺陷。
   若后续版本有意修复某个缺陷，必须同步更新此处断言。
2. 断言一律基于公开属性、公开方法与 HTTP 线上可见结果，
   不断言私有属性名，避免拆分时因内部结构调整而误报。
"""

import io
import json
import unittest
from errno import EAGAIN, EWOULDBLOCK
from unittest.mock import Mock, patch

from litefs.config import Config, load_config, merge_configs
from litefs.error_pages import ErrorPageRenderer
from litefs.exceptions import HttpError
from litefs.handlers.base import BaseRequestHandler
from litefs.handlers.response import (
    DEFAULT_STATUS_MESSAGE,
    Response,
    default_content_type,
    json_content_type,
    server_info,
    server_software,
)
from litefs.handlers.socket import (
    EOFS,
    FILES_HEADER_NAME,
    POSTS_HEADER_NAME,
    RequestHandler,
    SocketRequestHandler,
    double_slash_sub,
    imap,
    is_bytes,
    should_retry_error,
    startswith_dot_sub,
    suffixes,
)
from litefs.server.greenlet import (
    make_environ,
    make_headers,
    parse_header,
)


# ==================== 测试夹具 ====================


class FakeRW(io.BytesIO):
    """可记录写入内容的伪读写流，close() 不释放缓冲区以便断言"""

    def __init__(self, initial=b""):
        super().__init__(initial)
        self.written = bytearray()
        self.close_called = False

    def write(self, data):
        self.written.extend(data)
        return len(data)

    def close(self):
        # 故意不调用父类 close()，保留缓冲区内容供断言
        self.close_called = True

    def getvalue(self):
        return bytes(self.written)


class FailingRW(io.BytesIO):
    """首次写入即失败的伪读写流，用于覆盖异常分支"""

    def __init__(self, initial=b""):
        super().__init__(initial)
        self.written = bytearray()
        self._failed = False

    def write(self, data):
        if not self._failed:
            self._failed = True
            raise OSError("模拟写入失败")
        self.written.extend(data)
        return len(data)

    def close(self):
        pass

    def getvalue(self):
        return bytes(self.written)


def make_environ_dict(**overrides):
    """构造符合 WSGI 约定的 environ 字典"""
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/index",
        "QUERY_STRING": "",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "CONTENT_TYPE": "",
        "CONTENT_LENGTH": "",
    }
    environ.update(overrides)
    return environ


def make_app():
    """构造最小可用的 app Mock"""
    app = Mock()
    app.config = Mock()
    app.config.max_request_size = 10485760
    app.config.max_upload_size = 52428800
    app.config.session_name = "litefs.sid"
    app.config.session_secure = False
    app.config.session_http_only = True
    app.config.session_same_site = "Lax"
    app.config.debug = False
    app.debug = False
    app.logger = Mock()
    app.sessions = Mock()
    app.sessions.get.return_value = None
    app.sessions.put.return_value = None
    return app


def make_server(max_request_size=10485760, server_port=8080):
    """构造 greenlet 测试所需的 server Mock"""
    server = Mock()
    server.server_name = "localhost"
    server.server_port = server_port
    server.max_request_size = max_request_size
    return server


# ==================== socket.py 快照 ====================


class TestSocketModuleConstants(unittest.TestCase):
    """socket 模块级常量与工具函数"""

    def test_module_constants(self):
        """模块常量取值冻结"""
        self.assertEqual(EOFS, ("", "\n", "\r\n"))
        self.assertEqual(POSTS_HEADER_NAME, "litefs.posts")
        self.assertEqual(FILES_HEADER_NAME, "litefs.files")
        self.assertEqual(suffixes, (".py", ".pyc", ".pyo", ".so"))
        self.assertIn(EAGAIN, should_retry_error)
        self.assertIn(EWOULDBLOCK, should_retry_error)

    def test_is_bytes(self):
        """is_bytes 只对 bytes 返回 True"""
        self.assertTrue(is_bytes(b"x"))
        self.assertFalse(is_bytes("x"))
        self.assertFalse(is_bytes(1))
        self.assertFalse(is_bytes(None))

    def test_imap(self):
        """imap 为延迟 map"""
        result = imap(str, [1, 2, 3])
        self.assertFalse(isinstance(result, list))
        self.assertEqual(list(result), ["1", "2", "3"])

    def test_regex_sub_helpers(self):
        """double_slash_sub / startswith_dot_sub 为 re.sub 绑定方法，替换串为必填参数"""
        self.assertEqual(double_slash_sub("", "//a///b"), "ab")
        self.assertEqual(startswith_dot_sub("", "/../a"), "/a")

    def test_alias_equivalence(self):
        """RequestHandler 是 SocketRequestHandler 的别名"""
        self.assertIs(RequestHandler, SocketRequestHandler)

    def test_default_headers(self):
        """类级默认响应头冻结"""
        headers = SocketRequestHandler.default_headers
        self.assertEqual(headers["Content-Type"], default_content_type)
        self.assertEqual(headers["Server"], server_software)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(headers["X-XSS-Protection"], "1; mode=block")

    def test_server_header_formats(self):
        """两条响应链路的 Server 头格式必须不同且稳定"""
        # 原生 Socket 链路：仅框架版本
        self.assertEqual(server_software, "litefs/%s" % server_software.split("/")[1])
        self.assertNotIn(" python/", server_software)
        # WSGI 链路：框架版本 + Python 版本
        self.assertTrue(server_info.startswith("litefs/"))
        self.assertIn(" python/", server_info)


class TestSocketRequestHandlerSnapshot(unittest.TestCase):
    """SocketRequestHandler 请求侧行为快照"""

    def setUp(self):
        self.app = make_app()
        self.rw = FakeRW()

    def _make_handler(self, **overrides):
        environ = make_environ_dict(**overrides)
        return SocketRequestHandler(self.app, self.rw, environ, "GET /index HTTP/1.1")

    def test_init_reads_environ(self):
        """初始化后基础属性可读"""
        handler = self._make_handler()
        self.assertEqual(handler.request_method, "GET")
        self.assertEqual(handler.path_info, "/index")
        self.assertEqual(handler.query_string, "")
        self.assertEqual(handler.server_protocol, "HTTP/1.1")
        self.assertEqual(handler.params, {})
        self.assertEqual(handler.data, {})
        self.assertEqual(handler.files, {})
        self.assertEqual(handler.body, "")
        self.assertEqual(handler.json, {})

    def test_content_length_absent_is_minus_one(self):
        """socket 链路缺少 CONTENT_LENGTH 时为 -1（与基类 0 不同，需保持差异）"""
        handler = self._make_handler()
        self.assertEqual(handler.content_length, -1)

    def test_request_uri_with_query(self):
        """request_uri 在有查询串时拼接路径与查询串"""
        handler = self._make_handler(PATH_INFO="/search", QUERY_STRING="q=py")
        self.assertEqual(handler.request_uri, "/search?q=py")

    def test_request_uri_without_query(self):
        """request_uri 在无查询串时仅返回路径"""
        handler = self._make_handler(PATH_INFO="/plain")
        self.assertEqual(handler.request_uri, "/plain")

    def test_json_property_parses_json_body(self):
        """json 属性在 Content-Type 为 JSON 时解析请求体"""
        environ = make_environ_dict(
            REQUEST_METHOD="POST",
            CONTENT_TYPE="application/json",
            CONTENT_LENGTH="13",
        )
        handler = SocketRequestHandler(
            self.app, FakeRW(b'{"k": "v"}'), environ, "POST /x HTTP/1.1"
        )
        self.assertEqual(handler.json, {"k": "v"})

    def test_json_property_ignores_non_json(self):
        """非 JSON Content-Type 时 json 属性返回空字典"""
        handler = self._make_handler(CONTENT_TYPE="text/plain")
        self.assertEqual(handler.json, {})

    def test_charset_default(self):
        """charset 缺省为 UTF-8"""
        handler = self._make_handler(CONTENT_TYPE="text/plain; charset=gbk")
        self.assertEqual(handler.charset, "gbk")
        handler2 = self._make_handler(CONTENT_TYPE="text/plain")
        self.assertEqual(handler2.charset, "UTF-8")

    def test_cookie_property(self):
        """cookie 属性解析 Cookie 请求头"""
        handler = self._make_handler(HTTP_COOKIE="a=1; b=2")
        self.assertEqual(handler.cookie["a"].value, "1")
        self.assertEqual(handler.cookie["b"].value, "2")

    def test_referer_property(self):
        """referer 属性读取 Referer 请求头"""
        handler = self._make_handler(HTTP_REFERER="http://example.com")
        self.assertEqual(handler.referer, "http://example.com")
        self.assertIsNone(self._make_handler().referer)

    def test_form_urlencoded_body(self):
        """application/x-www-form-urlencoded 请求体被解析到 data"""
        environ = make_environ_dict(
            REQUEST_METHOD="POST",
            CONTENT_TYPE="application/x-www-form-urlencoded",
            CONTENT_LENGTH="10",
        )
        handler = SocketRequestHandler(
            self.app, FakeRW(b"name=alice"), environ, "POST /x HTTP/1.1"
        )
        self.assertEqual(handler.data, {"name": "alice"})
        self.assertEqual(handler.body, b"name=alice")

    def test_body_too_large_raises(self):
        """请求体超过 max_request_size 时抛出 413"""
        self.app.config.max_request_size = 10
        environ = make_environ_dict(
            REQUEST_METHOD="POST",
            CONTENT_TYPE="application/x-www-form-urlencoded",
            CONTENT_LENGTH="100",
        )
        with self.assertRaises(HttpError) as ctx:
            SocketRequestHandler(self.app, FakeRW(), environ, "POST /x HTTP/1.1")
        self.assertEqual(ctx.exception.status_code, 413)

    def test_set_cookie_uses_hyphenated_options(self):
        """set_cookie 将下划线选项转换为连字符形式"""
        handler = self._make_handler()
        handler.set_cookie("k", "v", max_age=60, httponly=True)
        rendered = str(handler._cookies["k"])
        self.assertIn("Max-Age=60", rendered)
        self.assertIn("httponly", rendered.lower())

    def test_redirect_builds_location(self):
        """redirect 生成带 Location 头的 302 响应"""
        handler = self._make_handler(HTTP_HOST="example.com")
        content = handler.redirect("/next")
        self.assertEqual(content, "302 Found")
        self.assertEqual(handler._response_headers["Location"], "http://example.com/next")
        self.assertEqual(
            handler._response_headers["Content-Type"], "text/html;charset=utf-8"
        )

    def test_redirect_default_path(self):
        """redirect 未指定路径时重定向到根路径"""
        handler = self._make_handler(HTTP_HOST="example.com")
        handler.redirect()
        self.assertEqual(handler._response_headers["Location"], "http://example.com/")

    def test_redirect_without_host_uses_server_name(self):
        """缺少 Host 头时回落到 SERVER_NAME"""
        handler = self._make_handler()
        handler.redirect("/next")
        self.assertEqual(handler._response_headers["Location"], "http://localhost/next")

    def test_redirect_twice_raises(self):
        """响应头已发出后再次 redirect 抛错"""
        handler = self._make_handler(HTTP_HOST="example.com")
        handler.redirect("/a")
        with self.assertRaises(ValueError):
            handler.redirect("/b")


class TestSocketResponseChainSnapshot(unittest.TestCase):
    """Socket 处理器三条响应链路的行为快照"""

    def setUp(self):
        self.app = make_app()
        self.rw = FakeRW()

    def _make_handler(self, **overrides):
        environ = make_environ_dict(**overrides)
        return SocketRequestHandler(self.app, self.rw, environ, "GET /index HTTP/1.1")

    def test_response_builds_standard_headers(self):
        """_response 产出标准安全头与 Server 头"""
        handler = self._make_handler()
        content = handler._response(200, content="hello")
        self.assertEqual(content, "hello")
        headers = handler._response_headers
        self.assertEqual(headers["Server"], server_software)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(headers["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(headers["Content-Type"], default_content_type)
        self.assertEqual(headers["Content-Length"], "5")

    def test_response_json_content_type(self):
        """dict 内容使用 JSON Content-Type"""
        handler = self._make_handler()
        handler._response(200, content={"a": 1})
        self.assertEqual(handler._response_headers["Content-Type"], json_content_type)

    def test_response_html_content_type(self):
        """以 < 开头的字符串内容使用 HTML Content-Type"""
        handler = self._make_handler()
        handler._response(200, content="<h1>hi</h1>")
        self.assertEqual(
            handler._response_headers["Content-Type"], "text/html; charset=utf-8"
        )

    def test_response_bytes_content_type(self):
        """bytes 内容使用二进制流 Content-Type"""
        handler = self._make_handler()
        handler._response(200, content=b"\x00\x01")
        self.assertEqual(
            handler._response_headers["Content-Type"], "application/octet-stream"
        )

    def test_response_error_status_content_type(self):
        """4xx/5xx 状态使用 HTML Content-Type"""
        handler = self._make_handler()
        handler._response(404, content="missing")
        self.assertEqual(
            handler._response_headers["Content-Type"], "text/html; charset=utf-8"
        )

    def test_response_default_body(self):
        """content 为 None 时回落到默认状态消息"""
        handler = self._make_handler()
        content = handler._response(404)
        self.assertEqual(
            content,
            DEFAULT_STATUS_MESSAGE
            % {"code": 404, "message": "Not Found", "explain": "Not Found"},
        )

    def test_response_sets_session_cookie(self):
        """首次响应设置会话 Cookie"""
        handler = self._make_handler()
        handler._response(200, content="ok")
        self.assertIsNotNone(handler._cookies)
        self.assertIn("litefs.sid", handler._cookies)

    def test_response_after_headers_raises(self):
        """响应头已发出后再次 _response 抛错"""
        handler = self._make_handler()
        handler._response(200, content="ok")
        with self.assertRaises(ValueError):
            handler._response(200, content="again")

    def test_build_response_headers_returns_dict(self):
        """_build_response_headers 返回字典且含标准头"""
        handler = self._make_handler()
        headers = handler._build_response_headers(200, content="x")
        self.assertIsInstance(headers, dict)
        self.assertEqual(headers["Server"], server_software)
        self.assertEqual(headers["Content-Type"], default_content_type)

    def test_handle_response_with_response_object(self):
        """handle_response 处理 Response 对象"""
        handler = self._make_handler()
        resp = Response({"ok": True}, 201, [("X-Test", "1")])
        result = handler.handle_response(resp)
        self.assertEqual(handler._status_code, 201)
        self.assertEqual(handler._response_headers["X-Test"], "1")
        self.assertEqual(json.loads(result), {"ok": True})

    def test_finish_writes_raw_response(self):
        """finish 直接向 socket 写出完整 HTTP 响应"""
        handler = self._make_handler()
        handler._response(200, content="hello")
        handler.finish("hello")
        raw = self.rw.getvalue().decode("utf-8")
        self.assertTrue(raw.startswith("HTTP/1.1 200 OK\r\n"))
        self.assertIn("Server: %s\r\n" % server_software, raw)
        self.assertIn("Content-Length: 5\r\n", raw)
        self.assertIn("Content-Type: %s\r\n" % default_content_type, raw)
        self.assertTrue(raw.endswith("hello"))

    def test_finish_writes_session_cookie_header(self):
        """会话 Cookie 以 Set-Cookie 响应头形式写出"""
        handler = self._make_handler()
        handler._response(200, content="hello")
        handler.finish("hello")
        raw = self.rw.getvalue().decode("utf-8")
        self.assertIn("Set-Cookie: litefs.sid=", raw)

    def test_finish_writes_chunked_for_iterable(self):
        """可迭代内容使用 chunked 编码"""
        handler = self._make_handler()
        handler._response(200, content=iter([b"ab", b"cd"]))
        handler.finish(iter([b"ab", b"cd"]))
        raw = self.rw.getvalue().decode("utf-8")
        self.assertIn("Transfer-Encoding: chunked\r\n", raw)
        self.assertIn("2\r\nab\r\n", raw)
        self.assertIn("0\r\n\r\n", raw)

    def test_finish_writes_redirect_with_empty_body(self):
        """3xx 重定向写出空响应体"""
        handler = self._make_handler(HTTP_HOST="example.com")
        content = handler.redirect("/next")
        handler.finish(content)
        raw = self.rw.getvalue().decode("utf-8")
        self.assertIn("HTTP/1.1 302 Found\r\n", raw)
        self.assertIn("Location: http://example.com/next\r\n", raw)

    def test_finish_exception_branch_writes_500(self):
        """写入失败时回落到 500 响应"""
        app = make_app()
        rw = FailingRW()
        environ = make_environ_dict()
        handler = SocketRequestHandler(app, rw, environ, "GET /index HTTP/1.1")
        with self.assertRaises(Exception):
            handler.finish("hello")
        raw = rw.getvalue().decode("utf-8")
        self.assertTrue(raw.startswith("HTTP/1.1 500 "))
        self.assertIn("Server: %s\r\n" % server_software, raw)

    def test_cast_empty_content(self):
        """_cast 对空内容返回空列表并补 Content-Length=0"""
        handler = self._make_handler()
        result = handler._cast(None)
        self.assertEqual(result, [])
        self.assertEqual(handler._response_headers["Content-Length"], 0)

    def test_cast_dict_serializes_json(self):
        """_cast 对 dict 在 JSON Content-Type 下序列化"""
        handler = self._make_handler()
        handler._response_headers["Content-Type"] = json_content_type
        result = handler._cast({"a": 1})
        self.assertEqual(json.loads(result[0].decode("utf-8")), {"a": 1})

    def test_cast_list_joins_strings(self):
        """_cast 对字符串列表做拼接"""
        handler = self._make_handler()
        result = handler._cast(["a", "b"])
        self.assertEqual(result[0], b"ab")


# ==================== greenlet.py 快照 ====================


class TestGreenletSnapshot(unittest.TestCase):
    """greenlet 服务器模块行为快照"""

    def test_parse_header(self):
        """parse_header 解析 Content-Type 头，返回 (mime 元组, 参数字典)"""
        content_type, params = parse_header("application/json; charset=utf-8")
        self.assertEqual(content_type[0], "application/json")
        self.assertEqual(params["charset"], "utf-8")

    def test_parse_header_plain(self):
        """parse_header 处理无参数的 Content-Type"""
        content_type, params = parse_header("text/plain")
        self.assertEqual(content_type[0], "text/plain")
        self.assertEqual(params, {})

    def test_make_headers(self):
        """make_headers 解析请求头为小写字典"""
        rw = io.BytesIO(b"Host: example.com\r\nAccept: */*\r\n\r\n")
        headers = make_headers(rw)
        self.assertEqual(headers["host"], "example.com")
        self.assertEqual(headers["accept"], "*/*")

    def test_make_environ(self):
        """make_environ 构造标准 WSGI environ"""
        server = make_server()
        rw = io.BytesIO(
            b"GET /path?q=1 HTTP/1.1\r\n"
            b"Host: example.com\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            b"Content-Length: 0\r\n"
            b"\r\n"
        )
        environ = make_environ(server, rw, ("127.0.0.1", 54321))
        self.assertEqual(environ["REQUEST_METHOD"], "GET")
        self.assertEqual(environ["PATH_INFO"], "/path")
        self.assertEqual(environ["QUERY_STRING"], "q=1")
        self.assertEqual(environ["SERVER_PROTOCOL"], "HTTP/1.1")
        self.assertEqual(environ["SERVER_SOFTWARE"], server_software)
        self.assertEqual(environ["REMOTE_ADDR"], "127.0.0.1")
        self.assertEqual(environ["REMOTE_PORT"], 54321)
        self.assertEqual(environ["CONTENT_TYPE"], "application/json; charset=utf-8")
        self.assertEqual(environ["CHARSET"], "utf-8")
        self.assertEqual(environ["HTTP_HOST"], "example.com")

    def test_make_environ_default_content_type(self):
        """缺少 Content-Type 时使用默认纯文本类型"""
        server = make_server(server_port=80)
        rw = io.BytesIO(b"GET / HTTP/1.1\r\n\r\n")
        environ = make_environ(server, rw, ("127.0.0.1", 1))
        self.assertEqual(environ["CONTENT_TYPE"], "text/plain; charset=utf-8")

    def test_make_environ_root_path_script_name(self):
        """根路径请求的 SCRIPT_NAME 回落为 index.html"""
        server = make_server(server_port=80)
        rw = io.BytesIO(b"GET / HTTP/1.1\r\n\r\n")
        environ = make_environ(server, rw, ("127.0.0.1", 1))
        self.assertEqual(environ["SCRIPT_NAME"], "index.html")

    def test_make_environ_invalid_request(self):
        """空请求行抛出 HttpError"""
        server = make_server(server_port=80)
        with self.assertRaises(HttpError):
            make_environ(server, io.BytesIO(b""), ("127.0.0.1", 1))

    def test_make_environ_body_too_large(self):
        """请求体超过 max_request_size 时抛出 413"""
        server = make_server(max_request_size=10, server_port=80)
        rw = io.BytesIO(b"POST / HTTP/1.1\r\nContent-Length: 100\r\n\r\n")
        with self.assertRaises(HttpError) as ctx:
            make_environ(server, rw, ("127.0.0.1", 1))
        self.assertEqual(ctx.exception.status_code, 413)


# ==================== error_pages.py 快照 ====================


class TestErrorPagesSnapshot(unittest.TestCase):
    """错误页面渲染行为快照"""

    def setUp(self):
        self.renderer = ErrorPageRenderer()

    def test_default_templates_cover_expected_codes(self):
        """默认模板覆盖预期状态码"""
        for code in (400, 403, 404, 500, 502, 503, 504):
            self.assertIn(code, ErrorPageRenderer.DEFAULT_ERROR_TEMPLATES)

    def test_render_error_page_contains_placeholders_replaced(self):
        """渲染后占位符被替换"""
        content = self.renderer.render_error_page(404, "缺失", "详情")
        self.assertNotIn("{{ERROR_MESSAGE}}", content)
        self.assertNotIn("{{ERROR_DETAIL}}", content)
        self.assertIn("缺失", content)
        self.assertIn("详情", content)

    def test_render_error_page_without_message(self):
        """未提供消息时占位符替换为空"""
        content = self.renderer.render_error_page(500)
        self.assertNotIn("{{ERROR_MESSAGE}}", content)
        self.assertNotIn("{{ERROR_DETAIL}}", content)

    def test_render_unknown_code_falls_back_to_500(self):
        """未知状态码回落到 500 模板"""
        content = self.renderer.render_error_page(418)
        self.assertIn("500", content)

    def test_get_error_page_returns_triple(self):
        """get_error_page 返回 (状态码, 内容类型, HTML)"""
        status, content_type, content = self.renderer.get_error_page(404)
        self.assertEqual(status, 404)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("<html", content.lower())

    def test_custom_template_dir(self):
        """自定义错误页目录中的模板优先"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = "%s/404.html" % tmpdir
            with open(path, "w", encoding="utf-8") as f:
                f.write("<h1>自定义 404</h1>")
            renderer = ErrorPageRenderer(tmpdir)
            content = renderer.render_error_page(404)
            self.assertIn("自定义 404", content)


# ==================== handlers/base.py 快照 ====================


class TestBaseRequestHandlerSnapshot(unittest.TestCase):
    """基类请求处理器行为快照"""

    def _make_handler(self, **overrides):
        app = make_app()
        environ = make_environ_dict(**overrides)
        return BaseRequestHandler(app, environ)

    def test_basic_properties(self):
        """基础属性读取冻结"""
        handler = self._make_handler()
        self.assertEqual(handler.request_method, "GET")
        self.assertEqual(handler.path_info, "/index")
        self.assertEqual(handler.query_string, "")
        self.assertEqual(handler.server_protocol, "HTTP/1.1")
        self.assertEqual(handler.get, {})
        self.assertEqual(handler.post, {})
        self.assertEqual(handler.body, "")
        self.assertEqual(handler.files, {})
        self.assertEqual(handler.form, {})
        self.assertEqual(handler.json, {})
        self.assertEqual(handler.data, {})
        self.assertEqual(handler.params, {})
        self.assertIsNone(handler.session_id)
        self.assertIsNone(handler.session)

    def test_content_length_absent_is_zero(self):
        """WSGI 链路缺少 CONTENT_LENGTH 时为 0（与 socket 链路的 -1 不同）"""
        handler = self._make_handler()
        self.assertEqual(handler.content_length, 0)

    def test_request_uri(self):
        """request_uri 拼接路径与查询串"""
        handler = self._make_handler(PATH_INFO="/a", QUERY_STRING="b=1")
        self.assertEqual(handler.request_uri, "/a?b=1")

    def test_headers_from_environ(self):
        """headers 从 environ 的 HTTP_ 前缀键构造，键名统一小写"""
        handler = self._make_handler(HTTP_X_CUSTOM="v")
        self.assertEqual(handler.headers["x-custom"], "v")

    def test_start_response_sets_status(self):
        """start_response 记录状态码与响应头"""
        handler = self._make_handler()
        handler.start_response(201, headers=[("X-A", "1")])
        self.assertEqual(handler._status_code, 201)
        self.assertTrue(handler._headers_responsed)
        self.assertEqual(handler._headers, [("X-A", "1")])

    def test_start_response_twice_raises(self):
        """响应头已发出后再次 start_response 抛错"""
        handler = self._make_handler()
        handler.start_response(200)
        with self.assertRaises(ValueError):
            handler.start_response(200)

    def test_add_header_and_response_headers(self):
        """_add_header 与 _add_response_headers 累积响应头"""
        handler = self._make_handler()
        handler._add_header("X-One", "1")
        extra = []
        handler._add_response_headers(extra)
        self.assertEqual(handler._headers, [("X-One", "1")])
        self.assertEqual(extra, [("X-One", "1")])

    def test_response_builds_standard_headers(self):
        """_response 产出标准安全头并返回 (状态行, 响应头, 内容) 三元组"""
        handler = self._make_handler()
        status, headers, content = handler._response(200, content="ok")
        self.assertEqual(status, "200 OK")
        self.assertEqual(content, "ok")
        header_map = dict(headers)
        self.assertEqual(header_map["Server"], server_info)
        self.assertEqual(header_map["X-Content-Type-Options"], "nosniff")
        self.assertEqual(header_map["X-Frame-Options"], "SAMEORIGIN")
        self.assertEqual(header_map["Content-Type"], default_content_type)
        self.assertEqual(header_map["Content-Length"], "2")

    def test_response_default_body(self):
        """content 为 None 时回落到默认状态消息"""
        handler = self._make_handler()
        status, _headers, content = handler._response(404)
        self.assertEqual(status, "404 Not Found")
        self.assertIn("404", content)

    def test_redirect_helper(self):
        """_redirect 生成 302 状态行与 Location 头"""
        handler = self._make_handler(HTTP_HOST="example.com")
        status, headers, content = handler._redirect("/go")
        self.assertEqual(status, "302 Found")
        self.assertEqual(content, "302 Found")
        self.assertIn(("Location", "/go"), headers)

    def test_inject_translations_is_idempotent(self):
        """_inject_translations 不覆盖调用方显式传入的同名变量"""
        result = BaseRequestHandler._inject_translations({"_": "custom"})
        self.assertEqual(result["_"], "custom")

    def test_build_request_headers_lowercases_keys(self):
        """_build_request_headers 生成小写键的请求头字典"""
        headers = BaseRequestHandler._build_request_headers(
            {"HTTP_X_UPPER": "v", "HTTP_X_UPPER2": "w"}
        )
        self.assertEqual(headers["x-upper"], "v")
        self.assertEqual(headers["x-upper2"], "w")


# ==================== config.py 快照 ====================


class TestConfigSnapshot(unittest.TestCase):
    """配置管理行为快照"""

    def test_default_config_keys(self):
        """默认配置包含关键项"""
        config = Config()
        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 9090)
        self.assertEqual(config.cache_backend, "tree")
        self.assertEqual(config.session_backend, "memory")
        self.assertEqual(config.session_name, "litefs.sid")

    def test_kwargs_override_defaults(self):
        """关键字参数覆盖默认值"""
        config = Config(port=1234, debug=True)
        self.assertEqual(config.port, 1234)
        self.assertTrue(config.debug)

    def test_set_and_get(self):
        """set / get 读写配置"""
        config = Config()
        config.set("port", 1234)
        self.assertEqual(config.get("port"), 1234)
        self.assertEqual(config.get("missing", "fallback"), "fallback")

    def test_set_unknown_key_raises(self):
        """未知配置项在 set 时抛 ValueError"""
        config = Config()
        with self.assertRaises(ValueError):
            config.set("not_a_real_key", "value")

    def test_update_and_to_dict(self):
        """update 与 to_dict 行为"""
        config = Config()
        config.update(port=1234, host="example.com")
        data = config.to_dict()
        self.assertEqual(data["port"], 1234)
        self.assertEqual(data["host"], "example.com")

    def test_update_unknown_key_raises(self):
        """未知配置项在 update 时抛 ValueError"""
        config = Config()
        with self.assertRaises(ValueError):
            config.update(not_a_real_key=1)

    def test_membership_and_iteration(self):
        """in / keys / values / items 行为"""
        config = Config()
        self.assertIn("port", config)
        self.assertNotIn("no_such_key", config)
        self.assertIn("port", config.keys())
        self.assertIn(9090, config.values())
        self.assertIn(("port", 9090), config.items())

    def test_invalid_cache_backend_raises(self):
        """非法缓存后端抛 ValueError"""
        with self.assertRaises(ValueError):
            Config(cache_backend="nonexistent")

    def test_invalid_port_raises(self):
        """非法端口抛 ValueError"""
        with self.assertRaises(ValueError):
            Config(port=0)
        with self.assertRaises(ValueError):
            Config(port=70000)

    def test_invalid_samesite_raises(self):
        """非法 SameSite 策略抛 ValueError"""
        with self.assertRaises(ValueError):
            Config(session_same_site="Invalid")

    def test_env_var_override(self):
        """环境变量覆盖默认值且按默认值推断类型"""
        with patch.dict("os.environ", {"LITEFS_PORT": "8888", "LITEFS_DEBUG": "true"}):
            config = Config()
        self.assertEqual(config.port, 8888)
        self.assertTrue(config.debug)

    def test_env_var_list_parsing(self):
        """列表型默认值的环境变量按逗号切分"""
        with patch.dict("os.environ", {"LITEFS_I18N_SUPPORTED_LOCALES": "en,zh"}):
            config = Config()
        self.assertEqual(config.i18n_supported_locales, ["en", "zh"])

    def test_yaml_config_loading(self):
        """YAML 配置文件被正确加载"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = "%s/config.yaml" % tmpdir
            with open(path, "w", encoding="utf-8") as f:
                f.write("port: 7777\ncache_backend: memory\n")
            config = Config(path)
        self.assertEqual(config.port, 7777)
        self.assertEqual(config.cache_backend, "memory")

    def test_json_config_loading(self):
        """JSON 配置文件被正确加载"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = "%s/config.json" % tmpdir
            with open(path, "w", encoding="utf-8") as f:
                f.write('{"port": 6666}')
            config = Config(path)
        self.assertEqual(config.port, 6666)

    def test_unsupported_config_format_raises(self):
        """不支持的配置文件格式抛 ValueError"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = "%s/config.txt" % tmpdir
            with open(path, "w", encoding="utf-8") as f:
                f.write("port = 1\n")
            with self.assertRaises(ValueError):
                Config(path)

    def test_missing_config_file_falls_back_to_defaults(self):
        """配置文件不存在时回落默认值而非抛错"""
        config = Config("/nonexistent/path/config.yaml")
        self.assertEqual(config.port, 9090)

    def test_encrypt_decrypt_roundtrip(self):
        """配置加密解密往返一致"""
        config = Config(config_secret_key="my-secret")
        encrypted = config.encrypt_config("k", {"a": 1})
        self.assertIsInstance(encrypted, str)
        self.assertEqual(config.decrypt_config(encrypted), {"a": 1})

    def test_encrypt_without_secret_key_raises(self):
        """未设置加密密钥时抛 ValueError"""
        config = Config()
        with self.assertRaises(ValueError):
            config.encrypt_config("k", "v")

    def test_load_config_helper(self):
        """load_config 返回 Config 实例"""
        config = load_config(port=3210)
        self.assertIsInstance(config, Config)
        self.assertEqual(config.port, 3210)

    def test_merge_configs(self):
        """merge_configs 合并多个配置且后者优先"""
        merged = merge_configs({"port": 1, "host": "a"}, {"port": 2})
        self.assertIsInstance(merged, Config)
        self.assertEqual(merged.port, 2)
        self.assertEqual(merged.host, "a")

    def test_repr_contains_class_name(self):
        """repr 包含类名"""
        self.assertIn("Config", repr(Config()))


if __name__ == "__main__":
    unittest.main()
