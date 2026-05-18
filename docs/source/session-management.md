# 会话管理

## 会话后端

### Database Session

使用 SQLite 数据库存储 Session 数据，提供持久化的 Session 支持。

**特点：**
* 持久化存储，重启后数据不丢失
* 支持过期时间自动清理
* 支持复杂的数据类型
* 线程安全
* **连接池支持**：基于 SQLAlchemy 的高性能连接池
* **并发优化**：支持多线程并发访问

**连接池配置：**

DatabaseSession 支持通过 SQLAlchemy 连接池优化性能，避免频繁创建和关闭数据库连接：

```python
from litefs.session import DatabaseSession

# 使用默认连接池配置
session_store = DatabaseSession(
    db_path="/path/to/sessions.db",
    table_name="sessions",
    session_timeout=3600
)

# 自定义连接池配置
session_store = DatabaseSession(
    db_path="/path/to/sessions.db",
    pool_size=10,           # 连接池大小（默认 5）
    max_overflow=20,        # 最大溢出连接数（默认 10）
    pool_timeout=60,        # 获取连接超时时间（默认 30 秒）
    pool_recycle=1800,      # 连接回收时间（默认 3600 秒）
    use_pool=True           # 是否使用连接池（默认 True）
)

# 禁用连接池（使用传统连接方式）
session_store = DatabaseSession(
    db_path="/path/to/sessions.db",
    use_pool=False
)
```

**连接池参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| ``pool_size`` | 5 | 连接池保持的连接数 |
| ``max_overflow`` | 10 | 允许的最大溢出连接数 |
| ``pool_timeout`` | 30 | 获取连接的超时时间（秒） |
| ``pool_recycle`` | 3600 | 连接回收时间（秒） |
| ``use_pool`` | True | 是否使用连接池 |

**性能提升：**

使用连接池后，DatabaseSession 的性能显著提升：
- 减少数据库连接创建/关闭开销
- 支持高并发访问
- 避免连接泄漏
- 自动管理连接生命周期

**使用示例：**

```python
from litefs.session import DatabaseSession

# 创建 Session 存储
session_store = DatabaseSession(
    db_path="/path/to/sessions.db",
    table_name="sessions",
    session_timeout=3600,
    pool_size=10,
    max_overflow=20
)

# 创建 Session
session = session_store.create()
session.data["user_id"] = 123
session.data["username"] = "test_user"

# 保存 Session
session_store.save(session)

# 获取 Session
retrieved_session = session_store.get(session.id)
print(retrieved_session.data["username"])  # 输出: test_user

# 删除 Session
session_store.delete(session.id)

# 关闭连接
session_store.close()
```

### Redis Session

使用 Redis 存储 Session 数据，提供高性能的分布式 Session 支持。

**特点：**
* 高性能读写
* 支持分布式部署
* 自动过期清理
* 支持数据持久化

**使用示例：**

```python
from litefs.session import RedisSession

# 创建 Session 存储
session_store = RedisSession(
    host="localhost",
    port=6379,
    db=0,
    password=None,
    key_prefix="session:",
    session_timeout=3600
)

# 使用方式与 DatabaseSession 相同
session = session_store.create()
session.data["user_id"] = 123
session_store.save(session)

# 获取 Session
retrieved_session = session_store.get(session.id)
```

### Memcache Session

使用 Memcache 存储 Session 数据，提供高性能的分布式 Session 支持。

**特点：**
* 极高性能
* 支持分布式部署
* 内存存储，访问速度快
* 适合临时 Session 数据

**使用示例：**

```python
from litefs.session import MemcacheSession

# 创建 Session 存储
session_store = MemcacheSession(
    servers=["localhost:11211"],
    key_prefix="session:",
    session_timeout=3600
)

# 使用方式与其他 Session 后端相同
session = session_store.create()
session.data["user_id"] = 123
session_store.save(session)
```

## Session 工厂

使用 ``SessionFactory`` 可以方便地创建不同类型的 Session 实例。

```python
from litefs.session import SessionFactory, SessionBackend

# 创建 Database Session
session_store = SessionFactory.create_session(
    backend=SessionBackend.DATABASE,
    db_path="/path/to/sessions.db",
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

## 配置示例

在配置文件中设置 Session 后端：

```yaml
session:
  backend: "database"  # 或 "redis", "memcache"

session.database:
  path: "/path/to/sessions.db"
  table: "sessions"
  timeout: 3600

session.redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""
  key_prefix: "session:"
  timeout: 3600

session.memcache:
  servers: ["localhost:11211"]
  key_prefix: "session:"
  timeout: 3600
```

## 性能考虑

### 选择建议

* **Database Session**: 适合需要持久化存储的场景，重启后数据不丢失
* **Redis Session**: 适合需要高性能和分布式部署的场景
* **Memcache Session**: 适合对性能要求极高且不需要持久化的场景

### 性能对比

| 后端 | 读取速度 | 写入速度 | 持久化 | 分布式 |
|------|---------|---------|--------|--------|
| Database | 中 | 中 | 是 | 否 |
| Redis | 快 | 快 | 可选 | 是 |
| Memcache | 极快 | 极快 | 否 | 是 |

## 注意事项

1. **Database Session**:
   * 使用 SQLite，适合中小规模应用
   * 需要定期清理过期 Session
   * 文件路径需要有写入权限

2. **Redis Session**:
   * 需要安装 Redis 服务器
   * 需要安装 redis-py 包：``pip install redis``
   * 建议配置 Redis 持久化以防止数据丢失

3. **Memcache Session**:
   * 需要安装 Memcache 服务器
   * 需要安装 pymemcache 或 python-memcached 包
   * 数据存储在内存中，重启后丢失
   * 不支持 TTL 查询和模式匹配

## 上下文管理器

所有 Session 后端都支持上下文管理器，可以自动关闭连接：

```python
with DatabaseSession(db_path="/path/to/sessions.db") as session_store:
    session = session_store.create()
    session.data["user_id"] = 123
    session_store.save(session)
# 连接自动关闭
```

## 相关文档

* :doc:`getting-started` - 快速开始
* :doc:`routing-guide` - 路由系统
* :doc:`middleware-guide` - 中间件
* :doc:`cache-system` - 缓存系统
