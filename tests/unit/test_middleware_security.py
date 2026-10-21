#!/usr/bin/env python
# coding: utf-8

"""
安全中间件测试

覆盖 litefs.middleware.security 模块：SecurityMiddleware 安全响应头
与 AuthMiddleware Bearer Token 认证。
"""

import unittest
from unittest.mock import Mock

from litefs.middleware.security import AuthMiddleware, SecurityMiddleware


class TestSecurityMiddleware(unittest.TestCase):
    """测试安全响应头中间件"""

    def _make(self, **kwargs):
        return SecurityMiddleware(app=Mock(), **kwargs)

    def test_default_headers_added(self):
        """默认安全响应头齐全"""
        mw = self._make()
        _, headers, _ = mw.process_response(
            Mock(), ("200 OK", [("Content-Type", "text/html")], b"ok")
        )
        header_dict = dict(headers)
        self.assertEqual(header_dict["X-Frame-Options"], "DENY")
        self.assertEqual(header_dict["X-Content-Type-Options"], "nosniff")
        self.assertEqual(header_dict["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(header_dict["Referrer-Policy"],
                         "strict-origin-when-cross-origin")
        self.assertIn("Strict-Transport-Security", header_dict)
        # 原有头保留
        self.assertEqual(header_dict["Content-Type"], "text/html")

    def test_optional_headers_omitted_by_default(self):
        """CSP 与 Permissions-Policy 默认不加"""
        mw = self._make()
        _, headers, _ = mw.process_response(
            Mock(), ("200 OK", [], b"")
        )
        names = [k for k, _ in headers]
        self.assertNotIn("Content-Security-Policy", names)
        self.assertNotIn("Permissions-Policy", names)

    def test_custom_headers(self):
        """可配置 CSP / Permissions-Policy / HSTS 关闭"""
        mw = self._make(
            content_security_policy="default-src 'self'",
            permissions_policy="geolocation=()",
            strict_transport_security="",
            x_frame_options="SAMEORIGIN",
        )
        _, headers, _ = mw.process_response(Mock(), ("200 OK", [], b""))
        header_dict = dict(headers)
        self.assertEqual(header_dict["Content-Security-Policy"],
                         "default-src 'self'")
        self.assertEqual(header_dict["Permissions-Policy"], "geolocation=()")
        self.assertEqual(header_dict["X-Frame-Options"], "SAMEORIGIN")
        self.assertNotIn("Strict-Transport-Security", header_dict)

    def test_non_tuple_response_passthrough_with_headers(self):
        """非三元组响应：仍生成头列表但原响应原样返回"""
        mw = self._make()
        response = {"key": "value"}
        result = mw.process_response(Mock(), response)
        self.assertIs(result, response)


class TestAuthMiddleware(unittest.TestCase):
    """测试 Bearer Token 认证中间件"""

    def _make(self, **kwargs):
        return AuthMiddleware(app=Mock(), **kwargs)

    def _handler(self, auth_value=None):
        handler = Mock()
        handler.environ = {}
        if auth_value is not None:
            handler.environ["HTTP_AUTHORIZATION"] = auth_value
        return handler

    def test_missing_token_401(self):
        """缺少认证头返回 401"""
        status, headers, content = self._make().process_request(self._handler())
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn(("WWW-Authenticate", 'Bearer realm="Litefs"'), headers)
        self.assertIn(b"Missing authentication token", content)

    def test_bearer_token_verifier(self):
        """Bearer Token 走自定义验证器"""
        mw = self._make(token_verifier=lambda t: t == "good")
        self.assertIsNone(
            mw.process_request(self._handler("Bearer good"))
        )
        status, _, content = mw.process_request(
            self._handler("Bearer bad")
        )
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn(b"Invalid authentication token", content)

    def test_raw_token_without_bearer(self):
        """兼容无 Bearer 前缀的裸 token"""
        mw = self._make(token_verifier=lambda t: t == "raw-token")
        self.assertIsNone(mw.process_request(self._handler("raw-token")))

    def test_invalid_header_format(self):
        """非 Bearer 认证方案返回格式错误 401"""
        mw = self._make(token_verifier=lambda t: True)
        status, _, content = mw.process_request(
            self._handler("Basic dXNlcjpwYXNz")
        )
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn(b"Expected: Bearer <token>", content)

    def test_verifier_exception_rejected(self):
        """验证器抛异常时拒绝"""
        def broken(_token):
            raise RuntimeError("boom")

        status, _, _ = self._make(token_verifier=broken).process_request(
            self._handler("Bearer t")
        )
        self.assertEqual(status, "401 Unauthorized")

    def test_jwt_manager_verification(self):
        """无 token_verifier 时使用 jwt_manager"""
        jwt_manager = Mock()
        jwt_manager.decode.return_value = {"sub": "u"}
        mw = self._make(jwt_manager=jwt_manager)
        self.assertIsNone(mw.process_request(self._handler("Bearer jwt")))

        jwt_manager.decode.return_value = None
        status, _, _ = mw.process_request(self._handler("Bearer jwt"))
        self.assertEqual(status, "401 Unauthorized")

    def test_jwt_manager_exception_rejected(self):
        """jwt_manager 抛异常时拒绝"""
        jwt_manager = Mock()
        jwt_manager.decode.side_effect = RuntimeError("bad jwt")
        status, _, _ = self._make(jwt_manager=jwt_manager).process_request(
            self._handler("Bearer jwt")
        )
        self.assertEqual(status, "401 Unauthorized")

    def test_no_verifier_rejects_all(self):
        """未配置任何验证器时默认拒绝（安全默认值）"""
        status, _, content = self._make().process_request(
            self._handler("Bearer anything")
        )
        self.assertEqual(status, "401 Unauthorized")
        self.assertIn(b"Invalid authentication token", content)

    def test_custom_auth_header(self):
        """可自定义认证头名称"""
        mw = self._make(
            auth_header="X-Api-Key", token_verifier=lambda t: t == "k"
        )
        handler = Mock()
        handler.environ = {"HTTP_X_API_KEY": "k"}
        self.assertIsNone(mw.process_request(handler))


if __name__ == "__main__":
    unittest.main()
