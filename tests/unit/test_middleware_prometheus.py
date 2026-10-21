#!/usr/bin/env python
# coding: utf-8

"""
Prometheus 监控中间件测试

覆盖指标注册中心的渲染与计数逻辑、PrometheusMiddleware 的
指标端点、状态码解析、路由模板标签、幂等去重与异常兜底，
以及完整的 WSGI 请求链路集成验证。
"""

import asyncio
import sys
import unittest
from unittest.mock import patch

from litefs.core import Litefs
from litefs.metrics import (
    DEFAULT_CONTENT_TYPE,
    MetricsRegistry,
    PrometheusNotAvailable,
    build_metrics_registry,
    load_prometheus_client,
)
from litefs.middleware import PrometheusMiddleware


class MockRequestHandler:
    """模拟请求处理器"""

    def __init__(self, path="/api", method="GET", **attrs):
        self._environ = {
            "PATH_INFO": path,
            "REQUEST_METHOD": method,
        }
        for key, value in attrs.items():
            setattr(self, key, value)


class TestMetricsRegistry(unittest.TestCase):
    """指标注册中心"""

    def test_render_contains_all_metric_names(self):
        """渲染结果包含全部指标名称"""
        text = MetricsRegistry().render()

        self.assertIn("litefs_http_requests_total", text)
        self.assertIn("litefs_http_errors_total", text)
        self.assertIn("litefs_http_request_duration_seconds", text)
        self.assertIn("litefs_http_response_size_bytes", text)
        self.assertIn("litefs_db_pool_connections", text)
        self.assertIn("litefs_cache_operations_total", text)
        self.assertIn("litefs_cache_entries", text)

    def test_custom_namespace(self):
        """自定义命名空间生效"""
        text = MetricsRegistry(namespace="myapp").render()
        self.assertIn("myapp_http_requests_total", text)

    def test_custom_buckets(self):
        """自定义分桶生效"""
        registry = MetricsRegistry(buckets=(0.1, 1.0))
        self.assertEqual(registry.buckets, (0.1, 1.0))

    def test_content_type(self):
        """Content-Type 为 Prometheus 文本格式"""
        self.assertEqual(MetricsRegistry().content_type, DEFAULT_CONTENT_TYPE)

    def test_observe_request_success(self):
        """成功请求只累加请求总数"""
        registry = MetricsRegistry()
        registry.observe_request("GET", "/", 200, 0.01, 100)

        text = registry.render()
        self.assertIn(
            'litefs_http_requests_total{method="GET",path="/",status="200"} 1.0',
            text,
        )
        self.assertNotIn('litefs_http_errors_total{method="GET",path="/",status="200"}', text)

    def test_observe_request_error(self):
        """状态码 >= 400 时累加错误计数"""
        registry = MetricsRegistry()
        registry.observe_request("GET", "/boom", 500, 0.02, 0)

        text = registry.render()
        self.assertIn(
            'litefs_http_errors_total{method="GET",path="/boom",status="500"} 1.0',
            text,
        )

    def test_observe_request_accumulates(self):
        """多次请求累加计数"""
        registry = MetricsRegistry()
        for _ in range(3):
            registry.observe_request("GET", "/", 200, 0.01, 10)

        text = registry.render()
        self.assertIn(
            'litefs_http_requests_total{method="GET",path="/",status="200"} 3.0',
            text,
        )

    def test_build_metrics_registry(self):
        """便捷构造函数生效"""
        registry = build_metrics_registry(namespace="svc", buckets=[0.5])
        self.assertEqual(registry.namespace, "svc")
        self.assertEqual(registry.buckets, (0.5,))


class TestPrometheusNotAvailable(unittest.TestCase):
    """可选依赖缺失场景"""

    def test_load_prometheus_client_raises(self):
        """未安装 prometheus-client 时抛出明确异常"""
        with patch.dict(sys.modules, {"prometheus_client": None}):
            with self.assertRaises(PrometheusNotAvailable) as ctx:
                load_prometheus_client()

        self.assertIn("prometheus-client", str(ctx.exception))

    def test_middleware_init_raises(self):
        """中间件构造时校验可选依赖"""
        with patch.dict(sys.modules, {"prometheus_client": None}):
            with self.assertRaises(PrometheusNotAvailable):
                PrometheusMiddleware(None)


