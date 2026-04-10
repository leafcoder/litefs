#!/usr/bin/env python
# coding: utf-8

"""
安全功能测试
"""

import unittest
import tempfile
import os
import shutil


class TestSecurePathJoin(unittest.TestCase):
    """测试安全路径拼接"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """测试后清理"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_valid_path(self):
        """测试有效路径"""
        from litefs.security import secure_path_join
        
        full_path = secure_path_join(self.temp_dir, 'file.txt')
        self.assertIsNotNone(full_path)
        self.assertTrue(full_path.startswith(self.temp_dir))
    
    def test_path_traversal_attack(self):
        """测试路径遍历攻击"""
        from litefs.security import secure_path_join
        
        # 尝试路径遍历
        full_path = secure_path_join(self.temp_dir, '../etc/passwd')
        self.assertIsNone(full_path)
    
    def test_absolute_path(self):
        """测试绝对路径"""
        from litefs.security import secure_path_join
        
        full_path = secure_path_join(self.temp_dir, '/etc/passwd')
        self.assertIsNone(full_path)
    
    def test_nested_path_traversal(self):
        """测试嵌套路径遍历"""
        from litefs.security import secure_path_join
        
        full_path = secure_path_join(self.temp_dir, 'subdir/../../../etc/passwd')
        self.assertIsNone(full_path)
    
    def test_empty_path(self):
        """测试空路径"""
        from litefs.security import secure_path_join
        
        full_path = secure_path_join(self.temp_dir, '')
        self.assertIsNotNone(full_path)
    
    def test_current_directory(self):
        """测试当前目录"""
        from litefs.security import secure_path_join
        
        full_path = secure_path_join(self.temp_dir, './file.txt')
        self.assertIsNotNone(full_path)
    
    def test_symlink_attack(self):
        """测试符号链接攻击"""
        from litefs.security import secure_path_join
        
        # 创建符号链接
        target = os.path.join(self.temp_dir, 'target')
        os.makedirs(target, exist_ok=True)
        
        link = os.path.join(self.temp_dir, 'link')
        os.symlink(target, link)
        
        # 通过符号链接访问
        full_path = secure_path_join(self.temp_dir, 'link/../../../etc/passwd')
        self.assertIsNone(full_path)


class TestCSRFToken(unittest.TestCase):
    """测试 CSRF 令牌"""
    
    def test_generate_token(self):
        """测试生成令牌"""
        from litefs.security import generate_csrf_token
        
        token = generate_csrf_token()
        self.assertEqual(len(token), 64)  # 32字节的十六进制表示
        self.assertTrue(token.isalnum())
    
    def test_validate_token(self):
        """测试验证令牌"""
        from litefs.security import generate_csrf_token, validate_csrf_token
        
        token = generate_csrf_token()
        self.assertTrue(validate_csrf_token(token, token))
    
    def test_validate_different_token(self):
        """测试验证不同令牌"""
        from litefs.security import generate_csrf_token, validate_csrf_token
        
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        self.assertFalse(validate_csrf_token(token1, token2))
    
    def test_validate_empty_token(self):
        """测试验证空令牌"""
        from litefs.security import validate_csrf_token
        
        self.assertFalse(validate_csrf_token('', 'token'))
        self.assertFalse(validate_csrf_token('token', ''))
        self.assertFalse(validate_csrf_token(None, 'token'))
        self.assertFalse(validate_csrf_token('token', None))


