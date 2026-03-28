# WSGI 部署

Litefs WSGI 部署示例。

## 示例文件

- `wsgi_example.py` - 标准 WSGI 应用
- `wsgi_simple.py` - 简单 WSGI 应用（调试模式）
- `wsgi_example_advanced.py` - 高级 WSGI 应用（带中间件）
- `wsgi_standalone.py` - 独立 WSGI 服务器

## WSGI 服务器

### 1. Gunicorn

推荐用于生产环境。

```bash
pip install gunicorn gevent
```

基本使用：

```bash
gunicorn -w 4 -k gevent -b :8000 wsgi_example:application
```

高级配置：

```bash
gunicorn \
  --workers 4 \
  --worker-class gevent \
  --worker-connections 1000 \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --keepalive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile access.log \
  --error-logfile error.log \
  --log-level info \
  wsgi_example:application
```

配置文件 `gunicorn.conf.py`：

```python
import multiprocessing

bind = '0.0.0.0:8000'
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gevent'
worker_connections = 1000
timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = 'access.log'
errorlog = 'error.log'
loglevel = 'info'
```

使用配置文件：

```bash
gunicorn -c gunicorn.conf.py wsgi_example:application
```

### 2. uWSGI

另一个高性能 WSGI 服务器。

```bash
pip install uwsgi
```

基本使用：

```bash
uwsgi --http :8000 --wsgi-file wsgi_example.py --processes 4 --threads 2
```

高级配置：

```bash
uwsgi \
  --http :8000 \
  --wsgi-file wsgi_example.py \
  --processes 4 \
  --threads 2 \
  --master \
  --enable-threads \
  --single-interpreter \
  --lazy-apps \
  --harakiri 30 \
  --max-requests 1000 \
  --vacuum \
  --die-on-term \
  --logto uwsgi.log
```

配置文件 `uwsgi.ini`：

```ini
[uwsgi]
http = :8000
wsgi-file = wsgi_example.py
processes = 4
threads = 2
master = true
enable-threads = true
single-interpreter = true
lazy-apps = true
harakiri = 30
max-requests = 1000
vacuum = true
die-on-term = true
logto = uwsgi.log
```

使用配置文件：

```bash
uwsgi --ini uwsgi.ini
```

### 3. Waitress

Windows 平台推荐使用。

```bash
pip install waitress
```

基本使用：

```bash
waitress-serve --port=8000 wsgi_example:application
```

高级配置：

```bash
waitress-serve \
  --port=8000 \
  --host=0.0.0.0 \
  --threads=4 \
  --url-prefix=/ \
  --ident=Litefs \
  --send-bytes=1024 \
  --outbuf-high-watermark=16777216 \
  --inbuf-high-watermark=16777216 \
  wsgi_example:application
```

### 4. mod_wsgi

Apache 模块部署。

```apache
<VirtualHost *:80>
    ServerName example.com
    WSGIScriptAlias / /path/to/wsgi_example.py
    WSGIDaemonProcess litefs processes=4 threads=2
    WSGIProcessGroup litefs
    WSGIScriptReloading On
</VirtualHost>
```

## 性能优化

### 1. 工作进程数

```python
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
```

### 2. 工作线程数

```python
threads = 2  # I/O 密集型应用
threads = 4  # CPU 密集型应用
```

### 3. 连接数

```python
worker_connections = 1000  # gevent
```

### 4. 超时设置

```python
timeout = 30  # 请求超时
keepalive = 5  # 保持连接时间
```

### 5. 请求限制

```python
max_requests = 1000  # 每个工作进程处理的最大请求数
max_requests_jitter = 100  # 随机抖动
```

## 负载均衡

### Nginx 配置

```nginx
upstream litefs {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://litefs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 监控和日志

### 访问日志

```bash
gunicorn --access-logfile access.log wsgi_example:application
```

### 错误日志

```bash
gunicorn --error-logfile error.log wsgi_example:application
```

### 日志级别

```bash
gunicorn --log-level info wsgi_example:application
```

## 安全配置

### SSL/TLS

```bash
gunicorn \
  --keyfile server.key \
  --certfile server.crt \
  --bind 0.0.0.0:443 \
  wsgi_example:application
```

### 限制访问

```bash
gunicorn --bind 127.0.0.1:8000 wsgi_example:application
```

## 最佳实践

1. 使用 gunicorn + gevent 获得最佳性能
2. 根据 CPU 核心数设置工作进程数
3. 使用配置文件管理部署参数
4. 启用访问日志和错误日志
5. 设置合理的超时时间
6. 使用 Nginx 作为反向代理
7. 配置负载均衡提高可用性
8. 定期重启工作进程避免内存泄漏
9. 监控服务器性能指标
10. 使用 SSL/TLS 保护通信安全
