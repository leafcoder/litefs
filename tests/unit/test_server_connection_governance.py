#!/usr/bin/env python
# coding: utf-8
"""
原生服务器连接治理测试

覆盖连接数上限快速拒绝（max_connections）、空闲读超时（idle_read_timeout）
与 asyncio 服务器 500 响应信息泄露修复。
"""

import asyncio
import socket
import time
import unittest
from unittest.mock import Mock

from litefs.server import HTTPServer
from litefs.server.greenlet_server_base import Epoll
from litefs.server.asyncio import (
    AsyncHTTPRequestHandler,
    AsyncHTTPServer,
    _internal_error_message,
)


def _dummy_handler(request, rw, environ, server):
    """占位请求处理器（连接治理测试中不会被真正调用）"""


class FakeGreenlet:
    """记录 throw 调用的伪 greenlet"""

    def __init__(self):
        self.thrown = []

    def throw(self, exc=None):
        self.thrown.append(exc)


class TestMaxConnections(unittest.TestCase):
    """原生服务器最大连接数治理"""

    def test_default_unlimited(self):
        """测试类默认不限制连接数（保持 API 层向后兼容）"""
        server = HTTPServer(('127.0.0.1', 0), _dummy_handler)
        try:
            self.assertIsNone(server.max_connections)
        finally:
            server.server_close()

    def test_verify_request_rejects_when_full(self):
        """测试达到连接数上限时 verify_request 返回 False"""
        server = HTTPServer(('127.0.0.1', 0), _dummy_handler)
        try:
            server.max_connections = 0
            self.assertFalse(
                server.verify_request(object(), ('127.0.0.1', 1))
            )
            server.max_connections = 100
            self.assertTrue(
                server.verify_request(object(), ('127.0.0.1', 1))
            )
        finally:
            server.server_close()

    def test_excess_connection_fast_rejected(self):
        """测试超限连接被快速关闭，不进入请求处理流程"""
        server = HTTPServer(('127.0.0.1', 0), _dummy_handler)
        server.max_connections = 0
        client = socket.create_connection(server.socket.getsockname()[:2])
        try:
            server.handle_request()
            # 快速拒绝表现为连接被立即关闭（读到 EOF）
            self.assertEqual(client.recv(1024), b'')
        finally:
            client.close()
            server.server_close()


class TestIdleReadTimeout(unittest.TestCase):
    """原生服务器空闲读超时治理"""

    def test_default_30s(self):
        """测试空闲读超时默认 30 秒"""
        server = HTTPServer(('127.0.0.1', 0), _dummy_handler)
        try:
            self.assertEqual(server.idle_read_timeout, 30.0)
        finally:
            server.server_close()

    def test_expired_deadline_throws_timeout(self):
        """测试过期的读等待被注入 socket.timeout 并移出调度"""
        ep = Epoll()
        gr = FakeGreenlet()
        ep._greenlets[101] = gr
        ep._read_deadlines[101] = time.time() - 0.01

        ep._check_read_deadlines()

        self.assertNotIn(101, ep._greenlets)
        self.assertNotIn(101, ep._read_deadlines)
        self.assertEqual(len(gr.thrown), 1)
        self.assertIsInstance(gr.thrown[0], socket.timeout)

    def test_live_deadline_not_thrown(self):
        """测试未过期的读等待不受影响"""
        ep = Epoll()
        gr = FakeGreenlet()
        ep._greenlets[102] = gr
        ep._read_deadlines[102] = time.time() + 30

        ep._check_read_deadlines()

        self.assertIn(102, ep._greenlets)
        self.assertEqual(gr.thrown, [])

    def test_deadline_without_greenlet_ignored(self):
        """测试无对应 greenlet 的过期记录被安全清理"""
        ep = Epoll()
        ep._read_deadlines[103] = time.time() - 0.01

        ep._check_read_deadlines()

        self.assertNotIn(103, ep._read_deadlines)


class _FakeAsyncWriter:
    """asyncio.StreamWriter 伪对象（记录关闭状态）"""

    def __init__(self):
        self.closed = False
        self.written = b''

    def get_extra_info(self, name):
        return ('127.0.0.1', 1)

    def write(self, data):
        self.written += data

    async def drain(self):
        return None

    def close(self):
        self.closed = True

    async def wait_closed(self):
        return None

    def is_closing(self):
        return self.closed


class TestAsyncioServerErrorResponse(unittest.TestCase):
    """asyncio 服务器 500 响应信息泄露修复"""

    def test_non_debug_hides_exception_detail(self):
        """测试非 debug 模式 500 响应不包含异常细节"""
        app = Mock()
        app.config.debug = False

        message = _internal_error_message(app, ValueError('secret db password'))

        self.assertNotIn('secret db password', message)
        self.assertIn('Internal Server Error', message)

    def test_debug_keeps_exception_detail(self):
        """测试 debug 模式 500 响应保留异常细节"""
        app = Mock()
        app.config.debug = True

        message = _internal_error_message(app, ValueError('secret db password'))

        self.assertIn('secret db password', message)

    def test_handle_request_sends_sanitized_500(self):
        """测试请求处理异常时发送脱敏的 500 响应"""
        app = Mock()
        app.config.debug = False

        async def scenario():
            reader = Mock()

            async def bad_scope():
                raise RuntimeError('secret db password')

            handler = AsyncHTTPRequestHandler(
                Mock(), reader, _FakeAsyncWriter(),
                ('127.0.0.1', 1), Mock(),
            )
            handler.app = app
            handler._build_scope = bad_scope
            await handler.handle_request()
            return handler

        handler = asyncio.run(scenario())
        self.assertNotIn(b'secret db password', handler.writer.written)
        self.assertIn(b'Internal Server Error', handler.writer.written)


class TestAsyncioConnectionGovernance(unittest.TestCase):
    """asyncio 服务器连接治理"""

    def test_excess_connection_fast_rejected(self):
        """测试超过 max_connections 后新连接被立即关闭"""

        async def scenario():
            server = AsyncHTTPServer(Mock(), max_connections=0)
            writer = _FakeAsyncWriter()
            await server.handle_client(Mock(), writer)
            return writer

        writer = asyncio.run(scenario())
        self.assertTrue(writer.closed)

    def test_idle_read_timeout_closes_connection(self):
        """测试空闲读超时后连接被关闭（慢速请求头攻击防护）"""

        async def scenario():
            server = Mock()
            reader = Mock()

            async def hang_readline():
                await asyncio.sleep(5)
                return b''

            reader.readline = hang_readline
            writer = _FakeAsyncWriter()
            handler = AsyncHTTPRequestHandler(
                Mock(), reader, writer, ('127.0.0.1', 1), server,
                idle_read_timeout=0.05,
            )
            await handler.handle_request()
            return writer

        writer = asyncio.run(scenario())
        self.assertTrue(writer.closed)


if __name__ == '__main__':
    unittest.main()