class TestPrometheusMiddleware(unittest.TestCase):
    """Prometheus 监控中间件"""

    def setUp(self):
        self.middleware = PrometheusMiddleware(None)

    def test_metrics_endpoint_returns_tuple(self):
        """指标端点返回三元组响应"""
        result = self.middleware.process_request(MockRequestHandler("/metrics"))

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

        status, headers, content = result
        self.assertEqual(status, "200 OK")
        self.assertEqual(dict(headers)["Content-Type"], DEFAULT_CONTENT_TYPE)
        self.assertIn("litefs_http_requests_total", content)

    def test_metrics_endpoint_requires_get(self):
        """非 GET 方法不短路请求"""
        result = self.middleware.process_request(
            MockRequestHandler("/metrics", "POST")
        )
        self.assertIsNone(result)

    def test_other_path_not_short_circuited(self):
        """非指标路径继续处理"""
        self.assertIsNone(self.middleware.process_request(MockRequestHandler("/api")))

    def test_process_request_start_time_idempotent(self):
        """重复调用不覆盖计时起点"""
        handler = MockRequestHandler("/api")
        self.middleware.process_request(handler)
        first = getattr(handler, "_prometheus_start_time")

        self.middleware.process_request(handler)
        self.assertEqual(getattr(handler, "_prometheus_start_time"), first)

    def test_process_response_records_request(self):
        """响应阶段记录请求指标"""
        handler = MockRequestHandler("/api")
        self.middleware.process_request(handler)

        response = ("200 OK", [("Content-Length", "5")], "hello")
        self.assertIs(self.middleware.process_response(handler, response), response)

        text = self.middleware.registry.render()
        self.assertIn(
            'litefs_http_requests_total{method="GET",path="unmatched",status="200"} 1.0',
            text,
        )

    def test_process_response_uses_route_template(self):
        """使用路由模板作为标签，保证低基数"""
        handler = MockRequestHandler("/user/42", route_path="/user/{id}")
        self.middleware.process_request(handler)
        self.middleware.process_response(handler, ("200 OK", [], "ok"))

        text = self.middleware.registry.render()
        self.assertIn('path="/user/{id}"', text)
        self.assertNotIn('path="/user/42"', text)

    def test_process_response_ignores_non_tuple(self):
        """非三元组响应原样返回"""
        handler = MockRequestHandler("/api")
        response = object()

        self.assertIs(self.middleware.process_response(handler, response), response)

    def test_process_response_ignores_invalid_status(self):
        """状态行无法解析时原样返回"""
        handler = MockRequestHandler("/api")
        response = ("NOT-A-STATUS", [], "")

        self.assertIs(self.middleware.process_response(handler, response), response)

    def test_process_response_only_once(self):
        """同一请求只记录一次"""
        handler = MockRequestHandler("/api", route_path="/api")
        self.middleware.process_request(handler)
        self.middleware.process_response(handler, ("200 OK", [], "ok"))
        self.middleware.process_response(handler, ("200 OK", [], "ok"))

        text = self.middleware.registry.render()
        self.assertIn(
            'litefs_http_requests_total{method="GET",path="/api",status="200"} 1.0',
            text,
        )

    def test_process_exception_records_500(self):
        """异常兜底记录 500 错误指标"""
        handler = MockRequestHandler("/api", route_path="/api")
        self.middleware.process_request(handler)

        self.assertIsNone(self.middleware.process_exception(handler, RuntimeError("boom")))

        text = self.middleware.registry.render()
        self.assertIn(
            'litefs_http_errors_total{method="GET",path="/api",status="500"} 1.0',
            text,
        )

    def test_process_exception_does_not_double_count(self):
        """已记录过响应的请求不再重复计数"""
        handler = MockRequestHandler("/api", route_path="/api")
        self.middleware.process_request(handler)
        self.middleware.process_response(handler, ("500 Internal Server Error", [], "err"))
        self.middleware.process_exception(handler, RuntimeError("boom"))

        text = self.middleware.registry.render()
        self.assertIn(
            'litefs_http_errors_total{method="GET",path="/api",status="500"} 1.0',
            text,
        )

    def test_exclude_paths(self):
        """排除列表内的路径不采集指标"""
        middleware = PrometheusMiddleware(None, exclude_paths=["/internal"])
        handler = MockRequestHandler("/internal/x", route_path="/internal/x")
        middleware.process_request(handler)
        middleware.process_response(handler, ("200 OK", [], "ok"))

        text = middleware.registry.render()
        self.assertNotIn('path="/internal/x"', text)

    def test_content_length_estimate(self):
        """响应体大小估算"""
        middleware = PrometheusMiddleware(None)
        self.assertEqual(middleware._content_length([("Content-Length", "42")], "x"), 42)
        self.assertEqual(middleware._content_length([], "abc"), 3)
        self.assertEqual(middleware._content_length([], b"abcd"), 4)
        self.assertEqual(middleware._content_length([], None), 0)

    def test_async_delegates_to_sync(self):
        """异步接口委托同步实现"""
        middleware = PrometheusMiddleware(None)
        handler = MockRequestHandler("/api")

        self.assertIsNone(asyncio.run(middleware.async_process_request(handler)))

        response = ("200 OK", [], "ok")
        self.assertIs(
            asyncio.run(middleware.async_process_response(handler, response)), response
        )
        self.assertIsNone(
            asyncio.run(middleware.async_process_exception(handler, RuntimeError()))
        )


