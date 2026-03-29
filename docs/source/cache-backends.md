# 缓存后端

Litefs 支持多种缓存后端，包括内存、树形结构、Redis、数据库和 Memcache。

## 支持的后端

### Memory Cache

内存缓存，使用字典实现，适合单机应用。

**特点：**
- 最快的读写速度
- 线程安全
- 支持最大容量限制
- 进程重启后数据丢失

**使用示例：**

```python
from litefs.cache import MemoryCache

# 创建内存缓存
cache = MemoryCache(max_size=10000)

# 存储数据
cache.put("key1", "value1")
cache.put("key2", {"data": "complex"})

# 获取数据
value = cache.get("key1")
print(value)  # 输出: value1

# 删除数据
cache.delete("key1")

# 检查键是否存在
exists = cache.exists("key2")
print(exists)  # 输出: True
```

### Tree Cache

树形缓存，支持自动清理过期数据。

**特点：**
- 自动清理过期数据
- 支持过期时间设置
- 定期清理机制
- 适合需要自动管理过期数据的场景

**使用示例：**

```python
from litefs.cache import TreeCache

# 创建树形缓存
cache = TreeCache(
    clean_period=60,          # 清理周期（秒）
    expiration_time=3600      # 默认过期时间（秒）
)

# 存储数据
cache.put("key1", "value1", expiration=1800)

# 获取数据
value = cache.get("key1")
```

### Redis Cache

使用 Redis 作为缓存后端，提供高性能的分布式缓存支持。

**特点：**
- 高性能读写
- 支持分布式部署
- 自动过期清理
- 支持数据持久化
- 支持丰富的数据结构

**使用示例：**

```python
from litefs.cache import RedisCache

# 创建 Redis 缓存
cache = RedisCache(
    host="localhost",
    port=6379,
    db=0,
    password=None,
    key_prefix="litefs:",
    expiration_time=3600
)

# 存储数据
cache.put("key1", "value1")
cache.put("key2", {"data": "complex"})

# 获取数据
value = cache.get("key1")

# 批量操作
cache.set_many({"key3": "value3", "key4": "value4"})
values = cache.get_many(["key1", "key2", "key3"])

# 删除数据
cache.delete("key1")
cache.delete_many(["key2", "key3"])

# 模式匹配删除
cache.delete_pattern("user:*")

# 检查键是否存在
exists = cache.exists("key1")

# 设置过期时间
cache.expire("key1", 7200)

# 获取剩余过期时间
ttl = cache.ttl("key1")

# 清空所有缓存
cache.clear()

# 获取缓存大小
size = len(cache)

# 关闭连接
cache.close()
```

### Database Cache

使用 SQLite 数据库作为缓存后端，提供持久化的缓存支持。

**特点：**
- 持久化存储，重启后数据不丢失
- 支持过期时间自动清理
- 支持复杂的数据类型
- 线程安全
- 支持批量操作

**使用示例：**

```python
from litefs.cache import DatabaseCache

# 创建数据库缓存
cache = DatabaseCache(
    db_path="/path/to/cache.db",  # 数据库文件路径，默认为内存数据库
    table_name="cache",            # 表名
    expiration_time=3600           # 默认过期时间（秒）
)

# 存储数据
cache.put("key1", "value1")
cache.put("key2", {"data": "complex"}, expiration=7200)

# 获取数据
value = cache.get("key1")

# 批量操作
cache.set_many({"key3": "value3", "key4": "value4"})
values = cache.get_many(["key1", "key2", "key3"])

# 删除数据
cache.delete("key1")
cache.delete_many(["key2", "key3"])

# 模式匹配删除（支持 SQL LIKE 语法）
cache.delete_pattern("user:%")

# 检查键是否存在
exists = cache.exists("key1")

# 设置过期时间
cache.expire("key1", 7200)

# 获取剩余过期时间
ttl = cache.ttl("key1")

# 清空所有缓存
cache.clear()

# 获取缓存大小
size = len(cache)

# 关闭连接
cache.close()

# 使用上下文管理器
with DatabaseCache(db_path="/path/to/cache.db") as cache:
    cache.put("key1", "value1")
    value = cache.get("key1")
# 连接自动关闭
```

### Memcache Cache

使用 Memcache 作为缓存后端，提供高性能的分布式缓存支持。

**特点：**
- 极高性能
- 支持分布式部署
- 内存存储，访问速度快
- 适合临时缓存数据
- 支持批量操作

**使用示例：**

```python
from litefs.cache import MemcacheCache

# 创建 Memcache 缓存
cache = MemcacheCache(
    servers=["localhost:11211"],
    key_prefix="litefs:",
    expiration_time=3600
)

# 存储数据
cache.put("key1", "value1")
cache.put("key2", {"data": "complex"})

# 获取数据
value = cache.get("key1")

# 批量操作
cache.set_many({"key3": "value3", "key4": "value4"})
values = cache.get_many(["key1", "key2", "key3"])

# 删除数据
cache.delete("key1")
cache.delete_many(["key2", "key3"])

# 检查键是否存在
exists = cache.exists("key1")

# 设置过期时间
cache.expire("key1", 7200)

# 关闭连接
cache.close()
```

**注意：** Memcache 不支持以下功能：
- 模式匹配删除（`delete_pattern`）
- TTL 查询（`ttl` 返回 -1）
- 键数量统计（`__len__` 返回 0）
- 清空所有缓存（`clear`）

## 缓存工厂

使用 `CacheFactory` 可以方便地创建不同类型的缓存实例。

