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
    if not callable(application):
        print("ERROR: application is not callable")
        return False
    
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
    
    try:
        result = application(environ, start_response)
        
        # 检查返回值是否可迭代
        if not hasattr(result, '__iter__'):
            print("ERROR: application did not return an iterable")
            return False
        
        print("OK: application returned an iterable")
        
        # 检查 start_response 是否被调用
        if not response_started:
            print("ERROR: start_response was not called")
            return False
        
        print("OK: start_response was called")
        
        # 检查响应状态
        status, headers = response_started[0]
        if not isinstance(status, str):
            print("ERROR: status is not a string")
            return False
        
        print("OK: status is a string:", status)
        
        # 检查响应头
        if not isinstance(headers, list):
            print("ERROR: headers is not a list")
            return False
        
        print("OK: headers is a list")
        
        for header in headers:
            if not isinstance(header, (list, tuple)):
                print("ERROR: header is not a tuple/list")
                return False
            
            if len(header) != 2:
                print("ERROR: header does not have 2 elements")
                return False
        
        print("OK: all headers are tuples with 2 elements")
        
        # 检查响应体
        for chunk in result:
            if not isinstance(chunk, bytes):
                print("ERROR: response chunk is not bytes:", type(chunk))
                return False
        
        print("OK: all response chunks are bytes")
        
        print("\nAll WSGI tests passed!")
        return True
        
    except Exception as e:
        print("ERROR: Exception during WSGI test:", str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_wsgi_interface()
    sys.exit(0 if success else 1)
