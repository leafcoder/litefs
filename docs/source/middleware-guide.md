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

### HealthCheck

健康检查中间件：

```python
from litefs.middleware import HealthCheck

app = (
    Litefs(**config)
    .add_middleware(HealthCheck)
)
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