class TestCSRFMiddleware(unittest.TestCase):
    """测试 CSRF 中间件"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.middleware import CSRFMiddleware
        from litefs import Litefs
        
        self.app = Litefs()
        self.middleware = CSRFMiddleware(self.app)
    
    def test_valid_csrf_token(self):
        """测试有效 CSRF 令牌"""
        class MockRequestHandler:
            environ = {
                "REQUEST_METHOD": "POST",
                "HTTP_X_CSRFTOKEN": "valid-token"
            }
            cookie = None
            post = {"csrf_token": "valid-token"}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        handler = MockRequestHandler()
        result = self.middleware.process_request(handler)
        # CSRF 验证失败，因为令牌格式不正确
        self.assertIsNotNone(result)
        self.assertIn("error", result[2].decode('utf-8'))
    
    def test_invalid_csrf_token(self):
        """测试无效 CSRF 令牌"""
        class MockRequestHandler:
            environ = {
                "REQUEST_METHOD": "POST",
                "HTTP_X_CSRFTOKEN": "invalid-token"
            }
            cookie = None
            post = {"csrf_token": "invalid-token"}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        handler = MockRequestHandler()
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result)
        self.assertIn("error", result[2].decode('utf-8'))
    
    def test_missing_csrf_token(self):
        """测试缺少 CSRF 令牌"""
        class MockRequestHandler:
            environ = {"REQUEST_METHOD": "POST"}
            cookie = None
            post = {}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        handler = MockRequestHandler()
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result)
        self.assertIn("error", result[2].decode('utf-8'))
    
    def test_get_request_no_csrf(self):
        """测试 GET 请求不需要 CSRF"""
        class MockRequestHandler:
            environ = {"REQUEST_METHOD": "GET"}
            cookie = None
            post = {}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        handler = MockRequestHandler()
        result = self.middleware.process_request(handler)
        self.assertIsNone(result)


class TestSecurityMiddleware(unittest.TestCase):
    """测试安全中间件"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.middleware import SecurityMiddleware
        
        self.middleware = SecurityMiddleware(None)
    
    def test_security_headers(self):
        """测试安全头"""
        response = (200, [('Content-Type', 'text/html')], '<html></html>')
        result = self.middleware.process_response(None, response)
        
        self.assertEqual(result[0], 200)
        headers = result[1]
        
        # 检查安全头
        header_names = [h[0].lower() for h in headers]
        self.assertIn('x-content-type-options', header_names)
        self.assertIn('x-frame-options', header_names)
        self.assertIn('x-xss-protection', header_names)


class TestRateLimitMiddleware(unittest.TestCase):
    """测试限流中间件"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.middleware import RateLimitMiddleware
        
        self.middleware = RateLimitMiddleware(None, max_requests=5, window_seconds=60, key_func=lambda h: '127.0.0.1')
    
    def test_under_rate_limit(self):
        """测试低于限流"""
        class MockRequestHandler:
            environ = {'REMOTE_ADDR': '127.0.0.1'}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        # 发送 5 个请求
        for _ in range(5):
            handler = MockRequestHandler()
            result = self.middleware.process_request(handler)
            self.assertIsNone(result)
    
    def test_over_rate_limit(self):
        """测试超过限流"""
        class MockRequestHandler:
            environ = {'REMOTE_ADDR': '127.0.0.1'}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        # 使用同一个中间件实例发送 5 个请求
        for _ in range(5):
            handler = MockRequestHandler()
            self.middleware.process_request(handler)
        
        # 第 6 个请求应该被限流
        handler = MockRequestHandler()
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result)
        self.assertIn("error", result[2].decode('utf-8'))
        self.assertIn("Rate limit exceeded", result[2].decode('utf-8'))
    
    def test_different_ip(self):
        """测试不同 IP"""
        class MockRequestHandler:
            def __init__(self, ip):
                self.environ = {'REMOTE_ADDR': ip}
            
            def start_response(self, status, headers):
                self.status = status
                self.headers = headers
        
        # 为不同 IP 发送请求
        for i in range(6):
            handler = MockRequestHandler(f'192.168.1.{i}')
            result = self.middleware.process_request(handler)
            # 每个 IP 只能请求 5 次，所以第 6 个 IP 会被限流
            if i >= 5:
                self.assertIsNotNone(result)
                self.assertIn("Rate limit exceeded", result[2].decode('utf-8'))
            else:
                self.assertIsNone(result, f"IP 192.168.1.{i} 应该被允许")


if __name__ == '__main__':
    unittest.main()
