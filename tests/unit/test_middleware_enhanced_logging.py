#!/usr/bin/env python
# coding: utf-8

"""
增强日志中间件测试

覆盖 litefs.middleware.enhanced_logging 模块：请求追踪、敏感信息过滤、
日志级别、性能装饰器与请求上下文日志记录器。
"""

import asyncio
import logging
import unittest
from unittest.mock import Mock

from litefs.middleware.enhanced_logging import (
    EnhancedLoggingMiddleware,
    RequestContextLogger,
    log_async_performance,
    log_performance,
)


def make_handler(path="/index", method="GET", **extra_environ):
    """构造测试用请求处理器（无 get/post/body 属性）"""
    handler = Mock(spec=[])
    handler.environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "REMOTE_ADDR": "127.0.0.1",
        **extra_environ,
    }
    return handler


class TestFilterSensitiveData(unittest.TestCase):
    """测试敏感信息过滤"""

    def setUp(self):
        self.mw = EnhancedLoggingMiddleware(app=Mock(spec=[]), logger=Mock())

    def test_sensitive_keys_masked(self):
        """常见敏感键被遮蔽（大小写不敏感）"""
        data = {"Password": "x", "api_key": "y", "TOKEN": "z", "name": "a"}
        filtered = self.mw._filter_sensitive_data(data)
        self.assertEqual(filtered["Password"], "***FILTERED***")
        self.assertEqual(filtered["api_key"], "***FILTERED***")
        self.assertEqual(filtered["TOKEN"], "***FILTERED***")
        self.assertEqual(filtered["name"], "a")

    def test_nested_dict_filtered(self):
        """嵌套字典递归过滤"""
        data = {"user": {"password": "secret", "age": 1}}
        filtered = self.mw._filter_sensitive_data(data)
        self.assertEqual(filtered["user"]["password"], "***FILTERED***")
        self.assertEqual(filtered["user"]["age"], 1)

    def test_non_dict_passthrough(self):
        """非字典输入原样返回"""
        self.assertEqual(self.mw._filter_sensitive_data("raw"), "raw")

    def test_custom_sensitive_params(self):
        """可追加自定义敏感参数"""
        mw = EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=Mock(), sensitive_params=["biz_secret"]
        )
        filtered = mw._filter_sensitive_data({"biz_secret": "v"})
        self.assertEqual(filtered["biz_secret"], "***FILTERED***")


class TestHelpers(unittest.TestCase):
    """测试辅助方法"""

    def setUp(self):
        self.mw = EnhancedLoggingMiddleware(app=Mock(spec=[]), logger=Mock())

    def test_generate_request_id_unique(self):
        """请求 ID 为 UUID 且唯一"""
        id1 = self.mw._generate_request_id()
        id2 = self.mw._generate_request_id()
        self.assertNotEqual(id1, id2)
        self.assertEqual(len(id1.split("-")), 5)

    def test_should_skip_logging_wildcard(self):
        """排除路径支持通配符匹配"""
        mw = EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=Mock(), exclude_paths=["/health*", "/static/*"]
        )
        self.assertTrue(mw._should_skip_logging("/health"))
        self.assertTrue(mw._should_skip_logging("/health/live"))
        self.assertTrue(mw._should_skip_logging("/static/a.css"))
        self.assertFalse(mw._should_skip_logging("/index"))

    def test_truncate_body(self):
        """超长内容被截断并标注"""
        self.assertEqual(self.mw._truncate_body(None), "")
        self.assertEqual(self.mw._truncate_body("short"), "short")
        long_text = "x" * 1500
        result = self.mw._truncate_body(long_text)
        self.assertTrue(result.endswith("... (truncated)"))
        self.assertEqual(len(result), 1000 + len("... (truncated)"))

    def test_truncate_body_binary(self):
        """不可解码字节显示为二进制占位"""
        result = self.mw._truncate_body(b"\xff\xfe\xfa")
        self.assertEqual(result, "<binary data: 3 bytes>")

    def test_truncate_body_custom_length(self):
        """支持自定义截断长度"""
        self.assertEqual(
            self.mw._truncate_body("abcdef", max_length=3), "abc... (truncated)"
        )

    def test_get_log_level_mapping(self):
        """状态码映射日志级别：5xx=ERROR, 4xx=WARNING, 其他=INFO"""
        self.assertEqual(self.mw._get_log_level(500), logging.ERROR)
        self.assertEqual(self.mw._get_log_level(404), logging.WARNING)
        self.assertEqual(self.mw._get_log_level(200), logging.INFO)


