# 缓存后端 Web 示例

Litefs 各类缓存后端的 Web 管理界面示例。

## 示例文件

- `cache_backends_web_example.py` - 缓存后端 Web 示例主程序
- `wsgi.py` - WSGI 部署配置
- `site/cache_backends_web.py` - 缓存后端 Web 处理器

## 运行示例

### 开发模式

```bash
python cache_backends_web_example.py
```

访问 http://localhost:8080/cache-backends-web 查看缓存后端管理界面。

### 生产部署

#### 使用 Gunicorn

```bash
gunicorn -w 4 -b :8080 wsgi:application
```

#### 使用 uWSGI

```bash
uwsgi --http :8080 --wsgi-file wsgi.py
```

#### 使用 Waitress

```bash
waitress-serve --port=8080 wsgi:application
```

## 支持的缓存后端

### 1. Memory Cache

基于内存的缓存，最快的读写速度。

**特性：**
- 极快速度
- 线程安全
- 支持容量限制
- 进程重启数据丢失

**适用场景：**
- 单机应用
- 临时数据存储
- 需要极高性能的场景

### 2. Tree Cache

树形结构缓存，支持自动清理过期数据。

**特性：**
- 自动过期清理
- 支持层级访问
- 定期清理机制

**适用场景：**
- 需要自动清理过期数据
- 层级数据结构
- 定期维护需求

### 3. Redis Cache

基于 Redis 的分布式缓存。

**特性：**
- 高性能读写
- 支持分布式
- 自动过期
- 数据持久化

**适用场景：**
- 分布式应用
- 高性能需求
- 需要数据持久化

**配置要求：**
- Redis 服务器需要运行在 localhost:6379
- 需要安装 redis-py 库：`pip install redis`

### 4. Database Cache

基于 SQLite 的持久化缓存。

**特性：**
- 持久化存储
- 自动过期清理
- 支持复杂类型
- 线程安全

**适用场景：**
- 需要持久化存储
- 复杂数据类型
- 需要事务支持

### 5. Memcache Cache

基于 Memcache 的分布式缓存。

**特性：**
- 极高性能
- 支持分布式
- 内存存储
- 访问速度快

**适用场景：**
- 高性能需求
- 临时数据
- 分布式缓存

**配置要求：**
- Memcache 服务器需要运行在 localhost:11211
- 需要安装 python-memcached 库：`pip install python-memcached`

## 缓存操作

### 基本操作

- **设置缓存**：向缓存中添加键值对
- **获取缓存**：从缓存中读取数据
- **删除缓存**：删除指定的缓存键
- **清除所有**：清空当前缓存的所有数据

### 批量操作

- **设置多个缓存**：批量添加多个键值对
- **批量获取**：批量读取多个键的值
- **批量删除**：批量删除多个键

### 高级操作

- **设置带 TTL 的缓存**：设置有过期时间的缓存
- **设置大数据缓存**：测试大容量数据的存储
- **检查键是否存在**：验证键是否在缓存中
- **设置过期时间**：为已存在的键设置过期时间
- **检查 TTL**：查询键的剩余过期时间
- **查看统计**：查看缓存的统计信息

## Web 界面功能

### 缓存类型选择器

页面顶部提供缓存类型选择器，可以快速切换不同的缓存后端进行测试。

### 缓存信息展示

显示当前选中缓存的名称、描述和特性列表。

### 操作按钮

提供所有缓存操作的快捷按钮，点击即可执行相应的缓存操作。

### 缓存数据展示

实时显示当前缓存中的所有数据，包括键、值和类型。

### API 使用示例

展示当前缓存类型的 API 使用代码示例。

### 应用场景说明

介绍各种缓存在实际应用中的使用场景。

### 性能对比表

对比不同缓存类型的性能特点和适用场景。

## 代码示例

### Memory Cache

```python
from litefs.cache import MemoryCache

cache = MemoryCache(max_size=10000)

cache.put('key', 'value')
value = cache.get('key')
cache.delete('key')
cache.clear()
```

### Tree Cache

```python
from litefs.cache import TreeCache

cache = TreeCache(clean_period=60, expiration_time=3600)

cache.put('user:1:name', '张三')
cache.put('user:1:age', 25)
name = cache.get('user:1:name')
```

### Redis Cache

```python
from litefs.cache import RedisCache

cache = RedisCache(
    host='localhost',
    port=6379,
    db=0,
    key_prefix='litefs:',
    expiration_time=3600
)

cache.put('key', 'value')
value = cache.get('key')
```

### Database Cache

```python
from litefs.cache import DatabaseCache

cache = DatabaseCache(
    db_path=':memory:',
    table_name='cache',
    expiration_time=3600
)

cache.put('key', 'value')
value = cache.get('key')
```

