# 配置管理

## 配置来源

Litefs 支持多种配置来源，按优先级从高到低排列：

1. **代码配置** - 通过代码直接设置配置项
2. **环境变量** - 通过环境变量设置配置（前缀：``LITEFS_``）
3. **配置文件** - 通过 YAML、JSON 或 TOML 文件设置配置
4. **默认配置** - 系统内置的默认值

## 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|---------|------|
| ``host`` | str | ``localhost`` | 服务器监听地址 |
| ``port`` | int | ``9090`` | 服务器监听端口 |
| ``debug`` | bool | ``false`` | 调试模式 |
| ``log`` | str | ``./default.log`` | 日志文件路径 |
| ``listen`` | int | ``1024`` | 服务器监听队列大小 |
| ``max_request_size`` | int | ``10485760`` | 最大请求体大小（字节，默认 10MB） |
| ``max_upload_size`` | int | ``52428800`` | 最大上传文件大小（字节，默认 50MB） |
| ``config_file`` | str | ``None`` | 配置文件路径 |
| ``session_backend`` | str | ``memory`` | 会话后端（memory/redis/database/memcache） |
| ``session_expiration_time`` | int | ``3600`` | 会话过期时间（秒） |
| ``session_name`` | str | ``litefs_session`` | 会话 cookie 名称 |
| ``session_secure`` | bool | ``false`` | 是否使用安全 cookie |
| ``session_http_only`` | bool | ``true`` | 是否仅 HTTP 访问 cookie |
| ``session_same_site`` | str | ``Lax`` | SameSite 策略（Strict, Lax, None） |
| ``cache_backend`` | str | ``tree`` | 缓存后端（memory, tree, redis, database, memcache） |

## 使用方法

### 代码配置

```python
from litefs.core import Litefs

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    max_request_size=20971520,
)

app.run()
```

### 配置文件

创建 ``config.yaml``：

```yaml
host: localhost
port: 9090
debug: false
log: ./default.log
listen: 1024
max_request_size: 10485760
max_upload_size: 52428800
session_backend: memory
session_expiration_time: 3600
session_name: my_session
session_secure: false
session_http_only: true
session_same_site: Lax
cache_backend: tree
```

使用配置文件：

```python
from litefs.core import Litefs

app = Litefs(config_file='config.yaml')
app.run()
```

### 环境变量

```bash
export LITEFS_HOST=0.0.0.0
export LITEFS_PORT=8080
export LITEFS_DEBUG=true
export LITEFS_MAX_REQUEST_SIZE=20971520
```

## 相关文档

* :doc:`getting-started` - 快速开始
* :doc:`routing-guide` - 路由系统
* :doc:`middleware-guide` - 中间件
* :doc:`wsgi-deployment` - WSGI 部署
