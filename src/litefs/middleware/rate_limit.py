#!/usr/bin/env python
# coding: utf-8

import ipaddress
import threading
import time
from collections import OrderedDict
from typing import Optional

from .base import Middleware

#: 限流 / 节流键字典的默认淘汰上限
DEFAULT_MAX_KEYS = 65536


def _extract_client_ip(remote_addr) -> str:
    """从 REMOTE_ADDR 提取完整客户端 IP 作为限流键

    IPv4 与 IPv6 均保留完整地址（IPv6 不做任何截断，避免不同用户
    共享配额）；带端口的 ``IPv4:port`` / ``[IPv6]:port`` 形式剥离端口。

    Args:
        remote_addr: REMOTE_ADDR 值（str / tuple / 其他）

    Returns:
        完整 IP 地址字符串
    """
    if isinstance(remote_addr, tuple):
        remote_addr = remote_addr[0]
    remote_addr = str(remote_addr).strip()
    if not remote_addr:
        return "unknown"

    # [IPv6]:port 形式
    if remote_addr.startswith('[') and ']' in remote_addr:
        remote_addr = remote_addr[1:remote_addr.index(']')]

    try:
        # 合法 IP（含完整 IPv6）直接使用
        ipaddress.ip_address(remote_addr)
        return remote_addr
    except ValueError:
        pass

    # 兼容 IPv4:port 形式（标准 REMOTE_ADDR 不含端口，防御性处理）
    if remote_addr.count(':') == 1:
        host, _, port = remote_addr.rpartition(':')
        if port.isdigit():
            try:
                ipaddress.ip_address(host)
                return host
            except ValueError:
                pass

    # 非法地址原样返回（自定义 key_func 场景兜底）
    return remote_addr


class RateLimitMiddleware(Middleware):
    """
    限流中间件

    基于令牌桶算法实现请求限流，支持按 IP 地址或用户限流。
    内部状态受锁保护（多线程 WSGI 容器安全），键字典按 LRU 策略
    淘汰，防止随攻击者伪造源地址无界增长。
    """

    def __init__(
        self,
        app,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_func: Optional[callable] = None,
        block_duration: int = 60,
        max_keys: int = DEFAULT_MAX_KEYS,
    ):
        """
        初始化限流中间件

        Args:
            app: Litefs 应用实例
            max_requests: 时间窗口内允许的最大请求数
            window_seconds: 时间窗口大小（秒）
            key_func: 用于提取限流键的函数，默认使用 IP 地址
            block_duration: 超过限流后的封禁时长（秒）
            max_keys: 键字典淘汰上限（LRU），超过后最旧的键被逐出
        """
        super(RateLimitMiddleware, self).__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.block_duration = block_duration
        self.max_keys = int(max_keys)
        # OrderedDict 保持插入顺序以实现 LRU 淘汰；锁保护全部状态读写
        self.requests: OrderedDict = OrderedDict()
        self.blocked_until: OrderedDict = OrderedDict()
        self._lock = threading.RLock()

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

        with self._lock:
            return self._process_request_locked(key)

    def _process_request_locked(self, key: str):
        """在持锁状态下执行限流判定"""
        current_time = time.time()

        blocked_at = self.blocked_until.get(key)
        if blocked_at is not None:
            if current_time < blocked_at:
                retry_after = int(blocked_at - current_time)
                return self._create_rate_limit_response(
                    f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    retry_after,
                )
            # 封禁已过期，清理条目
            del self.blocked_until[key]

        request_times = self.requests.get(key)
        if request_times is None:
            request_times = []
        else:
            self.requests.move_to_end(key)
        request_times = [
            t for t in request_times if current_time - t < self.window_seconds
        ]
        request_times.append(current_time)
        self.requests[key] = request_times

        if len(request_times) > self.max_requests:
            # 达到窗口上限：移除本次记录并封禁
            request_times.pop()
            self.requests[key] = request_times
            self.blocked_until[key] = current_time + self.block_duration
            retry_after = self.block_duration
            self._evict_keys_locked()
            return self._create_rate_limit_response(
                f"Rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after,
            )

        self._evict_keys_locked()
        return None

    def _evict_keys_locked(self):
        """键字典 LRU 淘汰（持锁调用）

        先清理封禁过期的条目，仍超限时从最旧一端逐出。
        """
        blocked_until = self.blocked_until
        if len(blocked_until) > self.max_keys:
            now_ts = time.time()
            expired = [k for k, v in blocked_until.items() if v <= now_ts]
            for k in expired:
                del blocked_until[k]
            while len(blocked_until) > self.max_keys:
                blocked_until.popitem(last=False)

        requests = self.requests
        if len(requests) > self.max_keys:
            now_ts = time.time()
            window = self.window_seconds
            stale = [
                k for k, times in requests.items()
                if not times or now_ts - times[-1] >= window
            ]
            for k in stale:
                del requests[k]
            while len(requests) > self.max_keys:
                requests.popitem(last=False)

    def _default_key_func(self, request_handler) -> str:
        """
        默认的限流键提取函数，使用完整 IP 地址

        Args:
            request_handler: 请求处理器实例

        Returns:
            限流键（完整 IP 地址，IPv6 不截断）
        """
        return _extract_client_ip(
            request_handler.environ.get("REMOTE_ADDR", "unknown")
        )

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

    控制请求的处理速率，防止服务器过载。
    内部状态受锁保护，键字典按 LRU 策略淘汰。
    """

    def __init__(
        self,
        app,
        min_interval: float = 0.1,
        key_func: Optional[callable] = None,
        max_keys: int = DEFAULT_MAX_KEYS,
    ):
        """
        初始化节流中间件

        Args:
            app: Litefs 应用实例
            min_interval: 两次请求之间的最小间隔（秒）
            key_func: 用于提取节流键的函数，默认使用 IP 地址
            max_keys: 键字典淘汰上限（LRU），超过后最旧的键被逐出
        """
        super(ThrottleMiddleware, self).__init__(app)
        self.min_interval = min_interval
        self.key_func = key_func or self._default_key_func
        self.max_keys = int(max_keys)
        self.last_request_time: OrderedDict = OrderedDict()
        self._lock = threading.RLock()

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

        with self._lock:
            last_time = self.last_request_time.get(key)
            if last_time is not None:
                self.last_request_time.move_to_end(key)
                elapsed = current_time - last_time
                if elapsed < self.min_interval:
                    retry_after = int(self.min_interval - elapsed) + 1
                    return self._create_throttle_response(
                        f"Too many requests. Please wait {retry_after} seconds.",
                        retry_after,
                    )

            self.last_request_time[key] = current_time

            while len(self.last_request_time) > self.max_keys:
                self.last_request_time.popitem(last=False)

        return None

    def _default_key_func(self, request_handler) -> str:
        """
        默认的节流键提取函数，使用完整 IP 地址

        与限流中间件保持一致：IPv4 / IPv6 均保留完整地址，
        带端口形式剥离端口。

        Args:
            request_handler: 请求处理器实例

        Returns:
            节流键（完整 IP 地址，IPv6 不截断）
        """
        return _extract_client_ip(
            request_handler.environ.get("REMOTE_ADDR", "unknown")
        )

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
