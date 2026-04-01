# 中间件

Litefs 中间件使用示例，包括与新路由系统的集成。

## 示例文件

- `middleware_example.py` - 中间件示例主程序

## 内置中间件

### 1. 日志中间件 (LoggingMiddleware)

记录请求和响应日志。

```python
from litefs.middleware import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

### 2. 安全中间件 (SecurityMiddleware)

添加安全相关的 HTTP 头。

```python
from litefs.middleware import SecurityMiddleware

app.add_middleware(SecurityMiddleware)
```

### 3. CORS 中间件 (CORSMiddleware)

处理跨域资源共享。

```python
from litefs.middleware import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
    allow_credentials=True,
    max_age=86400
)
```

### 4. 限流中间件 (RateLimitMiddleware)

限制请求频率。

```python
from litefs.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,
    window_seconds=60,
    block_duration=120
)
```

### 5. 健康检查中间件 (HealthCheck)

提供健康检查端点。

```python
from litefs.middleware import HealthCheck

app.add_middleware(HealthCheck, path='/health', ready_path='/health/ready')
```

## 自定义中间件

创建自定义中间件：

```python
from litefs.middleware import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request_handler):
        pass
    
    def process_response(self, request_handler, response):
        return response

app.add_middleware(CustomMiddleware)
```

## 链式添加中间件

```python
app = (
    Litefs()
    .add_middleware(LoggingMiddleware)
    .add_middleware(SecurityMiddleware)
    .add_middleware(CORSMiddleware)
)
```

## 运行示例

```bash
python middleware_example.py
```

## 中间件执行顺序

中间件按照添加的顺序执行，后添加的中间件先处理请求，先处理响应。

## 与新路由系统集成

中间件可以与新的路由系统无缝集成：

```python
from litefs import Litefs
from litefs.middleware import LoggingMiddleware, SecurityMiddleware
from litefs.routing import get, post

# 创建应用实例
app = Litefs()

# 添加中间件
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)

# 定义路由
@get('/hello')
def hello_handler(self):
    return 'Hello, World!'

@post('/submit')
def submit_handler(self):
    return 'Form submitted!'

# 注册路由
app.register_routes(hello_handler)
app.register_routes(submit_handler)

# 运行应用
app.run()
```

### 中间件与路由的执行顺序

1. 请求到达服务器
2. 中间件的 `process_request` 方法按添加顺序的逆序执行
3. 路由系统匹配并执行对应的处理函数
4. 中间件的 `process_response` 方法按添加顺序执行
5. 响应返回给客户端
