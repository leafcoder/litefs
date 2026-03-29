# Session 后端

Litefs 支持多种 Session 后端，包括数据库、Redis 和 Memcache。

## 支持的后端

### Database Session

使用 SQLite 数据库存储 Session 数据，提供持久化的 Session 支持。

**特点：**
- 持久化存储，重启后数据不丢失
- 支持过期时间自动清理
- 支持复杂的数据类型
- 线程安全

**使用示例：**

```python
from litefs.session import DatabaseSession

# 创建 Session 存储
session_store = DatabaseSession(
    db_path="/path/to/sessions.db",  # 数据库文件路径，默认为内存数据库
    table_name="sessions",              # 表名
    session_timeout=3600                 # Session 超时时间（秒）
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
- 高性能读写
- 支持分布式部署
- 自动过期清理
- 支持数据持久化

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
- 极高性能
- 支持分布式部署
- 内存存储，访问速度快
- 适合临时 Session 数据

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

使用 `SessionFactory` 可以方便地创建不同类型的 Session 实例。

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

## API 参考

### DatabaseSession

```python
class DatabaseSession:
    def __init__(
        self,
        db_path: str = ":memory:",
        table_name: str = "sessions",
        session_timeout: int = 3600,
        **kwargs
    )
```

**参数：**
- `db_path`: 数据库文件路径，默认为内存数据库
- `table_name`: Session 表名
- `session_timeout`: Session 默认超时时间（秒）
- `**kwargs`: 其他数据库连接参数

**方法：**
- `create() -> Session`: 创建新的 Session
- `get(session_id: str) -> Optional[Session]`: 获取 Session
- `save(session: Session) -> None`: 保存 Session
- `delete(session_id: str) -> None`: 删除 Session
- `exists(session_id: str) -> bool`: 检查 Session 是否存在
- `expire(session_id: str, expiration: int) -> bool`: 设置 Session 过期时间
- `ttl(session_id: str) -> int`: 获取 Session 剩余过期时间
- `clear() -> None`: 清空所有 Session
- `__len__() -> int`: 获取 Session 数量
- `close() -> None`: 关闭数据库连接

### RedisSession

```python
class RedisSession:
    def __init__(
        self,
        redis_client=None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "session:",
        session_timeout: int = 3600,
        **kwargs
    )
```

**参数：**
- `redis_client`: Redis 客户端实例（如果提供，则忽略其他连接参数）
- `host`: Redis 服务器地址
- `port`: Redis 服务器端口
- `db`: Redis 数据库编号
- `password`: Redis 密码
- `key_prefix`: 键前缀
- `session_timeout`: Session 默认超时时间（秒）
- `**kwargs`: 其他 Redis 连接参数

**方法：** 与 `DatabaseSession` 相同

### MemcacheSession

```python
class MemcacheSession:
    def __init__(
        self,
        memcache_client=None,
        servers: list = ["localhost:11211"],
        key_prefix: str = "session:",
        session_timeout: int = 3600,
        **kwargs
    )
```

**参数：**
- `memcache_client`: Memcache 客户端实例（如果提供，则忽略其他连接参数）
- `servers`: Memcache 服务器列表
- `key_prefix`: 键前缀
- `session_timeout`: Session 默认超时时间（秒）
- `**kwargs`: 其他 Memcache 连接参数

**方法：** 与 `DatabaseSession` 相同

## 配置示例

在配置文件中设置 Session 后端：

```toml
[session]
backend = "database"  # 或 "redis", "memcache"

[session.database]
path = "/path/to/sessions.db"
table = "sessions"
timeout = 3600

[session.redis]
host = "localhost"
port = 6379
db = 0
password = ""
key_prefix = "session:"
timeout = 3600

[session.memcache]
servers = ["localhost:11211"]
key_prefix = "session:"
timeout = 3600
```

## 性能考虑

### 选择建议

- **Database Session**: 适合需要持久化存储的场景，重启后数据不丢失
- **Redis Session**: 适合需要高性能和分布式部署的场景
- **Memcache Session**: 适合对性能要求极高且不需要持久化的场景

### 性能对比

| 后端 | 读取速度 | 写入速度 | 持久化 | 分布式 |
|------|---------|---------|--------|--------|
| Database | 中 | 中 | 是 | 否 |
| Redis | 快 | 快 | 可选 | 是 |
| Memcache | 极快 | 极快 | 否 | 是 |

## 注意事项

1. **Database Session**:
   - 使用 SQLite，适合中小规模应用
   - 需要定期清理过期 Session
   - 文件路径需要有写入权限

2. **Redis Session**:
   - 需要安装 Redis 服务器
   - 需要安装 redis-py 包：`pip install redis`
   - 建议配置 Redis 持久化以防止数据丢失

3. **Memcache Session**:
   - 需要安装 Memcache 服务器
   - 需要安装 pymemcache 或 python-memcached 包
   - 数据存储在内存中，重启后丢失
   - 不支持 TTL 查询和模式匹配

## 上下文管理器

所有 Session 后端都支持上下文管理器，可以自动关闭连接：

```python
with DatabaseSession(db_path="/path/to/sessions.db") as session_store:
    session = session_store.create()
    session.data["user_id"] = 123
    session_store.save(session)
# 连接自动关闭
```