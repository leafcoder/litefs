#!/usr/bin/env python
# coding: utf-8

"""
CSRF 保护中间件测试

覆盖 litefs.middleware.csrf 模块：令牌生成/验证、请求校验、响应 Cookie 注入。
"""

import unittest
from http.cookies import SimpleCookie
from unittest.mock import Mock

from litefs.middleware.csrf import CSRFMiddleware


def make_handler(method="GET", path="/submit", cookie=None, post=None):
    """构造测试用请求处理器（固定 session_id 保证令牌跨实例可验证）"""
    handler = Mock()
    handler.environ = {"REQUEST_METHOD": method, "PATH_INFO": path}
    handler.cookie = cookie
    handler.session_id = None
    handler.session = None
    if post is None:
        del handler.post
    else:
        handler.post = post
    return handler


class CSRFTestCase(unittest.TestCase):
    """CSRF 测试基类"""

    def setUp(self):
        self.middleware = CSRFMiddleware(app=Mock(), secret_key="test-secret-key")


class TestTokenLifecycle(CSRFTestCase):
    """测试令牌生成与验证"""

    def test_generate_token_format(self):
        """令牌格式为 nonce.signature 两段"""
        token = self.middleware._generate_csrf_token(make_handler())
        nonce, signature = token.rsplit(".", 1)
        self.assertTrue(nonce)
        self.assertEqual(len(signature), 64)  # SHA256 hex

    def test_validate_own_token(self):
        """自己生成的令牌验证通过"""
        handler = make_handler()
        token = self.middleware._generate_csrf_token(handler)
        self.assertTrue(self.middleware._validate_csrf_token(token, handler))

    def test_validate_rejects_tampered(self):
        """篡改签名后验证失败"""
        token = self.middleware._generate_csrf_token(make_handler())
        nonce, _ = token.rsplit(".", 1)
        tampered = f"{nonce}.{'0' * 64}"
        self.assertFalse(self.middleware._validate_csrf_token(tampered, make_handler()))

    def test_validate_rejects_wrong_session(self):
        """session_id 不同则令牌验证失败"""
        token = self.middleware._generate_csrf_token(make_handler())
        other = make_handler()
        other.session_id = "other-session"
        self.assertFalse(self.middleware._validate_csrf_token(token, other))

    def test_validate_rejects_malformed(self):
        """非法格式令牌验证失败"""
        for bad in (None, "", "short", "onlynonce" + "x" * 70, ".signature"):
            self.assertFalse(
                self.middleware._validate_csrf_token(bad, make_handler()),
                f"应拒绝令牌: {bad!r}",
            )

    def test_reuse_valid_cookie_token(self):
        """Cookie 中已有有效令牌时复用而非重新生成"""
        handler = make_handler()
        token = self.middleware._generate_csrf_token(handler)

        cookie = SimpleCookie()
        cookie[self.middleware.cookie_name] = token
        handler2 = make_handler(cookie=cookie)
        self.assertEqual(self.middleware._generate_csrf_token(handler2), token)

    def test_regen_invalid_cookie_token(self):
        """Cookie 中令牌无效时生成新令牌"""
        cookie = SimpleCookie()
        cookie[self.middleware.cookie_name] = "bogus-token-value"
        new_token = self.middleware._generate_csrf_token(make_handler(cookie=cookie))
        self.assertNotEqual(new_token, "bogus-token-value")

    def test_session_id_binding(self):
        """session_id 绑定到签名"""
        handler = make_handler()
        handler.session_id = "sess-123"
        token = self.middleware._generate_csrf_token(handler)
        self.assertTrue(self.middleware._validate_csrf_token(token, handler))

        handler2 = make_handler()
        handler2.session_id = "sess-456"
        self.assertFalse(self.middleware._validate_csrf_token(token, handler2))


