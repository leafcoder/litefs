# Litefs WSGI 部署指南

Litefs 现在完全支持 WSGI 规范 (PEP 3333)，可以在 gunicorn、uWSGI 等
WSGI 服务器中运行。

## Python 版本兼容性

**重要提示**：

- **Python 2.6-2.7**: 完全支持
- **Python 3.4-3.12**: 完全支持（推荐用于生产环境）
- **Python 3.13+**: greenlet 可能存在兼容性问题
- **Python 3.14+**: greenlet 尚未完全支持，建议使用 Python 3.9-3.12

**注意**：greenlet 仅用于内置的 epoll 服务器。WSGI 接口本身不依赖 greenlet，
因此可以在任何 Python 版本中使用 WSGI 服务器部署。

## 快速开始

### 1. 创建 WSGI 应用文件

创建 `wsgi_example.py` 文件：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

import litefs

app = litefs.Litefs(webroot='./site')
application = app.wsgi()
```

### 2. 使用 Gunicorn 部署

#### 安装 Gunicorn

```bash
pip install gunicorn
```

#### 启动服务器

```bash
# 基本启动
gunicorn -w 4 -b :8000 wsgi_example:application

# 生产环境推荐配置
gunicorn -w 4 -k gevent -b 0.0.0.0:8000 \
  --access-logfile access.log \
  --error-logfile error.log \
  --log-level info \
  --timeout 30 \
  --keepalive 5 \
  wsgi_example:application
```

#### Gunicorn 参数说明

- `-w 4`: 工作进程数，建议设置为 CPU 核心数的 2-4 倍
- `-k gevent`: 使用 gevent worker（需要安装 gevent）
- `-b 0.0.0.0:8000`: 绑定地址和端口
- `--access-logfile`: 访问日志文件
- `--error-logfile`: 错误日志文件
- `--timeout`: 请求超时时间（秒）
- `--keepalive`: 保持连接时间（秒）

### 3. 使用 uWSGI 部署

#### 安装 uWSGI

```bash
pip install uwsgi
```

#### 启动服务器

```bash
# 基本启动
uwsgi --http :8000 --wsgi-file wsgi_example.py

# 生产环境推荐配置
uwsgi --http 0.0.0.0:8000 \
  --wsgi-file wsgi_example.py \
  --processes 4 \
  --threads 2 \
  --master \
  --pidfile /tmp/uwsgi.pid \
  --daemonize /var/log/uwsgi.log \
  --harakiri 30 \
  --max-requests 5000 \
  --vacuum
```

#### uWSGI 参数说明

- `--processes 4`: 工作进程数
- `--threads 2`: 每个进程的线程数
- `--master`: 启用主进程模式
- `--daemonize`: 后台运行并记录日志
- `--harakiri`: 请求超时时间（秒）
- `--max-requests`: 每个进程处理的最大请求数后重启
- `--vacuum`: 退出时清理 socket 文件

### 4. 使用 Waitress 部署（Windows 推荐）

#### 安装 Waitress

```bash
pip install waitress
```

#### 启动服务器

```bash
# 基本启动
waitress-serve --port=8000 wsgi_example:application

# 生产环境推荐配置
waitress-serve --port=8000 \
  --threads=4 \
  --url-prefix=/ \
  --log-untrusted-proxy-headers=true \
  wsgi_example:application
```

## 性能优化建议

### 1. 工作进程数

根据服务器配置调整工作进程数：

```bash
# CPU 核心数 * 2-4
gunicorn -w $(($(nproc) * 2)) wsgi_example:application
```

### 2. Worker 类型选择

- `sync`: 同步 worker，适合 CPU 密集型任务
- `gevent`: 异步 worker，适合 I/O 密集型任务
- `eventlet`: 异步 worker，类似 gevent

```bash
# 使用 gevent worker
pip install gevent
gunicorn -w 4 -k gevent wsgi_example:application
```

### 3. 连接优化

```bash
gunicorn -w 4 \
  --backlog 2048 \
  --keepalive 5 \
  --timeout 30 \
  wsgi_example:application
```

### 4. 日志配置

```bash
gunicorn -w 4 \
  --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"' \
  --access-logfile access.log \
  --error-logfile error.log \
  --log-level info \
  wsgi_example:application
```

## Nginx 反向代理配置

在生产环境中，建议使用 Nginx 作为反向代理：

```nginx
upstream litefs_backend {
    server 127.0.0.1:8000;
    # 多个后端服务器时可以添加更多
    # server 127.0.0.1:8001;
    # server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://litefs_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /static/ {
        alias /path/to/your/site/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Systemd 服务配置

创建 `/etc/systemd/system/litefs.service`：

```ini
[Unit]
Description=Litefs WSGI Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/litefs
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn \
    -w 4 \
    -k gevent \
    -b 127.0.0.1:8000 \
    --access-logfile /var/log/litefs/access.log \
    --error-logfile /var/log/litefs/error.log \
    --log-level info \
    --timeout 30 \
    wsgi_example:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable litefs
sudo systemctl start litefs
sudo systemctl status litefs
```

## Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn gevent

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-k", "gevent", "-b", "0.0.0.0:8000", 
     "wsgi_example:application"]
```

构建和运行：

```bash
docker build -t litefs .
docker run -d -p 8000:8000 -v $(pwd)/site:/app/site litefs
```

## 监控和健康检查

### 健康检查端点

在 `site/health.py` 中创建：

```python
def handler(self):
    return "OK"
```

### 监控脚本

```bash
#!/bin/bash
# health_check.sh

HEALTH_URL="http://localhost:8000/health.py"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "Service is healthy"
    exit 0
else
    echo "Service is unhealthy (HTTP $RESPONSE)"
    exit 1
fi
```

## 故障排查

### 1. 查看日志

```bash
# Gunicorn
tail -f access.log error.log

# uWSGI
tail -f /var/log/uwsgi.log

# Systemd
journalctl -u litefs -f
```

### 2. 检查进程

```bash
ps aux | grep gunicorn
ps aux | grep uwsgi
```

### 3. 测试连接

```bash
curl -I http://localhost:8000/
```

### 4. 常见问题

**问题**: 端口被占用
```bash
# 查找占用端口的进程
lsof -i :8000
# 或
netstat -tulpn | grep 8000
```

**问题**: 权限错误
```bash
# 确保目录权限正确
chown -R www-data:www-data /path/to/litefs
chmod -R 755 /path/to/litefs
```

**问题**: 内存不足
```bash
# 减少工作进程数
gunicorn -w 2 wsgi_example:application
```

## 安全建议

1. **使用 HTTPS**: 在生产环境中始终使用 HTTPS
2. **限制访问**: 使用防火墙限制访问
3. **定期更新**: 保持依赖包和系统更新
4. **监控日志**: 定期检查访问和错误日志
5. **备份**: 定期备份数据和配置

## 更多资源

- [Gunicorn 文档](https://docs.gunicorn.org/)
- [uWSGI 文档](https://uwsgi-docs.readthedocs.io/)
- [Waitress 文档](https://docs.pylonsproject.org/projects/waitress/)
- [PEP 3333 - WSGI 规范](https://www.python.org/dev/peps/pep-3333/)
