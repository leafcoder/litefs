#!/usr/bin/env python
# coding: utf-8

import time
from collections import defaultdict
from typing import Dict, Optional, Tuple

from .base import Middleware


class RateLimitMiddleware(Middleware):
    """
    限流中间件

    基于令牌桶算法实现请求限流，支持按 IP 地址或用户限流
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func: Optional[callable] = None,
        block_duration: int = 60,
    ):
        """
        初始化限流中间件

        Args:
            app: Litefs 应用实例
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
            key_func: 用于提取限流键的函数，默认使用 IP 地址
            block_duration: 超过限流后的封禁时长（秒）
        """
        super(RateLimitMiddleware, self).__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.block_duration = block_duration
        self.requests: Dict[str, list] = defaultdict(list)
        self.blocked_until: Dict[str, float] = {}

    def process_request(self, request_handler):
        """
        处理请求，检查是否超过限流

        Args:
            request_handler: 请求处理器实例

        Returns:
            如果超过限流，返回 429 响应
            否则返回 None，继续处理请求
        """
        key = self.key_func(request_handler)

        current_time = time.time()

        if key in self.blocked_until:
            if current_time < self.blocked_until[key]:
                retry_after = int(self.blocked_until[key] - current_time)
                return self._create_rate_limit_response(
                    f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    retry_after,
                )
            else:
                del self.blocked_until[key]
        if key not in self.requests:
            self.requests[key] = []

        request_times = self.requests[key]
        request_times = [t for t in request_times if current_time - t < self.window_seconds]
        self.requests[key] = request_times

        if len(request_times) >= self.max_requests:
            self.blocked_until[key] = current_time + self.block_duration
            retry_after = self.block_duration
            return self._create_rate_limit_response(
                f"Rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after,
            )

        request_times.append(current_time)

        return None

    def _default_key_func(self, request_handler) -> str:
        """
        默认的限流键提取函数，使用 IP 地址

        Args:
            request_handler: 请求处理器实例

        Returns:
            限流键（IP 地址）
        """
        remote_addr = request_handler.environ.get("REMOTE_ADDR", "unknown")
        if isinstance(remote_addr, tuple):
            remote_addr = remote_addr[0]
        elif ":" in remote_addr:
            remote_addr = remote_addr.split(":")[0]
        return remote_addr

    def _create_rate_limit_response(self, message: str, retry_after: int):
        """
        创建限流响应

        Args:
            message: 错误消息
            retry_after: 重试时间（秒）

        Returns:
            429 响应
        """
        from ..handlers import Response

        response = Response(
            content={
                'error': message,
                'retry_after': retry_after
            },
            status_code=429
        )
        response.headers.insert(0, ('Content-Type', 'application/json; charset=utf-8'))
        response.headers.append(('Retry-After', str(retry_after)))

        return response


class ThrottleMiddleware(Middleware):
    """
    节流中间件

    控制请求的处理速率，防止服务器过载
    """

    def __init__(
        self,
        app,
        min_interval: float = 0.1,
        key_func: Optional[callable] = None,
    ):
        """
        初始化节流中间件

        Args:
            app: Litefs 应用实例
            min_interval: 两次请求之间的最小间隔（秒）
            key_func: 用于提取节流键的函数，默认使用 IP 地址
        """
        super(ThrottleMiddleware, self).__init__(app)
        self.min_interval = min_interval
        self.key_func = key_func or self._default_key_func
        self.last_request_time: Dict[str, float] = {}

    def process_request(self, request_handler):
        """
        处理请求，检查是否需要节流

        Args:
            request_handler: 请求处理器实例

        Returns:
            如果需要节流，返回 429 响应
            否则返回 None，继续处理请求
        """
        key = self.key_func(request_handler)
        current_time = time.time()

        if key in self.last_request_time:
            elapsed = current_time - self.last_request_time[key]
            if elapsed < self.min_interval:
                retry_after = int(self.min_interval - elapsed) + 1
                return self._create_throttle_response(
                    f"Too many requests. Please wait {retry_after} seconds.",
                    retry_after,
                )

        self.last_request_time[key] = current_time

        return None

    def _default_key_func(self, request_handler) -> str:
        """
        默认的节流键提取函数，使用 IP 地址

        Args:
            request_handler: 请求处理器实例

        Returns:
            节流键（IP 地址）
        """
        return request_handler.environ.get("REMOTE_ADDR", "unknown")

    def _create_throttle_response(self, message: str, retry_after: int):
        """
        创建节流响应

        Args:
            message: 错误消息
            retry_after: 重试时间（秒）

        Returns:
            429 响应
        """
        from ..handlers import Response
        
        response = Response(
            content={
                'error': message,
                'retry_after': retry_after
            },
            status_code=429
        )
        response.headers.insert(0, ('Content-Type', 'application/json; charset=utf-8'))
        response.headers.append(('Retry-After', str(retry_after)))

        return response
