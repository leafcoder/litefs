# Litefs Prometheus 监控

**更新日期**: 2026-10-21
**适用版本**: v0.9.0（开发中）

## 概述

Litefs 内置 Prometheus 监控中间件，用于暴露应用的运行指标：

- **HTTP 请求总数 / 错误数 / 延迟直方图 / 响应体大小**
- **数据库连接池状态**（连接池容量、空闲、在用、溢出、失效）
- **缓存命中率与条目数**

设计原则：

| 原则 | 实现方式 |
|------|----------|
| 零侵入 | 以中间件形式接入，不改动业务代码 |
| 可选依赖 | `prometheus-client` 懒加载，未安装时不影响框架启动 |
| 低基数 | 路由标签使用**路由模板**（`/user/{id}`）而非原始路径 |
| 线程安全 | 指标对象由 prometheus-client 内部保证线程安全；动态采集加锁串行化 |

## 安装

```bash
# 仅启用监控能力
pip install 'litefs[prometheus]'

# 或直接安装依赖
pip install prometheus-client
```

未安装时使用监控功能会抛出 `PrometheusNotAvailable`（继承 `ImportError`），并给出安装指引：

```text
未安装 prometheus-client，请执行 pip install 'litefs[prometheus]' 或 pip install prometheus-client
```

## 快速开始

### 方式一：代码挂载（推荐）

```python
from litefs.core import Litefs
from litefs.middleware import PrometheusMiddleware

app = Litefs()
app.add_middleware(PrometheusMiddleware)
app.run()
```

### 方式二：配置驱动

```python
app = Litefs(
    prometheus_enabled=True,        # 开启监控
    prometheus_path='/metrics',     # 指标暴露路径
    prometheus_namespace='litefs',  # 指标名前缀
)
```

配置项同样支持写在 `config.yaml` 中：

```yaml
prometheus_enabled: true
prometheus_path: /metrics
prometheus_namespace: litefs
```

> `prometheus_enabled` 为 `true` 时，框架会在**应用构造阶段**校验 `prometheus-client` 是否可用，缺失时立即失败，避免延迟到首个请求才报错。

### 方式三：自定义参数

```python
app.add_middleware(
    PrometheusMiddleware,
    path='/internal/metrics',        # 自定义暴露路径
    namespace='myapp',               # 自定义指标前缀
    buckets=(0.01, 0.1, 1.0, 10.0),  # 自定义延迟分桶（秒）
    exclude_paths=('/internal',),    # 这些路径不采集指标
)
```

## 指标清单

所有指标均以 `namespace` 为前缀（默认 `litefs`）。

| 指标名 | 类型 | 标签 | 含义 |
|--------|------|------|------|
| `litefs_http_requests_total` | Counter | `method`, `path`, `status` | 请求总数 |
| `litefs_http_errors_total` | Counter | `method`, `path`, `status` | 错误响应总数（状态码 ≥ 400） |
| `litefs_http_request_duration_seconds` | Histogram | `method`, `path` | 请求耗时（秒） |
| `litefs_http_response_size_bytes` | Histogram | `method`, `path` | 响应体大小（字节） |
| `litefs_db_pool_connections` | Gauge | `database`, `state` | 数据库连接池状态 |
| `litefs_cache_operations_total` | Counter | `cache`, `backend`, `result` | 缓存读操作总数（`result` 为 `hit` / `miss`） |
| `litefs_cache_entries` | Gauge | `cache`, `backend` | 缓存条目数量 |

### 标签语义

| 标签 | 取值 | 说明 |
|------|------|------|
| `method` | `GET` / `POST` / ... | HTTP 请求方法 |
| `path` | `/user/{id}` | **路由模板**，未匹配到路由时为 `unmatched` |
| `status` | `200` / `404` / `500` | HTTP 状态码 |
| `database` | `default` | 数据库实例名 |
| `state` | `pool_size` / `checked_in` / `checked_out` / `overflow` / `invalid` | 连接池状态项 |
| `cache` | `app_cache` / `sessions` / ... | 缓存实例标识 |
| `backend` | `tree` / `memory` / `redis` / `memcache` / `db` | 缓存后端类型 |
| `result` | `hit` / `miss` | 缓存读命中情况 |

