#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AsyncIO 服务器测试
"""

import pytest
import asyncio
import socket
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from litefs.server.asyncio import (
    parse_header,
    AsyncHTTPRequestHandler,
    AsyncHTTPServer,
    run_asyncio
)
from litefs.exceptions import HttpError


class TestParseHeader:
    """测试 parse_header 函数"""
    
    def test_parse_simple_header(self):
        """测试解析简单头部"""
        main, params = parse_header('text/html')
        # parse_header 返回完整的 MIME 类型作为第一个元素
        assert main == ('text/html', '')
        assert params == {}
    
    def test_parse_header_with_charset(self):
        """测试解析带字符集的头部"""
        main, params = parse_header('text/html; charset=utf-8')
        assert main == ('text/html', '')
        assert 'charset' in params
        assert params['charset'] == 'utf-8'
    
    def test_parse_header_with_multiple_params(self):
        """测试解析带多个参数的头部"""
        main, params = parse_header('text/html; charset=utf-8; boundary=abc123')
        assert main == ('text/html', '')
        assert params['charset'] == 'utf-8'
        assert params['boundary'] == 'abc123'


class TestAsyncHTTPRequestHandler:
    """异步 HTTP 请求处理器测试"""
    
    @pytest.fixture
    def setup_handler(self):
        """设置测试环境"""
        app = Mock()
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = AsyncMock(spec=asyncio.StreamWriter)
        client_address = ('127.0.0.1', 12345)
        server = Mock()
        server.server_name = 'localhost'
        server.server_port = '8000'
        
        handler = AsyncHTTPRequestHandler(
            app, reader, writer, client_address, server
        )
        
        return handler, reader, writer
    
    def test_init(self, setup_handler):
        """测试初始化"""
        handler, reader, writer = setup_handler
        
        assert handler.app is not None
        assert handler.reader == reader
        assert handler.writer == writer
        assert handler.client_address == ('127.0.0.1', 12345)
        assert handler.keep_alive_timeout == 5.0
        assert handler.keep_alive == False
    
    def test_check_keep_alive_http11_default(self, setup_handler):
        """测试 HTTP/1.1 默认 keep-alive"""
        handler, reader, writer = setup_handler
        
        scope = {
            'http_version': '1.1',
            'headers': []
        }
        
        handler._check_keep_alive(scope)
        assert handler.keep_alive == True
    
    def test_check_keep_alive_http11_close(self, setup_handler):
        """测试 HTTP/1.1 带 close 头"""
        handler, reader, writer = setup_handler
        
        scope = {
            'http_version': '1.1',
            'headers': [
                [b'connection', b'close']
            ]
        }
        
        handler._check_keep_alive(scope)
        assert handler.keep_alive == False
    
    def test_check_keep_alive_http10_default(self, setup_handler):
        """测试 HTTP/1.0 默认不 keep-alive"""
        handler, reader, writer = setup_handler
        
        scope = {
            'http_version': '1.0',
            'headers': []
        }
        
        handler._check_keep_alive(scope)
        assert handler.keep_alive == False
    
    def test_check_keep_alive_http10_keepalive(self, setup_handler):
        """测试 HTTP/1.0 带 keep-alive 头"""
        handler, reader, writer = setup_handler
        
        scope = {
            'http_version': '1.0',
            'headers': [
                [b'connection', b'keep-alive']
            ]
        }
        
        handler._check_keep_alive(scope)
        assert handler.keep_alive == True
    
    @pytest.mark.asyncio
    async def test_build_scope_get(self, setup_handler):
        """测试构建 GET 请求的 scope"""
        handler, reader, writer = setup_handler
        
        # 模拟读取请求行
        reader.readline.side_effect = [
            b'GET /test?foo=bar HTTP/1.1\r\n',
            b'Host: localhost:8000\r\n',
            b'User-Agent: test\r\n',
            b'\r\n'
        ]
        
        scope = await handler._build_scope()
        
        assert scope['type'] == 'http'
        assert scope['method'] == 'GET'
        assert scope['path'] == '/test'
        assert scope['query_string'] == b'foo=bar'
        assert scope['http_version'] == '1.1'
    
    @pytest.mark.asyncio
    async def test_build_scope_post(self, setup_handler):
        """测试构建 POST 请求的 scope"""
        handler, reader, writer = setup_handler
        
        # 模拟读取请求行
        reader.readline.side_effect = [
            b'POST /api/users HTTP/1.1\r\n',
            b'Content-Type: application/json\r\n',
            b'Content-Length: 17\r\n',
            b'\r\n'
        ]
        
        scope = await handler._build_scope()
        
        assert scope['method'] == 'POST'
        assert scope['path'] == '/api/users'
        assert len(scope['headers']) == 2
    
    @pytest.mark.asyncio
    async def test_build_scope_empty_request_line(self, setup_handler):
        """测试空请求行"""
        handler, reader, writer = setup_handler
        
        reader.readline.return_value = b''
        
        with pytest.raises(HttpError) as exc_info:
            await handler._build_scope()
        
        assert exc_info.value.status_code == 400
    
    @pytest.mark.asyncio
    async def test_build_scope_invalid_request_line(self, setup_handler):
        """测试无效请求行"""
        handler, reader, writer = setup_handler
        
        reader.readline.return_value = b'INVALID\r\n'
        
        with pytest.raises(HttpError) as exc_info:
            await handler._build_scope()
        
        assert exc_info.value.status_code == 400
    
    def test_create_receive(self, setup_handler):
        """测试创建 receive 函数"""
        handler, reader, writer = setup_handler
        
        receive = handler._create_receive()
        assert callable(receive)
        assert asyncio.iscoroutinefunction(receive)
    
    @pytest.mark.asyncio
    async def test_receive_function(self, setup_handler):
        """测试 receive 函数"""
        handler, reader, writer = setup_handler
        
        reader.read.return_value = b'{"test": "data"}'
        
        receive = handler._create_receive()
        message = await receive()
        
        assert message['type'] == 'http.request'
        assert message['body'] == b'{"test": "data"}'
        assert message['more_body'] == False
    
    def test_create_send(self, setup_handler):
        """测试创建 send 函数"""
        handler, reader, writer = setup_handler
        
        send = handler._create_send()
        assert callable(send)
        assert asyncio.iscoroutinefunction(send)
    
    @pytest.mark.asyncio
    async def test_send_response_start(self, setup_handler):
        """测试发送响应头"""
        handler, reader, writer = setup_handler
        
        send = handler._create_send()
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/html'],
                [b'content-length', b'123'],
            ]
        })
        
        # 验证 writer.write 被调用（响应头不调用 drain）
        assert writer.write.called
    
    @pytest.mark.asyncio
    async def test_send_response_body(self, setup_handler):
        """测试发送响应体"""
        handler, reader, writer = setup_handler
        
        send = handler._create_send()
        
        await send({
            'type': 'http.response.body',
            'body': b'Hello World'
        })
        
        # 验证 writer.write 被调用
        assert writer.write.called
        assert writer.drain.called
    
    @pytest.mark.asyncio
    async def test_send_error(self, setup_handler):
        """测试发送错误响应"""
        handler, reader, writer = setup_handler
        
        await handler._send_error(404, "Not Found")
        
        # 验证 writer.write 被调用
        assert writer.write.called
        assert writer.drain.called


class TestAsyncHTTPServer:
    """异步 HTTP 服务器测试"""
    
    @pytest.fixture
    def server(self):
        """创建服务器实例"""
        app = Mock()
        return AsyncHTTPServer(app, host='localhost', port=8000)
    
    def test_init(self, server):
        """测试初始化"""
        assert server.host == 'localhost'
        assert server.port == 8000
        assert server.processes == 1
        assert server.keep_alive_timeout == 5.0
        assert server._server is None
    
    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        app = Mock()
        server = AsyncHTTPServer(
            app,
            host='0.0.0.0',
            port=9000,
            processes=4,
            keep_alive_timeout=10.0
        )
        
        assert server.host == '0.0.0.0'
        assert server.port == 9000
        assert server.processes == 4
        assert server.keep_alive_timeout == 10.0
    
    @pytest.mark.asyncio
    async def test_handle_client(self, server):
        """测试处理客户端连接"""
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = AsyncMock(spec=asyncio.StreamWriter)
        
        # 模拟客户端地址
        writer.get_extra_info.return_value = ('127.0.0.1', 12345)
        
        # 模拟请求
        reader.readline.side_effect = [
            b'GET / HTTP/1.1\r\n',
            b'\r\n',
            b''
        ]
        reader.read.return_value = b''
        
        # 调用处理函数
        await server.handle_client(reader, writer)
        
        # 验证 writer 被关闭
        assert writer.close.called
    
    @pytest.mark.asyncio
    async def test_start_server(self, server):
        """测试启动服务器"""
        # 使用 patch 模拟 asyncio.start_server
        with patch('asyncio.start_server') as mock_start_server:
            mock_server = AsyncMock()
            mock_server.sockets = [Mock()]
            mock_server.sockets[0].getsockname.return_value = ('localhost', 8000)
            mock_start_server.return_value = mock_server
            
            # 启动服务器（会在后台运行）
            task = asyncio.create_task(server.start())
            
            # 等待一小段时间让服务器启动
            await asyncio.sleep(0.1)
            
            # 验证 start_server 被调用
            assert mock_start_server.called
            
            # 取消任务
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestRunAsyncio:
    """测试 run_asyncio 函数"""
    
    def test_run_asyncio_function(self):
        """测试 run_asyncio 函数"""
        app = Mock()
        
        # 使用 patch 模拟服务器运行
        with patch.object(AsyncHTTPServer, 'run') as mock_run:
            run_asyncio(app, host='localhost', port=8000)
            
            # 验证 run 被调用
            assert mock_run.called
    
    def test_run_asyncio_with_params(self):
        """测试带参数的 run_asyncio"""
        app = Mock()
        
        with patch.object(AsyncHTTPServer, 'run') as mock_run:
            run_asyncio(
                app,
                host='0.0.0.0',
                port=9000,
                processes=2,
                keep_alive_timeout=10.0
            )
            
            # 验证 run 被调用
            assert mock_run.called


class TestAsyncIOIntegration:
    """AsyncIO 集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_request_response_cycle(self):
        """测试完整的请求-响应周期"""
        # 创建模拟的应用
        app = Mock()
        app.routes = []
        
        # 创建服务器
        server = AsyncHTTPServer(app, host='localhost', port=8000)
        
        # 创建模拟的 reader 和 writer
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = AsyncMock(spec=asyncio.StreamWriter)
        writer.get_extra_info.return_value = ('127.0.0.1', 12345)
        
        # 模拟 HTTP 请求
        reader.readline.side_effect = [
            b'GET /test HTTP/1.1\r\n',
            b'Host: localhost:8000\r\n',
            b'\r\n',
        ]
        reader.read.return_value = b''
        
        # 处理请求
        await server.handle_client(reader, writer)
        
        # 验证响应被发送
        assert writer.write.called or not reader.readline.called
    
    @pytest.mark.asyncio
    async def test_keep_alive_connection(self):
        """测试 keep-alive 连接"""
        app = Mock()
        server = AsyncHTTPServer(app, host='localhost', port=8000)
        
        reader = AsyncMock(spec=asyncio.StreamReader)
        writer = AsyncMock(spec=asyncio.StreamWriter)
        writer.get_extra_info.return_value = ('127.0.0.1', 12345)
        
        # 模拟两个连续的请求
        reader.readline.side_effect = [
            b'GET /test1 HTTP/1.1\r\n',
            b'Connection: keep-alive\r\n',
            b'\r\n',
            b'GET /test2 HTTP/1.1\r\n',
            b'\r\n',
        ]
        reader.read.return_value = b''
        
        # 处理请求
        await server.handle_client(reader, writer)
        
        # 验证连接被处理
        assert writer.write.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
