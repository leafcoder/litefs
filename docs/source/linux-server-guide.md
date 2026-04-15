# Linux 服务器部署指南

**文档版本**: 1.0  
**最后更新**: 2026-04-14

---

## 概述

本文档详细介绍如何在 Linux 生产环境中部署 Litefs 应用，包括环境配置、性能优化、安全设置和监控。

---

## 1. 环境准备

### 1.1 系统要求

**最低配置**:
- CPU: 1 核心
- 内存: 512 MB
- 磁盘: 5 GB
- 系统: Ubuntu 18.04+ / Debian 10+ / CentOS 7+

**推荐配置**:
- CPU: 2+ 核心
- 内存: 2 GB+
- 磁盘: 20 GB
- 系统: Ubuntu 20.04+ / Debian 11+

### 1.2 安装 Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install -y python3 python3-pip

# 验证安装
python3 --version
# 输出: Python 3.10.9
```

### 1.3 创建用户

```bash
# 创建专用用户（安全最佳实践）
sudo useradd -m -s /bin/bash litefs
sudo usermod -aG sudo litefs

# 创建应用目录
sudo mkdir -p /opt/litefs
sudo chown litefs:litefs /opt/litefs
```

---

## 2. 部署配置

### 2.1 使用 Gunicorn 部署

**安装 Gunicorn**:
```bash
pip install gunicorn
```

**创建 WSGI 应用** (`wsgi.py`):
```python
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

application = create_app()
app = application
```

**创建 Gunicorn 配置文件** (`gunicorn.conf.py`):
```python
import multiprocessing

# 绑定地址
bind = "127.0.0.1:8000"

# 工作进程数（推荐: CPU 核心数 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"  # 或 "gevent" 用于异步

# 超时设置
timeout = 30
keepalive = 2

# 日志
accesslog = "/var/log/litefs/access.log"
errorlog = "/var/log/litefs/error.log"
loglevel = "info"

# 进程名
proc_name = "litefs"

# 预加载应用（推荐）
preload_app = True

# 守护进程
daemon = False  # 使用 systemd 管理时设为 False
```

**创建日志目录**:
```bash
sudo mkdir -p /var/log/litefs
sudo chown -R litefs:litefs /var/log/litefs
```

**启动服务**:
```bash
gunicorn -c gunicorn.conf.py wsgi:application
```

### 2.2 使用 systemd 管理

**创建服务文件** (`/etc/systemd/system/litefs.service`):
```ini
[Unit]
Description=Litefs Application
After=network.target

