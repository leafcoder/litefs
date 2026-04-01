# Session 各后端使用示例

本目录包含 Litefs Session 功能的完整使用示例，覆盖所有支持的后端，包括与新路由系统的集成。

## 目录结构

```
12-session-backends/
├── session_backends_example.py  # 命令行示例（5个示例）
└── README.md                    # 本文件
```

## 快速开始

### 1. 命令行示例

运行命令行示例，查看所有 Session 后端的使用场景：

```bash
python examples/12-session-backends/session_backends_example.py
```

**包含的示例：**

1. **直接使用 Database Session**
   - 创建 Database Session 存储
   - 设置、获取、删除 Session
   - 检查 Session 存在性
   - 设置过期时间
   - 查看剩余过期时间

2. **直接使用 Redis Session**
   - 创建 Redis Session 存储
   - 存储复杂数据类型（列表、字典）
   - 基本 Session 操作

3. **直接使用 Memcache Session**
   - 创建 Memcache Session 存储
   - 存储用户偏好设置
   - 基本 Session 操作

4. **使用 Session 工厂**
   - 使用 `SessionFactory` 创建不同类型的 Session
   - 统一的 Session 创建接口

5. **在 Web 应用中使用 Session**
   - 启动 Web 应用
   - 访问 http://localhost:8084/session-demo

### 2. Web 应用示例

运行 Web 示例：

```bash
python examples/12-session-backends/session_backends_example.py
```

然后访问：http://localhost:8084/session-demo

**功能演示：**

- **Session 后端选择**：切换不同的 Session 后端
- **基本操作**：设置、获取、删除 Session 数据
- **计数器示例**：访问计数和点击计数
- **预设场景**：用户登录信息、购物车数据、用户偏好设置
- **Session 信息**：查看 Session ID 和原始数据

## 依赖说明

- **Database Session**：内置支持，无需额外依赖
- **Redis Session**：需要安装 `redis` 包
  ```bash
  pip install redis
  ```
- **Memcache Session**：需要安装 `pymemcache` 或 `python-memcached` 包
  ```bash
  pip install pymemcache
  # 或
  pip install python-memcached
  ```

## 配置说明

### 1. Database Session 配置

```python
from litefs.session import DatabaseSession

session_store = DatabaseSession(
    db_path=":memory:",  # 数据库文件路径，默认为内存数据库
    table_name="sessions",  # 表名
    session_timeout=3600     # Session 超时时间（秒）
)
```

### 2. Redis Session 配置

```python
from litefs.session import RedisSession

session_store = RedisSession(
    host="localhost",      # Redis 服务器地址
    port=6379,            # Redis 服务器端口
    db=0,                 # Redis 数据库编号
    password=None,        # Redis 密码
    key_prefix="session:",  # 键前缀
    session_timeout=3600   # Session 超时时间（秒）
)
```

### 3. Memcache Session 配置

```python
from litefs.session import MemcacheSession

session_store = MemcacheSession(
    servers=["localhost:11211"],  # Memcache 服务器列表
    key_prefix="session:",       # 键前缀
    session_timeout=3600          # Session 超时时间（秒）
)
```

### 4. 使用 Session 工厂

```python
from litefs.session import SessionFactory, SessionBackend

# 创建 Database Session
session_store = SessionFactory.create_session(
    backend=SessionBackend.DATABASE,
    db_path=":memory:",
    session_timeout=3600
)

# 创建 Redis Session
session_store = SessionFactory.create_session(
    backend=SessionBackend.REDIS,
    host="localhost",
    port=6379,
    session_timeout=3600
)

# 创建 Memcache Session
session_store = SessionFactory.create_session(
    backend=SessionBackend.MEMCACHE,
    servers=["localhost:11211"],
    session_timeout=3600
)
```

## 使用场景

### 1. 直接使用 Session

```python
# 创建 Session
session = session_store.create()

# 设置数据
session.data["user_id"] = 123
session.data["username"] = "test_user"

# 保存 Session
session_store.save(session)

# 获取 Session
retrieved_session = session_store.get(session.id)

# 删除 Session
session_store.delete(session.id)
```

### 2. 在 Web 应用中使用 Session

```python
def handler(self):
    # 设置 Session
    self.session["user_id"] = 123
    self.session["username"] = "test_user"
    
    # 获取 Session
    user_id = self.session.get("user_id")
    
    # 删除 Session
    del self.session["user_id"]
    
    # 清除所有 Session
    # self.session.clear()
    
    return f"Hello, {self.session.get('username', 'guest')}!"
```

## 最佳实践

1. **选择合适的后端**：
   - 开发环境：使用默认内存 Session
   - 生产环境：根据需求选择 Database、Redis 或 Memcache

2. **合理设置超时时间**：
   - 登录 Session：30 分钟 - 2 小时
   - 临时数据：5 - 15 分钟

3. **Session 数据管理**：
   - 只存储必要的数据
   - 避免存储大型对象
   - 定期清理过期 Session

4. **安全性**：
   - 不要存储敏感信息（如密码）
   - 使用 HTTPS 保护 Session
   - 考虑使用 Session 签名

## 故障排查

### 1. Redis Session 连接失败
- 检查 Redis 服务器是否运行
- 检查网络连接和防火墙设置
- 验证 Redis 密码是否正确

### 2. Memcache Session 连接失败
- 检查 Memcache 服务器是否运行
- 检查网络连接和防火墙设置
- 验证服务器地址和端口是否正确

### 3. Database Session 错误
- 检查数据库文件权限
- 确保数据库目录存在且可写
- 验证表结构是否正确

## 总结

本示例展示了 Litefs 支持的三种 Session 后端的使用方法，包括：
- **Database Session**：持久化存储，适合需要数据持久化的场景
- **Redis Session**：高性能分布式存储，适合多实例部署
- **Memcache Session**：极高性能，适合临时 Session 数据

通过这些示例，您可以根据应用需求选择合适的 Session 后端，确保数据安全和性能优化。

## 与新路由系统集成

使用新的路由系统定义 Session 相关的路由：

```python
from litefs import Litefs
from litefs.routing import get, post

app = Litefs(
    session_backend='database',
    session_expiration_time=3600
)

@get('/session-demo')
def session_demo_handler(self):
    # Session 演示页面逻辑
    # ...

@get('/get-put')
def get_put_handler(self):
    # 简单的 Session 操作示例
    print(self.session_id, self.session.get('name'))
    self.session['name'] = 'Tomy2'
    self.session.save()
    return 'get put name'

# 注册路由
app.register_routes(session_demo_handler)
app.register_routes(get_put_handler)

app.run()
```

### 访问端点

- **Session 演示页面**：http://localhost:8085/session-demo
- **简单 Session 操作**：http://localhost:8085/get-put
