#!/usr/bin/env python
# coding: utf-8

"""
增强日志中间件测试用例

测试 EnhancedLoggingMiddleware 的各项功能
"""

import json
import logging
import sys
import os
import unittest
from io import StringIO
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.middleware.enhanced_logging import (
    EnhancedLoggingMiddleware,
    log_performance,
    log_async_performance,
    RequestContextLogger
)


class TestEnhancedLoggingMiddleware(unittest.TestCase):
    """增强日志中间件测试"""
    
    def setUp(self):
        """测试前准备"""
        self.app = Mock()
        self.app.logger = logging.getLogger('test')
        
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger('test_enhanced_logging')
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        
        self.middleware = EnhancedLoggingMiddleware(
            self.app,
            logger=self.logger,
            structured=False,
            log_request_body=False,
            log_response_body=False
        )
    
    def tearDown(self):
        """测试后清理"""
        self.logger.removeHandler(self.handler)
        self.log_stream.close()
    
    def test_generate_request_id(self):
        """测试请求 ID 生成"""
        request_id = self.middleware._generate_request_id()
        
        self.assertIsInstance(request_id, str)
        self.assertEqual(len(request_id), 36)  # UUID 格式
        self.assertEqual(request_id.count('-'), 4)  # UUID 有 4 个连字符
    
    def test_filter_sensitive_data(self):
        """测试敏感数据过滤"""
        data = {
            'username': 'admin',
            'password': 'secret123',
            'email': 'admin@example.com',
            'token': 'abc123',
            'nested': {
                'api_key': 'key123',
                'normal_field': 'value'
            }
        }
        
        filtered = self.middleware._filter_sensitive_data(data)
        
        self.assertEqual(filtered['username'], 'admin')
        self.assertEqual(filtered['password'], '***FILTERED***')
        self.assertEqual(filtered['email'], 'admin@example.com')
        self.assertEqual(filtered['token'], '***FILTERED***')
        self.assertEqual(filtered['nested']['api_key'], '***FILTERED***')
        self.assertEqual(filtered['nested']['normal_field'], 'value')
    
    def test_truncate_body(self):
        """测试请求/响应体截断"""
        long_body = 'a' * 2000
        short_body = 'short'
        
        truncated_long = self.middleware._truncate_body(long_body, 1000)
        truncated_short = self.middleware._truncate_body(short_body, 1000)
        
        self.assertEqual(len(truncated_long), 1015)  # 1000 + '... (truncated)'
        self.assertIn('... (truncated)', truncated_long)
        self.assertEqual(truncated_short, 'short')
    
    def test_get_log_level(self):
        """测试日志级别判断"""
        self.assertEqual(self.middleware._get_log_level(200), logging.INFO)
        self.assertEqual(self.middleware._get_log_level(301), logging.INFO)
        self.assertEqual(self.middleware._get_log_level(400), logging.WARNING)
        self.assertEqual(self.middleware._get_log_level(404), logging.WARNING)
        self.assertEqual(self.middleware._get_log_level(500), logging.ERROR)
        self.assertEqual(self.middleware._get_log_level(503), logging.ERROR)
    
    def test_format_log_message_traditional(self):
        """测试传统格式日志消息"""
        data = {
            'request_id': 'test-123',
            'method': 'GET',
            'path': '/test',
            'status_code': 200,
            'duration': 0.123,
            'remote_addr': '127.0.0.1'
        }
        
        message = self.middleware._format_log_message(data, logging.INFO)
        
        self.assertIn('test-123', message)
        self.assertIn('GET', message)
        self.assertIn('/test', message)
        self.assertIn('200', message)
        self.assertIn('0.123', message)
        self.assertIn('127.0.0.1', message)
    
    def test_format_log_message_structured(self):
        """测试结构化日志消息"""
        middleware = EnhancedLoggingMiddleware(
            self.app,
            logger=self.logger,
            structured=True
        )
        
        data = {
            'request_id': 'test-123',
            'method': 'GET',
            'path': '/test',
            'status_code': 200,
            'duration': 0.123
        }
        
        message = middleware._format_log_message(data, logging.INFO)
        
        parsed = json.loads(message)
        self.assertEqual(parsed['request_id'], 'test-123')
        self.assertEqual(parsed['method'], 'GET')
        self.assertEqual(parsed['path'], '/test')
        self.assertEqual(parsed['status_code'], 200)
        self.assertEqual(parsed['duration'], 0.123)
    
    def test_should_skip_logging(self):
        """测试日志跳过判断"""
        middleware = EnhancedLoggingMiddleware(
            self.app,
            logger=self.logger,
            exclude_paths=['/health', '/static/*']
        )
        
        self.assertTrue(middleware._should_skip_logging('/health'))
        self.assertTrue(middleware._should_skip_logging('/static/css/style.css'))
        self.assertFalse(middleware._should_skip_logging('/api/users'))
        self.assertFalse(middleware._should_skip_logging('/'))
    
    def test_process_request(self):
        """测试请求处理"""
        request_handler = Mock()
        request_handler.environ = {
            'PATH_INFO': '/test',
            'REQUEST_METHOD': 'GET',
            'QUERY_STRING': 'name=test',
            'REMOTE_ADDR': '127.0.0.1',
            'HTTP_USER_AGENT': 'TestAgent/1.0',
            'CONTENT_TYPE': 'application/json',
            'CONTENT_LENGTH': '100'
        }
        request_handler.get = {'name': ['test']}
        request_handler.post = {}
        
        result = self.middleware.process_request(request_handler)
        
        self.assertIsNone(result)
        self.assertTrue(hasattr(request_handler, 'request_id'))
        self.assertTrue(hasattr(request_handler, '_start_time'))
        self.assertTrue(hasattr(request_handler, '_log_data'))
        
        log_output = self.log_stream.getvalue()
        self.assertIn('Request started', log_output)
    
    def test_process_response(self):
        """测试响应处理"""
        request_handler = Mock()
        request_handler.request_id = 'test-123'
        request_handler._start_time = 1000.0
        request_handler.environ = {
            'PATH_INFO': '/test',
            'REQUEST_METHOD': 'GET',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        response = ('200 OK', [('Content-Type', 'application/json')], b'{"status":"ok"}')
        
        with patch('time.time', return_value=1000.5):
            result = self.middleware.process_response(request_handler, response)
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        
        status, headers, content = result
        self.assertEqual(status, '200 OK')
        
        header_dict = dict(headers)
        self.assertIn('X-Request-ID', header_dict)
        self.assertIn('X-Response-Time', header_dict)
        self.assertEqual(header_dict['X-Request-ID'], 'test-123')
        
        log_output = self.log_stream.getvalue()
        self.assertIn('Request completed', log_output)
    
    def test_process_exception(self):
        """测试异常处理"""
        request_handler = Mock()
        request_handler.request_id = 'test-123'
        request_handler._start_time = 1000.0
        request_handler.environ = {
            'PATH_INFO': '/test',
            'REQUEST_METHOD': 'GET',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        exception = ValueError("Test exception")
        
        with patch('time.time', return_value=1000.5):
            result = self.middleware.process_exception(request_handler, exception)
        
        self.assertIsNone(result)
        
        log_output = self.log_stream.getvalue()
        self.assertIn('Request failed', log_output)
        self.assertIn('Test exception', log_output)


class TestPerformanceDecorators(unittest.TestCase):
    """性能日志装饰器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger('test_performance')
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
    
    def tearDown(self):
        """测试后清理"""
        self.logger.removeHandler(self.handler)
        self.log_stream.close()
    
    def test_log_performance_success(self):
        """测试性能日志装饰器（成功情况）"""
        @log_performance
        def test_function():
            return "success"
        
        result = test_function()
        
        self.assertEqual(result, "success")
    
    def test_log_performance_failure(self):
        """测试性能日志装饰器（失败情况）"""
        @log_performance
        def test_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            test_function()


class TestRequestContextLogger(unittest.TestCase):
    """请求上下文日志记录器测试"""
    
    def setUp(self):
        """测试前准备"""
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.logger = logging.getLogger('test_context')
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        
        self.request_handler = Mock()
        self.request_handler.request_id = 'test-123'
        
        self.ctx_logger = RequestContextLogger(self.request_handler)
    
    def tearDown(self):
        """测试后清理"""
        self.logger.removeHandler(self.handler)
        self.log_stream.close()
    
    def test_info_logging(self):
        """测试 INFO 级别日志"""
        self.ctx_logger.info("Test info message")
    
    def test_warning_logging(self):
        """测试 WARNING 级别日志"""
        self.ctx_logger.warning("Test warning message")
    
    def test_error_logging(self):
        """测试 ERROR 级别日志"""
        self.ctx_logger.error("Test error message")
    
    def test_debug_logging(self):
        """测试 DEBUG 级别日志"""
        self.ctx_logger.debug("Test debug message")


if __name__ == '__main__':
    unittest.main(verbosity=2)