class TestFormatLogMessage(unittest.TestCase):
    """测试日志格式化"""

    def _make(self, structured=False):
        return EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=Mock(), structured=structured
        )

    def test_plain_format(self):
        """传统格式包含关键信息"""
        mw = self._make()
        msg = mw._format_log_message(
            {
                "request_id": "rid",
                "method": "GET",
                "path": "/a",
                "status_code": 200,
                "duration": 0.5,
                "remote_addr": "1.2.3.4",
            },
            logging.INFO,
        )
        self.assertIn("[rid]", msg)
        self.assertIn("1.2.3.4", msg)
        self.assertIn("GET /a", msg)
        self.assertIn("0.500s", msg)

    def test_plain_format_with_error(self):
        """带错误信息的格式"""
        mw = self._make()
        msg = mw._format_log_message({"error": "boom"}, logging.ERROR)
        self.assertIn("ERROR: boom", msg)

    def test_structured_format_is_json(self):
        """结构化模式输出 JSON"""
        mw = self._make(structured=True)
        msg = mw._format_log_message({"path": "/a", "status_code": 200}, logging.INFO)
        self.assertIn('"path": "/a"', msg)


class TestProcessRequestResponse(unittest.TestCase):
    """测试请求/响应处理流程"""

    def setUp(self):
        self.logger = Mock()
        self.mw = EnhancedLoggingMiddleware(app=Mock(spec=[]), logger=self.logger)

    def test_process_request_records_id_and_start_time(self):
        """请求处理：记录 request_id、开始时间与日志"""
        handler = make_handler()
        result = self.mw.process_request(handler)
        self.assertIsNone(result)
        self.assertTrue(handler.request_id)
        self.assertIsNotNone(handler._start_time)
        self.logger.info.assert_called_once()
        self.assertIn("Request started", self.logger.info.call_args.args[0])
        self.assertIsNotNone(handler._log_data)

    def test_process_request_skips_excluded_path(self):
        """排除路径不记录日志、不分配 request_id"""
        mw = EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=self.logger, exclude_paths=["/health"]
        )
        handler = make_handler(path="/health")
        mw.process_request(handler)
        self.logger.info.assert_not_called()
        self.assertFalse(hasattr(handler, "request_id"))

    def test_process_request_records_get_post_params(self):
        """记录过滤后的 GET/POST 参数"""
        handler = make_handler()
        handler.get = {"q": "abc", "token": "secret"}
        handler.post = {"password": "x"}
        self.mw.process_request(handler)
        log_data = handler._log_data
        self.assertEqual(log_data["get_params"]["token"], "***FILTERED***")
        self.assertEqual(log_data["post_params"]["password"], "***FILTERED***")
        self.assertEqual(log_data["get_params"]["q"], "abc")

    def test_process_request_logs_body_when_enabled(self):
        """开启 log_request_body 时记录请求体"""
        mw = EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=self.logger, log_request_body=True
        )
        handler = make_handler()
        handler.body = b"payload"
        mw.process_request(handler)
        self.assertEqual(handler._log_data["request_body"], "payload")

    def test_process_response_tuple_adds_headers(self):
        """响应处理：三元组响应追加追踪与耗时头"""
        handler = make_handler()
        handler.request_id = "rid-1"
        handler._start_time = 0.0
        response = ("200 OK", [("Content-Type", "text/html")], b"ok")
        status, headers, content = self.mw.process_response(handler, response)
        header_names = [k for k, _ in headers]
        self.assertIn("X-Request-ID", header_names)
        self.assertIn("X-Response-Time", header_names)
        self.assertEqual(status, "200 OK")
        self.logger.log.assert_called_once()

    def test_process_response_log_level_by_status(self):
        """4xx 响应使用 WARNING 级别"""
        handler = make_handler()
        response = ("404 Not Found", [], b"")
        self.mw.process_response(handler, response)
        self.assertEqual(self.logger.log.call_args.args[0], logging.WARNING)

    def test_process_response_skips_excluded_path(self):
        """排除路径的响应不记录日志且原样返回"""
        mw = EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=self.logger, exclude_paths=["/health"]
        )
        handler = make_handler(path="/health")
        response = ("200 OK", [], b"")
        self.assertIs(mw.process_response(handler, response), response)
        self.logger.log.assert_not_called()

    def test_process_response_dict_status(self):
        """字典响应读取 status_code 字段"""
        handler = make_handler()
        self.mw.process_response(handler, {"status_code": 503})
        self.assertEqual(self.logger.log.call_args.args[0], logging.ERROR)

    def test_process_response_logs_body_when_enabled(self):
        """开启 log_response_body 时，结构化日志包含响应体"""
        mw = EnhancedLoggingMiddleware(
            app=Mock(spec=[]), logger=self.logger,
            log_response_body=True, structured=True,
        )
        handler = make_handler()
        mw.process_response(handler, ("200 OK", [], b"body-content"))
        logged = self.logger.log.call_args.args[1]
        self.assertIn("body-content", logged)

    def test_process_exception_returns_none(self):
        """异常处理：记录 ERROR 日志并返回 None（继续抛出）"""
        handler = make_handler()
        handler.request_id = "rid-e"
        handler._start_time = 0.0
        result = self.mw.process_exception(handler, ValueError("oops"))
        self.assertIsNone(result)
        self.logger.error.assert_called_once()
        self.assertIn("Request failed", self.logger.error.call_args.args[0])


