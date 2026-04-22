# 缓存系统

## 缓存类型

### MemoryCache（内存缓存）

最快的缓存类型，基于 Python 字典实现。

**特点：**
* 极快的读写速度
* 线程安全
* 支持最大容量限制
* 进程重启后数据丢失

**适用场景：**
* 单机应用
* 临时数据缓存
* 需要最高性能的场景

### TreeCache（树形缓存）

支持自动清理过期数据的缓存。

**特点：**
* 自动清理过期数据
* 支持过期时间设置
* 定期清理机制
* 适合需要自动管理过期数据的场景

**适用场景：**
* 会话数据
* 临时文件缓存
* 需要自动过期的数据

### RedisCache（Redis 缓存）

基于 Redis 的分布式缓存。

**特点：**
* 高性能读写
* 支持分布式部署
* 自动过期清理
* 支持数据持久化
* 支持丰富的数据结构

**适用场景：**
* 分布式系统
* 需要持久化的缓存
* 多实例共享缓存

### DatabaseCache（数据库缓存）

基于 SQLite 的持久化缓存。

**特点：**
* 支持内存数据库（``:memory:``）和文件数据库
* 支持键存在检查 (``exists``)
* 支持过期时间管理 (``ttl``, ``expire``)
* 支持批量操作 (``set_many``, ``get_many``, ``delete_many``)
* 支持复杂数据类型（需 JSON 序列化）
* 文件数据库支持持久化存储

**适用场景：**
* 需要持久化的缓存
* 单机应用
* 不想额外安装 Redis 的场景

### MemcacheCache（Memcache 缓存）

基于 Memcache 的分布式缓存。

**特点：**
* 支持键存在检查 (``exists``)
* 支持过期时间管理 (``ttl``, ``expire``)
* 支持批量操作 (``set_many``, ``get_many``, ``delete_many``)
* 支持复杂数据类型（需 JSON 序列化）
* 极高性能，适合高并发场景
* 支持分布式部署

**适用场景：**
* 高并发场景
* 分布式系统
* 需要极高性能的缓存

## 基本使用

### 创建缓存实例

```python
from litefs.cache import MemoryCache, TreeCache, CacheFactory, CacheBackend

# 直接创建内存缓存
cache = MemoryCache(max_size=10000)

# 直接创建树形缓存
cache = TreeCache(clean_period=60, expiration_time=3600)

# 使用工厂创建缓存
cache = CacheFactory.create_cache(
    backend=CacheBackend.MEMORY,
    max_size=10000
)
```

### 基本操作

```python
# 设置缓存
cache.put("key1", "value1")
cache.put("user:1", {"id": 1, "name": "张三"})

# 获取缓存
value = cache.get("key1")
user = cache.get("user:1")

# 删除缓存
cache.delete("key1")

# 检查缓存大小
size = len(cache)
```

### 在 Litefs 应用中使用

```python
from litefs.core import Litefs

# 创建应用实例
app = Litefs(
    host='localhost',
    port=9090,
    webroot='./site'
)

# 使用应用内置的缓存
app.caches.put("config:theme", "dark")
theme = app.caches.get("config:theme")

# 使用会话缓存
app.sessions.put("session:abc", {"user_id": 1})
session = app.sessions.get("session:abc")

# 使用文件缓存
app.files.put("/index.html", "<html>Hello</html>")
html = app.files.get("/index.html")
```

## 高级用法

### 全局缓存管理器

使用 ``CacheManager`` 确保缓存对象常驻内存，在多个实例间共享。

```python
from litefs.cache import CacheManager, CacheBackend

# 获取全局缓存实例
cache = CacheManager.get_cache(
    backend=CacheBackend.MEMORY,
    cache_key="my_app_cache",
    max_size=10000
)

# 在不同地方获取同一缓存实例
cache2 = CacheManager.get_cache(
    backend=CacheBackend.MEMORY,
    cache_key="my_app_cache"
)

# cache 和 cache2 是同一实例，数据共享
assert cache is cache2
```

### Redis 缓存高级操作

```python
from litefs.cache import RedisCache
import json

cache = RedisCache(
    host="localhost",
    port=6379,
    db=0,
    key_prefix="litefs:",
    expiration_time=3600
)

# 基本操作
cache.put("key1", "value1")
value = cache.get("key1")

# 更新缓存
cache.put("key1", "updated_value")

# 键操作
exists = cache.exists("key1")  # 检查键是否存在
cache.delete("key1")           # 删除键

# 过期时间管理
cache.put("temp_key", "temp_value")
ttl = cache.ttl("temp_key")    # 查询剩余过期时间
cache.expire("temp_key", 7200) # 设置新的过期时间

# 批量操作
cache.set_many({
    "user:1": '{"id": 1, "name": "张三"}',
    "user:2": '{"id": 2, "name": "李四"}'
})
values = cache.get_many(["user:1", "user:2"])
cache.delete_many(["user:1", "user:2"])
```

### 缓存复杂数据类型

```python
from litefs.cache import MemoryCache

cache = MemoryCache(max_size=10000)

# 缓存字典
user_data = {
    "id": 1,
    "name": "张三",
    "profile": {
        "age": 25,
        "city": "北京"
    }
}
cache.put("user:1", user_data)

# 缓存列表
products = [
    {"id": 1, "name": "商品1", "price": 100},
    {"id": 2, "name": "商品2", "price": 200}
]
cache.put("products", products)
```

## 最佳实践

### 使用命名空间组织缓存键

```python
# 用户数据
cache.put("user:profile:1", {"name": "张三"})
cache.put("user:settings:1", {"theme": "dark"})

# 商品数据
cache.put("product:info:1", {"name": "商品1", "price": 100})
cache.put("product:stock:1", 100)

# 配置数据
cache.put("config:theme", "dark")
cache.put("config:language", "zh-CN")
```

### 缓存计算结果

```python
def expensive_calculation(n):
    return sum(range(n))

# 先检查缓存
result = cache.get("calc:100")
if result is None:
    result = expensive_calculation(100)
    cache.put("calc:100", result)
```

### 缓存数据库查询结果

```python
# 缓存查询结果
users = cache.get("db:query:users")
if users is None:
    users = db.query("SELECT * FROM users")
    cache.put("db:query:users", users)
```

### 设置合理的过期时间

```python
# 短期缓存（5分钟）
cache.put("temp_data", data, expiration=300)

# 中期缓存（1小时）
cache.put("user_data", data, expiration=3600)

# 长期缓存（1天）
cache.put("config_data", data, expiration=86400)
```

### 定期清理缓存

```python
# 删除单个缓存
cache.delete("old_key")

# 清除所有缓存
cache.clear()

# 使用全局管理器重置缓存
CacheManager.reset_cache("my_app_cache")
```

## 性能优化建议

### 选择合适的缓存类型

* **单机应用**：优先使用 ``MemoryCache``
* **分布式系统**：使用 ``RedisCache`` 或 ``MemcacheCache``
* **需要持久化**：使用 ``DatabaseCache``

### 设置合理的容量

* ``MemoryCache`` 根据内存大小设置 ``max_size``
* 避免缓存过大的数据

### 使用命名空间

* 使用冒号分隔的命名空间组织缓存键
* 便于管理和清理

### 定期清理

* 设置合理的过期时间
* 定期清理不再使用的缓存

### 监控缓存命中率

* 记录缓存命中和未命中的次数
* 根据命中率调整缓存策略

## 相关文档

* :doc:`getting-started` - 快速开始
* :doc:`routing-guide` - 路由系统
* :doc:`middleware-guide` - 中间件
* :doc:`wsgi-deployment` - WSGI 部署
