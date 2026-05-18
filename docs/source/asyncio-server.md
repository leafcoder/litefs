# AsyncIO HTTP 服务器

## 概述

Litefs 现在提供了基于 asyncio 的 HTTP 服务器实现，与原有的 greenlet 版本形成对比。

## 两种实现对比

### Greenlet 版本
- **实现方式**：使用 epoll + greenlet 实现协程
- **特点**：
  - 成熟的实现，经过生产验证
  - 支持多进程模式
  - 在 Linux 上性能优异
  - 使用 C 扩展，上下文切换更快

### AsyncIO 版本
- **实现方式**：使用 Python 原生 asyncio
- **特点**：
  - 更现代的实现方式
  - 更好的异步生态兼容性
  - 单进程模式，需要外部进程管理器
  - 纯 Python 实现，跨平台性更好

## 使用方法

### 基本使用

```python
from litefs.core import Litefs
from litefs.server.asyncio import run_asyncio

app = Litefs()

@app.add_get('/', name='index')
async def index_handler(request):
    return 'Hello from Litefs AsyncIO!'

if __name__ == '__main__':
    run_asyncio(app, host='0.0.0.0', port=8080)
```

### 异步处理

```python
import asyncio

@app.add_get('/async', name='async_example')
async def async_handler(request):
    # 异步操作
    await asyncio.sleep(0.01)
    return {
        'message': 'Hello from async handler!',
        'async': True
    }
```

### 路径参数

```python
@app.add_get('/user/{id}', name='user_detail')
async def user_detail_handler(request, id):
    return {
        'user_id': id,
        'message': f'User details for ID: {id}'
    }
```

## 性能对比

### 测试环境
- Python 3.10.9
- Linux 操作系统
- 测试工具：Apache Benchmark (ab)
- 测试命令：`ab -n 10000 -c 100 http://127.0.0.1:PORT/ENDPOINT`

### 测试结果

| 端点 | Greenlet QPS | AsyncIO QPS | 差异 |
|------|--------------|-------------|------|
| / | 8,437 | 8,966 | +6.27% |
| /async | 8,043 | 9,213 | +14.54% |
| /user/123 | 7,521 | 8,143 | +8.28% |

**延迟对比 (ms):**

| 端点 | Greenlet | AsyncIO | 差异 |
|------|----------|---------|------|
| / | 0.12 | 0.11 | -5.88% |
| /async | 0.12 | 0.11 | -12.10% |
| /user/123 | 0.13 | 0.12 | -7.52% |

### 性能分析

1. **AsyncIO 版本优势**：
   - 性能比 Greenlet 版本更好（约 6-15% 的提升）
   - 延迟更低（约 5-12% 的降低）
   - 使用 ASGIRequestHandler，有更好的优化
   - 更现代的实现方式

2. **Greenlet 版本特点**：
   - 使用 C 扩展，上下文切换更快
   - epoll 在 Linux 上性能优异
   - 成熟的实现，经过生产验证
   - 支持多进程模式

3. **性能差异原因分析**：
   - AsyncIO 版本使用了更优化的 ASGIRequestHandler
   - AsyncIO 的事件循环在 Python 3.10+ 中有显著优化
   - Greenlet 版本可能需要进一步优化

## 使用建议

### 选择 AsyncIO 版本
- 性能更好（测试显示比 Greenlet 快 6-15%）
- 延迟更低
- 更好的异步生态兼容性
- 与 async/await 无缝集成
- 跨平台性更好

### 选择 Greenlet 版本
- 需要多进程模式
- 生产环境需要更成熟的实现
- 与现有 Greenlet 生态集成

## 部署建议

### Greenlet 版本
```bash
# 直接运行
python app.py

# 多进程模式
python app.py  # 在代码中设置 processes=N
```

### AsyncIO 版本
```bash
# 单进程运行
python app.py

# 使用进程管理器（如 Gunicorn）
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:application
```

## 注意事项

1. **AsyncIO 版本不支持多进程**：
   - asyncio 的设计是单线程事件循环
   - 需要外部进程管理器来实现多进程

2. **性能权衡**：
   - Greenlet 版本性能更高
   - AsyncIO 版本开发体验更好

3. **兼容性**：
   - 两个版本都支持相同的 API
   - 可以根据需求选择使用哪个版本

## 相关文档

- [ASGI 部署](asgi-deployment.md) - ASGI 部署指南
- [WSGI 部署](wsgi-deployment.md) - WSGI 部署指南
- [性能测试](performance-stress-tests.md) - 性能测试文档