[Service]
Type=notify
User=litefs
Group=litefs
WorkingDirectory=/opt/litefs
Environment="PATH=/opt/litefs/venv/bin"
ExecStart=/opt/litefs/venv/bin/gunicorn -c /opt/litefs/gunicorn.conf.py wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**启用服务**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable litefs
sudo systemctl start litefs
sudo systemctl status litefs
```

### 2.3 使用 Nginx 反向代理

**安装 Nginx**:
```bash
sudo apt install -y nginx
```

**创建 Nginx 配置** (`/etc/nginx/sites-available/litefs`):
```nginx
upstream litefs_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name example.com www.example.com;

    # 访问日志
    access_log /var/log/nginx/litefs_access.log;

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 静态文件（可选，让 Nginx 直接处理）
    location /static/ {
        alias /opt/litefs/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 媒体文件
    location /media/ {
        alias /opt/litefs/media/;
    }

    # 代理到 Gunicorn
    location / {
        proxy_pass http://litefs_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # WebSocket 支持（如果需要）
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**启用站点**:
```bash
sudo ln -s /etc/nginx/sites-available/litefs /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2.4 配置 HTTPS

**使用 Let's Encrypt**:
```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d example.com -d www.example.com

# 自动续期测试
sudo certbot renew --dry-run
```

**手动配置 HTTPS**:
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # 其他配置...
}

# HTTP 重定向到 HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 3. 性能优化

### 3.1 Gunicorn 优化

**同步工作模式**（适用于 CPU 密集型）:
```python
worker_class = "sync"
workers = multiprocessing.cpu_count() * 2 + 1
```

**异步工作模式**（适用于 I/O 密集型）:
```python
worker_class = "gevent"
workers = multiprocessing.cpu_count() * 2 + 1
worker_connections = 1000
```

**多线程模式**:
```python
worker_class = "gthread"
threads = 4
workers = multiprocessing.cpu_count() * 2 + 1
```

### 3.2 系统优化

**文件描述符限制** (`/etc/security/limits.conf`):
```bash
litefs soft nofile 65535
litefs hard nofile 65535
```

**网络优化** (`/etc/sysctl.conf`):
```bash
# 网络缓冲区
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216

# TCP 优化
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_fastopen = 3

# 连接队列
net.core.somaxconn = 1024
```

**应用这些设置**:
```bash
sudo sysctl -p
```

### 3.3 缓存配置

**启用内存缓存**:
```python
app = Litefs(
    cache_backend='memory',
    cache_max_size=10000,
    cache_expiration_time=3600
)
```

**启用 Redis 缓存**:
```python
app = Litefs(
    cache_backend='redis',
    redis_host='localhost',
    redis_port=6379,
    redis_db=0,
    cache_expiration_time=3600
)
```

---

## 4. 安全设置

### 4.1 防火墙配置

**使用 UFW**:
```bash
# 安装 UFW
sudo apt install -y ufw

# 默认策略
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许 SSH（重要！）
sudo ufw allow ssh

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### 4.2 安全加固

**关闭不必要的服务**:
```bash
sudo systemctl stop postfix
sudo systemctl disable postfix
```

**定期更新**:
```bash
# 自动安全更新
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

**监控可疑活动**:
```bash
# 安装 Fail2Ban
sudo apt install -y fail2ban

# 配置 Fail2Ban
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo nano /etc/fail2ban/jail.local
```

### 4.3 应用安全

**安全配置**:
```python
app = Litefs(
    # 安全设置
    secret_key='your-secret-key-here',
    enable_csrf=True,
    enable_security_headers=True,
    
    # 上传限制
    max_content_length=10 * 1024 * 1024,  # 10MB
    
    # CORS 配置
    cors_origins=['https://example.com'],
)
```

---

## 5. 监控和日志

### 5.1 日志配置

**日志轮转** (`/etc/logrotate.d/litefs`):
```
/var/log/litefs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 litefs litefs
    sharedscripts
    postrotate
        systemctl reload litefs > /dev/null 2>&1 || true
    endscript
}
```

### 5.2 监控设置

**使用 Prometheus**:
```python
from prometheus_client import start_http_server, Counter

REQUEST_COUNT = Counter('litefs_requests_total', 'Total requests')

@app.middleware
def metrics_middleware(request, next):
    REQUEST_COUNT.inc()
    return next(request)

# 启动指标端点
start_http_server(9090)
```

**使用 Grafana**:
- 安装 Grafana
- 添加 Prometheus 数据源
- 导入 Litefs 仪表板

### 5.3 健康检查

**配置健康检查端点**:
```python
from litefs.middleware import HealthCheck

app = Litefs()
app.add_middleware(HealthCheck)
```

**Nginx 健康检查**:
```nginx
location /health {
    proxy_pass http://litefs_backend/health;
    proxy_connect_timeout 5s;
    proxy_read_timeout 5s;
}
```

---

## 6. 备份和恢复

### 6.1 数据库备份

**PostgreSQL**:
```bash
# 备份
pg_dump -U litefs litefs_db > backup_$(date +%Y%m%d).sql

# 恢复
psql -U litefs litefs_db < backup_20260414.sql
```

**自动备份脚本**:
```bash
#!/bin/bash
# /opt/litefs/backup.sh

BACKUP_DIR="/opt/litefs/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -U litefs litefs_db > $BACKUP_DIR/db_$DATE.sql

# 备份应用文件
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /opt/litefs/app

# 保留 7 天备份
find $BACKUP_DIR -type f -mtime +7 -delete
```

**添加定时任务**:
```bash
crontab -e
# 每天凌晨 3 点执行备份
0 3 * * * /opt/litefs/backup.sh >> /var/log/litefs/backup.log 2>&1
```

---

## 7. 故障排查

### 7.1 常见问题

**502 Bad Gateway**:
```bash
# 检查 Gunicorn 状态
sudo systemctl status litefs

# 查看日志
sudo journalctl -u litefs -n 50
```

**503 Service Unavailable**:
```bash
# 检查应用是否启动
ps aux | grep gunicorn

# 检查端口占用
netstat -tlnp | grep 8000
```

**内存使用过高**:
```bash
# 查看内存使用
free -h

# 查看进程内存
ps aux --sort=-%mem | head -10
```

### 7.2 性能问题

**CPU 使用率高**:
```bash
# 查看 CPU 使用
top -c

# 查看具体进程
pidstat -p <PID> 1
```

**响应时间长**:
```bash
# 启用 Gunicorn 慢查询日志
timeout = 30
slow = 10  # 记录超过 10 秒的请求
```

---

## 8. 容器化部署

### 8.1 Docker 部署

**创建 Dockerfile**:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用
COPY . .

# 创建非 root 用户
RUN useradd -m litefs && chown -R litefs:litefs /app
USER litefs

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:application"]
```

**构建和运行**:
```bash
docker build -t litefs:latest .
docker run -d -p 8000:8000 --name litefs litefs:latest
```

### 8.2 Docker Compose

**创建 docker-compose.yml**:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/litefs
      - REDIS_URL=redis://cache:6379/0
    depends_on:
      - db
      - cache

  db:
    image: postgres:14
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: litefs
    volumes:
      - postgres_data:/var/lib/postgresql/data

  cache:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**启动服务**:
```bash
docker-compose up -d
```

---

## 9. 相关资源

- [Gunicorn 文档](https://docs.gunicorn.org/)
- [Nginx 文档](https://nginx.org/en/docs/)
- [Let's Encrypt](https://letsencrypt.org/)
- [Fail2Ban](https://www.fail2ban.org/)

---

**文档维护**: 开发团队  
**最后更新**: 2026-04-14
