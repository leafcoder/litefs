# Litefs 中间件系统使用指南

## 概述

Litefs 中间件系统提供了一种灵活的方式来处理 HTTP 请求和响应的横切关注点。中间件可以在请求到达业务逻辑之前、响应返回给客户端之前以及异常发生时执行自定义逻辑。

## 中间件架构

### 中间件基类

所有中间件都应该继承 `Middleware` 基类并实现相应的方法：

```python
from litefs.middleware import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request_handler):
        """
        处理请求，在请求到达业务逻辑之前执行
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应，中断后续处理
        """
        pass

    def process_response(self, request_handler, response):
        """
        处理响应，在响应返回给客户端之前执行
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            修改后的响应数据
        """
        return response

    def process_exception(self, request_handler, exception):
        """
        处理异常
        
        Args:
            request_handler: 请求处理器实例
            exception: 异常对象
            
        Returns:
            None: 继续抛出异常
            其他值: 返回该值作为响应，不抛出异常
        """
        return None
```

### 中间件执行顺序

中间件按照添加的顺序执行：

1. **请求阶段**：按照添加顺序执行 `process_request`
2. **响应阶段**：按照逆序执行 `process_response`
3. **异常阶段**：按照添加顺序执行 `process_exception`

## 内置中间件

### 1. 日志中间件 (LoggingMiddleware)

记录所有请求和响应的详细信息。

```python
from litefs import Litefs
from litefs.middleware import LoggingMiddleware

app = Litefs(webroot='./site')
app.add_middleware(LoggingMiddleware)
```

### 2. CORS 中间件 (CORSMiddleware)

处理跨域资源共享请求。

```python
from litefs import Litefs
from litefs.middleware import CORSMiddleware

app = Litefs(webroot='./site')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000', 'https://example.com'],
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Content-Type', 'Authorization'],
    allow_credentials=True,
    max_age=86400,
)
```

### 3. 安全中间件 (SecurityMiddleware)

添加安全相关的 HTTP 响应头。

```python
from litefs import Litefs
from litefs.middleware import SecurityMiddleware

app = Litefs(webroot='./site')

app.add_middleware(
    SecurityMiddleware,
    x_frame_options='DENY',
    x_content_type_options='nosniff',
    x_xss_protection='1; mode=block',
    strict_transport_security='max-age=31536000; includeSubDomains',
    content_security_policy="default-src 'self'",
    referrer_policy='strict-origin-when-cross-origin',
)
```

### 4. 认证中间件 (AuthMiddleware)

基于请求头的简单认证。

```python
from litefs import Litefs
from litefs.middleware import AuthMiddleware

app = Litefs(webroot='./site')
app.add_middleware(AuthMiddleware, auth_header='Authorization')
```

### 5. 限流中间件 (RateLimitMiddleware)

基于令牌桶算法的请求限流。

```python
from litefs import Litefs
from litefs.middleware import RateLimitMiddleware

app = Litefs(webroot='./site')

app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,
    window_seconds=60,
    block_duration=60,
)
```

### 6. 节流中间件 (ThrottleMiddleware)

控制请求的处理速率。

```python
from litefs import Litefs
from litefs.middleware import ThrottleMiddleware

app = Litefs(webroot='./site')

app.add_middleware(
    ThrottleMiddleware,
    min_interval=0.1,
)
```

## 中间件管理

### 添加中间件

```python
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)
```

### 链式添加中间件

```python
app = (
    Litefs(webroot='./site')
    .add_middleware(LoggingMiddleware)
    .add_middleware(SecurityMiddleware)
    .add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000'],
        allow_methods=['GET', 'POST'],
    )
)
```

### 移除中间件

```python
app.remove_middleware(LoggingMiddleware)
```

### 清空所有中间件

```python
app.clear_middleware()
```

## 自定义中间件

### 示例 1: 计时中间件

```python
import time
from litefs.middleware import Middleware

class TimingMiddleware(Middleware):
    def process_request(self, request_handler):
        request_handler._start_time = time.time()
    
    def process_response(self, request_handler, response):
        if hasattr(request_handler, '_start_time'):
            duration = time.time() - request_handler._start_time
            print(f'请求处理耗时: {duration:.3f}秒')
        return response

app = Litefs(webroot='./site')
app.add_middleware(TimingMiddleware)
```

### 示例 2: 请求验证中间件

```python
from litefs.middleware import Middleware

class ValidationMiddleware(Middleware):
    def process_request(self, request_handler):
        user_agent = request_handler.environ.get('HTTP_USER_AGENT', '')
        
        if 'bot' in user_agent.lower():
            status = '403 Forbidden'
            headers = [('Content-Type', 'application/json')]
            content = b'{"error": "Bots are not allowed"}'
            return status, headers, content
        
        return None

app = Litefs(webroot='./site')
app.add_middleware(ValidationMiddleware)
```

### 示例 3: 异常处理中间件

```python
from litefs.middleware import Middleware
import json

class ExceptionHandlingMiddleware(Middleware):
    def process_exception(self, request_handler, exception):
        status = '500 Internal Server Error'
        headers = [('Content-Type', 'application/json')]
        
        error_info = {
            'error': str(exception),
            'type': type(exception).__name__,
        }
        
        content = json.dumps(error_info).encode('utf-8')
        return status, headers, content

app = Litefs(webroot='./site')
app.add_middleware(ExceptionHandlingMiddleware)
```

## WSGI 模式下的中间件

中间件系统完全兼容 WSGI 模式：

```python
from litefs import Litefs
from litefs.middleware import LoggingMiddleware, SecurityMiddleware

app = Litefs(webroot='./site')
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)

application = app.wsgi()
```

在 gunicorn 中使用：

```bash
gunicorn -w 4 -b :8000 wsgi_example:application
```

在 uWSGI 中使用：

```bash
uwsgi --http :8000 --wsgi-file wsgi_example.py
```

## 最佳实践

1. **中间件顺序很重要**：将影响请求处理的中间件（如认证、限流）放在前面，将影响响应的中间件（如日志、CORS）放在后面。

2. **避免阻塞操作**：中间件应该快速执行，避免阻塞请求处理。

3. **正确处理异常**：在中间件中捕获异常时要小心，确保不会隐藏重要的错误信息。

4. **使用类型注解**：为自定义中间件添加类型注解，提高代码可读性。

5. **编写测试**：为自定义中间件编写单元测试，确保其正确性。

## 性能考虑

1. **中间件数量**：避免添加过多的中间件，每个中间件都会增加请求处理的开销。

2. **缓存**：在中间件中使用缓存来存储频繁访问的数据。

3. **异步操作**：对于耗时的操作，考虑使用异步处理。

## 测试

运行中间件测试：

```bash
python -m unittest tests.unit.test_middleware -v
```

运行示例代码：

```bash
python examples/middleware_example.py
```

## 参考资源

- [PEP 3333 - WSGI 规范](https://peps.python.org/pep-3333/)
- [HTTP 响应头参考](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers)
- [CORS 规范](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
