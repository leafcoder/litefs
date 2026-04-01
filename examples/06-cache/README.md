# 缓存管理

Litefs 缓存管理示例，包括与新路由系统的集成。

## 示例文件

- `cache_example.py` - 缓存管理示例主程序（使用新的路由系统）

## 运行示例

```bash
python cache_example.py
```

访问 http://localhost:8080/cache 查看缓存管理示例。

## 缓存类型

### 1. MemoryCache

基于内存的缓存，支持 TTL（过期时间）。

```python
from litefs.cache import MemoryCache

cache = MemoryCache(max_size=1000)

cache.put('key', 'value')
cache.put('key', 'value', ttl=60)  # 60秒后过期
value = cache.get('key')
cache.delete('key')
cache.clear()
```

### 2. TreeCache

树形结构缓存，支持层级访问。

```python
from litefs.cache import TreeCache

cache = TreeCache()

cache.put('user:1:name', '张三')
cache.put('user:1:age', 25)
cache.put('user:2:name', '李四')

name = cache.get('user:1:name')
user1 = cache.get_tree('user:1')
```

### 3. RedisCache

基于 Redis 的分布式缓存。

```python
from litefs.cache import RedisCache

cache = RedisCache(host='localhost', port=6379, db=0)

cache.put('key', 'value')
value = cache.get('key')
```

## 缓存操作

### 基本操作

```python
from litefs.cache import MemoryCache

cache = MemoryCache(max_size=1000)

cache.put('key', 'value')
value = cache.get('key')
exists = cache.exists('key')
cache.delete('key')
cache.clear()
```

### TTL 操作

```python
cache.put('key', 'value', ttl=60)  # 设置过期时间
cache.expire('key', 120)  # 更新过期时间
ttl = cache.ttl('key')  # 获取剩余时间
```

### 批量操作

```python
cache.put_many({
    'key1': 'value1',
    'key2': 'value2',
    'key3': 'value3'
})

values = cache.get_many(['key1', 'key2', 'key3'])
```

### 统计信息

```python
stats = cache.get_stats()
print(stats)
# {'hits': 100, 'misses': 10, 'size': 50, 'max_size': 1000}
```

## 缓存应用场景

### 1. 数据库查询结果缓存

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

```python
def api_handler(self):
    cache_key = f'api:{self.path_info}:{self.query_string}'
    response = cache.get(cache_key)
    
    if response is None:
        response = call_external_api(self.path_info, self.query_string)
        cache.put(cache_key, response, ttl=60)
    
    return response
```

### 3. 计算结果缓存

```python
def expensive_calculation(n):
    cache_key = f'calc:{n}'
    result = cache.get(cache_key)
    
    if result is None:
        result = calculate(n)
        cache.put(cache_key, result, ttl=600)
    
    return result
```

### 4. 会话数据缓存

```python
def get_session_data(session_id):
    cache_key = f'session:{session_id}'
    data = cache.get(cache_key)
    
    if data is None:
        data = load_session_from_db(session_id)
        cache.put(cache_key, data, ttl=1800)
    
    return data
```

## 缓存最佳实践

1. 合理设置缓存大小和过期时间
2. 使用有意义的缓存键
3. 考虑缓存失效策略
4. 监控缓存命中率
5. 在生产环境使用分布式缓存

## 与新路由系统集成

使用新的路由系统定义缓存相关的路由：

```python
from litefs import Litefs
from litefs.routing import get, post
from litefs.cache import MemoryCache

app = Litefs()

# 创建缓存实例
cache = MemoryCache(max_size=1000)

@get('/cache')
def cache_handler(self):
    # 获取缓存数据
    counter = cache.get('counter', 0)
    
    # 更新计数器
    cache.put('counter', counter + 1, ttl=3600)
    
    # 生成响应
    return f"Cache counter: {counter + 1}"

@post('/cache/set')
def set_cache_handler(self):
    # 获取表单数据
    key = self.post.get('key')
    value = self.post.get('value')
    ttl = int(self.post.get('ttl', 3600))
    
    if key and value:
        # 设置缓存
        cache.put(key, value, ttl=ttl)
        return f"Cache set: {key} = {value}"
    
    return "Invalid parameters"

@get('/cache/get')
def get_cache_handler(self):
    # 获取查询参数
    key = self.get.get('key')
    
    if key:
        # 获取缓存
        value = cache.get(key)
        if value is not None:
            return f"Cache value: {value}"
        return "Cache miss"
    
    return "Invalid parameters"

@get('/cache/delete')
def delete_cache_handler(self):
    # 获取查询参数
    key = self.get.get('key')
    
    if key:
        # 删除缓存
        cache.delete(key)
        return f"Cache deleted: {key}"
    
    return "Invalid parameters"

@get('/cache/clear')
def clear_cache_handler(self):
    # 清除所有缓存
    cache.clear()
    return "Cache cleared"

# 注册路由
app.register_routes(cache_handler)
app.register_routes(set_cache_handler)
app.register_routes(get_cache_handler)
app.register_routes(delete_cache_handler)
app.register_routes(clear_cache_handler)

app.run()
```

### 访问端点

- **缓存计数器**：http://localhost:8080/cache
- **设置缓存**：POST http://localhost:8080/cache/set
- **获取缓存**：http://localhost:8080/cache/get?key=example
- **删除缓存**：http://localhost:8080/cache/delete?key=example
- **清除缓存**：http://localhost:8080/cache/clear
