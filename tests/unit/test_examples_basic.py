#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import Litefs
import json
from io import BytesIO

def create_environ(path='/', method='GET', query_string='', content_type='', body=b''):
    return {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8000',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'CONTENT_LENGTH': str(len(body)),
        'CONTENT_TYPE': content_type,
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': BytesIO(body),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }

def test_index_page():
    print("Testing index page...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    # 使用新路由系统定义路由
    @app.add_get('/', name='index')
    def index_handler(request):
        request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
        return '<h1>Hello World</h1>'
    
    application = app.wsgi()
    
    environ = create_environ('/')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    assert b'<h1>Hello World</h1>' in content, f"Expected HTML content, got {content}"
    
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html, got {headers_dict.get('Content-Type')}"
    
    print("OK: index page test passed")

def test_datetime_response():
    print("Testing datetime response...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test', name='test')
    def test_handler(request):
        import datetime
        request.start_response(200, [('Content-Type', 'application/json; charset=utf-8')])
        return str(datetime.datetime.now())
    
    application = app.wsgi()
    
    environ = create_environ('/test')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert isinstance(data, str), f"Expected string, got {type(data)}"
    
    print("OK: datetime response test passed")

def test_error_handling():
    print("Testing error handling...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_error', name='test_error')
    def test_error_handler(request):
        raise Exception("Test error")
    
    application = app.wsgi()
    
    environ = create_environ('/test_error')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '500' in status, f"Expected 500, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html for error, got {headers_dict.get('Content-Type')}"
    
    print("OK: error handling test passed")

def test_generator_response():
    print("Testing generator response...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_generator', name='test_generator')
    def test_generator_handler(request):
        def generate():
            for i in range(5):
                yield f"line {i}\n"
        request.start_response(200, [('Content-Type', 'text/plain; charset=utf-8')])
        return generate()
    
    application = app.wsgi()
    
    environ = create_environ('/test_generator')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/plain' in headers_dict.get('Content-Type', ''), f"Expected text/plain for generator, got {headers_dict.get('Content-Type')}"
    
    expected_lines = [b'line 0\n', b'line 1\n', b'line 2\n', b'line 3\n', b'line 4\n']
    for line in expected_lines:
        assert line in content, f"Expected line {line} in content, got {content}"
    
    print("OK: generator response test passed")

def test_json_response():
    print("Testing JSON response...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_json', name='test_json')
    def test_json_handler(request):
        request.start_response(200, [('Content-Type', 'application/json; charset=utf-8')])
        return {"message": "Hello, World!", "status": "success"}
    
    application = app.wsgi()
    
    environ = create_environ('/test_json')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert data == {"message": "Hello, World!", "status": "success"}, f"Expected JSON data, got {data}"
    
    print("OK: JSON response test passed")

def test_complex_json_response():
    print("Testing complex JSON response...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_json_complex', name='test_json_complex')
    def test_json_complex_handler(request):
        request.start_response(200, [('Content-Type', 'application/json; charset=utf-8')])
        return {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"}
            ],
            "count": 3
        }
    
    application = app.wsgi()
    
    environ = create_environ('/test_json_complex')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert 'users' in data, f"Expected 'users' key in data"
    assert len(data['users']) == 3, f"Expected 3 users, got {len(data['users'])}"
    assert data['count'] == 3, f"Expected count=3, got {data['count']}"
    
    print("OK: complex JSON response test passed")

def test_json_custom_header():
    print("Testing JSON with custom header...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_json_custom_header', name='test_json_custom_header')
    def test_json_custom_header_handler(request):
        request.start_response(200, [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('X-Custom-Header', 'CustomValue')
        ])
        return {"message": "Hello, World!", "status": "success"}
    
    application = app.wsgi()
    
    environ = create_environ('/test_json_custom_header')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json, got {headers_dict.get('Content-Type')}"
    assert headers_dict.get('X-Custom-Header') == 'CustomValue', f"Expected X-Custom-Header, got {headers_dict.get('X-Custom-Header')}"
    
    data = json.loads(content)
    assert data == {"message": "Hello, World!", "status": "success"}, f"Expected JSON data, got {data}"
    
    print("OK: JSON custom header test passed")

def test_mixed_response():
    print("Testing mixed type response...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_mixed', name='test_mixed')
    def test_mixed_handler(request):
        request.start_response(200, [('Content-Type', 'text/plain; charset=utf-8')])
        return b'Hello world!'
    
    application = app.wsgi()
    
    environ = create_environ('/test_mixed')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    assert content == b'Hello world!', f"Expected 'Hello world!', got {content}"
    
    print("OK: mixed type response test passed")

def test_mixed_tuple_json():
    print("Testing mixed tuple in JSON mode...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_mixed_tuple', name='test_mixed_tuple')
    def test_mixed_tuple_handler(request):
        request.start_response(200, [('Content-Type', 'application/json; charset=utf-8')])
        return (1, 2, 3)
    
    application = app.wsgi()
    
    environ = create_environ('/test_mixed_tuple')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert len(data) == 3, f"Expected 3 items, got {len(data)}"
    
    print("OK: mixed tuple JSON mode test passed")

def test_mixed_tuple_text():
    print("Testing mixed tuple in text mode...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_mixed_tuple_text', name='test_mixed_tuple_text')
    def test_mixed_tuple_text_handler(request):
        request.start_response(200, [('Content-Type', 'text/plain; charset=utf-8')])
        return (1, 2, 3)
    
    application = app.wsgi()
    
    environ = create_environ('/test_mixed_tuple_text')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/plain' in headers_dict.get('Content-Type', ''), f"Expected text/plain, got {headers_dict.get('Content-Type')}"
    
    print("OK: mixed tuple text mode test passed")

def test_html_response():
    print("Testing HTML response...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_html', name='test_html')
    def test_html_handler(request):
        request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
        return '<h1>Hello, World!</h1>'
    
    application = app.wsgi()
    
    environ = create_environ('/test_html')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html, got {headers_dict.get('Content-Type')}"
    
    assert b'<h1>Hello, World!</h1>' in content, f"Expected HTML content, got {content}"
    
    print("OK: HTML response test passed")

def test_text_mode():
    print("Testing text mode...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/test_text_mode', name='test_text_mode')
    def test_text_mode_handler(request):
        request.start_response(200, [('Content-Type', 'text/plain; charset=utf-8')])
        return {"message": "Hello, World!"}
    
    application = app.wsgi()
    
    environ = create_environ('/test_text_mode')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/plain' in headers_dict.get('Content-Type', ''), f"Expected text/plain, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert data == {"message": "Hello, World!"}, f"Expected JSON data, got {data}"
    
    print("OK: text mode test passed")

def test_404_page():
    print("Testing 404 page...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    # 不定义任何路由，测试 404
    application = app.wsgi()
    
    environ = create_environ('/nonexistent')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '404' in status, f"Expected 404, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html for 404, got {headers_dict.get('Content-Type')}"
    
    print("OK: 404 page test passed")

def test_auto_content_type_dict():
    """测试 dict 返回值自动设置 Content-Type 为 application/json"""
    print("Testing auto Content-Type for dict...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/auto_dict', name='auto_dict')
    def auto_dict_handler(request):
        return {"message": "auto json"}
    
    application = app.wsgi()
    
    environ = create_environ('/auto_dict')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json for dict, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert data == {"message": "auto json"}, f"Expected JSON data, got {data}"
    
    print("OK: auto Content-Type for dict test passed")

def test_auto_content_type_list():
    """测试 list 返回值自动设置 Content-Type 为 application/json"""
    print("Testing auto Content-Type for list...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/auto_list', name='auto_list')
    def auto_list_handler(request):
        return [1, 2, 3]
    
    application = app.wsgi()
    
    environ = create_environ('/auto_list')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/json' in headers_dict.get('Content-Type', ''), f"Expected application/json for list, got {headers_dict.get('Content-Type')}"
    
    data = json.loads(content)
    assert data == [1, 2, 3], f"Expected JSON list, got {data}"
    
    print("OK: auto Content-Type for list test passed")

def test_auto_content_type_html():
    """测试 HTML 字符串自动设置 Content-Type 为 text/html"""
    print("Testing auto Content-Type for HTML...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/auto_html', name='auto_html')
    def auto_html_handler(request):
        return '<html><body>Hello</body></html>'
    
    application = app.wsgi()
    
    environ = create_environ('/auto_html')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html for HTML string, got {headers_dict.get('Content-Type')}"
    
    assert b'<html>' in content, f"Expected HTML content, got {content}"
    
    print("OK: auto Content-Type for HTML test passed")

def test_auto_content_type_plain_string():
    """测试普通字符串默认设置 Content-Type 为 text/html"""
    print("Testing auto Content-Type for plain string...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/auto_plain', name='auto_plain')
    def auto_plain_handler(request):
        return 'Hello World'
    
    application = app.wsgi()
    
    environ = create_environ('/auto_plain')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html for plain string, got {headers_dict.get('Content-Type')}"
    
    print("OK: auto Content-Type for plain string test passed")

def test_auto_content_type_bytes():
    """测试 bytes 返回值自动设置 Content-Type 为 application/octet-stream"""
    print("Testing auto Content-Type for bytes...")
    app = Litefs(webroot='./examples/02-basic-handlers/site')
    
    @app.add_get('/auto_bytes', name='auto_bytes')
    def auto_bytes_handler(request):
        return b'\x00\x01\x02\x03'
    
    application = app.wsgi()
    
    environ = create_environ('/auto_bytes')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    
    headers_dict = dict(headers)
    assert 'application/octet-stream' in headers_dict.get('Content-Type', ''), f"Expected application/octet-stream for bytes, got {headers_dict.get('Content-Type')}"
    
    print("OK: auto Content-Type for bytes test passed")

def run_all_tests():
    tests = [
        test_index_page,
        test_datetime_response,
        test_error_handling,
        test_generator_response,
        test_json_response,
        test_complex_json_response,
        test_json_custom_header,
        test_mixed_response,
        test_mixed_tuple_json,
        test_mixed_tuple_text,
        test_html_response,
        test_text_mode,
        test_404_page,
        test_auto_content_type_dict,
        test_auto_content_type_list,
        test_auto_content_type_html,
        test_auto_content_type_plain_string,
        test_auto_content_type_bytes,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\nRunning: {test.__name__}")
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"FAILED: {test.__name__} - {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Test Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
