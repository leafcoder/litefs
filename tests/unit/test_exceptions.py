#!/usr/bin/env python
# coding: utf-8

"""
统一异常处理体系测试

覆盖 litefs.exceptions 模块：HTTPException 系列、abort、ErrorHandler。
"""

import unittest

from litefs.exceptions import (
    HTTP_STATUS_CODES,
    BadRequest,
    BadGateway,
    ConfigurationError,
    DatabaseError,
    CacheError,
    ErrorHandler,
    Forbidden,
    GatewayTimeout,
    HTTPException,
    HttpError,
    InternalServerError,
    MethodNotAllowed,
    NotFound,
    NotImplemented as NotImplementedHTTP,
    PayloadTooLarge,
    RouteNotFound,
    ServiceUnavailable,
    TooManyRequests,
    Unauthorized,
    UnprocessableEntity,
    ValidationError,
    abort,
    error_handler,
)


class TestHTTPException(unittest.TestCase):
    """测试 HTTP 异常基类"""

    def test_default_values(self):
        """默认 500 状态码，消息取自状态码表"""
        exc = HTTPException()
        self.assertEqual(exc.status_code, 500)
        self.assertEqual(exc.message, "Internal Server Error")
        self.assertEqual(exc.headers, [])
        self.assertIsNone(exc.description)

    def test_unknown_status_code_message(self):
        """未登记的状态码使用 Unknown Error"""
        exc = HTTPException(599)
        self.assertEqual(exc.message, "Unknown Error")

    def test_custom_message_and_headers(self):
        """支持自定义消息、响应头与描述"""
        headers = [("X-Custom", "v")]
        exc = HTTPException(404, message="找不到", headers=headers, description="详情")
        self.assertEqual(exc.message, "找不到")
        self.assertEqual(exc.headers, headers)
        self.assertEqual(exc.description, "详情")

    def test_str_repr(self):
        """str/repr 输出状态码与消息"""
        exc = NotFound()
        self.assertEqual(str(exc), "404 Not Found")
        self.assertEqual(repr(exc), "<NotFound [404]>")

    def test_to_dict(self):
        """to_dict 返回错误字典，含 description 时附加"""
        exc = NotFound(description="missing")
        data = exc.to_dict()
        self.assertEqual(data["error"], "NotFound")
        self.assertEqual(data["status_code"], 404)
        self.assertEqual(data["message"], "Not Found")
        self.assertEqual(data["description"], "missing")

        data2 = NotFound().to_dict()
        self.assertNotIn("description", data2)

    def test_http_error_alias(self):
        """HttpError 是 HTTPException 的别名"""
        self.assertIs(HttpError, HTTPException)

    def test_status_codes_table(self):
        """状态码表覆盖常见码"""
        self.assertEqual(HTTP_STATUS_CODES[418], "I'm a teapot")
        self.assertEqual(HTTP_STATUS_CODES[429], "Too Many Requests")


class TestConcreteExceptions(unittest.TestCase):
    """测试具体 HTTP 异常类"""

    def test_bad_request(self):
        exc = BadRequest()
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.message, "Bad Request")

    def test_unauthorized_with_www_authenticate(self):
        """Unauthorized 支持 WWW-Authenticate 响应头"""
        exc = Unauthorized(www_authenticate='Basic realm="litefs"')
        self.assertEqual(exc.status_code, 401)
        self.assertIn(("WWW-Authenticate", 'Basic realm="litefs"'), exc.headers)

    def test_forbidden_and_not_found(self):
        self.assertEqual(Forbidden().status_code, 403)
        self.assertEqual(NotFound().status_code, 404)

    def test_method_not_allowed_headers(self):
        """MethodNotAllowed 生成 Allow 响应头"""
        exc = MethodNotAllowed(allowed_methods=["GET", "POST"])
        self.assertEqual(exc.status_code, 405)
        self.assertIn(("Allow", "GET, POST"), exc.headers)

    def test_payload_too_large_with_max_size(self):
        """PayloadTooLarge 支持附加最大尺寸描述"""
        exc = PayloadTooLarge(max_size=1024)
        self.assertEqual(exc.status_code, 413)
        self.assertIn("1024 bytes", exc.description)

    def test_too_many_requests_retry_after(self):
        """TooManyRequests 生成 Retry-After 响应头"""
        exc = TooManyRequests(retry_after=30)
        self.assertEqual(exc.status_code, 429)
        self.assertIn(("Retry-After", "30"), exc.headers)

    def test_service_unavailable_retry_after(self):
        """ServiceUnavailable 生成 Retry-After 响应头"""
        exc = ServiceUnavailable(retry_after=60)
        self.assertEqual(exc.status_code, 503)
        self.assertIn(("Retry-After", "60"), exc.headers)

    def test_unprocessable_entity(self):
        exc = UnprocessableEntity()
        self.assertEqual(exc.status_code, 422)
        self.assertEqual(exc.message, "Unprocessable Entity")

    def test_server_error_family(self):
        """5xx 系列异常状态码正确"""
        self.assertEqual(InternalServerError().status_code, 500)
        self.assertEqual(NotImplementedHTTP().status_code, 501)
        self.assertEqual(BadGateway().status_code, 502)
        self.assertEqual(GatewayTimeout().status_code, 504)

    def test_inheritance(self):
        """具体异常都是 HTTPException 的子类"""
        for cls in (BadRequest, Unauthorized, Forbidden, NotFound, TooManyRequests):
            self.assertTrue(issubclass(cls, HTTPException))