> **为什么使用路由模板**：若直接用原始路径作为标签，`/user/1`、`/user/2` … 会产生无限增长的时序，撑爆 Prometheus 存储。框架在路由匹配成功后会把 `route.path`（模板）挂到请求处理器上，中间件据此打标签，从而保证标签基数与路由数量同阶。

### 默认延迟分桶

```text
0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0  （秒）
```

该分桶覆盖 5ms ~ 10s 的典型区间，P99 落在 100ms ~ 1s 之间。如需贴合业务 SLO，建议按实际延迟分布自定义 `buckets`。

## /metrics 端点

```bash
curl http://127.0.0.1:8080/metrics
```

返回 `Content-Type: text/plain; version=0.0.4; charset=utf-8`，内容为 Prometheus 文本格式：

```text
# HELP litefs_http_requests_total HTTP 请求总数
# TYPE litefs_http_requests_total counter
litefs_http_requests_total{method="GET",path="/user/{id}",status="200"} 12.0
# HELP litefs_http_errors_total HTTP 错误响应总数（状态码 >= 400）
# TYPE litefs_http_errors_total counter
litefs_http_errors_total{method="GET",path="/user/{id}",status="404"} 1.0
```

端点本身**不会**被计入请求指标（请求在中间件层直接短路），因此不会产生自监控噪声。

### 响应链路兼容性

Litefs 存在两条响应链路，中间件对两者均能正常采集指标：

| 链路 | 典型场景 | `process_response` 收到的响应 | 状态码来源 |
| --- | --- | --- | --- |
| WSGI / ASGI | gunicorn、uvicorn、`app.wsgi()` / `app.asgi()` | `(status_line, headers, content)` 三元组 | 三元组第一段 |
| 原生 Socket | `app.run()` 默认模式 | 仅响应体字符串 | `request_handler._status_code` |

原生 Socket 路径下，响应头保存在 `request_handler._headers`，状态码保存在 `request_handler._status_code`。
中间件通过 `_extract_response()` 统一这两种形态，提取出统一的三元组后再记录指标，因此
**在 `app.run()` 默认模式下 `/metrics` 同样能采集到完整的请求指标**。

### 动态指标的采集时机

连接池与缓存指标是**快照型**数据，在每次 `/metrics` 抓取时实时采集（scrape-time collection），而非在业务请求路径上采集：

- **连接池**：遍历所有已初始化的数据库实例，读取 `pool_size` / `checked_in` / `checked_out` / `overflow` / `invalid`。
  某些连接池实现（如 SQLite 的 `SingletonThreadPool`）不提供完整状态接口，此时该数据库会被自动跳过，不影响其他指标。
- **缓存**：遍历缓存管理器中的实例，按**增量**方式累加命中/未命中计数（避免重复计数），并以 Gauge 反映当前条目数。

采集过程全部包裹异常保护，任何采集失败都不会影响业务请求。

## Prometheus 抓取配置

```yaml
scrape_configs:
  - job_name: 'litefs'
    scrape_interval: 15s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['127.0.0.1:8080']
```

多实例部署时用服务发现（`consul_sd_configs` / `kubernetes_sd_configs`）替代静态列表。

### Grafana 常用查询

```promql
# QPS
sum(rate(litefs_http_requests_total[1m]))

# 错误率（按状态码分组）
sum(rate(litefs_http_errors_total[5m])) by (status)

# P95 延迟
histogram_quantile(0.95, sum(rate(litefs_http_request_duration_seconds_bucket[5m])) by (le, path))

# 数据库连接池水位
litefs_db_pool_connections{state="checked_out"} / litefs_db_pool_connections{state="pool_size"}

# 缓存命中率
sum(rate(litefs_cache_operations_total{result="hit"}[5m]))
  / sum(rate(litefs_cache_operations_total[5m]))
```

## 生产部署要点

### 1. 隔离暴露面

`/metrics` 会暴露内部路径、状态码分布等信息，**不要**直接暴露到公网。推荐在 Nginx 层做限制：

