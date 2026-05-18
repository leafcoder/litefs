#!/usr/bin/env python
# coding: utf-8

import sys
import os
import time
from unittest.mock import Mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import Litefs
from litefs.middleware import RateLimitMiddleware


def test_concurrent_different_keys_debug():
    """
    测试不同 key 的并发请求（调试版本）
    """
    app = Mock()
    middleware = RateLimitMiddleware(
        app,
        max_requests=3,
        window_seconds=60,
    )
    
    # IP 1 发送 3 个请求
    request_handler1 = Mock()
    request_handler1.environ = {'REMOTE_ADDR': '127.0.0.1'}
    
    print('=== IP 1 发送 3 个请求 ===')
    for i in range(3):
        result = middleware.process_request(request_handler1)
        print(f'IP 1 第 {i+1} 个请求: {result}')
    
    # IP 1 的第 4 个请求应该被限流
    print('=== IP 1 发送第 4 个请求 ===')
    result = middleware.process_request(request_handler1)
    print(f'IP 1 第 4 个请求: {result}')
    
    print(f'IP 1 请求记录: {middleware.requests}')
    print(f'IP 1 封禁记录: {middleware.blocked_until}')
    
    # IP 2 应该可以正常发送请求（不受 IP 1 影响）
    request_handler2 = Mock()
    request_handler2.environ = {'REMOTE_ADDR': '127.0.0.2'}
    
    print('\n=== IP 2 发送第 1 个请求 ===')
    result = middleware.process_request(request_handler2)
    print(f'IP 2 第 1 个请求: {result}')
    
    print(f'IP 2 请求记录: {middleware.requests}')
    print(f'IP 2 封禁记录: {middleware.blocked_until}')


if __name__ == '__main__':
    test_concurrent_different_keys_debug()
