# 缓存使用示例

本目录包含 Litefs 缓存功能的完整使用示例。

## 目录结构

```
11-cache-usage/
├── cache_usage_example.py      # 命令行示例（10个示例）
├── cache_usage_web_example.py  # Web 应用示例
├── site/
│   └── cache_demo.py          # 缓存演示页面
└── README.md                  # 本文件
```

## 快速开始

### 1. 命令行示例

运行命令行示例，查看所有缓存使用场景：

```bash
python examples/11-cache-usage/cache_usage_example.py
```

**包含的示例：**

1. **基本内存缓存使用**
   - 创建内存缓存
   - 设置、获取、删除缓存
   - 查看缓存大小

2. **树形缓存（支持自动过期）**
   - 创建树形缓存
   - 设置清理周期和过期时间
   - 自动清理过期数据

3. **使用缓存工厂创建缓存**
   - 使用 `CacheFactory` 创建不同类型的缓存
   - 统一的缓存创建接口

4. **全局缓存管理器**
   - 使用 `CacheManager` 确保缓存常驻内存
   - 在多个实例间共享缓存
   - 便捷函数：`get_session_cache()`、`get_file_cache()`

5. **在 Litefs 应用中使用缓存**
   - 使用应用内置的缓存
   - `app.caches` - 应用缓存
   - `app.sessions` - 会话缓存
   - `app.files` - 文件缓存

6. **缓存复杂数据类型**
   - 缓存字典、列表、字符串、数字
   - 支持任意 Python 对象

7. **缓存最佳实践**
   - 使用命名空间组织缓存键
   - 缓存计算结果
   - 缓存数据库查询结果
   - 定期清理缓存

8. **Redis 缓存高级用法**
   - 基本操作（设置、获取、更新、删除）
   - 键操作（检查存在、删除）
   - 过期时间管理（TTL、设置过期时间）
   - 批量操作（批量设置、获取、删除）
   - 复杂数据类型（字典、列表）
   - 缓存统计和清除

9. **数据库缓存**
   - 内存数据库缓存
   - 文件数据库缓存（持久化存储）
   - 基本操作和键操作
   - 过期时间管理
   - 批量操作
   - 复杂数据类型支持

10. **Memcache 缓存**
    - 连接到 Memcache 服务器
    - 基本操作和键操作
    - 过期时间管理
    - 批量操作
    - 复杂数据类型支持
    - 缓存统计和清除

11. **在多个 Litefs 实例间共享缓存**
    - 验证缓存在多个实例间共享
    - 确保缓存常驻内存

### 2. Web 应用示例

启动 Web 服务器，通过浏览器交互式体验缓存功能：

```bash
python examples/11-cache-usage/cache_usage_web_example.py
```

然后在浏览器中访问：

```
http://localhost:8080/cache-demo
```

**Web 示例功能：**

- **基本操作**
  - 设置缓存
  - 获取缓存
  - 删除缓存
  - 清除所有缓存

- **用户数据缓存**
  - 设置用户数据
  - 获取用户数据

- **商品列表缓存**
  - 设置商品列表
  - 获取商品列表

- **系统配置缓存**
  - 设置系统配置
  - 获取系统配置

- **缓存数据展示**
  - 查看当前所有缓存
  - 实时更新缓存状态

## 代码示例

### 基本使用

```python
from litefs.cache import MemoryCache

# 创建缓存
cache = MemoryCache(max_size=10000)

# 设置缓存
cache.put("key", "value")

# 获取缓存
value = cache.get("key")

# 删除缓存
cache.delete("key")
```

### 使用全局缓存管理器

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

### 在 Litefs 应用中使用

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
```

### Redis 缓存

```python
from litefs.cache import RedisCache

cache = RedisCache(
    host="localhost",
    port=6379,
    db=0,
    key_prefix="litefs:",
    expiration_time=3600
)

# 基本操作
cache.put("key", "value")
value = cache.get("key")

# 高级操作
cache.expire("key", 7200)
ttl = cache.ttl("key")

cache.close()
```

## 缓存类型对比

| 缓存类型 | 速度 | 持久化 | 分布式 | 适用场景 |
|---------|------|--------|--------|----------|
| MemoryCache | ⭐⭐⭐⭐⭐ | ❌ | ❌ | 单机应用、临时数据 |
| TreeCache | ⭐⭐⭐⭐ | ❌ | ❌ | 会话数据、自动过期 |
| RedisCache | ⭐⭐⭐⭐ | ✅ | ✅ | 分布式系统、持久化 |
| DatabaseCache | ⭐⭐⭐ | ✅ | ❌ | 单机应用、持久化 |
| MemcacheCache | ⭐⭐⭐⭐⭐ | ❌ | ✅ | 高并发、分布式 |

## 最佳实践

1. **使用命名空间组织缓存键**
   ```python
   cache.put("user:profile:1", data)
   cache.put("product:info:1", data)
   ```

2. **缓存计算结果**
   ```python
   result = cache.get("calc:100")
   if result is None:
       result = expensive_calculation(100)
       cache.put("calc:100", result)
   ```

3. **设置合理的过期时间**
   ```python
   # 短期缓存（5分钟）
   cache.put("temp_data", data, expiration=300)

   # 中期缓存（1小时）
   cache.put("user_data", data, expiration=3600)

   # 长期缓存（1天）
   cache.put("config_data", data, expiration=86400)
   ```

4. **定期清理缓存**
   ```python
   # 删除单个缓存
   cache.delete("old_key")

   # 清除所有缓存
   cache.clear()
   ```

## 注意事项

1. **缓存常驻内存**：使用 `CacheManager` 确保缓存对象在应用生命周期内常驻内存
2. **线程安全**：所有缓存实现都是线程安全的
3. **容量限制**：`MemoryCache` 有最大容量限制
4. **过期管理**：部分缓存类型支持自动过期清理
5. **连接管理**：使用外部缓存服务后记得关闭连接

## 相关文档

- [缓存使用指南](../../docs/cache-usage-guide.md)
- [缓存后端文档](../../docs/source/cache-backends.md)
- [API 文档](../../docs/api.md)

## 运行环境

- Python 3.7+
- Litefs 框架

## 可选依赖

- Redis（用于 RedisCache）
- Memcache（用于 MemcacheCache）

## 许可证

MIT License
