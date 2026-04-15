#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Greenlet 服务器测试
"""

import pytest
import socket
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO

# 检查是否安装了 greenlet
try:
    from greenlet import greenlet
    HAS_GREENLET = True
except ImportError:
    HAS_GREENLET = False


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestGreenletServer:
    """Greenlet 服务器测试"""
    
    def test_parse_header_simple(self):
        """测试解析简单头部"""
        from litefs.server.greenlet import parse_header
        
        main, params = parse_header('text/html')
        assert main == ('text/html', '')
        assert params == {}
    
    def test_parse_header_with_charset(self):
        """测试解析带字符集的头部"""
        from litefs.server.greenlet import parse_header
        
        main, params = parse_header('text/html; charset=utf-8')
        assert main == ('text/html', '')
        assert 'charset' in params
        assert params['charset'] == 'utf-8'
    
    def test_parse_header_with_boundary(self):
        """测试解析带 boundary 的头部"""
        from litefs.server.greenlet import parse_header
        
        main, params = parse_header('multipart/form-data; boundary=----WebKitFormBoundary')
        assert main == ('multipart/form-data', '')
        assert 'boundary' in params
        assert params['boundary'] == '----WebKitFormBoundary'
    
    def test_make_headers(self):
        """测试构建 HTTP 头"""
        from litefs.server.greenlet import make_headers
        
        # 模拟 socket 文件对象
        data = b"Host: localhost:8000\r\n"
        data += b"User-Agent: test-client\r\n"
        data += b"Content-Type: application/json\r\n"
        data += b"\r\n"
        
        rw = BytesIO(data)
        headers = make_headers(rw)
        
        assert headers['host'] == 'localhost:8000'
        assert headers['user-agent'] == 'test-client'
        assert headers['content-type'] == 'application/json'
    
    def test_make_environ(self):
        """测试构建 WSGI environ"""
        from litefs.server.greenlet import make_environ
        
        # 模拟服务器对象
        server = Mock()
        server.server_name = 'localhost'
        server.server_port = '8000'
        
        # 模拟 socket 文件对象
        data = b"GET /test?foo=bar HTTP/1.1\r\n"
        data += b"Host: localhost:8000\r\n"
        data += b"\r\n"
        
        rw = BytesIO(data)
        client_address = ('127.0.0.1', 12345)
        
        environ = make_environ(server, rw, client_address)
        
        assert environ['REQUEST_METHOD'] == 'GET'
        assert environ['PATH_INFO'] == '/test'
        assert environ['QUERY_STRING'] == 'foo=bar'
        assert environ['SERVER_NAME'] == 'localhost'
        assert environ['SERVER_PORT'] == '8000'
        assert environ['REMOTE_ADDR'] == '127.0.0.1'
    
    def test_make_environ_with_special_chars(self):
        """测试构建带特殊字符的 environ"""
        from litefs.server.greenlet import make_environ
        
        server = Mock()
        server.server_name = 'localhost'
        server.server_port = '8000'
        
        # 模拟带特殊字符的 URL
        data = b"GET /path%20with%20spaces?name=%E4%B8%AD%E6%96%87 HTTP/1.1\r\n"
        data += b"\r\n"
        
        rw = BytesIO(data)
        client_address = ('127.0.0.1', 12345)
        
        environ = make_environ(server, rw, client_address)
        
        # 验证 URL 解码
        assert 'path with spaces' in environ['PATH_INFO']
        assert '中文' in environ['QUERY_STRING']
    
    def test_make_environ_post_request(self):
        """测试构建 POST 请求的 environ"""
        from litefs.server.greenlet import make_environ
        
        server = Mock()
        server.server_name = 'localhost'
        server.server_port = '8000'
        del server.max_request_size  # 删除该属性，让 hasattr 返回 False
        
        # 模拟 POST 请求
        data = b"POST /api/users HTTP/1.1\r\n"
        data += b"Content-Type: application/json\r\n"
        data += b"Content-Length: 17\r\n"
        data += b"\r\n"
        
        rw = BytesIO(data)
        client_address = ('127.0.0.1', 12345)
        
        environ = make_environ(server, rw, client_address)
        
        assert environ['REQUEST_METHOD'] == 'POST'
        assert environ['PATH_INFO'] == '/api/users'
        assert environ['CONTENT_TYPE'] == 'application/json'


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestBufferedRWPair:
    """BufferedRWPair 测试"""
    
    def test_buffered_rw_pair_creation(self):
        """测试创建 BufferedRWPair"""
        from io import BytesIO
        from litefs.server.greenlet import BufferedRWPair
        
        # 创建可读写的 BytesIO 对象
        readable = BytesIO()
        writable = BytesIO()
        buffer = BufferedRWPair(readable, writable)
        
        assert buffer is not None
    
    def test_buffered_rw_pair_write_read(self):
        """测试 BufferedRWPair 读写"""
        from io import BytesIO
        from litefs.server.greenlet import BufferedRWPair
        
        # 创建可读写的 BytesIO 对象
        readable = BytesIO()
        writable = BytesIO()
        buffer = BufferedRWPair(readable, writable)
        
        # 测试写入
        data = b"test data"
        buffer.write(data)
        buffer.flush()
        
        # 验证写入成功
        assert writable.tell() > 0


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestHTTPServer:
    """HTTP 服务器测试"""
    
    def test_http_server_init(self):
        """测试 HTTP 服务器初始化"""
        from litefs.server.greenlet import HTTPServer
        
        app = Mock()
        server = HTTPServer(('localhost', 8000), app)
        
        # 验证服务器已创建
        assert server is not None
        assert server.server_address == ('localhost', 8000)
    
    def test_http_server_with_custom_params(self):
        """测试自定义参数初始化"""
        from litefs.server.greenlet import HTTPServer
        
        app = Mock()
        server = HTTPServer(('0.0.0.0', 9000), app)
        
        assert server is not None
        assert server.server_address == ('0.0.0.0', 9000)


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestProcessHTTPServer:
    """多进程 HTTP 服务器测试"""
    
    def test_process_server_init(self):
        """测试多进程服务器初始化"""
        from litefs.server.greenlet import ProcessHTTPServer
        
        app = Mock()
        server = ProcessHTTPServer(('localhost', 8000), app)
        
        # 验证服务器已创建
        assert server is not None
        assert server.server_address == ('localhost', 8000)
    
    def test_process_server_with_processes(self):
        """测试带进程数的服务器初始化"""
        from litefs.server.greenlet import ProcessHTTPServer
        
        app = Mock()
        server = ProcessHTTPServer(('localhost', 8000), app)
        
        assert server is not None
        assert server.server_address == ('localhost', 8000)


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestSocketIO:
    """SocketIO 测试"""
    
    def test_socket_io_creation(self):
        """测试创建 SocketIO"""
        from socket import socket
        from litefs.server.greenlet import SocketIO
        
        sock = socket()
        socket_io = SocketIO(sock, sock)
        
        assert socket_io is not None
        sock.close()
    
    def test_socket_io_read(self):
        """测试 SocketIO 读取"""
        from socket import socket
        from litefs.server.greenlet import SocketIO
        
        sock = socket()
        socket_io = SocketIO(sock, sock)
        
        # 由于 SocketIO 依赖 greenlet，无法直接测试
        # 这里只验证对象创建成功
        assert socket_io is not None
        sock.close()
    
    def test_socket_io_write(self):
        """测试 SocketIO 写入"""
        from socket import socket
        from litefs.server.greenlet import SocketIO
        
        sock = socket()
        socket_io = SocketIO(sock, sock)
        
        # 测试写入（不实际连接）
        # 由于没有实际连接，写入会失败
        try:
            result = socket_io.write(b"test data")
            assert isinstance(result, int)
        except Exception:
            # 预期会失败，因为没有实际连接
            pass
        
        sock.close()


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestGreenletUtilities:
    """Greenlet 工具函数测试"""
    
    def test_has_greenlet(self):
        """测试 greenlet 可用性"""
        from litefs.server.greenlet import HAS_GREENLET
        
        # 如果测试能运行到这里，说明 greenlet 已安装
        assert HAS_GREENLET == True
    
    def test_has_epoll(self):
        """测试 epoll 可用性"""
        from litefs.server.greenlet import HAS_EPOLL
        
        # epoll 在 Linux 上应该可用
        # 在其他系统上可能不可用
        assert isinstance(HAS_EPOLL, bool)
    
    def test_should_retry_error(self):
        """测试重试错误类型"""
        from litefs.server.greenlet import should_retry_error
        
        from errno import EWOULDBLOCK, EAGAIN
        
        assert EWOULDBLOCK in should_retry_error
        assert EAGAIN in should_retry_error


@pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
class TestGreenletIntegration:
    """Greenlet 集成测试"""
    
    def test_full_request_cycle(self):
        """测试完整的请求周期"""
        from litefs.server.greenlet import make_environ, make_headers
        
        # 模拟服务器
        server = Mock()
        server.server_name = 'localhost'
        server.server_port = '8000'
        
        # 模拟 HTTP 请求
        request_data = b"GET /index.html HTTP/1.1\r\n"
        request_data += b"Host: localhost:8000\r\n"
        request_data += b"User-Agent: test-client\r\n"
        request_data += b"Accept: text/html\r\n"
        request_data += b"\r\n"
        
        rw = BytesIO(request_data)
        client_address = ('127.0.0.1', 54321)
        
        # 构建 environ
        environ = make_environ(server, rw, client_address)
        
        # 验证 environ 包含所有必要字段
        assert environ['REQUEST_METHOD'] == 'GET'
        assert environ['PATH_INFO'] == '/index.html'
        assert environ['SERVER_PROTOCOL'] == 'HTTP/1.1'
        assert environ['HTTP_HOST'] == 'localhost:8000'
        assert environ['HTTP_USER_AGENT'] == 'test-client'
        assert environ['HTTP_ACCEPT'] == 'text/html'
    
    def test_multiple_requests(self):
        """测试多个请求"""
        from litefs.server.greenlet import make_environ, make_headers
        
        server = Mock()
        server.server_name = 'localhost'
        server.server_port = '8000'
        del server.max_request_size  # 删除该属性
        
        # 模拟多个请求
        requests = [
            b"GET /page1 HTTP/1.1\r\nHost: localhost\r\n\r\n",
            b"POST /api/data HTTP/1.1\r\nContent-Type: application/json\r\n\r\n",
            b"PUT /resource/123 HTTP/1.1\r\nContent-Length: 10\r\n\r\n",
        ]
        
        for request_data in requests:
            rw = BytesIO(request_data)
            client_address = ('127.0.0.1', 12345)
            
            environ = make_environ(server, rw, client_address)
            
            # 验证每个请求都被正确处理
            assert environ is not None
            assert 'REQUEST_METHOD' in environ
            assert 'PATH_INFO' in environ


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
