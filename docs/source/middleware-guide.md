# 中间件系统

## 功能特性

* 请求中间件 - 在请求处理前执行
* 响应中间件 - 在响应处理后执行
* 异常中间件 - 在异常处理时执行
* 内置中间件 - 日志、安全、CORS、限流、健康检查
* 自定义中间件 - 支持自定义中间件

## 内置中间件

### LoggingMiddleware

记录请求日志：

```python
from litefs.middleware import LoggingMiddleware

app = (
    Litefs(**config)
    .add_middleware(LoggingMiddleware)
)
```

### SecurityMiddleware

安全防护中间件：

```python
from litefs.middleware import SecurityMiddleware

app = (
    Litefs(**config)
    .add_middleware(SecurityMiddleware)
)
```

### CORSMiddleware

跨域资源共享中间件：

```python
from litefs.middleware import CORSMiddleware

app = (
    Litefs(**config)
    .add_middleware(CORSMiddleware)
)
```

### RateLimitMiddleware

速率限制中间件：

```python
from litefs.middleware import RateLimitMiddleware

app = (
    Litefs(**config)
    .add_middleware(RateLimitMiddleware)
)
```

构造参数：`max_requests=100`（窗口内最大请求数）、`window_seconds=60`、
`block_duration=60`（超限封禁时长）、`key_func=None`（默认按完整 IP 地址限流，
IPv6 不截断）、`max_keys=65536`（键字典 LRU 淘汰上限）。

内部状态受锁保护（多线程 WSGI 容器安全）；达到配额后按 `block_duration`
封禁来源并返回 429（含 `Retry-After` 头）。注意该实现为进程内计数，
多进程 / 多实例部署下实际配额为 `配置值 × 实例数`（分布式共享后端规划于 v0.14.0）。

### HealthCheck

健康检查中间件：

```python
from litefs.middleware import HealthCheck

app = (
    Litefs(**config)
    .add_middleware(HealthCheck)
)
```

## 配置驱动挂载

中间件的挂载由 config.yaml 的 ``middleware`` 配置项驱动：
**应用创建时**（``Litefs(...)`` 构造阶段）按该列表自动挂载，无需手动调用
``add_middleware``（详见 :doc:`configuration`）。条目支持内置中间件名称与
自定义中间件模块路径：

```yaml
# config.yaml
middleware:
  - logging
  - security
  - cors
  - health
  - myapp.middleware.ThrottleMiddleware   # 自定义中间件（模块路径，动态导入）

# 内置中间件可用同名配置段注入构造参数
cors:
  allow_origins: ["*"]
  allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]

health_check:
  path: "/health"
  ready_path: "/health/ready"

# 自定义（或内置）中间件统一经 middleware_options 注入构造参数，
# 以 middleware 条目原文为键
middleware_options:
  myapp.middleware.ThrottleMiddleware:
    rate: 100
    period: 60
```

应用代码只需正常创建实例：

```python
from litefs.core import Litefs

# middleware 配置项控制的中间件在构造阶段自动挂载
app = Litefs(config_file='config.yaml')
```

## 自定义中间件

```python
from litefs.middleware.base import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request_handler):
        # 在请求处理前执行
        request_handler._start_time = time.time()
        return None
    
    def process_response(self, request_handler, response):
        # 在响应处理后执行
        duration = time.time() - request_handler._start_time
        response.headers['X-Response-Time'] = f'{duration:.3f}s'
        return response
    
    def process_exception(self, request_handler, exception):
        # 在异常处理时执行
        print(f"Exception: {exception}")
        return None
```

## 中间件执行顺序

中间件按照添加顺序执行，响应时逆序执行：

```
请求: 1 → 2 → 3 → Handler → 3 → 2 → 1
```

## 最佳实践

* **职责单一**：每个中间件只做一件事
* **顺序配置**：日志 → 安全 → 功能 → 特殊
* **错误处理**：合理处理异常

## 相关文档

* :doc:`routing-guide` - 路由系统
* :doc:`configuration` - 配置管理