```python
from litefs.cache import CacheFactory, CacheBackend

# 创建 Memory Cache
cache = CacheFactory.create_cache(
    backend=CacheBackend.MEMORY,
    max_size=10000
)

# 创建 Tree Cache
cache = CacheFactory.create_cache(
    backend=CacheBackend.TREE,
    clean_period=60,
    expiration_time=3600
)

# 创建 Redis Cache
cache = CacheFactory.create_cache(
    backend=CacheBackend.REDIS,
    host="localhost",
    port=6379,
    db=0,
    key_prefix="litefs:",
    expiration_time=3600
)

# 创建 Database Cache
cache = CacheFactory.create_cache(
    backend=CacheBackend.DATABASE,
    db_path="/path/to/cache.db",
    table_name="cache",
    expiration_time=3600
)

# 创建 Memcache Cache
cache = CacheFactory.create_cache(
    backend=CacheBackend.MEMCACHE,
    servers=["localhost:11211"],
    key_prefix="litefs:",
    expiration_time=3600
)
```

## API 参考

### RedisCache

```python
class RedisCache:
    def __init__(
        self,
        redis_client=None,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        key_prefix: str = "litefs:",
        expiration_time: int = 3600,
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
- `expiration_time`: 默认过期时间（秒）
- `**kwargs`: 其他 Redis 连接参数

**方法：**
- `put(key: str, val: Any, expiration: Optional[int] = None) -> None`: 存储值到缓存
- `get(key: str) -> Optional[Any]`: 从缓存获取值
- `delete(key: str) -> None`: 从缓存删除值
- `delete_pattern(pattern: str) -> int`: 删除匹配模式的键
- `exists(key: str) -> bool`: 检查键是否存在
- `expire(key: str, expiration: int) -> bool`: 设置键的过期时间
- `ttl(key: str) -> int`: 获取键的剩余过期时间
- `clear() -> None`: 清空所有缓存
- `__len__() -> int`: 获取缓存中的键数量
- `get_many(keys: list) -> dict`: 批量获取值
- `set_many(mapping: dict, expiration: Optional[int] = None) -> None`: 批量存储值
- `delete_many(keys: list) -> None`: 批量删除键
- `close() -> None`: 关闭 Redis 连接

### DatabaseCache

```python
class DatabaseCache:
    def __init__(
        self,
        db_path: str = ":memory:",
        table_name: str = "cache",
        expiration_time: int = 3600,
        **kwargs
    )
```

**参数：**
- `db_path`: 数据库文件路径，默认为内存数据库
- `table_name`: 缓存表名
- `expiration_time`: 默认过期时间（秒）
- `**kwargs`: 其他数据库连接参数

**方法：** 与 `RedisCache` 相同

### MemcacheCache

```python
class MemcacheCache:
    def __init__(
        self,
        memcache_client=None,
        servers: list = ["localhost:11211"],
        key_prefix: str = "litefs:",
        expiration_time: int = 3600,
        **kwargs
    )
```

**参数：**
- `memcache_client`: Memcache 客户端实例（如果提供，则忽略其他连接参数）
- `servers`: Memcache 服务器列表
- `key_prefix`: 键前缀
- `expiration_time`: 默认过期时间（秒）
- `**kwargs`: 其他 Memcache 连接参数

**方法：** 与 `RedisCache` 相同（但不支持 `delete_pattern`、`ttl`、`__len__`、`clear`）

## 配置示例

在配置文件中设置缓存后端：

```toml
[cache]
backend = "redis"  # 或 "memory", "tree", "database", "memcache"

[cache.redis]
host = "localhost"
port = 6379
db = 0
password = ""
key_prefix = "litefs:"
expiration_time = 3600

[cache.database]
path = "/path/to/cache.db"
table = "cache"
expiration_time = 3600

[cache.memcache]
servers = ["localhost:11211"]
key_prefix = "litefs:"
expiration_time = 3600

[cache.memory]
max_size = 10000

[cache.tree]
clean_period = 60
expiration_time = 3600
```

## 性能考虑

### 选择建议

- **Memory Cache**: 适合单机应用，对性能要求极高的场景
- **Tree Cache**: 适合需要自动管理过期数据的场景
- **Redis Cache**: 适合需要高性能和分布式部署的场景
- **Database Cache**: 适合需要持久化存储的场景
- **Memcache Cache**: 适合对性能要求极高且不需要持久化的场景

### 性能对比

| 后端 | 读取速度 | 写入速度 | 持久化 | 分布式 | 自动过期 |
|------|---------|---------|--------|--------|---------|
| Memory | 极快 | 极快 | 否 | 否 | 否 |
| Tree | 快 | 快 | 否 | 否 | 是 |
| Redis | 快 | 快 | 可选 | 是 | 是 |
| Database | 中 | 中 | 是 | 否 | 是 |
| Memcache | 极快 | 极快 | 否 | 是 | 是 |

## 注意事项

1. **Redis Cache**:
   - 需要安装 Redis 服务器
   - 需要安装 redis-py 包：`pip install redis`
   - 建议配置 Redis 持久化以防止数据丢失

2. **Database Cache**:
   - 使用 SQLite，适合中小规模应用
   - 需要定期清理过期缓存
   - 文件路径需要有写入权限

3. **Memcache Cache**:
   - 需要安装 Memcache 服务器
   - 需要安装 pymemcache 或 python-memcached 包
   - 数据存储在内存中，重启后丢失
   - 不支持 TTL 查询和模式匹配

## 上下文管理器

所有缓存后端都支持上下文管理器，可以自动关闭连接：

```python
# Redis Cache
with RedisCache(host="localhost", port=6379) as cache:
    cache.put("key1", "value1")
    value = cache.get("key1")

# Database Cache
with DatabaseCache(db_path="/path/to/cache.db") as cache:
    cache.put("key1", "value1")
    value = cache.get("key1")

# Memcache Cache
with MemcacheCache(servers=["localhost:11211"]) as cache:
    cache.put("key1", "value1")
    value = cache.get("key1")
```