class TestProcessRequest(CSRFTestCase):
    """测试请求校验流程"""

    def test_exempt_methods_pass(self):
        """豁免方法（GET/HEAD 等）直接放行"""
        for method in ("GET", "HEAD", "OPTIONS", "TRACE"):
            self.assertIsNone(
                self.middleware.process_request(make_handler(method=method)),
                f"{method} 应被豁免",
            )

    def test_api_path_exempt(self):
        """/api/ 前缀路径跳过 CSRF 校验"""
        result = self.middleware.process_request(make_handler(path="/api/users"))
        self.assertIsNone(result)

    def test_missing_token_returns_403(self):
        """POST 无令牌返回 403"""
        result = self.middleware.process_request(make_handler(method="POST"))
        status, headers, content = result
        self.assertEqual(status, "403 Forbidden")
        self.assertIn(b"CSRF token missing", content)

    def test_invalid_token_returns_403(self):
        """POST 非法令牌返回 403"""
        handler = make_handler(method="POST")
        handler.environ["HTTP_X_CSRFTOKEN"] = "invalid-token-value-0123456789abcdef"
        status, _, content = self.middleware.process_request(handler)
        self.assertEqual(status, "403 Forbidden")
        self.assertIn(b"CSRF token invalid", content)

    def test_valid_token_via_header_passes(self):
        """通过请求头携带有效令牌时放行"""
        handler = make_handler(method="POST")
        token = self.middleware._generate_csrf_token(handler)
        handler.environ["HTTP_X_CSRFTOKEN"] = token
        self.assertIsNone(self.middleware.process_request(handler))

    def test_valid_token_via_post_form_passes(self):
        """通过表单字段携带有效令牌时放行"""
        handler = make_handler(method="POST")
        token = self.middleware._generate_csrf_token(handler)
        handler.post = {self.middleware.token_name: token}
        self.assertIsNone(self.middleware.process_request(handler))

    def test_valid_token_via_cookie_passes(self):
        """通过 Cookie 携带有效令牌时放行"""
        handler = make_handler(method="POST")
        token = self.middleware._generate_csrf_token(handler)
        cookie = SimpleCookie()
        cookie[self.middleware.cookie_name] = token
        handler.cookie = cookie
        self.assertIsNone(self.middleware.process_request(handler))

    def test_custom_exempt_methods(self):
        """可自定义豁免方法列表"""
        mw = CSRFMiddleware(app=Mock(), secret_key="k", exempt_methods=["GET"])
        self.assertIsNone(mw.process_request(make_handler(method="GET")))
        # OPTIONS 不再豁免，需要令牌 → 403
        status, _, _ = mw.process_request(make_handler(method="OPTIONS"))
        self.assertEqual(status, "403 Forbidden")


class TestProcessResponse(CSRFTestCase):
    """测试响应处理与 Cookie 注入"""

    def test_tuple_response_gets_cookie(self):
        """三元组响应追加 Set-Cookie 头"""
        handler = make_handler()
        response = ("200 OK", [("Content-Type", "text/html")], b"<html></html>")
        status, headers, content = self.middleware.process_response(handler, response)

        self.assertEqual(status, "200 OK")
        self.assertEqual(content, b"<html></html>")
        set_cookies = [v for k, v in headers if k == "Set-Cookie"]
        self.assertEqual(len(set_cookies), 1)
        self.assertIn("csrftoken=", set_cookies[0])
        self.assertIn("Path=/", set_cookies[0])
        self.assertIn("HttpOnly", set_cookies[0])
        self.assertIn("SameSite=Lax", set_cookies[0])

    def test_non_tuple_response_builds_status(self):
        """非三元组响应按 request_handler 状态码构造"""
        handler = make_handler()
        handler._status_code = 201
        status, headers, content = self.middleware.process_response(handler, b"data")
        self.assertEqual(status, "201 Created")
        self.assertEqual(content, b"data")
        self.assertEqual(len([1 for k, _ in headers if k == "Set-Cookie"]), 1)

    def test_token_stored_on_handler(self):
        """令牌同时暴露在 request_handler._csrf_token 上"""
        handler = make_handler()
        _, headers, _ = self.middleware.process_response(
            handler, ("200 OK", [], b"")
        )
        token = handler._csrf_token
        self.assertTrue(self.middleware._validate_csrf_token(token, handler))
        set_cookie = [v for k, v in headers if k == "Set-Cookie"][0]
        self.assertIn(token, set_cookie)

    def test_cookie_options_applied(self):
        """secure/samesite 等选项写入 Cookie"""
        mw = CSRFMiddleware(
            app=Mock(),
            secret_key="k",
            cookie_secure=True,
            cookie_same_site="Strict",
        )
        handler = make_handler()
        _, headers, _ = mw.process_response(handler, ("200 OK", [], b""))
        set_cookie = [v for k, v in headers if k == "Set-Cookie"][0]
        self.assertIn("Secure", set_cookie)
        self.assertIn("SameSite=Strict", set_cookie)


class TestConfigDefaults(CSRFTestCase):
    """测试配置默认值"""

    def test_default_names(self):
        """默认字段名配置"""
        self.assertEqual(self.middleware.token_name, "csrf_token")
        self.assertEqual(self.middleware.header_name, "X-CSRFToken")
        self.assertEqual(self.middleware.cookie_name, "csrftoken")

    def test_random_secret_when_missing(self):
        """未提供 secret_key 时随机生成且实例间不同"""
        mw1 = CSRFMiddleware(app=Mock())
        mw2 = CSRFMiddleware(app=Mock())
        self.assertTrue(mw1.secret_key)
        self.assertNotEqual(mw1.secret_key, mw2.secret_key)


if __name__ == "__main__":
    unittest.main()
