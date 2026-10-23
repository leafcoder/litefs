#!/usr/bin/env python
# coding: utf-8

import sys
import os
import threading
import time
import unittest
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import Litefs
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


class TestRateLimitHardening(unittest.TestCase):
    """v0.11.0 限流中间件加固（并发安全 / 键淘汰 / IPv6 键）"""

    def test_concurrent_requests_exact_quota(self):
        """
        测试并发请求不突破配额

        多线程同时打满配额时，放行数必须恰好等于 max_requests，
        无锁实现存在丢失窗口会导致超发。
        """
        app = Mock()
        middleware = RateLimitMiddleware(app, max_requests=100, window_seconds=60)

        handler = Mock()
        handler.environ = {'REMOTE_ADDR': '10.0.0.1'}

        allowed = []
        barrier = threading.Barrier(20)

        def worker():
            barrier.wait()
            for _ in range(10):
                result = middleware.process_request(handler)
                allowed.append(result is None)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(sum(allowed), 100)
        self.assertEqual(len(allowed), 200)

    def test_key_dictionary_eviction(self):
        """
        测试键字典淘汰策略

        键数量超过 max_keys 上限后，最旧的键被逐出，字典不无界增长。
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app, max_requests=100, window_seconds=60, max_keys=2
        )

        for ip in ('10.0.0.1', '10.0.0.2', '10.0.0.3'):
            handler = Mock()
            handler.environ = {'REMOTE_ADDR': ip}
            middleware.process_request(handler)

        self.assertLessEqual(len(middleware.requests), 2)
        self.assertNotIn('10.0.0.1', middleware.requests)
        self.assertIn('10.0.0.3', middleware.requests)

    def test_blocked_until_eviction_and_cleanup(self):
        """
        测试封禁键字典的过期清理与淘汰
        """
        app = Mock()
        middleware = RateLimitMiddleware(
            app, max_requests=1, window_seconds=60, block_duration=60,
            max_keys=2,
        )

        # 打满两个 IP 的配额触发封禁
        for ip in ('10.0.0.1', '10.0.0.2'):
            handler = Mock()
            handler.environ = {'REMOTE_ADDR': ip}
            middleware.process_request(handler)
            middleware.process_request(handler)

        self.assertEqual(len(middleware.blocked_until), 2)

        # 封禁过期且窗口内无请求记录时，条目被清理并允许重新请求
        middleware.blocked_until['10.0.0.1'] = time.time() - 1
        del middleware.requests['10.0.0.1']
        handler = Mock()
        handler.environ = {'REMOTE_ADDR': '10.0.0.1'}
        self.assertIsNone(middleware.process_request(handler))
        self.assertNotIn('10.0.0.1', middleware.blocked_until)

    def test_ipv6_full_address_key(self):
        """
        测试 IPv6 限流键保留完整地址

        旧的 split(':')[0] 逻辑会将 2001:db8::* 全部截断为 2001，
        导致不同 IPv6 用户共享配额；修复后必须保留完整地址。
        """
        app = Mock()
        middleware = RateLimitMiddleware(app, max_requests=1, window_seconds=60)

        handler_a = Mock()
        handler_a.environ = {'REMOTE_ADDR': '2001:db8::1'}
        handler_b = Mock()
        handler_b.environ = {'REMOTE_ADDR': '2001:db8::2'}
        handler_loopback = Mock()
        handler_loopback.environ = {'REMOTE_ADDR': '::1'}

        # 各自的第一个请求都应放行（不共享配额）
        self.assertIsNone(middleware.process_request(handler_a))
        self.assertIsNone(middleware.process_request(handler_b))
        self.assertIsNone(middleware.process_request(handler_loopback))

        # 各自的第二个请求都被限流
        self.assertEqual(middleware.process_request(handler_a).status_code, 429)
        self.assertEqual(middleware.process_request(handler_b).status_code, 429)
        self.assertEqual(middleware.process_request(handler_loopback).status_code, 429)

        # 键为完整地址
        self.assertIn('2001:db8::1', middleware.requests)
        self.assertIn('2001:db8::2', middleware.requests)
        self.assertIn('::1', middleware.requests)

    def test_ipv6_with_port_and_brackets(self):
        """
        测试 [IPv6]:port 形式剥离端口并保留完整地址
        """
        app = Mock()
        middleware = RateLimitMiddleware(app, max_requests=1, window_seconds=60)

        handler = Mock()
        handler.environ = {'REMOTE_ADDR': '[2001:db8::1]:8080'}
        self.assertIsNone(middleware.process_request(handler))
        self.assertIn('2001:db8::1', middleware.requests)


class TestThrottleHardening(unittest.TestCase):
    """v0.11.0 节流中间件加固（并发安全 / 键淘汰）"""

    def test_key_dictionary_eviction(self):
        """
        测试节流键字典淘汰策略
        """
        from litefs.middleware import ThrottleMiddleware

        app = Mock()
        middleware = ThrottleMiddleware(app, min_interval=0.01, max_keys=2)

        for ip in ('10.0.0.1', '10.0.0.2', '10.0.0.3'):
            handler = Mock()
            handler.environ = {'REMOTE_ADDR': ip}
            middleware.process_request(handler)

        self.assertLessEqual(len(middleware.last_request_time), 2)
        self.assertNotIn('10.0.0.1', middleware.last_request_time)

    def test_concurrent_no_crash(self):
        """
        测试并发访问节流中间件无异常
        """
        from litefs.middleware import ThrottleMiddleware

        app = Mock()
        middleware = ThrottleMiddleware(app, min_interval=0.001)

        handler = Mock()
        handler.environ = {'REMOTE_ADDR': '10.0.0.9'}
        errors = []

        def worker():
            try:
                for _ in range(50):
                    middleware.process_request(handler)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
