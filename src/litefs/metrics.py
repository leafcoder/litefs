#!/usr/bin/env python
# coding: utf-8

"""
指标注册中心

封装 Prometheus 指标的创建与动态刷新，供 PrometheusMiddleware 使用。

设计要点：
- prometheus-client 为可选依赖，本模块**顶层不导入**它，
  所有导入均通过 :func:`load_prometheus_client` 懒加载。
- 每个 :class:`MetricsRegistry` 实例持有独立的 ``CollectorRegistry``，
  避免多应用 / 多测试场景下的指标重复注册冲突。
- 连接池与缓存指标在 scrape 时（``refresh``）实时采集，
  仅使用 prometheus-client 的公开 API，不依赖内部模块。
"""

import threading
from typing import Any, Dict, List, Optional, Tuple

# 默认的 HTTP 延迟直方图分桶（秒）
DEFAULT_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
)

# Prometheus 文本格式的内容类型
DEFAULT_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# 未匹配到路由时使用的低基数占位标签
UNMATCHED_ROUTE = "unmatched"

_INSTALL_HINT = (
    "未安装 prometheus-client，请执行 pip install 'litefs[prometheus]' "
    "或 pip install prometheus-client"
)


class PrometheusNotAvailable(ImportError):
    """prometheus-client 未安装时抛出的异常"""


def load_prometheus_client() -> Any:
    """
    懒加载 prometheus_client 模块

    Returns:
        prometheus_client 模块对象

    Raises:
        PrometheusNotAvailable: 未安装 prometheus-client 时抛出
    """
    try:
        import prometheus_client  # noqa: PLC0415  # 延迟导入，避免强制依赖
    except ImportError as exc:
        raise PrometheusNotAvailable(_INSTALL_HINT) from exc
    return prometheus_client


