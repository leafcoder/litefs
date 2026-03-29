# Cache 和 Session 后端示例

本目录包含使用 Database 和 Memcache 作为缓存和 Session 后端的示例代码。

## 示例文件

- [cache_session_backends_example.py](./cache_session_backends_example.py) - 演示如何使用 Database 和 Memcache 缓存/Session 后端

## 运行示例

```bash
python cache_session_backends_example.py
```

## 示例内容

### Database Cache

演示如何使用 SQLite 数据库作为缓存后端：

- 创建 Database Cache
- 存储和获取数据
- 批量操作
- 过期时间管理
- 模式匹配删除

### Memcache Cache

演示如何使用 Memcache 作为缓存后端：

- 创建 Memcache Cache
- 存储和获取数据
- 批量操作
- 高性能缓存访问

### Database Session

演示如何使用 SQLite 数据库作为 Session 后端：

- 创建 Database Session
- 存储 Session 数据
- 获取和删除 Session
- 过期时间管理

### Memcache Session

演示如何使用 Memcache 作为 Session 后端：

- 创建 Memcache Session
- 存储 Session 数据
- 获取和删除 Session
- 高性能 Session 访问

### Cache Factory

演示如何使用 CacheFactory 创建不同类型的缓存实例。

### Session Factory

演示如何使用 SessionFactory 创建不同类型的 Session 实例。

## 前置条件

### Database Cache/Session

无需额外依赖，使用 Python 内置的 SQLite。

### Memcache Cache/Session

需要安装 Memcache 服务器和客户端库：

```bash
# 安装 Memcache 服务器
# Ubuntu/Debian
sudo apt-get install memcached

# macOS
brew install memcached

# 启动 Memcache 服务器
memcached -p 11211

# 安装客户端库（二选一）
pip install pymemcache
# 或
pip install python-memcached
```

## 注意事项

1. **Memcache 示例**需要 Memcache 服务器运行，否则会跳过相关示例
2. **Database 示例**使用内存数据库，重启后数据会丢失
3. 所有示例都包含错误处理，确保在没有相关服务时也能正常运行

## 相关文档

- [缓存后端文档](../../docs/source/cache-backends.md)
- [Session 后端文档](../../docs/source/session-backends.md)