```nginx
server {
    listen 80;

    location /metrics {
        # 仅允许内网监控网段访问
        allow 10.0.0.0/8;
        deny all;

        proxy_pass http://127.0.0.1:8080;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

或使用 `exclude_paths` 排除敏感前缀。

### 2. 多进程模型（Gunicorn）

每个 worker 进程拥有**独立的**指标注册表，因此 `/metrics` 只会返回**当前处理该请求的那个 worker** 的数据。若使用 `gunicorn -w 4`，抓取到的指标只有 1/4 的量。

两种应对方式：

- **方式一（简单）**：Prometheus 对每个 worker 单独抓取。使用 `gunicorn` 的 `SO_REUSEPORT` 或让每个 worker 绑定不同端口，逐个加入 `targets`。
- **方式二（推荐）**：启用 prometheus-client 的多进程模式。

```bash
export PROMETHEUS_MULTIPROC_DIR=/var/run/litefs/prometheus
gunicorn -w 4 -b :8080 wsgi:application
```

> 多进程模式需要使用 `MultiProcessCollector`，且指标需在进程启动时创建。本框架默认的**单进程 / 多线程 / greenlet** 模型无需额外配置。

### 3. 采样与降载

指标采集发生在**请求路径**上（Counter 递增、Histogram 观测），开销为常数级（微秒级），通常无需优化。但在超高 QPS 场景下可：

- 缩小 `buckets` 数量（分桶越多，直方图开销越大）。
- 对 `/metrics` 端点本身做限流，避免被高频抓取。

### 4. 中间件顺序

监控中间件会记录**所有**请求，因此建议放在中间件链的**最外层**（最先注册），这样才能覆盖到被其它中间件短路掉的请求：

```python
app.add_middleware(PrometheusMiddleware)   # 最外层
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)
```

## API 参考

### PrometheusMiddleware

```python
PrometheusMiddleware(
    app,
    path='/metrics',
    namespace='litefs',
    buckets=None,
    exclude_paths=None,
)
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | `str` | `/metrics` | 指标暴露路径 |
| `namespace` | `str` | `litefs` | 指标名前缀 |
| `buckets` | `Sequence[float]` | `None` | 延迟分桶（秒），`None` 使用默认值 |
| `exclude_paths` | `Sequence[str]` | `None` | 不采集指标的路径前缀列表 |

### MetricsRegistry

```python
from litefs.metrics import MetricsRegistry

registry = MetricsRegistry(namespace='litefs', buckets=None)
registry.observe_request(
    method='GET', path='/user/{id}', status_code=200,
    duration=0.012, response_size=1024,
)
print(registry.render())
```

| 方法 | 说明 |
|------|------|
| `render()` | 渲染 Prometheus 文本格式（内部会先刷新动态指标） |
| `refresh()` | 刷新连接池与缓存动态指标 |
| `observe_request(...)` | 记录一次 HTTP 请求 |
| `content_type` | Prometheus 文本格式的 Content-Type |

### 异常

| 异常 | 触发条件 |
|------|----------|
| `PrometheusNotAvailable` | 未安装 `prometheus-client`（继承 `ImportError`） |

## 常见问题

**Q：为什么 `/metrics` 返回 404？**

A：确认中间件已挂载。若使用配置驱动方式，确认 `prometheus_enabled: true` 生效且 `prometheus_path` 与实际请求路径一致（区分大小写、包含上下文前缀）。

**Q：指标里 `path` 都是 `unmatched`？**

A：说明请求未匹配到任何路由（例如 404 请求），框架会统一归类到 `unmatched`，这是预期行为。

**Q：连接池指标缺失？**

A：当前数据库使用的连接池实现不提供完整状态接口（如 SQLite 内存库的 `SingletonThreadPool`），框架会自动跳过。生产环境使用 MySQL / PostgreSQL 时指标完整可用。

**Q：缓存命中率为 0？**

A：`litefs_cache_operations_total` 统计的是缓存**读**操作。若应用只写不读，或使用了不继承 `CacheBackendBase` 的缓存（如 `FormCache`），则不会产生读计数。

**Q：如何统计某个特定接口的 QPS？**

A：使用路由模板作为过滤条件，例如 `rate(litefs_http_requests_total{path="/user/{id}"}[1m])`。

## 相关文档

- :doc:`middleware-guide` —— 中间件系统总览
- :doc:`cache-system` —— 缓存系统与后端说明
- :doc:`configuration` —— 配置项完整列表
- :doc:`static-checks` —— 静态检查规范
