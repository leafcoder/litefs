# 增强日志中间件示例

本示例展示 Litefs 框架的增强日志中间件功能，提供生产级别的日志记录能力。

## 功能特性

### 1. 请求追踪
- 为每个请求生成唯一的 Request ID
- 在所有日志消息中包含 Request ID
- 在响应头中添加 `X-Request-ID`

### 2. 结构化日志
- 支持 JSON 格式的结构化日志输出
- 便于日志分析和处理
- 可与 ELK、Splunk 等日志系统集成

### 3. 性能监控
- 记录请求处理时间
- 在响应头中添加 `X-Response-Time`
- 提供性能日志装饰器

### 4. 敏感信息过滤
- 自动过滤密码、令牌等敏感参数
- 可自定义敏感参数列表
- 防止敏感信息泄露到日志

### 5. 智能日志级别
- 根据响应状态码自动调整日志级别
- 2xx/3xx → INFO
- 4xx → WARNING
- 5xx → ERROR

### 6. 灵活配置
- 支持排除特定路径的日志记录
- 可配置是否记录请求/响应体
- 支持自定义日志记录器

## 运行示例

```bash
cd examples/12-enhanced-logging
python app.py
```

服务器将在 `http://localhost:8080` 启动。

## 示例端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页，展示功能列表 |
| `/login` | POST | 登录示例，演示敏感信息过滤 |
| `/slow` | GET | 慢请求示例，演示性能监控 |
| `/error` | GET | 错误示例，演示错误日志 |
| `/health` | GET | 健康检查，不记录日志 |
| `/structured` | GET | 结构化日志示例 |
| `/context` | GET | 上下文日志示例 |
| `/params` | GET | 参数日志示例 |

## 测试命令

### 1. 基本请求
```bash
curl http://localhost:8080/
```

### 2. 登录请求（敏感信息过滤）
```bash
curl -X POST -d 'username=admin&password=secret' http://localhost:8080/login
```

日志输出中 `password` 参数会被过滤为 `***FILTERED***`

### 3. 慢请求（性能监控）
```bash
curl http://localhost:8080/slow
```

日志会记录请求处理时间，响应头包含 `X-Response-Time`

### 4. 错误请求（错误日志）
```bash
curl http://localhost:8080/error
```

日志会记录异常信息和堆栈跟踪

### 5. 参数日志
```bash
curl 'http://localhost:8080/params?name=test&value=123'
```

日志会记录 GET 和 POST 参数

## 日志输出示例

### 传统格式
```
2024-01-15 10:30:45,123 - enhanced-logging-example - INFO - Request started: [a1b2c3d4-e5f6-7890-abcd-ef1234567890] 127.0.0.1 - GET / - 200 - 0.045s
```

### 结构化格式（JSON）
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

## 使用方法

### 基本使用
```python
from litefs import Litefs
from litefs.middleware import EnhancedLoggingMiddleware

app = Litefs()
app.add_middleware(EnhancedLoggingMiddleware)
```

### 自定义配置
```python
app.add_middleware(EnhancedLoggingMiddleware,
    logger=custom_logger,           # 自定义日志记录器
    structured=True,                # 使用结构化日志
    log_request_body=True,          # 记录请求体
    log_response_body=False,        # 不记录响应体
    exclude_paths=['/health'],      # 排除路径
    sensitive_params=['api_key']    # 自定义敏感参数
)
```

### 性能日志装饰器
```python
from litefs.middleware import log_performance

@log_performance
def slow_function():
    # 函数执行时间会被记录
    time.sleep(1)
```

### 请求上下文日志
```python
from litefs.middleware import RequestContextLogger

def view(request):
    ctx_logger = RequestContextLogger(request)
    ctx_logger.info("处理请求")
    ctx_logger.error("发生错误")
```

## 配置选项

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `logger` | Logger | None | 日志记录器，None 则使用应用默认 |
| `structured` | bool | False | 是否使用结构化日志 |
| `sensitive_params` | list | [] | 自定义敏感参数列表 |
| `exclude_paths` | list | [] | 不记录日志的路径列表 |
| `log_request_body` | bool | False | 是否记录请求体 |
| `log_response_body` | bool | False | 是否记录响应体 |
| `max_body_length` | int | 1000 | 记录的最大请求/响应体长度 |

## 生产环境建议

### 1. 日志级别配置
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
```

### 2. 结构化日志集成
```python
app.add_middleware(EnhancedLoggingMiddleware,
    structured=True,
    logger=logger
)
```

### 3. 排除健康检查
```python
app.add_middleware(EnhancedLoggingMiddleware,
    exclude_paths=['/health', '/metrics', '/static/*']
)
```

### 4. 敏感信息保护
```python
app.add_middleware(EnhancedLoggingMiddleware,
    sensitive_params=['password', 'token', 'api_key', 'secret']
)
```

## 性能影响

- 请求 ID 生成：< 1ms
- 日志格式化：< 1ms
- 敏感信息过滤：< 1ms
- 总体性能影响：< 2%

## 最佳实践

1. **生产环境使用结构化日志**：便于日志分析和搜索
2. **合理配置排除路径**：避免记录健康检查等无用日志
3. **定期清理日志文件**：防止日志文件过大
4. **监控错误日志**：及时发现和处理问题
5. **保护敏感信息**：配置完整的敏感参数列表

## 相关文档

- [Litefs 中间件文档](../../docs/middleware.md)
- [日志最佳实践](../../docs/logging.md)
- [性能监控指南](../../docs/performance.md)
