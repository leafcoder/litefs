# Litefs 性能优化功能示例

本示例展示 Litefs 框架的性能优化功能，包括静态文件服务优化、请求性能监控和增强的缓存装饰器。

## 功能特性

### 1. 优化的静态文件服务

**文件**: `src/litefs/static_handler.py`

提供高性能的静态文件服务：

- ✅ **文件缓存** - 内存缓存小文件，减少磁盘 I/O
- ✅ **Gzip 压缩** - 自动压缩文本文件，减少传输大小
- ✅ **ETag 支持** - 生成文件指纹，支持条件请求
- ✅ **Last-Modified** - 记录文件修改时间，支持缓存验证
- ✅ **Range 请求** - 支持断点续传
- ✅ **MIME 类型** - 自动识别文件类型
- ✅ **安全检查** - 防止路径遍历攻击

### 2. 请求性能监控

**文件**: `src/litefs/middleware/performance.py`

自动监控所有请求的性能：

- ✅ **自动监控** - 自动记录所有请求的处理时间
- ✅ **性能统计** - 统计每个端点的平均、最小、最大处理时间
- ✅ **慢请求告警** - 自动检测和记录慢请求
- ✅ **错误追踪** - 记录错误请求的数量和比例
- ✅ **数据导出** - 支持导出性能数据（JSON 格式）

### 3. 增强的缓存装饰器

**文件**: `src/litefs/cache_decorators.py`

提供灵活的缓存机制：

- ✅ **函数缓存** - `@cached` 装饰器缓存函数结果
- ✅ **响应缓存** - `@cache_response` 装饰器缓存 HTTP 响应
- ✅ **方法缓存** - `@cache_method` 装饰器缓存类方法
- ✅ **属性缓存** - `@cache_property` 装饰器缓存类属性
- ✅ **灵活配置** - 支持 TTL、键前缀、缓存存储等配置

## 运行示例

```bash
cd examples/14-performance-optimization
python app.py
```

服务器将在 `http://localhost:8080` 启动。

## 示例端点

### 首页
```
GET http://localhost:8080/
```

### 性能监控

#### 性能统计信息
```
GET http://localhost:8080/monitor/stats
```

#### 慢请求列表
```
GET http://localhost:8080/monitor/slow
```

#### 最近请求记录
```
GET http://localhost:8080/monitor/recent
```

### 缓存装饰器

#### 函数缓存示例
```
GET http://localhost:8080/cache/function
```

结果会被缓存 10 秒，在此期间重复访问会直接返回缓存结果。

#### 响应缓存示例
```
GET http://localhost:8080/cache/response
```

响应会被缓存 15 秒。

#### 方法缓存示例
```
GET http://localhost:8080/cache/method?id=test
```

方法结果会被缓存 20 秒。

#### 缓存统计信息
```
GET http://localhost:8080/cache/stats
```

#### 清空缓存
```
GET http://localhost:8080/cache/clear
```

### 性能测试

#### 慢请求测试
```
GET http://localhost:8080/test/slow?delay=2.0
```

触发慢请求告警（阈值 0.5 秒）。

#### 快速请求测试
```
GET http://localhost:8080/test/fast
```

## 使用指南

### 1. 优化的静态文件服务

```python
from litefs.static_handler import StaticFileHandler

# 创建静态文件处理器
handler = StaticFileHandler(
    directory='static',
    max_age=3600,          # 缓存 1 小时
    enable_gzip=True,      # 启用 Gzip 压缩
    enable_etag=True,      # 启用 ETag
    enable_range=True      # 支持范围请求
)

# 服务静态文件
status, headers, content = handler.serve('css/style.css', request_headers)
```

### 2. 请求性能监控