### Memcache Cache

```python
from litefs.cache import MemcacheCache

cache = MemcacheCache(
    servers=['localhost:11211'],
    key_prefix='litefs:',
    expiration_time=3600
)

cache.put('key', 'value')
value = cache.get('key')
```

## 缓存应用场景

### 1. 数据库查询结果缓存

减少数据库压力，提高查询速度。

```python
def get_user(user_id):
    cache_key = f'user:{user_id}'
    user = cache.get(cache_key)
    
    if user is None:
        user = db.query('SELECT * FROM users WHERE id = ?', user_id)
        cache.put(cache_key, user, ttl=300)
    
    return user
```

### 2. API 响应缓存

缓存 API 响应，减少重复计算。

```python
def api_handler(self):
    cache_key = f'api:{self.path_info}:{self.query_string}'
    response = cache.get(cache_key)
    
    if response is None:
        response = call_external_api(self.path_info, self.query_string)
        cache.put(cache_key, response, ttl=60)
    
    return response
```

### 3. 页面渲染缓存

缓存渲染后的页面，减少渲染时间。

```python
def render_page(page_id):
    cache_key = f'page:{page_id}'
    html = cache.get(cache_key)
    
    if html is None:
        html = template.render(page_id)
        cache.put(cache_key, html, ttl=600)
    
    return html
```

### 4. 会话数据缓存

缓存会话数据，提高访问速度。

```python
def get_session_data(session_id):
    cache_key = f'session:{session_id}'
    data = cache.get(cache_key)
    
    if data is None:
        data = load_session_from_db(session_id)
        cache.put(cache_key, data, ttl=1800)
    
    return data
```

### 5. 配置数据缓存

缓存配置信息，减少 I/O 操作。

```python
def get_config(key):
    cache_key = f'config:{key}'
    value = cache.get(cache_key)
    
    if value is None:
        value = load_config_from_file(key)
        cache.put(cache_key, value, ttl=3600)
    
    return value
```

### 6. 计算结果缓存

缓存复杂计算结果，避免重复计算。

```python
def expensive_calculation(n):
    cache_key = f'calc:{n}'
    result = cache.get(cache_key)
    
    if result is None:
        result = calculate(n)
        cache.put(cache_key, result, ttl=600)
    
    return result
```

## 性能对比

| 缓存类型 | 读取速度 | 写入速度 | 持久化 | 分布式 | 适用场景 |
|---------|---------|---------|-------|-------|---------|
| Memory Cache | 极快 | 极快 | 否 | 否 | 单机应用、临时数据 |
| Tree Cache | 快 | 快 | 否 | 否 | 需要自动清理过期数据 |
| Redis Cache | 快 | 快 | 可选 | 是 | 分布式应用、高性能需求 |
| Database Cache | 中 | 中 | 是 | 否 | 需要持久化存储 |
| Memcache Cache | 极快 | 极快 | 否 | 是 | 高性能、临时数据 |

## 缓存最佳实践

1. **合理设置缓存大小和过期时间**
   - 根据数据的重要性和更新频率设置合适的 TTL
   - 避免缓存过大导致内存压力

2. **使用有意义的缓存键**
   - 采用清晰的命名规范
   - 包含足够的上下文信息

3. **考虑缓存失效策略**
   - 实现缓存更新机制
   - 处理缓存穿透、击穿、雪崩问题

4. **监控缓存命中率**
   - 定期检查缓存效果
   - 根据命中率调整缓存策略

5. **在生产环境使用分布式缓存**
   - Redis 或 Memcache 适合生产环境
   - 配置合适的集群和副本策略

6. **处理缓存依赖**
   - 确保缓存服务可用
   - 实现降级机制

## 故障排查

### Redis 连接失败

如果 Redis 缓存无法使用，请检查：
- Redis 服务是否启动：`redis-cli ping`
- Redis 是否运行在 localhost:6379
- 是否安装了 redis-py 库：`pip install redis`

### Memcache 连接失败

如果 Memcache 缓存无法使用，请检查：
- Memcache 服务是否启动：`telnet localhost 11211`
- Memcache 是否运行在 localhost:11211
- 是否安装了 python-memcached 库：`pip install python-memcached`

### 数据库缓存错误

如果 Database Cache 出现错误，请检查：
- SQLite 是否可用
- 数据库文件路径是否正确
- 是否有足够的磁盘空间

## 扩展阅读

- [缓存后端文档](../../docs/source/cache-backends.md)
- [会话后端文档](../../docs/source/session-backends.md)
- [Litefs 主文档](../../docs/source/index.md)