class TestPrometheusIntegration(unittest.TestCase):
    """完整 WSGI 请求链路"""

    def setUp(self):
        self.app = Litefs()
        self.app.add_middleware(PrometheusMiddleware)
        self.app.add_get("/hello", lambda request: "hello")
        self.app.add_get("/user/{id}", lambda request, id: "user")
        self.application = self.app.wsgi()

    @staticmethod
    def _environ(path, method="GET"):
        return {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "8000",
            "SERVER_PROTOCOL": "HTTP/1.1",
        }

    def _request(self, path, method="GET"):
        """发起一次 WSGI 请求，返回 (状态行, 响应体)"""
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(self.application(self._environ(path, method), start_response))
        return captured["status"], body

    def test_metrics_endpoint_available(self):
        """指标端点可访问"""
        status, body = self._request("/metrics")

        self.assertEqual(status, "200 OK")
        self.assertIn(b"litefs_http_requests_total", body)

    def test_request_counted_with_route_template(self):
        """请求按路由模板计数，不记录原始路径"""
        self._request("/hello")
        self._request("/user/42")

        _, body = self._request("/metrics")
        text = body.decode("utf-8")

        self.assertIn('path="/hello"', text)
        self.assertIn('path="/user/{id}"', text)
        self.assertNotIn('path="/user/42"', text)

    def test_404_counted_as_error(self):
        """404 计入错误指标"""
        self._request("/missing")

        _, body = self._request("/metrics")
        text = body.decode("utf-8")

        self.assertIn(
            'litefs_http_errors_total{method="GET",path="unmatched",status="404"}',
            text,
        )

    def test_metrics_endpoint_not_self_counted(self):
        """指标端点自身的请求不计入统计"""
        self._request("/metrics")

        _, body = self._request("/metrics")
        text = body.decode("utf-8")

        self.assertNotIn('path="/metrics"', text)


class TestPrometheusConfig(unittest.TestCase):
    """配置项驱动的自动挂载"""

    def test_disabled_by_default(self):
        """默认不启用 Prometheus 中间件"""
        app = Litefs()
        classes = [cls for cls, _ in app.middleware_manager._middlewares]
        self.assertNotIn(PrometheusMiddleware, classes)

    def test_enabled_by_config(self):
        """prometheus_enabled 开启后自动挂载中间件"""
        app = Litefs(prometheus_enabled=True)
        classes = [cls for cls, _ in app.middleware_manager._middlewares]
        self.assertIn(PrometheusMiddleware, classes)

    def test_custom_path_and_namespace(self):
        """自定义路径与命名空间生效"""
        app = Litefs(
            prometheus_enabled=True,
            prometheus_path="/internal/metrics",
            prometheus_namespace="svc",
        )
        instances = app._get_middleware_instances()
        middleware = next(i for i in instances if isinstance(i, PrometheusMiddleware))

        self.assertEqual(middleware.path, "/internal/metrics")
        self.assertEqual(middleware.registry.namespace, "svc")

    def test_missing_dependency_fails_fast(self):
        """依赖缺失时在应用构造阶段失败"""
        with patch.dict(sys.modules, {"prometheus_client": None}):
            with self.assertRaises(PrometheusNotAvailable):
                Litefs(prometheus_enabled=True)


if __name__ == "__main__":
    unittest.main()
