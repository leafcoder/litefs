# WSGI 服务器配置管理

本目录包含 Litefs 项目的 WSGI 服务器配置文件，用于统一管理不同 WSGI 服务器的配置。

## 配置文件说明

### 1. Gunicorn 配置
- **文件**: `gunicorn.conf.py`
- **用途**: Gunicorn WSGI 服务器的配置文件
- **特点**: 高性能、支持异步 worker、适合生产环境

### 2. uWSGI 配置
- **文件**: `uwsgi.ini`
- **用途**: uWSGI 服务器的配置文件
- **特点**: 功能丰富、性能优异、适合高并发场景

### 3. Waitress 配置
- **文件**: `waitress.ini`
- **用途**: Waitress WSGI 服务器的配置文件
- **特点**: 纯 Python 实现、易于配置、适合开发和小型部署

## 使用方法

### 1. 安装 WSGI 服务器

```bash
# 安装 Gunicorn
pip install gunicorn gevent

# 安装 uWSGI
pip install uwsgi

# 安装 Waitress
pip install waitress
```

### 2. 使用配置文件启动服务器

#### Gunicorn
```bash
# 基本启动
gunicorn -c ../wsgi-configs/gunicorn.conf.py wsgi:application

# 后台运行
gunicorn -c ../wsgi-configs/gunicorn.conf.py wsgi:application --daemon
```

#### uWSGI
```bash
# 基本启动
uwsgi --ini ../wsgi-configs/uwsgi.ini

# 后台运行
uwsgi --ini ../wsgi-configs/uwsgi.ini --daemonize ./logs/uwsgi.log
```

#### Waitress
```bash
# 基本启动
waitress-serve --config ../wsgi-configs/waitress.ini wsgi:application

# 后台运行 (使用 nohup)
nohup waitress-serve --config ../wsgi-configs/waitress.ini wsgi:application > ./logs/waitress.log 2>&1 &
```

## 配置说明

### Gunicorn 配置要点
- **workers**: 工作进程数，建议设置为 CPU 核心数的 2-4 倍
- **worker_class**: 建议使用 `gevent` 以提高并发性能
- **timeout**: 超时时间，根据应用响应时间调整
- **accesslog/errorlog**: 日志文件路径

### uWSGI 配置要点
- **processes/threads**: 进程和线程数，根据服务器资源调整
- **master**: 启用主进程管理工作进程
- **harakiri**: 请求超时时间，防止长时间运行的请求阻塞
- **logto**: 日志文件路径

### Waitress 配置要点
- **threads**: 线程数，根据服务器资源调整
- **connection_limit**: 最大连接数，根据预期流量调整
- **channel_timeout**: 通道超时时间，根据应用响应时间调整
- **access_log/error_log**: 日志文件路径

## 生产环境建议

1. **选择合适的 WSGI 服务器**:
   - **高并发场景**: Gunicorn + gevent 或 uWSGI
   - **简单部署**: Waitress

2. **配置文件管理**:
   - 为不同环境（开发、测试、生产）创建不同的配置文件
   - 使用环境变量管理敏感配置

3. **监控和日志**:
   - 配置详细的访问日志和错误日志
   - 定期轮转日志文件
   - 监控服务器性能和资源使用

4. **安全设置**:
   - 限制请求大小和处理时间
   - 启用 HTTPS
   - 配置适当的安全头部

## 示例应用

所有 Litefs 示例代码都包含 `wsgi.py` 文件，可以直接使用这些配置文件启动。例如：

```bash
# 启动 01-quickstart 示例
cd ../01-quickstart
gunicorn -c ../wsgi-configs/gunicorn.conf.py wsgi:application
```

## 注意事项

- 确保 `logs` 目录存在，否则可能会导致启动失败
- 根据服务器硬件资源调整配置参数
- 生产环境建议使用反向代理（如 Nginx）前端
- 定期检查和优化配置以提高性能