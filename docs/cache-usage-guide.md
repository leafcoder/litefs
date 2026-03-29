# 缓存使用指南

本文档介绍如何在 Litefs 项目中使用缓存功能。

## 目录

- [概述](#概述)
- [缓存类型](#缓存类型)
- [基本使用](#基本使用)
- [高级用法](#高级用法)
- [最佳实践](#最佳实践)
- [示例代码](#示例代码)

## 概述

Litefs 提供了多种缓存后端，支持内存、树形结构、Redis、数据库和 Memcache 缓存。所有缓存对象通过 `CacheManager` 全局管理，确保在应用生命周期内常驻内存。

## 缓存类型

### 1. MemoryCache（内存缓存）

最快的缓存类型，基于 Python 字典实现。

**特点：**
- 极快的读写速度
- 线程安全
- 支持最大容量限制
- 进程重启后数据丢失

**适用场景：**
- 单机应用
- 临时数据缓存
- 需要最高性能的场景

### 2. TreeCache（树形缓存）

支持自动清理过期数据的缓存。

**特点：**
- 自动清理过期数据
- 支持过期时间设置
- 定期清理机制
- 适合需要自动管理过期数据的场景

**适用场景：**
- 会话数据
- 临时文件缓存
- 需要自动过期的数据

### 3. RedisCache（Redis 缓存）

基于 Redis 的分布式缓存。

**特点：**
- 高性能读写
- 支持分布式部署
- 自动过期清理
- 支持数据持久化
- 支持丰富的数据结构

**适用场景：**
- 分布式系统
- 需要持久化的缓存
- 多实例共享缓存

### 4. DatabaseCache（数据库缓存）### 9. 数据库缓存

基于 SQLite 的持久化缓存。

```python
from litefs.cache import DatabaseCache
import json

# 内存数据库缓存（进程重启数据丢失）
cache = DatabaseCache(
    db_path=":memory:",
    table_name="cache",
    expiration_time=3600
)

# 文件数据库缓存（持久化存储）
persistent_cache = DatabaseCache(
    db_path="/path/to/cache.db",
    table_name="cache",
    expiration_time=3600
)

# 基本操作
cache.put("key1", "value1")
value = cache.get("key1")

# 键操作
exists = cache.exists("key1")
cache.delete("key1")

# 过期时间管理
ttl = cache.ttl("key1")
cache.expire("key1", 7200)

# 批量操作
cache.set_many({
    "user:1": '{"id": 1, "name": "张三"}',
    "user:2": '{"id": 2, "name": "李四"}'
})
values = cache.get_many(["user:1", "user:2"])
cache.delete_many(["user:1", "user:2"])

# 复杂数据类型
user_data = {"id": 100, "name": "管理员", "roles": ["admin"]}
cache.put("admin:user", json.dumps(user_data))
retrieved = json.loads(cache.get("admin:user"))

# 清除所有缓存
cache.clear()
cache.close()
```

**数据库缓存特点：**
- 支持内存数据库（`:memory:`）和文件数据库
- 支持键存在检查 (`exists`)
- 支持过期时间管理 (`ttl`, `expire`)
- 支持批量操作 (`set_many`, `get_many`, `delete_many`)
- 支持复杂数据类型（需 JSON 序列化）
- 文件数据库支持持久化存储

**适用场景：**
- 需要持久化的缓存
- 单机应用
- 不想额外安装 Redis 的场景

### 5. MemcacheCache（Memcache 缓存）

基于 Memcache 的分布式缓存。

```python
from litefs.cache import MemcacheCache
import json

cache = MemcacheCache(
    servers=["localhost:11211"],
    key_prefix="litefs:",
    expiration_time=3600
)

# 基本操作
cache.put("key1", "value1")
value = cache.get("key1")

# 更新缓存
cache.put("key1", "updated_value")

# 键操作
exists = cache.exists("key1")
cache.delete("key1")

# 过期时间管理
cache.put("temp_key", "temp_value")
ttl = cache.ttl("temp_key")
cache.expire("temp_key", 7200)

# 批量操作
cache.set_many({
    "user:1": '{"id": 1, "name": "张三"}',
    "user:2": '{"id": 2, "name": "李四"}'
})
values = cache.get_many(["user:1", "user:2"])
cache.delete_many(["user:1", "user:2"])

# 复杂数据类型
user_data = {"id": 100, "name": "管理员", "roles": ["admin"]}
cache.put("admin:user", json.dumps(user_data))
retrieved = json.loads(cache.get("admin:user"))

# 缓存统计
print(f"缓存大小: {len(cache)}")

# 清除所有缓存
cache.clear()
cache.close()
```

**Memcache 缓存特点：**
- 支持键存在检查 (`exists`)
- 支持过期时间管理 (`ttl`, `expire`)
- 支持批量操作 (`set_many`, `get_many`, `delete_many`)
- 支持复杂数据类型（需 JSON 序列化）
- 极高性能，适合高并发场景
- 支持分布式部署

**适用场景：**
- 高并发场景
- 分布式系统
- 需要极高性能的缓存

## 基本使用

### 1. 创建缓存实例

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

### 2. 基本操作

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

### 3. 在 Litefs 应用中使用

```python
from litefs import Litefs

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

### 1. 全局缓存管理器

使用 `CacheManager` 确保缓存对象常驻内存，在多个实例间共享。

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

# 使用便捷函数
session_cache = CacheManager.get_session_cache(max_size=1000000)
file_cache = CacheManager.get_file_cache()
```

### 2. Redis 缓存高级操作

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

# 复杂数据类型
user_data = {"id": 100, "name": "管理员", "roles": ["admin"]}
cache.put("admin:user", json.dumps(user_data))
retrieved = json.loads(cache.get("admin:user"))

# 缓存统计
print(f"缓存大小: {len(cache)}")

# 清除所有缓存
cache.clear()
cache.close()
```

**Redis 缓存特点：**
- 支持键存在检查 (`exists`)
- 支持过期时间管理 (`ttl`, `expire`)
- 支持批量操作 (`set_many`, `get_many`, `delete_many`)
- 支持复杂数据类型（需 JSON 序列化）
- 支持分布式部署

### 3. 缓存复杂数据类型

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

# 缓存字符串
cache.put("html", "<html>Hello</html>")

# 缓存数字
cache.put("counter", 100)
```

## 最佳实践

### 1. 使用命名空间组织缓存键

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

### 2. 缓存计算结果

```python
def expensive_calculation(n):
    return sum(range(n))

# 先检查缓存
result = cache.get("calc:100")
if result is None:
    result = expensive_calculation(100)
    cache.put("calc:100", result)
```

### 3. 缓存数据库查询结果

```python
# 缓存查询结果
users = cache.get("db:query:users")
if users is None:
    users = db.query("SELECT * FROM users")
    cache.put("db:query:users", users)
```

### 4. 设置合理的过期时间

```python
# 短期缓存（5分钟）
cache.put("temp_data", data, expiration=300)

# 中期缓存（1小时）
cache.put("user_data", data, expiration=3600)

# 长期缓存（1天）
cache.put("config_data", data, expiration=86400)
```

### 5. 定期清理缓存

```python
# 删除单个缓存
cache.delete("old_key")

# 清除所有缓存
cache.clear()

# 使用全局管理器重置缓存
CacheManager.reset_cache("my_app_cache")
```

## 示例代码

### 运行命令行示例

```bash
# 运行缓存使用示例
python examples/11-cache-usage/cache_usage_example.py
```

### 运行 Web 示例

```bash
# 启动 Web 服务器
python examples/11-cache-usage/cache_usage_web_example.py

# 访问浏览器
# http://localhost:8080/cache-demo
```

### 示例功能

命令行示例包含以下功能：
1. **基本内存缓存使用** - MemoryCache 的基本操作
2. **树形缓存（支持自动过期）** - TreeCache 的自动过期功能
3. **使用缓存工厂创建缓存** - CacheFactory 统一创建接口
4. **全局缓存管理器** - CacheManager 确保缓存常驻内存
5. **在 Litefs 应用中使用缓存** - 应用内置缓存的使用
6. **缓存复杂数据类型** - 字典、列表等复杂数据
7. **缓存最佳实践** - 命名空间、缓存计算结果等
8. **Redis 缓存高级用法** - 完整 Redis 缓存功能演示
9. **数据库缓存** - SQLite 内存和文件缓存
10. **Memcache 缓存** - Memcache 缓存功能演示
11. **在多个 Litefs 实例间共享缓存** - 验证全局缓存共享

Web 示例包含以下功能：
1. 基本缓存操作（设置、获取、删除）
2. 用户数据缓存
3. 商品列表缓存
4. 系统配置缓存
5. 缓存数据展示

## 注意事项

1. **缓存常驻内存**：使用 `CacheManager` 确保缓存对象在应用生命周期内常驻内存
2. **线程安全**：所有缓存实现都是线程安全的，可以在多线程环境中使用
3. **容量限制**：`MemoryCache` 有最大容量限制，超过限制会自动清理最旧的数据
4. **过期管理**：`TreeCache`、`RedisCache`、`DatabaseCache` 支持自动过期清理
5. **连接管理**：使用 `RedisCache`、`DatabaseCache`、`MemcacheCache` 后记得关闭连接
6. **数据序列化**：缓存复杂数据类型时，确保数据可以被序列化

## 性能优化建议

1. **选择合适的缓存类型**：
   - 单机应用优先使用 `MemoryCache`
   - 分布式系统使用 `RedisCache` 或 `MemcacheCache`
   - 需要持久化使用 `DatabaseCache`

2. **设置合理的容量**：
   - `MemoryCache` 根据内存大小设置 `max_size`
   - 避免缓存过大的数据

3. **使用命名空间**：
   - 使用冒号分隔的命名空间组织缓存键
   - 便于管理和清理

4. **定期清理**：
   - 设置合理的过期时间
   - 定期清理不再使用的缓存

5. **监控缓存命中率**：
   - 记录缓存命中和未命中的次数
   - 根据命中率调整缓存策略

## 相关文档

- [缓存后端文档](./cache-backends.md)
- [API 文档](./api.md)
- [配置指南](./configuration.md)
