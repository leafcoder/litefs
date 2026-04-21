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


class TestRateLimitFixes(unittest.TestCase):
    """测试限流中间件的修复"""

    def test_middleware_instance_caching(self):
        """
        测试中间件实例是否被正确缓存
        
        验证多个请求使用同一个中间件实例
        """
        app = Litefs(webroot='./examples/basic/site')
        
        # 添加限流中间件（使用自定义参数）
        app.add_middleware(lambda app: RateLimitMiddleware(app, max_requests=3, window_seconds=60))
        
        # 获取中间件实例
        middleware_instances1 = app._get_middleware_instances()
        middleware_instances2 = app._get_middleware_instances()
        
        # 验证两次获取的是同一个实例列表
        self.assertIs(middleware_instances1, middleware_instances2)
        
        # 验证中间件实例是同一个
        self.assertEqual(len(middleware_instances1), 1)
        middleware1 = middleware_instances1[0]
        middleware2 = middleware_instances2[0]
        self.assertIs(middleware1, middleware2)

    def test_remote_addr_port_removal(self):
        """
        测试 REMOTE_ADDR 端口移除
        
        验证 IP:port 格式的地址被正确处理
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app,
            max_requests=3,
            window_seconds=60,
        )
        
        # 测试带端口的地址（字符串格式）
        request_handler1 = Mock()
        request_handler1.environ = {'REMOTE_ADDR': '127.0.0.1:8080'}
        
        key1 = middleware._default_key_func(request_handler1)
        self.assertEqual(key1, '127.0.0.1')
        
        # 测试不带端口的地址（字符串格式）
        request_handler2 = Mock()
        request_handler2.environ = {'REMOTE_ADDR': '127.0.0.1'}
        
        key2 = middleware._default_key_func(request_handler2)
        self.assertEqual(key2, '127.0.0.1')
        
        # 测试 tuple 格式的地址
        request_handler3 = Mock()
        request_handler3.environ = {'REMOTE_ADDR': ('127.0.0.1', 12132)}
        
        key3 = middleware._default_key_func(request_handler3)
        self.assertEqual(key3, '127.0.0.1')
        
        # 验证所有 key 相同
        self.assertEqual(key1, key2)
        self.assertEqual(key2, key3)

    def test_rate_limit_with_different_ports(self):
        """
        测试不同端口的相同 IP 共享限流
        
        验证同一 IP 的不同端口被视为同一个限流 key
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app,
            max_requests=3,
            window_seconds=60,
        )
        
        # IP 1 端口 8080 发送 3 个请求（tuple 格式）
        request_handler1 = Mock()
        request_handler1.environ = {'REMOTE_ADDR': ('127.0.0.1', 8080)}
        
        for i in range(3):
            result = middleware.process_request(request_handler1)
            self.assertIsNone(result)
        
        # IP 1 端口 9090 的第 4 个请求应该被限流（tuple 格式）
        request_handler2 = Mock()
        request_handler2.environ = {'REMOTE_ADDR': ('127.0.0.1', 9090)}
        
        result = middleware.process_request(request_handler2)
        self.assertIsNotNone(result)
        self.assertEqual(result.status_code, 429)

    def test_rate_limit_state_persistence(self):
        """
        测试限流状态持久化
        
        验证中间件实例在多个请求间共享状态
        """
        app = Litefs(webroot='./examples/basic/site')
        
        # 添加限流中间件（使用自定义参数）
        app.add_middleware(lambda app: RateLimitMiddleware(app, max_requests=3, window_seconds=60))
        
        # 获取中间件实例
        middleware_instances = app._get_middleware_instances()
        rate_limit_middleware = middleware_instances[0]
        
        # 发送 3 个请求
        request_handler1 = Mock()
        request_handler1.environ = {'REMOTE_ADDR': ('192.168.1.1', 12345)}
        
        for i in range(3):
            result = rate_limit_middleware.process_request(request_handler1)
            self.assertIsNone(result)
        
        # 验证请求记录存在
        self.assertIn('192.168.1.1', rate_limit_middleware.requests)
        self.assertEqual(len(rate_limit_middleware.requests['192.168.1.1']), 3)
        
        # 第 4 个请求应该被限流
        result = rate_limit_middleware.process_request(request_handler1)
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
