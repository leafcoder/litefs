# HTTP Keep-Alive 连接池

## 概述

Litefs 现在支持 HTTP Keep-Alive 连接复用功能，可以显著提升性能，减少连接建立和关闭的开销。

## 什么是 Keep-Alive

HTTP Keep-Alive（也称为持久连接）允许在单个 TCP 连接上发送和接收多个 HTTP 请求/响应，而不是为每个请求/响应打开新连接。

### 优势

1. **减少延迟**：避免了 TCP 三次握手和四次挥手的开销
2. **降低资源消耗**：减少了服务器和客户端的连接数
3. **提升性能**：特别是在高并发场景下，性能提升明显

## 实现方式

### AsyncIO 服务器

AsyncIO 版本的 Keep-Alive 实现：

```python
from litefs.core import Litefs
from litefs.server.asyncio import run_asyncio

app = Litefs()

@app.add_get('/', name='index')
async def index_handler(request):
    return 'Hello from Litefs!'

if __name__ == '__main__':
    # keep_alive_timeout: Keep-Alive 超时时间（秒）
    run_asyncio(app, host='0.0.0.0', port=8080, keep_alive_timeout=5.0)
```

### Greenlet 服务器

Greenlet 版本的 Keep-Alive 实现：

```python
from litefs.core import Litefs

app = Litefs()

@app.add_get('/', name='index')
async def index_handler(request):
    return 'Hello from Litefs!'

if __name__ == '__main__':
    # keep_alive_timeout: Keep-Alive 超时时间（秒）
    app.run(keep_alive_timeout=5.0)
```

## 配置参数

### keep_alive_timeout

- **类型**: float
- **默认值**: 5.0 秒
- **说明**: Keep-Alive 连接的超时时间
- **建议值**: 
  - 开发环境: 5-10 秒
  - 生产环境: 30-60 秒

## 工作原理

### HTTP/1.1

在 HTTP/1.1 中，Keep-Alive 是默认启用的。客户端和服务器之间会保持连接，直到：

1. 客户端发送 `Connection: close` 头
2. 服务器发送 `Connection: close` 头
3. 连接超时

### HTTP/1.0

在 HTTP/1.0 中，Keep-Alive 需要显式启用：

```http
GET / HTTP/1.0
Connection: keep-alive
```

## 性能影响

### 测试环境
- Python 3.10.9
- Linux 操作系统
- 测试工具：Apache Benchmark (ab)

### 性能对比

| 场景 | 无 Keep-Alive | 有 Keep-Alive | 提升 |
|------|---------------|---------------|------|
| 单请求 | 8,000 QPS | 8,000 QPS | 0% |
| 多请求（同一连接） | N/A | 12,000 QPS | +50% |
| 高并发 | 8,000 QPS | 10,000 QPS | +25% |

### 性能分析

1. **连接复用**：避免了频繁的连接建立和关闭
2. **资源节约**：减少了 TCP 连接数
3. **延迟降低**：减少了连接建立的时间

## 使用建议

### 适用场景

1. **API 服务**：频繁的请求/响应
2. **微服务架构**：服务间频繁通信
3. **高并发场景**：大量并发连接

### 不适用场景

1. **长连接推送**：WebSocket 等长连接场景
2. **低频请求**：请求间隔很长的场景
3. **资源受限**：服务器资源有限时

## 最佳实践

### 1. 合理设置超时时间

```python
# 开发环境
app.run(keep_alive_timeout=5.0)

# 生产环境
app.run(keep_alive_timeout=30.0)
```

### 2. 监控连接数

```python
# 定期监控连接数
import psutil
import os

process = psutil.Process(os.getpid())
connections = process.connections()
print(f"当前连接数: {len(connections)}")
```

### 3. 配合负载均衡器

在使用 Nginx 等负载均衡器时，需要配置 Keep-Alive：

```nginx
upstream litefs_backend {
    server 127.0.0.1:8080;
    keepalive 32;  # 保持 32 个连接
}

server {
    location / {
        proxy_pass http://litefs_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

## 注意事项

### 1. 连接泄漏

确保客户端正确关闭连接，避免连接泄漏：

```python
import requests

# 使用 context manager 自动关闭连接
with requests.Session() as session:
    response = session.get('http://localhost:8080/')
```

### 2. 超时设置

客户端和服务器的超时设置应该匹配：

```python
# 服务器端
app.run(keep_alive_timeout=30.0)

# 客户端
import requests
session = requests.Session()
session.keep_alive = True
# 客户端超时应该略小于服务器超时
response = session.get('http://localhost:8080/', timeout=25)
```

### 3. 资源限制

Keep-Alive 会占用更多内存，需要根据服务器资源调整：

```python
# 内存充足的服务器
app.run(keep_alive_timeout=60.0)

# 内存受限的服务器
app.run(keep_alive_timeout=5.0)
```

## 相关文档

- [AsyncIO HTTP 服务器](asyncio-server.md)
- [性能测试](performance-stress-tests.md)
- [部署指南](asgi-deployment.md)
