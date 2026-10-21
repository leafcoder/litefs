#!/usr/bin/env python
# coding: utf-8

"""
Prometheus 监控中间件

采集 HTTP 请求计数、延迟直方图、错误率，以及数据库连接池状态与缓存命中情况，
并通过 ``/metrics`` 端点以 Prometheus 文本格式暴露。

设计要点：
- prometheus-client 为可选依赖，未安装时抛出
  :class:`~litefs.metrics.PrometheusNotAvailable` 并给出安装指引。
- ``/metrics`` 端点直接返回 ``(status, headers, content)`` 三元组，
  以兼容框架的 ``_parse_result_tuple`` 解析逻辑。
- 路由标签使用**路由模板**（如 ``/user/{id}``）而非原始路径，
  保证指标基数可控。
"""

import time
from typing import Any, Optional, Sequence

from ..metrics import UNMATCHED_ROUTE, MetricsRegistry, PrometheusNotAvailable
from .base import Middleware

# 请求处理器上保存计时起点与去重标记的属性名
_START_TIME_ATTR = "_prometheus_start_time"
_RECORDED_ATTR = "_prometheus_recorded"


class PrometheusMiddleware(Middleware):
    """
    Prometheus 监控中间件

    挂载方式::

        app.add_middleware(PrometheusMiddleware)

    指定暴露路径与命名空间::

        app.add_middleware(PrometheusMiddleware, path='/internal/metrics',
                           namespace='myapp')
    """

    def __init__(
        self,
        app,
        path: str = "/metrics",
        namespace: str = "litefs",
        buckets: Optional[Sequence[float]] = None,
        exclude_paths: Optional[Sequence[str]] = None,
    ) -> None:
        """
        初始化 Prometheus 监控中间件

        Args:
            app: Litefs 应用实例
            path: 指标暴露路径，默认为 /metrics
            namespace: 指标名称前缀，默认为 litefs
            buckets: HTTP 延迟直方图分桶（秒），None 使用默认值
            exclude_paths: 不采集指标的路径前缀列表

        Raises:
            PrometheusNotAvailable: 未安装 prometheus-client 时抛出
        """
        super().__init__(app)
        self.path = path
        self.exclude_paths = tuple(exclude_paths or ())
        self.registry = MetricsRegistry(
            namespace=namespace,
            buckets=tuple(buckets) if buckets else None,
        )

    # ==================== 中间件接口 ====================

    def process_request(self, request_handler):
        """
        处理请求，记录起始时间并响应指标端点

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            三元组: 指标端点命中时直接返回响应
        """
        self._mark_start_time(request_handler)

        path = request_handler._environ.get("PATH_INFO", "")
        method = request_handler._environ.get("REQUEST_METHOD", "GET")

        if method == "GET" and path == self.path:
            return self._render_metrics()

        return None

    def process_response(self, request_handler, response):
        """
        处理响应，记录请求指标

        Args:
            request_handler: 请求处理器实例
            response: 响应数据，通常为 (status, headers, content) 三元组

        Returns:
            未修改的响应数据
        """
        if getattr(request_handler, _RECORDED_ATTR, False):
            return response

        if not (isinstance(response, tuple) and len(response) == 3):
            # Socket 路径下中间件可能收到非三元组响应，直接跳过
            return response

        status_line = response[0]
        headers = response[1]
        content = response[2]

        if not isinstance(status_line, str):
            return response

        try:
            status_code = int(status_line.split()[0])
        except (ValueError, IndexError):
            return response

        duration = self._elapsed(request_handler)
        response_size = self._content_length(headers, content)

        method = request_handler._environ.get("REQUEST_METHOD", "GET")
        route_path = getattr(request_handler, "route_path", None) or UNMATCHED_ROUTE

        if self._is_excluded(route_path):
            return response

        self.registry.observe_request(
            method=method,
            path=route_path,
            status_code=status_code,
            duration=duration,
            response_size=response_size,
        )

        setattr(request_handler, _RECORDED_ATTR, True)
        return response

    def process_exception(self, request_handler, exception):
        """
        处理异常，补记一次错误指标

        业务异常通常在路由执行阶段被框架捕获并转为 500 响应，
        此处仅作为兜底（如 ASGI 的 HttpError），避免指标重复计数。

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
        """
        if getattr(request_handler, _RECORDED_ATTR, False):
            return None

        duration = self._elapsed(request_handler)
        method = request_handler._environ.get("REQUEST_METHOD", "GET")
        route_path = getattr(request_handler, "route_path", None) or UNMATCHED_ROUTE

        if not self._is_excluded(route_path):
            self.registry.observe_request(
                method=method,
                path=route_path,
                status_code=500,
                duration=duration,
                response_size=0,
            )
            setattr(request_handler, _RECORDED_ATTR, True)

        return None

    # ==================== 异步接口 ====================

    async def async_process_request(self, request_handler):
        """
        异步版本的处理请求

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            三元组: 指标端点命中时直接返回响应
        """
        return self.process_request(request_handler)

    async def async_process_response(self, request_handler, response):
        """
        异步版本的处理响应

        Args:
            request_handler: 请求处理器实例
            response: 响应数据

        Returns:
            未修改的响应数据
        """
        return self.process_response(request_handler, response)

    async def async_process_exception(self, request_handler, exception):
        """
        异步版本的处理异常

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
        """
        return self.process_exception(request_handler, exception)

    # ==================== 内部方法 ====================

    def _mark_start_time(self, request_handler) -> None:
        """
        记录请求起始时间

        框架在 WSGI / ASGI 路径下均会重复调用 ``process_request``，
        因此这里只在首次调用时写入，保证计时起点不被覆盖。

        Args:
            request_handler: 请求处理器实例
        """
        if getattr(request_handler, _START_TIME_ATTR, None) is None:
            setattr(request_handler, _START_TIME_ATTR, time.perf_counter())

    def _elapsed(self, request_handler) -> float:
        """
        计算请求耗时

        Args:
            request_handler: 请求处理器实例

        Returns:
            耗时（秒），无法确定时返回 0
        """
        start = getattr(request_handler, _START_TIME_ATTR, None)
        if start is None:
            return 0.0
        return max(0.0, time.perf_counter() - float(start))

    def _is_excluded(self, route_path: str) -> bool:
        """
        判断路径是否在排除列表中

        Args:
            route_path: 路由模板

        Returns:
            是否排除采集
        """
        if not self.exclude_paths:
            return False
        return any(route_path.startswith(prefix) for prefix in self.exclude_paths)

    def _content_length(self, headers: Any, content: Any) -> int:
        """
        计算响应体大小

        优先读取 Content-Length 响应头；缺失时按内容类型估算。

        Args:
            headers: 响应头列表
            content: 响应内容

        Returns:
            响应体大小（字节），无法确定时返回 0
        """
        if isinstance(headers, (list, tuple)):
            for header in headers:
                try:
                    key, value = header
                except (TypeError, ValueError):
                    continue
                if str(key).lower() == "content-length":
                    try:
                        return int(value)
                    except (TypeError, ValueError):
                        break

        if isinstance(content, str):
            return len(content.encode("utf-8"))
        if isinstance(content, (bytes, bytearray)):
            return len(content)
        return 0

    def _render_metrics(self) -> Any:
        """
        渲染指标内容

        Returns:
            (status, headers, content) 三元组
        """
        try:
            content = self.registry.render()
        except PrometheusNotAvailable:
            raise
        except Exception as exc:  # pragma: no cover - 防御性保护
            content = f"# 指标采集失败: {exc}\n"

        return (
            "200 OK",
            [("Content-Type", self.registry.content_type)],
            content,
        )


__all__ = [
    "PrometheusMiddleware",
]