```python
from litefs import Litefs
from litefs.middleware.performance import PerformanceMonitoringMiddleware

app = Litefs()

# 添加性能监控中间件
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=1.0)

# 获取性能监控器
monitor = app.get_middleware(PerformanceMonitoringMiddleware).get_monitor()

# 获取性能统计
stats = monitor.get_stats()

# 获取慢请求
slow_requests = monitor.get_slow_requests(threshold=1.0)

# 导出性能数据
data = monitor.export(format='json')
```

### 3. 函数缓存

```python
from litefs.cache_decorators import cached

@cached(ttl=60, key_prefix='user')
def get_user(user_id):
    # 这个函数的结果会被缓存 60 秒
    return db.query(User).get(user_id)

# 第一次调用会执行函数
user = get_user(123)

# 60 秒内的后续调用会返回缓存结果
user = get_user(123)
```

### 4. 响应缓存

```python
from litefs.cache_decorators import cache_response

@cache_response(ttl=300, vary_on=['Accept-Encoding'])
def api_endpoint(request):
    # 这个响应会被缓存 5 分钟
    return {'data': 'value'}
```

### 5. 方法缓存

```python
from litefs.cache_decorators import cache_method

class UserService:
    @cache_method(ttl=120)
    def get_user(self, user_id):
        # 这个方法的结果会被缓存 2 分钟
        return db.query(User).get(user_id)
```

### 6. 属性缓存

```python
from litefs.cache_decorators import cache_property

class User:
    def __init__(self, user_id):
        self.user_id = user_id
    
    @cache_property(ttl=60)
    def profile(self):
        # 这个属性会被缓存 1 分钟
        return db.query(Profile).filter_by(user_id=self.user_id).first()
```

## 性能优化建议

### 1. 静态文件服务

- 启用 Gzip 压缩，减少传输大小
- 设置合理的缓存时间（max_age）
- 使用 CDN 加速静态资源
- 配置 ETag 和 Last-Modified，支持条件请求

### 2. 性能监控

- 设置合理的慢请求阈值
- 定期检查性能统计信息
- 关注错误率和平均响应时间
- 导出性能数据进行分析

### 3. 缓存策略

- 为频繁调用的函数使用缓存
- 设置合理的 TTL，避免数据过期
- 使用键前缀区分不同的缓存数据
- 定期清理缓存，避免内存占用过多

## 测试建议

### 1. 缓存效果测试

```bash
# 第一次访问（会执行函数）
curl http://localhost:8080/cache/function

# 立即再次访问（返回缓存结果）
curl http://localhost:8080/cache/function

# 等待 10 秒后访问（缓存过期，重新执行）
sleep 10 && curl http://localhost:8080/cache/function
```

### 2. 性能监控测试

```bash
# 触发慢请求
curl "http://localhost:8080/test/slow?delay=2.0"

# 查看慢请求列表
curl http://localhost:8080/monitor/slow

# 查看性能统计
curl http://localhost:8080/monitor/stats
```

### 3. 缓存统计测试

```bash
# 查看缓存统计
curl http://localhost:8080/cache/stats

# 清空缓存
curl http://localhost:8080/cache/clear

# 再次查看统计（应该为空）
curl http://localhost:8080/cache/stats
```

## 性能指标

### 静态文件服务

- **缓存命中率**: > 90%（对于重复访问的文件）
- **压缩率**: 60-80%（对于文本文件）
- **响应时间**: < 10ms（对于缓存命中的文件）

### 性能监控

- **性能影响**: < 1%
- **内存占用**: < 10MB（1000 条记录）
- **统计精度**: 毫秒级

### 缓存装饰器

- **性能提升**: 10-100 倍（对于耗时操作）
- **内存占用**: 可配置（默认 1000 条）
- **并发安全**: 线程安全

## 相关文档

- [静态文件服务文档](../../docs/static-files.md)
- [性能监控文档](../../docs/performance-monitoring.md)
- [缓存装饰器文档](../../docs/cache-decorators.md)

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 实现优化的静态文件服务
- 实现请求性能监控
- 实现增强的缓存装饰器