class TestPerformanceDecorators(unittest.TestCase):
    """测试性能日志装饰器"""

    def test_log_performance_success(self):
        """同步装饰器返回结果并记录耗时日志"""
        with self.assertLogs(level=logging.INFO) as captured:
            @log_performance
            def work():
                return 42

            self.assertEqual(work(), 42)
        self.assertIn("Performance: work executed", captured.output[0])

    def test_log_performance_exception(self):
        """同步装饰器异常时记录错误日志并重新抛出"""
        with self.assertLogs(level=logging.ERROR):

            @log_performance
            def broken():
                raise RuntimeError("bad")

            with self.assertRaises(RuntimeError):
                broken()

    def test_log_async_performance(self):
        """异步装饰器返回结果并记录耗时日志"""

        @log_async_performance
        async def awork():
            return "ok"

        with self.assertLogs(level=logging.INFO) as captured:
            self.assertEqual(asyncio.run(awork()), "ok")
        self.assertIn("Performance: awork executed", captured.output[0])

    def test_log_async_performance_exception(self):
        """异步装饰器异常时记录错误日志并重新抛出"""

        @log_async_performance
        async def abroken():
            raise ValueError("async bad")

        with self.assertLogs(level=logging.ERROR):
            with self.assertRaises(ValueError):
                asyncio.run(abroken())


class TestRequestContextLogger(unittest.TestCase):
    """测试请求上下文日志记录器"""

    def test_levels_with_request_id(self):
        """各级别日志均携带 request_id 前缀与 extra"""
        handler = Mock(spec=[])
        handler.request_id = "rid-x"
        logger = RequestContextLogger(handler)

        with self.assertLogs(level=logging.DEBUG) as captured:
            logger.debug("d")
            logger.info("i", extra_field=1)
            logger.warning("w")
            logger.error("e")
        messages = [r.getMessage() for r in captured.records]
        self.assertTrue(all("rid-x" in m for m in messages))
        levels = [r.levelname for r in captured.records]
        self.assertEqual(levels, ["DEBUG", "INFO", "WARNING", "ERROR"])

    def test_default_request_id(self):
        """无 request_id 时回退为 '-'"""
        logger = RequestContextLogger(Mock(spec=[]))
        self.assertEqual(logger.request_id, "-")

    def test_error_includes_exc_info(self):
        """error 级别附带 exc_info"""
        logger = RequestContextLogger(Mock(spec=[]))
        with self.assertLogs(level=logging.ERROR) as captured:
            logger.error("boom")
        self.assertTrue(captured.records[0].exc_info)


if __name__ == "__main__":
    unittest.main()
