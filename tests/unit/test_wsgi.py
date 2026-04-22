#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

from litefs.core import Litefs

def test_wsgi_interface():
    """
    测试 WSGI 接口是否符合 PEP 3333 规范
    """
    print("Testing WSGI interface...")
    
    app = Litefs(webroot='./examples/basic/site')
    application = app.wsgi()
    
    # 测试 application 是否可调用
    assert callable(application)
    print("OK: application is callable")
    
    # 测试 environ 字典
    environ = {
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/',
        'QUERY_STRING': '',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8000',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'CONTENT_LENGTH': '0',
        'CONTENT_TYPE': '',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': sys.stdin,
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    
    # 测试 start_response callable
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    
    # 检查返回值是否可迭代
    assert hasattr(result, '__iter__'), "application did not return an iterable"
    print("OK: application returned an iterable")
    
    # 检查 start_response 是否被调用
    assert response_started, "start_response was not called"
    print("OK: start_response was called")
    
    # 检查响应状态
    status, headers = response_started[0]
    assert isinstance(status, str)
    print("OK: status is a string:", status)
    
    # 检查响应头
    assert isinstance(headers, list)
    print("OK: headers is a list")
    
    for header in headers:
        assert isinstance(header, (list, tuple)), "header is not a tuple/list"
        assert len(header) == 2, "header does not have 2 elements"
    
    print("OK: all headers are tuples with 2 elements")
    
    # 检查响应体
    for chunk in result:
        assert isinstance(chunk, bytes), f"response chunk is not bytes: {type(chunk)}"
    
    print("OK: all response chunks are bytes")
    print("\nAll WSGI tests passed!")

if __name__ == '__main__':
    test_wsgi_interface()