class MetricsRegistry:
    """
    指标注册中心

    封装 LiteFS 暴露的全部 Prometheus 指标，并提供动态指标的实时刷新能力。

    使用示例:
        registry = MetricsRegistry(namespace='litefs')
        registry.requests_total.labels('GET', '/', '200').inc()
        print(registry.render())
    """

    def __init__(
        self,
        namespace: str = "litefs",
        buckets: Optional[Tuple[float, ...]] = None,
    ) -> None:
        """
        初始化指标注册中心

        Args:
            namespace: 指标名称前缀，默认为 litefs
            buckets: HTTP 延迟直方图分桶（秒），None 使用默认值
        """
        prometheus_client = load_prometheus_client()

        self.namespace = namespace
        self.buckets = tuple(buckets) if buckets else DEFAULT_BUCKETS

        # 每个实例使用独立注册表，避免多应用场景的重复注册异常
        self.registry = prometheus_client.CollectorRegistry()

        self.requests_total = prometheus_client.Counter(
            f"{namespace}_http_requests_total",
            "HTTP 请求总数",
            ["method", "path", "status"],
            registry=self.registry,
        )
        self.errors_total = prometheus_client.Counter(
            f"{namespace}_http_errors_total",
            "HTTP 错误响应总数（状态码 >= 400）",
            ["method", "path", "status"],
            registry=self.registry,
        )
        self.request_duration_seconds = prometheus_client.Histogram(
            f"{namespace}_http_request_duration_seconds",
            "HTTP 请求耗时（秒）",
            ["method", "path"],
            buckets=self.buckets,
            registry=self.registry,
        )
        self.response_size_bytes = prometheus_client.Histogram(
            f"{namespace}_http_response_size_bytes",
            "HTTP 响应体大小（字节）",
            ["method", "path"],
            buckets=self.buckets,
            registry=self.registry,
        )
        self.db_pool_connections = prometheus_client.Gauge(
            f"{namespace}_db_pool_connections",
            "数据库连接池状态",
            ["database", "state"],
            registry=self.registry,
        )
        self.cache_operations_total = prometheus_client.Counter(
            f"{namespace}_cache_operations_total",
            "缓存读操作总数",
            ["cache", "backend", "result"],
            registry=self.registry,
        )
        self.cache_entries = prometheus_client.Gauge(
            f"{namespace}_cache_entries",
            "缓存条目数量",
            ["cache", "backend"],
            registry=self.registry,
        )

        # 缓存累计值快照，用于计算增量（Counter 必须单调递增）
        self._cache_snapshot: Dict[Tuple[str, str, str], int] = {}
        self._refresh_lock = threading.Lock()

    @property
    def content_type(self) -> str:
        """Prometheus 文本格式的 Content-Type"""
        return DEFAULT_CONTENT_TYPE

    def render(self) -> str:
        """
        渲染 Prometheus 文本格式的指标内容

        Returns:
            指标文本内容
        """
        prometheus_client = load_prometheus_client()
        self.refresh()
        data = prometheus_client.generate_latest(self.registry)
        return str(data.decode("utf-8"))

    # ==================== 动态指标采集 ====================

    def refresh(self) -> None:
        """
        刷新动态指标（数据库连接池、缓存统计）

        在每次 scrape 前调用，保证 Gauge 反映当前真实状态，
        Counter 以增量方式累加，避免重复计数。
        """
        with self._refresh_lock:
            self._refresh_db_pool()
            self._refresh_cache()

    def _refresh_db_pool(self) -> None:
        """采集数据库连接池状态"""
        try:
            from .database.core import DatabaseManager
        except ImportError:  # pragma: no cover - 数据库模块为可选依赖
            return

        try:
            databases = DatabaseManager.get_databases()
        except Exception:  # pragma: no cover - 防御性保护，不影响主流程
            return

        for name, database in databases.items():
            try:
                status = database.get_pool_status()
            except Exception:
                # 某些连接池实现（如 SQLite 的 SingletonThreadPool）
                # 不提供完整的状态接口，跳过即可
                continue

            for state, value in status.items():
                try:
                    self.db_pool_connections.labels(database=name, state=state).set(value)
                except Exception:  # pragma: no cover - 防御性保护
                    continue

    def _refresh_cache(self) -> None:
        """采集缓存条目数与命中/未命中增量"""
        try:
            from .cache.manager import CacheManager
        except ImportError:  # pragma: no cover - 缓存模块为可选依赖
            return

        try:
            caches = CacheManager.list_cache_instances()
        except Exception:  # pragma: no cover - 防御性保护
            return

        for cache_key, cache, backend in caches:
            stats = getattr(cache, "stats", None)
            if stats is None:
                continue

            snapshot = stats.snapshot()
            for result in ("hit", "miss"):
                key = (cache_key, backend, result)
                current = snapshot.get(result, 0)
                previous = self._cache_snapshot.get(key, 0)
                delta = current - previous
                if delta > 0:
                    self.cache_operations_total.labels(
                        cache=cache_key, backend=backend, result=result
                    ).inc(delta)
                self._cache_snapshot[key] = current

            try:
                entries = len(cache)
            except Exception:  # pragma: no cover - 防御性保护
                entries = 0
            self.cache_entries.labels(cache=cache_key, backend=backend).set(entries)

    # ==================== 记录接口 ====================

    def observe_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        response_size: int,
    ) -> None:
        """
        记录一次 HTTP 请求

        Args:
            method: HTTP 方法
            path: 路由模板（低基数），未匹配时传 'unmatched'
            status_code: 响应状态码
            duration: 请求耗时（秒）
            response_size: 响应体大小（字节）
        """
        status = str(status_code)
        self.requests_total.labels(method, path, status).inc()
        self.request_duration_seconds.labels(method, path).observe(duration)
        self.response_size_bytes.labels(method, path).observe(response_size)

        if status_code >= 400:
            self.errors_total.labels(method, path, status).inc()


def build_metrics_registry(
    namespace: str = "litefs",
    buckets: Optional[List[float]] = None,
) -> MetricsRegistry:
    """
    创建指标注册中心的便捷函数

    Args:
        namespace: 指标名称前缀
        buckets: HTTP 延迟直方图分桶（秒）

    Returns:
        MetricsRegistry 实例
    """
    return MetricsRegistry(
        namespace=namespace,
        buckets=tuple(buckets) if buckets else None,
    )


__all__ = [
    "DEFAULT_BUCKETS",
    "DEFAULT_CONTENT_TYPE",
    "UNMATCHED_ROUTE",
    "MetricsRegistry",
    "PrometheusNotAvailable",
    "build_metrics_registry",
    "load_prometheus_client",
]
