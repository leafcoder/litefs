#!/usr/bin/env python
# coding: utf-8

"""
chunked 请求体支持测试

覆盖同步 read_chunked_body 工具函数、Socket 链路与 asyncio 链路的
chunked 传输编码解码及实际读取大小强制限制（对应代码审计 4.4 节 0.12-⭐2，D11）。
"""

import asyncio
import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from litefs.exceptions import HttpError
from litefs.handlers.form import read_chunked_body
from litefs.handlers.socket import SocketRequestHandler
from litefs.server.asyncio import AsyncHTTPRequestHandler


class _ChunkedRW(io.BytesIO):
    """同时提供 readline / read 的内存流（模拟 BufferedRWPair）"""


class TestReadChunkedBody(unittest.TestCase):
    """read_chunked_body 同步解码工具"""

    def test_basic_chunks(self):
        """多 chunk 顺序解码"""
        rw = _ChunkedRW(b'5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n')
        self.assertEqual(read_chunked_body(rw.readline, rw.read), b'hello world')

    def test_chunk_extension_ignored(self):
        """chunk 大小行的扩展声明被忽略"""
        rw = _ChunkedRW(b'5;ext=val\r\nhello\r\n0\r\n\r\n')
        self.assertEqual(read_chunked_body(rw.readline, rw.read), b'hello')

    def test_trailer_headers_consumed(self):
        """trailer 头部被消费"""
        rw = _ChunkedRW(b'5\r\nhello\r\n0\r\nX-Trailer: v\r\n\r\n')
        self.assertEqual(read_chunked_body(rw.readline, rw.read), b'hello')

    def test_oversized_raises_413(self):
        """解码字节数超过上限抛 413"""
        rw = _ChunkedRW(b'10\r\n0123456789\r\n0\r\n\r\n')
        with self.assertRaises(HttpError) as ctx:
            read_chunked_body(rw.readline, rw.read, max_size=5)
        self.assertEqual(ctx.exception.status_code, 413)

    def test_invalid_chunk_size_raises_400(self):
        """chunk 大小非法抛 400"""
        rw = _ChunkedRW(b'zz\r\nhello\r\n0\r\n\r\n')
        with self.assertRaises(HttpError) as ctx:
            read_chunked_body(rw.readline, rw.read)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_negative_chunk_size_raises_400(self):
        """chunk 大小为负抛 400"""
        rw = _ChunkedRW(b'-5\r\nhello\r\n0\r\n\r\n')
        with self.assertRaises(HttpError) as ctx:
            read_chunked_body(rw.readline, rw.read)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_truncated_chunk_raises_400(self):
        """chunk 数据被截断抛 400"""
        rw = _ChunkedRW(b'10\r\nshort')
        with self.assertRaises(HttpError) as ctx:
            read_chunked_body(rw.readline, rw.read)
        self.assertEqual(ctx.exception.status_code, 400)

    def test_bad_chunk_delimiter_raises_400(self):
        """chunk 数据后的分隔符非法抛 400"""
        rw = _ChunkedRW(b'5\r\nhelloXX0\r\n\r\n')
        with self.assertRaises(HttpError) as ctx:
            read_chunked_body(rw.readline, rw.read)
        self.assertEqual(ctx.exception.status_code, 400)


