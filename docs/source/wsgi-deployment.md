# WSGI 部署

## 创建 WSGI 应用

创建 ``wsgi.py``：

```python
from litefs import Litefs

app = Litefs()

@get('/', name='index')
def index_handler(request):
    return 'Hello, World!'

application = app.wsgi()
```

## 使用 Gunicorn

### 安装

```bash
pip install gunicorn
```

### 基本启动

```bash
gunicorn -w 4 -b :8000 wsgi:application
```

### 生产环境配置

```bash
gunicorn -w 4 -k gevent -b 0.0.0.0:8000 \
  --access-logfile access.log \
  --error-logfile error.log \
  --log-level info \
  --timeout 30 \
  --keepalive 5 \
  wsgi:application
```

## 使用 uWSGI

### 安装

```bash
pip install uwsgi
```

### 基本启动

```bash
uwsgi --http :8000 --wsgi-file wsgi.py
```

### 生产环境配置

```bash
uwsgi --http 0.0.0.0:8000 \
  --wsgi-file wsgi.py \
  --processes 4 \
  --threads 2 \
  --master \
  --pidfile /tmp/uwsgi.pid \
  --daemonize /var/log/uwsgi.log \
  --harakiri 30 \
  --max-requests 5000 \
  --vacuum
```

## 使用 Waitress（Windows）

### 安装

```bash
pip install waitress
```

### 启动

```bash
waitress-serve --port=8000 wsgi:application
```

## Nginx 反向代理

```nginx
upstream app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name example.com;
    
    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn gevent

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-k", "gevent", "-b", "0.0.0.0:8000", 
     "wsgi:application"]
```

## Systemd 服务

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
    wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 相关文档

* :doc:`getting-started` - 快速开始
* :doc:`routing-guide` - 路由系统
* :doc:`configuration` - 配置管理
* :doc:`middleware-guide` - 中间件
