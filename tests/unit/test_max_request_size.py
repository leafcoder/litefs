#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import litefs

def test_max_request_size():
    """
    测试 max_request_size 配置功能
    """
    print("Testing max_request_size configuration...")
    
    try:
        # 测试默认配置
        config = litefs.make_config(webroot='./demo/site')
        print(f"Default max_request_size: {config.max_request_size} bytes")
        assert config.max_request_size == 10485760, "Default max_request_size should be 10MB"
        print("OK: Default max_request_size is 10MB (10485760 bytes)")
        
        # 测试自定义配置
        custom_config = litefs.make_config(
            webroot='./demo/site',
            max_request_size=5242880
        )
        print(f"Custom max_request_size: {custom_config.max_request_size} bytes")
        assert custom_config.max_request_size == 5242880, "Custom max_request_size should be 5MB"
        print("OK: Custom max_request_size is 5MB (5242880 bytes)")
        
        # 测试 HTTPServer 默认值
        from litefs.server import HTTPServer
        server = HTTPServer(('localhost', 9090), lambda *args: None)
        print(f"HTTPServer default max_request_size: {server.max_request_size} bytes")
        assert server.max_request_size == 10485760, "HTTPServer default max_request_size should be 10MB"
        print("OK: HTTPServer default max_request_size is 10MB")
        
        # 测试 HTTPServer 自定义值
        server.max_request_size = 20971520
        print(f"HTTPServer custom max_request_size: {server.max_request_size} bytes")
        assert server.max_request_size == 20971520, "HTTPServer custom max_request_size should be 20MB"
        print("OK: HTTPServer custom max_request_size is 20MB")
        
        # 测试 make_environ 函数的请求大小检查
        from litefs.server import make_environ
        from io import BytesIO
        from litefs.exceptions import HttpError
        
        # 模拟一个小的请求
        small_request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 100\r\n\r\n"
        rw = BytesIO(small_request)
        
        try:
            environ = make_environ(server, rw, ('127.0.0.1', 12345))
            print(f"OK: Small request (100 bytes) accepted")
        except HttpError as e:
            print(f"ERROR: Small request rejected: {e}")
            return False
        
        # 测试超过限制的请求
        large_request = b"GET / HTTP/1.1\r\nHost: localhost\r\nContent-Length: 20971521\r\n\r\n"
        rw = BytesIO(large_request)
        
        try:
            environ = make_environ(server, rw, ('127.0.0.1', 12345))
            print("ERROR: Large request should have been rejected")
            return False
        except HttpError as e:
            print(f"OK: Large request (20971521 bytes) rejected with error: {e}")
            assert e.args[0] == 413, "Should return 413 status code"
            print("OK: Correct 413 status code returned")
        
        print("\nAll max_request_size tests passed!")
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_max_request_size()
    sys.exit(0 if success else 1)
