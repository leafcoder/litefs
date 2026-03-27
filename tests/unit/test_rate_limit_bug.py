#!/usr/bin/env python
# coding: utf-8

import sys
import os
import time
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.middleware import RateLimitMiddleware


class TestRateLimitBug(unittest.TestCase):
    """测试限流中间件的 bug 修复"""

    def test_large_requests_after_window(self):
        """
        测试大量请求后，时间窗口过期的情况
        
        这个测试用例验证了以下场景：
        1. 发送大量请求，超过限流阈值
        2. 等待时间窗口过期
        3. 再次发送请求，应该能够正常处理
        
        修复前的问题：
        - 由于 defaultdict 的特性，访问 self.requests[key] 会自动创建空列表
        - 但在大量请求后，所有请求时间都超过了时间窗口
        - 导致过滤后的列表为空，但后续请求无法正常添加
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app,
            max_requests=3,
            window_seconds=1,
            block_duration=1,
        )
        request_handler = Mock()
        request_handler.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        # 发送 3 个请求，刚好达到限流阈值
        for i in range(3):
            result = middleware.process_request(request_handler)
            self.assertIsNone(result)
        
        # 第 4 个请求应该被限流
        result = middleware.process_request(request_handler)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], '429 Too Many Requests')
        
        # 等待时间窗口过期
        time.sleep(1.1)
        
        # 等待封禁时间过期
        time.sleep(1.1)
        
        # 现在应该可以正常发送请求了
        result = middleware.process_request(request_handler)
        self.assertIsNone(result)
        
        # 验证请求时间列表被正确维护
        key = middleware._default_key_func(request_handler)
        self.assertIn(key, middleware.requests)
        self.assertEqual(len(middleware.requests[key]), 1)

    def test_concurrent_different_keys(self):
        """
        测试不同 key 的并发请求
        
        验证不同 IP 的请求不会互相影响
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app,
            max_requests=3,
            window_seconds=60,
        )
        
        # IP 1 发送 3 个请求
        request_handler1 = Mock()
        request_handler1.environ = {'REMOTE_ADDR': ('127.0.0.1', 8080)}
        
        for i in range(3):
            result = middleware.process_request(request_handler1)
            self.assertIsNone(result)
        
        # IP 1 的第 4 个请求应该被限流
        result = middleware.process_request(request_handler1)
        self.assertIsNotNone(result)
        
        # IP 2 应该可以正常发送请求（不受 IP 1 影响）
        # 使用不同的 Mock 对象
        request_handler2 = Mock()
        request_handler2.environ = {'REMOTE_ADDR': ('127.0.0.2', 9090)}
        
        # IP 2 的第一个请求应该通过
        result = middleware.process_request(request_handler2)
        self.assertIsNone(result)
        
        # 验证两个 IP 的请求记录是独立的
        key1 = middleware._default_key_func(request_handler1)
        key2 = middleware._default_key_func(request_handler2)
        
        self.assertNotEqual(key1, key2, '两个 IP 应该有不同的 key')
        self.assertEqual(len(middleware.requests[key1]), 3)
        self.assertEqual(len(middleware.requests[key2]), 1)

    def test_empty_key_initialization(self):
        """
        测试新 key 的初始化
        
        验证第一次访问新 key 时不会出错
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app,
            max_requests=5,
            window_seconds=60,
        )
        
        request_handler = Mock()
        request_handler.environ = {'REMOTE_ADDR': ('192.168.1.1', 12345)}
        
        # 第一次访问新 key
        result = middleware.process_request(request_handler)
        self.assertIsNone(result)
        
        # 验证 key 被正确初始化
        key = middleware._default_key_func(request_handler)
        self.assertIn(key, middleware.requests)
        self.assertEqual(len(middleware.requests[key]), 1)


if __name__ == '__main__':
    unittest.main()
