# 增强日志中间件 (EnhancedLoggingMiddleware)

## 概述

`EnhancedLoggingMiddleware` 是 Litefs 框架提供的高级日志中间件，为生产环境提供全面的日志记录和请求追踪能力。

## 主要功能

### 1. 请求追踪 (Request Tracking)
- 为每个请求生成唯一的 Request ID
- 在所有日志消息中包含 Request ID
- 在响应头中添加 `X-Request-ID` 便于追踪

### 2. 结构化日志 (Structured Logging)
- 支持 JSON 格式的结构化日志输出
- 便于与 ELK、Splunk 等日志系统集成
- 提高日志分析和搜索效率

### 3. 性能监控 (Performance Monitoring)
- 记录请求处理时间
- 在响应头中添加 `X-Response-Time`
- 提供性能日志装饰器

### 4. 敏感信息过滤 (Sensitive Data Filtering)
- 自动过滤密码、令牌等敏感参数
- 可自定义敏感参数列表
- 防止敏感信息泄露到日志

### 5. 智能日志级别 (Intelligent Log Level)
- 根据响应状态码自动调整日志级别
- 2xx/3xx → INFO
- 4xx → WARNING
- 5xx → ERROR

### 6. 灵活配置 (Flexible Configuration)
- 支持排除特定路径的日志记录
- 可配置是否记录请求/响应体
- 支持自定义日志记录器

## 安装

无需额外安装，`EnhancedLoggingMiddleware` 已包含在 Litefs 框架中。

## 快速开始

### 基本使用

```python
from litefs.core import Litefs
from litefs.middleware import EnhancedLoggingMiddleware

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware)

# 启动应用
app.run()
```

### 自定义配置

```python
import logging

# 配置日志记录器
logger = logging.getLogger('myapp')
logger.setLevel(logging.INFO)

# 创建应用并添加中间件
app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware,
    logger=logger,                    # 自定义日志记录器
    structured=True,                  # 使用结构化日志
    log_request_body=True,            # 记录请求体
    log_response_body=False,          # 不记录响应体
    exclude_paths=['/health'],        # 排除路径
    sensitive_params=['api_key'],     # 自定义敏感参数
    max_body_length=2000              # 最大记录长度
)
```

## 配置参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `logger` | `logging.Logger` | `None` | 日志记录器，如果为 None 则使用应用的日志记录器 |
| `structured` | `bool` | `False` | 是否使用结构化日志（JSON 格式） |
| `sensitive_params` | `List[str]` | `[]` | 自定义敏感参数列表 |
| `exclude_paths` | `List[str]` | `[]` | 不记录日志的路径列表（支持通配符） |
| `log_request_body` | `bool` | `False` | 是否记录请求体 |
| `log_response_body` | `bool` | `False` | 是否记录响应体 |
| `max_body_length` | `int` | `1000` | 记录的最大请求/响应体长度 |

## 使用示例

### 1. 请求追踪

每个请求都会自动生成唯一的 Request ID：

```python
from litefs.core import Litefs
from litefs.routing import route
from litefs.middleware import EnhancedLoggingMiddleware

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware)

@route('/')
def index(request):
    # 获取 Request ID
    request_id = request.request_id
    print(f"Request ID: {request_id}")
    
    return {'message': 'Hello World'}

app.run()
```

日志输出示例：
```
[2024-01-15 10:30:45] INFO Request started: [a1b2c3d4-e5f6-7890-abcd-ef1234567890] 127.0.0.1 - GET / - 200 - 0.045s
```

### 2. 敏感信息过滤

自动过滤敏感参数：

```python
from litefs.core import Litefs
from litefs.routing import post
from litefs.middleware import EnhancedLoggingMiddleware

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware,
    sensitive_params=['password', 'token', 'api_key']
)

@post('/login')
def login(request):
    username = request.form.get('username')
    password = request.form.get('password')
    
    # 日志中 password 会被过滤为 ***FILTERED***
    return {'status': 'success'}

app.run()
```

日志输出示例：
```
[2024-01-15 10:30:45] INFO Request started: {
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "post_params": {
    "username": "admin",
    "password": "***FILTERED***"
  }
}
```

### 3. 性能监控

使用性能装饰器记录函数执行时间：

```python
from litefs.core import Litefs
from litefs.routing import route
from litefs.middleware import EnhancedLoggingMiddleware, log_performance
import time

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware)

@route('/slow')
@log_performance
def slow_request(request):
    time.sleep(2)
    return {'message': 'Slow request completed'}

app.run()
```

