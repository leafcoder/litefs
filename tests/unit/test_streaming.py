#!/usr/bin/env python
# coding: utf-8

"""
测试流式响应功能
"""

import unittest
import time
from io import BytesIO
from litefs import Litefs, Response
from litefs.handlers import WSGIRequestHandler


class TestStreamingResponse(unittest.TestCase):
    """测试流式响应功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.app = Litefs()
    
    def test_stream_response(self):
        """测试基本流式响应"""
        
        def generate_text():
            yield "Hello, "
            time.sleep(0.01)
            yield "World!"
        
        response = Response.stream(generate_text())
        
        # 验证响应对象的属性
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(h[0] == "Content-Type" for h in response.headers))
        self.assertTrue(any(h[0] == "Transfer-Encoding" and h[1] == "chunked" for h in response.headers))
    
    def test_sse_response(self):
        """测试 Server-Sent Events 响应"""
        
        def generate_sse():
            yield "data: test\n\n"
        
        response = Response.sse(generate_sse())
        
        # 验证响应对象的属性
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(h[0] == "Content-Type" and h[1] == "text/event-stream" for h in response.headers))
        self.assertTrue(any(h[0] == "Cache-Control" and h[1] == "no-cache" for h in response.headers))
        self.assertTrue(any(h[0] == "Connection" and h[1] == "keep-alive" for h in response.headers))
    
    def test_file_stream_response(self):
        """测试文件流响应"""
        import tempfile
        import os
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello, File Stream!")
            temp_file_path = f.name
        
        try:
            response = Response.file_stream(temp_file_path)
            
            # 验证响应对象的属性
            self.assertEqual(response.status_code, 200)
            self.assertTrue(any(h[0] == "Content-Type" for h in response.headers))
            self.assertTrue(any(h[0] == "Content-Disposition" for h in response.headers))
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def test_file_stream_not_found(self):
        """测试文件流响应 - 文件不存在"""
        response = Response.file_stream("non_existent_file.txt")
        
        # 验证响应对象的属性
        self.assertEqual(response.status_code, 404)
    
    def test_streaming_in_wsgi(self):
        """测试在 WSGI 环境中使用流式响应"""
        
        # 注册测试路由
        @self.app.add_get('/stream')
        def stream_handler(request):
            def generate_text():
                yield "Line 1\n"
                yield "Line 2\n"
            return Response.stream(generate_text())
        
        # 创建 WSGI 环境
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': '/stream',
            'QUERY_STRING': '',
            'CONTENT_TYPE': '',
            'CONTENT_LENGTH': '0',
            'HTTP_HOST': 'localhost:9090',
        }
        
        # 捕获响应
        status = None
        headers = []
        response_body = []
        
        def start_response(s, h):
            nonlocal status, headers
            status = s
            headers = h
            return lambda data: response_body.append(data)
        
        # 调用 WSGI 应用
        application = self.app.wsgi()
        result = application(environ, start_response)
        
        # 处理响应
        for part in result:
            if part:
                response_body.append(part)
        
        # 验证响应
        self.assertEqual(status, '200 OK')
        self.assertTrue(any(h[0] == 'Transfer-Encoding' and h[1] == 'chunked' for h in headers))
        self.assertEqual(b''.join(response_body), b'Line 1\nLine 2\n')


if __name__ == '__main__':
    unittest.main()