class TestOtherExceptions(unittest.TestCase):
    """测试非 HTTP 异常类"""

    def test_route_not_found(self):
        exc = RouteNotFound("no route")
        self.assertEqual(str(exc), "no route")

    def test_configuration_error(self):
        exc = ConfigurationError("bad config", config_key="debug")
        self.assertEqual(exc.config_key, "debug")
        self.assertEqual(str(exc), "bad config")

    def test_validation_error(self):
        exc = ValidationError("invalid", field="age", value=-1)
        self.assertEqual(exc.field, "age")
        self.assertEqual(exc.value, -1)

    def test_database_and_cache_error(self):
        origin = ValueError("boom")
        self.assertIs(DatabaseError("db", original_error=origin).original_error, origin)
        self.assertIs(CacheError("cache", original_error=origin).original_error, origin)


class TestAbort(unittest.TestCase):
    """测试 abort 函数"""

    def test_abort_mapped_status_codes(self):
        """abort 按状态码抛出对应异常类"""
        cases = {
            400: BadRequest,
            401: Unauthorized,
            403: Forbidden,
            404: NotFound,
            405: MethodNotAllowed,
            413: PayloadTooLarge,
            429: TooManyRequests,
            500: InternalServerError,
            503: ServiceUnavailable,
        }
        for status, cls in cases.items():
            with self.assertRaises(cls):
                abort(status)

    def test_abort_unmapped_uses_base(self):
        """未映射的状态码抛 HTTPException 基类"""
        with self.assertRaises(HTTPException) as ctx:
            abort(599)
        self.assertEqual(ctx.exception.status_code, 599)

    def test_abort_with_kwargs(self):
        """abort 透传额外参数（如 retry_after）"""
        with self.assertRaises(TooManyRequests) as ctx:
            abort(429, retry_after=10)
        self.assertIn(("Retry-After", "10"), ctx.exception.headers)


class TestErrorHandler(unittest.TestCase):
    """测试错误处理器"""

    def test_register_and_get_handler(self):
        """register 装饰器注册处理函数并可获取"""
        handler = ErrorHandler()

        @handler.register(404)
        def handle_404(error, request_handler):
            return "custom-404"

        self.assertIs(handler.get_handler(404), handle_404)
        self.assertIsNone(handler.get_handler(500))

    def test_handle_http_exception_with_custom_handler(self):
        """HTTPException 优先使用注册的自定义处理函数"""
        handler = ErrorHandler()
        handler.register(404)(lambda error, rh: "custom")
        result = handler.handle(NotFound(), None)
        self.assertEqual(result, "custom")

    def test_handle_http_exception_default(self):
        """未注册时使用默认处理，返回三元组"""
        handler = ErrorHandler()
        body, status, headers = handler.handle(NotFound(description="x"), None)
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "NotFound")
        self.assertEqual(body["message"], "Not Found")
        self.assertEqual(body["description"], "x")
        self.assertEqual(headers, [])

    def test_handle_generic_exception_wraps_500(self):
        """非 HTTP 异常包装为 500 InternalServerError 处理"""
        handler = ErrorHandler()
        body, status, _ = handler.handle(ValueError("boom"), None)
        self.assertEqual(status, 500)
        self.assertEqual(body["description"], "boom")
        self.assertEqual(body["error"], "InternalServerError")

    def test_global_error_handler_instance(self):
        """模块级 error_handler 可用"""
        self.assertIsInstance(error_handler, ErrorHandler)


if __name__ == "__main__":
    unittest.main()