class TestSocketHandlerChunked(unittest.TestCase):
    """Socket 链路 chunked 请求体支持"""

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
        self.mock_app._get_middleware_instances = Mock(return_value=[])

    def _environ(self, content_type, transfer_encoding='chunked'):
        """构造带 Transfer-Encoding 的请求环境"""
        environ = {
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '8000',
            'SERVER_PROTOCOL': 'HTTP/1.1',
            'CONTENT_TYPE': content_type,
        }
        if transfer_encoding:
            environ['HTTP_TRANSFER_ENCODING'] = transfer_encoding
        return environ

    def test_urlencoded_chunked_body(self):
        """chunked 编码的 urlencoded 表单正常解析"""
        rw = _ChunkedRW(b'9\r\nname=tom&\r\n5\r\nage=1\r\n0\r\n\r\n')
        handler = SocketRequestHandler(
            self.mock_app, rw,
            self._environ('application/x-www-form-urlencoded'), Mock()
        )
        self.assertEqual(handler._post, {'name': 'tom', 'age': '1'})

    def test_multipart_chunked_body(self):
        """chunked 编码的 multipart 表单正常解析"""
        body = (
            b'--B\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'\r\nhello\r\n'
            b'--B--\r\n'
        )
        chunked = b''
        for i in range(0, len(body), 10):
            chunk = body[i:i + 10]
            chunked += b'%x\r\n%s\r\n' % (len(chunk), chunk)
        chunked += b'0\r\n\r\n'
        rw = _ChunkedRW(chunked)
        handler = SocketRequestHandler(
            self.mock_app, rw,
            self._environ('multipart/form-data; boundary=B'), Mock()
        )
        self.assertEqual(handler._post, {'title': 'hello'})

    def test_content_length_synced_to_actual_size(self):
        """解码后 CONTENT_LENGTH 同步为实际字节长度"""
        rw = _ChunkedRW(b'5\r\nhello\r\n0\r\n\r\n')
        environ = self._environ('text/plain')
        SocketRequestHandler(self.mock_app, rw, environ, Mock())
        self.assertEqual(environ['CONTENT_LENGTH'], '5')


class _FakeAsyncReader:
    """模拟 asyncio.StreamReader 的最小接口"""

    def __init__(self, data):
        self._fp = io.BytesIO(data)

    async def readline(self):
        return self._fp.readline()

    async def readexactly(self, n):
        data = self._fp.read(n)
        if len(data) < n:
            raise asyncio.IncompleteReadError(data, n)
        return data

    async def read(self, n=-1):
        return self._fp.read(n)


class TestAsyncChunkedBody(unittest.TestCase):
    """asyncio 链路 chunked 请求体与大小限制"""

    def _handler(self, data, headers):
        """构造带预置 scope 头部的处理器"""
        app = SimpleNamespace(config=SimpleNamespace(max_request_size=10485760))
        reader = _FakeAsyncReader(data)
        server = SimpleNamespace(server_name='localhost', server_port='8000')
        handler = AsyncHTTPRequestHandler(
            app, reader, Mock(), ('127.0.0.1', 12345), server
        )
        handler._scope = {
            'headers': [(k.encode('utf-8'), v.encode('utf-8')) for k, v in headers]
        }
        return handler, reader

    def test_chunked_body_decoded(self):
        """chunked 编码请求体被正确解码"""
        handler, _ = self._handler(
            b'5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n',
            [('transfer-encoding', 'chunked')],
        )
        body = asyncio.run(handler._read_request_body())
        self.assertEqual(body, b'hello world')

    def test_content_length_exact_read(self):
        """Content-Length 精确读取，多余字节留给 keep-alive 下一请求"""
        handler, reader = self._handler(b'helloWORLD', [('content-length', '5')])
        body = asyncio.run(handler._read_request_body())
        self.assertEqual(body, b'hello')
        self.assertEqual(asyncio.run(reader.read()), b'WORLD')

    def test_content_length_oversize_raises_413(self):
        """Content-Length 超过上限抛 413"""
        handler, _ = self._handler(b'x' * 20, [('content-length', '20')])
        handler.app.config.max_request_size = 10
        with self.assertRaises(HttpError) as ctx:
            asyncio.run(handler._read_request_body())
        self.assertEqual(ctx.exception.status_code, 413)

    def test_chunked_oversize_raises_413(self):
        """chunked 解码字节数超过上限抛 413"""
        handler, _ = self._handler(
            b'a\r\n0123456789\r\n0\r\n\r\n',
            [('transfer-encoding', 'chunked')],
        )
        handler.app.config.max_request_size = 5
        with self.assertRaises(HttpError) as ctx:
            asyncio.run(handler._read_request_body())
        self.assertEqual(ctx.exception.status_code, 413)

    def test_truncated_body_raises_400(self):
        """请求体被截断抛 400"""
        handler, _ = self._handler(b'hel', [('content-length', '5')])
        with self.assertRaises(HttpError) as ctx:
            asyncio.run(handler._read_request_body())
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == '__main__':
    unittest.main()
