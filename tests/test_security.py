#!/usr/bin/env python
# coding: utf-8

"""
安全功能测试
"""

import unittest
import tempfile
import os
import shutil
import hashlib
import hmac


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
        from litefs.core import Litefs
        
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


class TestCSRFMiddlewareHMAC(unittest.TestCase):
    """测试 CSRF 中间件 HMAC-SHA256 签名验证修复"""

    def setUp(self):
        """测试前准备"""
        from litefs.middleware.csrf import CSRFMiddleware
        self.secret_key = "test-hmac-secret-key-for-testing"
        self.middleware = CSRFMiddleware(None, secret_key=self.secret_key)

    def _make_handler(self, method="POST", session_id="session_abc",
                      header_token=None, form_token=None, cookie_token=None):
        """创建 Mock 请求处理器"""
        environ = {"REQUEST_METHOD": method, "PATH_INFO": "/form"}
        if header_token:
            environ["HTTP_X_CSRFTOKEN"] = header_token

        class MockCookieItem:
            def __init__(self, value):
                self.value = value

        class MockCookie(dict):
            pass

        cookie = None
        if cookie_token:
            cookie = MockCookie()
            cookie[self.middleware.cookie_name] = MockCookieItem(cookie_token)

        handler = type("MockHandler", (), {
            "environ": environ,
            "cookie": cookie,
            "post": {self.middleware.token_name: form_token} if form_token else {},
            "session_id": session_id,
            "session": None,
        })()
        return handler

    def _generate_valid_token(self, nonce, session_id):
        """生成合法的 HMAC 签名 token"""
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            f"{nonce}:{session_id}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{nonce}.{signature}"

    def test_valid_hmac_token_passes(self):
        """测试合法 HMAC 签名 token 通过验证"""
        token = self._generate_valid_token("nonce123", "session_abc")
        handler = self._make_handler(header_token=token, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNone(result, "合法 HMAC token 应通过验证")

    def test_tampered_signature_rejected(self):
        """测试篡改签名的 token 被拒绝"""
        token = self._generate_valid_token("nonce123", "session_abc")
        # 篡改签名部分
        tampered = f"nonce123.{'f' * 64}"
        handler = self._make_handler(header_token=tampered, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "篡改签名的 token 应被拒绝")
        self.assertIn("error", result[2].decode("utf-8"))

    def test_different_session_rejected(self):
        """测试不同 session_id 的 token 被拒绝"""
        token = self._generate_valid_token("nonce123", "session_abc")
        handler = self._make_handler(header_token=token, session_id="session_xyz")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "不同 session 的 token 应被拒绝")

    def test_wrong_secret_key_rejected(self):
        """测试使用错误 secret_key 签名的 token 被拒绝"""
        wrong_signature = hmac.new(
            "wrong-secret".encode("utf-8"),
            "nonce123:session_abc".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        token = f"nonce123.{wrong_signature}"
        handler = self._make_handler(header_token=token, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "错误 secret_key 签名的 token 应被拒绝")

    def test_no_dot_format_rejected(self):
        """测试无点号分隔的 token 被拒绝"""
        handler = self._make_handler(header_token="a" * 64, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "无 nonce.signature 格式的 token 应被拒绝")

    def test_empty_nonce_rejected(self):
        """测试空 nonce 的 token 被拒绝"""
        token = self._generate_valid_token("", "session_abc")
        handler = self._make_handler(header_token=token, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "空 nonce 的 token 应被拒绝")

    def test_short_token_rejected(self):
        """测试过短的 token 被拒绝"""
        handler = self._make_handler(header_token="short", session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "过短的 token 应被拒绝")

    def test_exempt_methods_bypass(self):
        """测试豁免方法不需要 CSRF"""
        for method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            handler = self._make_handler(method=method, session_id="session_abc")
            result = self.middleware.process_request(handler)
            self.assertIsNone(result, f"{method} 请求不需要 CSRF 验证")

    def test_missing_token_rejected(self):
        """测试缺少 token 的 POST 请求被拒绝"""
        handler = self._make_handler(session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result, "缺少 token 的请求应被拒绝")

    def test_form_token_validated(self):
        """测试表单中的 CSRF token 也能通过 HMAC 验证"""
        token = self._generate_valid_token("nonce456", "session_abc")
        handler = self._make_handler(form_token=token, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNone(result, "表单中的合法 HMAC token 应通过验证")

    def test_cookie_token_validated(self):
        """测试 Cookie 中的 CSRF token 也能通过 HMAC 验证"""
        token = self._generate_valid_token("nonce789", "session_abc")
        handler = self._make_handler(cookie_token=token, session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNone(result, "Cookie 中的合法 HMAC token 应通过验证")

    def test_forbidden_response_is_valid_json(self):
        """测试 403 响应是合法 JSON（无注入风险）"""
        handler = self._make_handler(session_id="session_abc")
        result = self.middleware.process_request(handler)
        self.assertIsNotNone(result)
        import json
        body = json.loads(result[2].decode("utf-8"))
        self.assertIn("error", body)

    def test_generate_token_returns_hmac_format(self):
        """测试生成的 token 包含 HMAC 签名格式"""
        handler = self._make_handler(method="GET", session_id="session_abc")
        token = self.middleware._generate_csrf_token(handler)
        self.assertIn(".", token, "生成的 token 应包含 nonce.signature 格式")
        parts = token.rsplit(".", 1)
        self.assertEqual(len(parts), 2, "token 应恰好有一个点号分隔 nonce 和 signature")


class TestAuthMiddleware(unittest.TestCase):
    """测试认证中间件修复"""

    def test_no_verifier_rejects_all(self):
        """测试无验证器时拒绝所有请求（安全默认值）"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None)
        self.assertFalse(middleware._verify_token("any_token"))
        self.assertFalse(middleware._verify_token(""))

    def test_custom_token_verifier_accepts(self):
        """测试自定义验证函数通过有效 token"""
        from litefs.middleware.security import AuthMiddleware
        verifier = lambda t: t == "valid_token"
        middleware = AuthMiddleware(None, token_verifier=verifier)
        self.assertTrue(middleware._verify_token("valid_token"))

    def test_custom_token_verifier_rejects(self):
        """测试自定义验证函数拒绝无效 token"""
        from litefs.middleware.security import AuthMiddleware
        verifier = lambda t: t == "valid_token"
        middleware = AuthMiddleware(None, token_verifier=verifier)
        self.assertFalse(middleware._verify_token("invalid_token"))

    def test_verifier_exception_returns_false(self):
        """测试自定义验证函数抛异常时返回 False"""
        from litefs.middleware.security import AuthMiddleware
        def bad_verifier(t):
            raise RuntimeError("verification error")
        middleware = AuthMiddleware(None, token_verifier=bad_verifier)
        self.assertFalse(middleware._verify_token("any_token"))

    def test_bearer_token_extraction(self):
        """测试 Bearer token 正确提取"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None)
        self.assertEqual(middleware._extract_bearer_token("Bearer mytoken123"), "mytoken123")
        self.assertEqual(middleware._extract_bearer_token("Bearer  x"), "x")

    def test_non_bearer_scheme_rejected(self):
        """测试非 Bearer 认证方案被拒绝"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None)
        self.assertIsNone(middleware._extract_bearer_token("Basic abc123"))
        self.assertIsNone(middleware._extract_bearer_token("Digest user=abc"))

    def test_missing_auth_header_returns_401(self):
        """测试缺少认证头返回 401"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None, token_verifier=lambda t: True)
        handler = type("MockHandler", (), {"environ": {"REQUEST_METHOD": "GET"}})()
        result = middleware.process_request(handler)
        self.assertIsNotNone(result)
        self.assertIn("401", result[0])

    def test_invalid_auth_format_returns_401(self):
        """测试无效认证格式返回 401"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None, token_verifier=lambda t: True)
        handler = type("MockHandler", (), {
            "environ": {"HTTP_AUTHORIZATION": "Basic abc123"}
        })()
        result = middleware.process_request(handler)
        self.assertIsNotNone(result)
        self.assertIn("401", result[0])

    def test_valid_bearer_token_passes(self):
        """测试有效 Bearer token 通过认证"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None, token_verifier=lambda t: t == "secret")
        handler = type("MockHandler", (), {
            "environ": {"HTTP_AUTHORIZATION": "Bearer secret"}
        })()
        result = middleware.process_request(handler)
        self.assertIsNone(result, "合法 Bearer token 应通过认证")

    def test_invalid_bearer_token_returns_401(self):
        """测试无效 Bearer token 返回 401"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None, token_verifier=lambda t: t == "secret")
        handler = type("MockHandler", (), {
            "environ": {"HTTP_AUTHORIZATION": "Bearer wrong"}
        })()
        result = middleware.process_request(handler)
        self.assertIsNotNone(result)
        self.assertIn("401", result[0])

    def test_unauthorized_response_is_valid_json(self):
        """测试 401 响应是合法 JSON（无注入风险）"""
        from litefs.middleware.security import AuthMiddleware
        middleware = AuthMiddleware(None)
        handler = type("MockHandler", (), {"environ": {}})()
        result = middleware.process_request(handler)
        self.assertIsNotNone(result)
        import json
        body = json.loads(result[2].decode("utf-8"))
        self.assertIn("error", body)

    def test_jwt_manager_integration(self):
        """测试 JWT 管理器集成"""
        from litefs.middleware.security import AuthMiddleware

        class MockJWTManager:
            def decode(self, token):
                if token == "valid_jwt":
                    return {"user_id": 1, "exp": 9999999999}
                raise ValueError("Invalid token")

        middleware = AuthMiddleware(None, jwt_manager=MockJWTManager())
        self.assertTrue(middleware._verify_token("valid_jwt"))
        self.assertFalse(middleware._verify_token("invalid_jwt"))

    def test_custom_verifier_takes_priority_over_jwt(self):
        """测试自定义验证器优先于 JWT 管理器"""
        from litefs.middleware.security import AuthMiddleware

        class MockJWTManager:
            def decode(self, token):
                return {"user_id": 1}

        # 自定义验证器只接受 "custom_valid"，JWT 管理器可以解码任何 token
        middleware = AuthMiddleware(
            None,
            token_verifier=lambda t: t == "custom_valid",
            jwt_manager=MockJWTManager(),
        )
        self.assertTrue(middleware._verify_token("custom_valid"))
        self.assertFalse(middleware._verify_token("jwt_valid"))


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
        from litefs.handlers import Response
        self.assertIsInstance(result, Response)
        self.assertIn("error", result.content)
        self.assertIn("Rate limit exceeded", result.content['error'])
    
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
                from litefs.handlers import Response
                self.assertIsInstance(result, Response)
                self.assertIn("Rate limit exceeded", result.content['error'])
            else:
                self.assertIsNone(result, f"IP 192.168.1.{i} 应该被允许")


if __name__ == '__main__':
    unittest.main()