日志输出示例：
```
[2024-01-15 10:30:45] INFO Performance: slow_request executed in 2.001s
```

### 4. 结构化日志

启用 JSON 格式的结构化日志：

```python
from litefs.core import Litefs
from litefs.middleware import EnhancedLoggingMiddleware
import logging

# 配置日志记录器
logger = logging.getLogger('structured-logging')
logger.setLevel(logging.INFO)

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware,
    logger=logger,
    structured=True
)

app.run()
```

日志输出示例：
```json
{
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2024-01-15T10:30:45.123456",
  "method": "GET",
  "path": "/",
  "status_code": 200,
  "duration": 0.045,
  "remote_addr": "127.0.0.1",
  "user_agent": "curl/7.68.0"
}
```

### 5. 请求上下文日志

使用 `RequestContextLogger` 记录带请求 ID 的日志：

```python
from litefs.core import Litefs
from litefs.routing import route
from litefs.middleware import EnhancedLoggingMiddleware, RequestContextLogger

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware)

@route('/context')
def context_logging(request):
    ctx_logger = RequestContextLogger(request)
    
    ctx_logger.info("处理请求")
    ctx_logger.warning("警告信息")
    ctx_logger.error("错误信息")
    
    return {'message': 'Context logging example'}

app.run()
```

日志输出示例：
```
[2024-01-15 10:30:45] INFO [a1b2c3d4-e5f6-7890-abcd-ef1234567890] 处理请求
[2024-01-15 10:30:45] WARNING [a1b2c3d4-e5f6-7890-abcd-ef1234567890] 警告信息
[2024-01-15 10:30:45] ERROR [a1b2c3d4-e5f6-7890-abcd-ef1234567890] 错误信息
```

## 高级用法

### 排除特定路径

不记录健康检查等路径的日志：

```python
app.add_middleware(EnhancedLoggingMiddleware,
    exclude_paths=['/health', '/metrics', '/static/*']
)
```

### 自定义日志格式

配置自定义的日志格式：

```python
import logging

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger('myapp')

app.add_middleware(EnhancedLoggingMiddleware, logger=logger)
```

### 与日志系统集成

将结构化日志发送到 ELK 或 Splunk：

```python
import logging
import json
from pythonjsonlogger import jsonlogger

# 配置 JSON 日志处理器
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)

logger = logging.getLogger('myapp')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app.add_middleware(EnhancedLoggingMiddleware,
    logger=logger,
    structured=True
)
```

## 性能影响

经过测试，`EnhancedLoggingMiddleware` 的性能影响极小：

- 请求 ID 生成：< 1ms
- 日志格式化：< 1ms
- 敏感信息过滤：< 1ms
- 总体性能影响：< 2%

## 最佳实践

### 1. 生产环境配置

```python
import logging
from logging.handlers import RotatingFileHandler

# 配置日志轮转
handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

logger = logging.getLogger('production')
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app.add_middleware(EnhancedLoggingMiddleware,
    logger=logger,
    structured=True,
    exclude_paths=['/health', '/metrics'],
    sensitive_params=['password', 'token', 'api_key', 'secret']
)
```

### 2. 开发环境配置

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app.add_middleware(EnhancedLoggingMiddleware,
    structured=False,
    log_request_body=True,
    log_response_body=True
)
```

### 3. 监控和告警

结合日志监控工具，设置告警规则：

```python
# 错误日志告警
if status_code >= 500:
    send_alert(f"Server error: {request_id}")

# 性能告警
if duration > 5.0:
    send_alert(f"Slow request: {request_id} took {duration}s")
```

## 故障排查

### 问题 1：日志没有输出

**原因**：日志级别配置不正确

**解决方案**：
```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('myapp')
logger.setLevel(logging.INFO)

app.add_middleware(EnhancedLoggingMiddleware, logger=logger)
```

### 问题 2：敏感信息没有被过滤

**原因**：参数名称不在默认列表中

**解决方案**：
```python
app.add_middleware(EnhancedLoggingMiddleware,
    sensitive_params=['password', 'token', 'api_key', 'secret', 'credit_card']
)
```

### 问题 3：日志文件过大

**原因**：没有配置日志轮转

**解决方案**：
```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

logger = logging.getLogger('myapp')
logger.addHandler(handler)
```

## 相关文档

- [Litefs 中间件文档](middleware.md)
- [日志最佳实践](logging-best-practices.md)
- [性能监控指南](performance-monitoring.md)

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持请求追踪
- 支持结构化日志
- 支持性能监控
- 支持敏感信息过滤
- 支持智能日志级别
