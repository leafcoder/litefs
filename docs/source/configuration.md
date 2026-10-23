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
| ``max_connections`` | int | ``1024`` | 原生服务器最大并发连接数，达到上限后新连接被快速拒绝（``None`` 表示不限制） |
| ``idle_read_timeout`` | float | ``30.0`` | 原生服务器空闲读超时（秒），连接阻塞等待读数据超时后断开（slowloris 防护；0/``None`` 禁用） |
| ``websocket_max_message_size`` | int | ``1048576`` | WebSocket 单条消息（帧负载）上限（字节），超限回 1009 关闭帧并断连 |
| ``request_queue_size`` | int | ``2048`` | 监听队列（listen backlog）长度，内核会截断到 ``net.core.somaxconn`` |
| ``config_file`` | str | ``None`` | 配置文件路径 |
| ``session_backend`` | str | ``memory`` | 会话后端（memory/redis/database/memcache） |
| ``session_expiration_time`` | int | ``3600`` | 会话过期时间（秒） |
| ``session_name`` | str | ``litefs_session`` | 会话 cookie 名称 |
| ``session_secure`` | bool | ``环境感知`` | 是否使用安全 cookie（生产环境默认 True，开发环境默认 False） |
| ``session_http_only`` | bool | ``true`` | 是否仅 HTTP 访问 cookie |
| ``session_same_site`` | str | ``Lax`` | SameSite 策略（Strict, Lax, None） |
| ``cache_backend`` | str | ``tree`` | 缓存后端（memory, tree, redis, database, memcache） |
| ``middleware`` | list | ``None`` | 中间件挂载列表（应用创建时按此列表自动挂载，支持内置名称与自定义模块路径，见 :doc:`middleware-guide`；未配置不挂载，``litefs runserver`` 未配置时默认启用全部） |
| ``middleware_options`` | dict | ``None`` | 中间件构造参数（以 ``middleware`` 条目原文为键的字典，仅支持配置文件与代码方式） |
| ``cors`` | dict | ``None`` | ``CORSMiddleware`` 构造参数（``middleware`` 含 ``cors`` 时生效） |
| ``health_check`` | dict | ``None`` | ``HealthCheck`` 构造参数（``middleware`` 含 ``health`` 时生效） |

## 环境感知配置

Litefs 支持环境感知配置，根据运行环境自动调整安全设置。

### session_secure 配置

``session_secure`` 配置项支持环境感知：

* **生产环境**（``debug=False``）：默认 ``True``，强制使用 HTTPS
* **开发环境**（``debug=True``）：默认 ``False``，允许 HTTP（便于本地开发）

```python
from litefs.core import Litefs

# 生产环境 - session_secure 自动设置为 True
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=False  # 生产环境
)

# 开发环境 - session_secure 自动设置为 False
app = Litefs(
    host='localhost',
    port=9090,
    debug=True  # 开发环境
)

# 强制指定（不推荐）
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=False,
    session_secure=False  # 强制禁用（不安全）
)
```

**安全建议：**

1. **生产环境**必须使用 HTTPS 并设置 ``session_secure=True``
2. **开发环境**可以使用 HTTP 和 ``session_secure=False``
3. 不要在生产环境强制设置 ``session_secure=False``
4. 系统会在不安全配置时发出警告

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

## 中间件配置

中间件的挂载由 ``middleware`` 配置项驱动：**应用创建时**（``Litefs(...)``
构造阶段）按该列表自动挂载，列表顺序即挂载顺序，配置为 ``None`` 或空列表时
不挂载任何中间件。条目支持两种形式：

- **内置中间件名称**：``logging`` / ``security`` / ``cors`` / ``health``
- **自定义中间件模块路径**：如 ``myapp.middleware.ThrottleMiddleware``，
  应用创建时动态导入（导入目标必须是类，建议继承
  ``litefs.middleware.Middleware``）

```yaml
# config.yaml
middleware:
  - logging
  - security
  - cors
  - health
  - myapp.middleware.ThrottleMiddleware   # 自定义中间件
```

也可通过环境变量覆盖（逗号分隔，内置名称与模块路径可混用）：

```bash
export LITEFS_MIDDLEWARE=logging,cors
```

中间件构造参数的注入方式：

- **内置中间件**：同名配置段（``cors`` / ``health`` 对应 ``health_check``），
  或统一使用 ``middleware_options``
- **自定义中间件**：``middleware_options`` 配置段，以 ``middleware`` 条目
  原文为键

```yaml
cors:
  allow_origins: ["*"]
  allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  allow_headers: ["Content-Type", "Authorization"]
  allow_credentials: false
  max_age: 3600

health_check:
  path: "/health"
  ready_path: "/health/ready"

middleware_options:
  myapp.middleware.ThrottleMiddleware:
    rate: 100
    period: 60
```

包含未知的内置中间件名称（不含 ``.`` 且不在白名单内）时应用创建直接抛出
``ValueError``（``litefs runserver`` 会预校验并以错误信息退出）；自定义
模块路径无法导入或目标不是类时同样抛出 ``ValueError``。

``litefs runserver`` 未指定 ``--config`` 时自动发现当前目录的配置文件
（``config.yaml`` / ``config.yml`` / ``config.json`` / ``config.toml``），
对 ``config.yaml`` 的中间件修改直接生效。

## 相关文档

* :doc:`getting-started` - 快速开始
* :doc:`routing-guide` - 路由系统
* :doc:`middleware-guide` - 中间件
* :doc:`wsgi-deployment` - WSGI 部署
