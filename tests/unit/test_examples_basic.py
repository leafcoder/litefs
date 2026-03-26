#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs
import json
from io import BytesIO

def create_environ(path='/', method='GET', query_string='', content_type=''):
    return {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '8000',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'CONTENT_LENGTH': '0',
        'CONTENT_TYPE': content_type,
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.input': BytesIO(b''),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }

def test_index_page():
    print("Testing index page...")
    app = litefs.Litefs(webroot='./examples/basic/site')
    application = app.wsgi()
    
    environ = create_environ('/', content_type='text/html')
    response_started = []
    
    def start_response(status, headers):
        response_started.append((status, headers))
    
    result = application(environ, start_response)
    content = b''.join(result)
    
    status, headers = response_started[0]
    assert '200' in status, f"Expected 200, got {status}"
    assert b'<h1>Hello World</h1>' in content, f"Expected HTML content, got {content}"
    print(headers)
    headers_dict = dict(headers)
    assert 'text/html' in headers_dict.get('Content-Type', ''), f"Expected text/html, got {headers_dict.get('Content-Type')}"
    
    print("OK: index page test passed")
    return True

def test_datetime_response():
    print("Testing datetime response...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_error_handling():
    print("Testing error handling...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_generator_response():
    print("Testing generator response...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_json_response():
    print("Testing JSON response...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_complex_json_response():
    print("Testing complex JSON response...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_json_custom_header():
    print("Testing JSON with custom header...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    
    data = json.loads(content)
    assert data == {"message": "Hello, World!", "status": "success"}, f"Expected JSON data, got {data}"
    
    print("OK: JSON custom header test passed")
    return True

def test_mixed_response():
    print("Testing mixed type response...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_mixed_tuple_json():
    print("Testing mixed tuple in JSON mode...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_mixed_tuple_text():
    print("Testing mixed tuple in text mode...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_html_response():
    print("Testing HTML response...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_text_mode():
    print("Testing text mode...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

def test_404_page():
    print("Testing 404 page...")
    app = litefs.Litefs(webroot='./examples/basic/site')
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
    return True

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