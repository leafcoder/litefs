#!/usr/bin/env python
# coding: utf-8

"""
工具函数测试

覆盖 litefs.utils.utils 模块：日志辅助、错误渲染、GMT 时间格式化。
"""

import logging
import tempfile
import unittest
from unittest.mock import Mock

from litefs.utils.utils import (
    format_gmt_date,
    gmt_date,
    log_debug,
    log_error,
    log_info,
    make_logger,
    render_error,
)


class TestLogHelpers(unittest.TestCase):
    """测试日志辅助函数"""

    def test_log_error_with_logger(self):
        """有 logger 时调用 logger.error 并附带 exc_info"""
        logger = Mock()
        log_error(logger, "custom error")
        logger.error.assert_called_once_with("custom error", exc_info=True)

    def test_log_error_default_message(self):
        """log_error 默认消息"""
        logger = Mock()
        log_error(logger)
        logger.error.assert_called_once_with("error occured", exc_info=True)

    def test_log_error_fallback_root(self):
        """logger 为 None 时回退到 root logger"""
        with self.assertLogs(level=logging.ERROR) as captured:
            log_error(None, "root error")
        self.assertIn("root error", captured.output[0])

    def test_log_info(self):
        """log_info 支持自定义 logger 与回退"""
        logger = Mock()
        log_info(logger, "info msg")
        logger.info.assert_called_once_with("info msg")
        with self.assertLogs(level=logging.INFO) as captured:
            log_info(None)
        self.assertIn("info", captured.output[0])

    def test_log_debug(self):
        """log_debug 支持自定义 logger 与回退"""
        logger = Mock()
        log_debug(logger, "debug msg")
        logger.debug.assert_called_once_with("debug msg")
        with self.assertLogs(level=logging.DEBUG) as captured:
            log_debug(None)
        self.assertIn("debug", captured.output[0])


class TestRenderError(unittest.TestCase):
    """测试错误 HTML 渲染"""

    def test_render_with_exception(self):
        """有活动异常时输出异常类型与堆栈"""
        try:
            raise ValueError("boom")
        except ValueError:
            html = render_error()
        self.assertIn("Error: ValueError", html)
        self.assertIn("boom", html)
        self.assertIn("Traceback:", html)

    def test_render_without_exception(self):
        """无活动异常时输出未知错误"""
        html = render_error()
        self.assertIn("Unknown Error", html)


class TestGmtDate(unittest.TestCase):
    """测试 GMT 时间格式化"""

    def test_format_gmt_date(self):
        """格式化时间戳为 GMT 字符串"""
        result = format_gmt_date(1767323045)
        self.assertEqual(result, "Fri, 02 Jan 2026 03:04:05 GMT")

    def test_gmt_date_with_timestamp(self):
        """gmt_date 接受时间戳参数"""
        self.assertEqual(
            gmt_date(1767323045), "Fri, 02 Jan 2026 03:04:05 GMT"
        )

    def test_gmt_date_now(self):
        """gmt_date 无参数时使用当前时间，返回合法 GMT 格式"""
        result = gmt_date()
        self.assertRegex(
            result,
            r"^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$",
        )


class TestMakeLogger(unittest.TestCase):
    """测试 logger 工厂"""

    def test_make_logger_console(self):
        """创建控制台 logger"""
        logger = make_logger("test-make-logger")
        self.assertEqual(logger.name, "test-make-logger")

    def test_make_logger_with_file(self):
        """创建带文件输出的 logger 并写入日志"""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name
        logger = make_logger("test-file-logger", log=log_path)
        logger.info("file handler message")
        for handler in logger.handlers:
            handler.flush()
        with open(log_path, encoding="utf-8") as f:
            content = f.read()
        self.assertIn("file handler message", content)
        # 清理文件 handler，避免影响其他测试
        for handler in list(logger.handlers):
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
                handler.close()


if __name__ == "__main__":
    unittest.main()
