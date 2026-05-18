# ASGI 部署

## 创建 ASGI 应用

创建 ``asgi.py``：

```python
from litefs.core import Litefs

app = Litefs()

@app.add_get('/', name='index')
def index_handler(request):
    return 'Hello, World!'

application = app.asgi()
```

## 使用 Uvicorn

### 安装

```bash
pip install uvicorn
```

### 基本启动

```bash
uvicorn asgi:application
```

### 生产环境配置

```bash
uvicorn asgi:application \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --access-log \
  --error-logfile error.log \
  --timeout-keep-alive 5 \
  --timeout-graceful-shutdown 30
```

## 使用 Daphne

### 安装

```bash
pip install daphne
```

### 基本启动

```bash
daphne asgi:application
```

### 生产环境配置

```bash
daphne \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --access-log /var/log/litefs/access.log \
  --error-log /var/log/litefs/error.log \
  asgi:application
```

## 使用 Hypercorn

### 安装

```bash
pip install hypercorn
```

### 基本启动

```bash
hypercorn asgi:application
```

### 生产环境配置

```bash
hypercorn \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --access-logfile /var/log/litefs/access.log \
  --error-logfile /var/log/litefs/error.log \
  --log-level info \
  asgi:application
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
        # 支持 WebSocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

COPY . .

EXPOSE 8000

CMD ["uvicorn", "asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

## Systemd 服务

```ini
[Unit]
Description=Litefs ASGI Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/litefs
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn \
    asgi:application \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 4 \
    --access-logfile /var/log/litefs/access.log \
    --error-logfile /var/log/litefs/error.log \
    --log-level info
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 异步处理支持

ASGI 模式下，你可以使用异步处理函数：

```python
from litefs.core import Litefs
import asyncio

app = Litefs()

@app.add_get('/async', name='async_example')
async def async_handler(request):
    # 模拟异步操作
    await asyncio.sleep(1)
    return 'Hello from async handler!'

application = app.asgi()
```

## 相关文档

* :doc:`getting-started` - 快速开始
* :doc:`routing-guide` - 路由系统
* :doc:`configuration` - 配置管理
* :doc:`middleware-guide` - 中间件
* :doc:`wsgi-deployment` - WSGI 部署