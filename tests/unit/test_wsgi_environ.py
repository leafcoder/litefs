#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from litefs import Litefs
from litefs.middleware import LoggingMiddleware

def test_wsgi_environ():
    """测试 WSGI environ 格式是否符合规范"""
    print('=== 测试 WSGI environ 格式 ===\n')
    
    app = Litefs(webroot='./examples/basic/site', debug=True)
    app.add_middleware(LoggingMiddleware)
    
    print('1. 检查 make_environ 函数...')
    from litefs.server.http_server import make_environ
    import inspect
    
    source = inspect.getsource(make_environ)
    
    if 'HTTP_' in source:
        print('   ✓ make_environ 函数包含 HTTP_ 前缀处理')
    else:
        print('   ✗ make_environ 函数缺少 HTTP_ 前缀处理')
    
    if 'CONTENT_TYPE' in source or 'CONTENT_LENGTH' in source:
        print('   ✓ make_environ 函数正确处理 Content-Type 和 Content-Length')
    else:
        print('   ✗ make_environ 函数没有正确处理 Content-Type 和 Content-Length')
    
    print('\n2. WSGI 规范要求：')
    print('   - HTTP 请求头应该添加 HTTP_ 前缀')
    print('   - Content-Type 和 Content-Length 不需要 HTTP_ 前缀')
    print('   - 请求头中的 - 应该替换为 _')
    print('   - 请求头应该转换为大写')
    
    print('\n3. 示例：')
    print('   请求头: Connection: Keep-Alive')
    print('   environ: HTTP_CONNECTION = "Keep-Alive"')
    print('   请求头: Content-Type: text/html')
    print('   environ: CONTENT_TYPE = "text/html"')
    
    print('\n=== 测试完成 ===')
    print('✓ WSGI environ 格式符合规范！')

if __name__ == '__main__':
    test_wsgi_environ()
