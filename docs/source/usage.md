# 使用文档

## 1. 快速开始

### 1.1 安装

```bash
pip install litefs
```

### 1.2 基本使用

创建 `app.py` 文件：

```python
from litefs import Litefs

app = Litefs(
    host='0.0.0.0',
    port=8080,
    webroot='./site',
    debug=True,
)

app.run()
```

创建 `site/index.py` 文件：

```python
def handler(self):
    return "Hello, Litefs!"
```

运行应用：

```bash
python app.py
```

访问 `http://localhost:8080/` 查看结果。

### 1.3 完整示例应用

Litefs 提供了一个完整的示例应用，展示了框架的核心功能和最佳实践。

#### 目录结构

```
examples/fullstack_example/
├── app.py          # 应用主文件
├── wsgi.py         # WSGI 应用文件
├── site/           # Web 根目录
│   ├── index.py    # 首页
│   ├── about.py    # 关于页面
│   ├── contact.py  # 联系页面
│   ├── dashboard.py # 仪表板页面
│   └── static/     # 静态文件
│       └── css/
│           └── style.css # 样式文件
└── README.md       # 说明文档
```

#### 功能特性

- **路由处理**：基本的页面路由和处理
- **表单处理**：联系表单提交和验证
- **会话管理**：用户会话和访问历史记录
- **缓存使用**：内存缓存示例
- **中间件集成**：日志、安全、CORS、限流中间件
- **静态文件服务**：CSS 样式和静态资源
- **健康检查**：应用健康状态和就绪检查
- **响应式设计**：适配不同屏幕尺寸

#### 运行示例

```bash
# 进入示例目录
cd examples/fullstack_example

# 运行开发服务器
python app.py
```

应用将在 `http://localhost:8080` 启动，可访问以下端点：

- **首页**：`http://localhost:8080/`
- **关于页面**：`http://localhost:8080/about`
- **联系页面**：`http://localhost:8080/contact`
- **仪表板**：`http://localhost:8080/dashboard`
- **健康检查**：`http://localhost:8080/health`
- **就绪检查**：`http://localhost:8080/health/ready`

#### 生产部署

使用 Gunicorn：

```bash
pip install gunicorn gevent
gunicorn -w 4 -k gevent -b :8000 wsgi:application
```

使用 uWSGI：

```bash
pip install uwsgi
uwsgi --http :8000 --wsgi-file wsgi.py --processes 4 --threads 2 --master
```

使用 Waitress（Windows 推荐）：

```bash
pip install waitress
waitress-serve --port=8000 wsgi:application
```

## 2. 配置管理

### 2.1 配置来源

Litefs 支持多种配置来源，按优先级从高到低排列：

1. **代码配置** - 通过代码直接设置配置项
2. **环境变量** - 通过环境变量设置配置（前缀：`LITEFS_`）
3. **配置文件** - 通过 YAML、JSON 或 TOML 文件设置配置
4. **默认配置** - 系统内置的默认值

### 2.2 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|---------|------|
| `host` | str | `localhost` | 服务器监听地址 |
| `port` | int | `9090` | 服务器监听端口 |
| `webroot` | str | `./site` | Web 根目录 |
| `debug` | bool | `false` | 调试模式 |
| `not_found` | str | `not_found` | 404 页面文件名 |
| `default_page` | str | `index,index.html` | 默认页面文件名（支持多个，逗号分隔） |
| `log` | str | `./default.log` | 日志文件路径 |
| `listen` | int | `1024` | 服务器监听队列大小 |
| `max_request_size` | int | `10485760` | 最大请求体大小（字节，默认 10MB） |
| `max_upload_size` | int | `52428800` | 最大上传文件大小（字节，默认 50MB） |
| `config_file` | str | `None` | 配置文件路径 |

### 2.3 使用方法

#### 2.3.1 使用默认配置

```python
from litefs import Litefs

app = Litefs()
app.run()
```

#### 2.3.2 使用代码配置

```python
from litefs import Litefs

app = Litefs(
    host='0.0.0.0',
    port=8080,
    webroot='./site',
    debug=True,
    max_request_size=20971520,
)

app.run()
```

#### 2.3.3 使用配置文件

创建 `litefs.yaml`：

```yaml
host: localhost
port: 9090
webroot: ./site
debug: false
not_found: not_found
default_page: index,index.html
log: ./default.log
listen: 1024
max_request_size: 10485760
max_upload_size: 52428800
```

使用配置文件：

```python
from litefs import Litefs

app = Litefs(config_file='litefs.yaml')
app.run()
```

#### 2.3.4 使用环境变量

设置环境变量：

```bash
export LITEFS_HOST=0.0.0.0
export LITEFS_PORT=8080
export LITEFS_DEBUG=true
export LITEFS_MAX_REQUEST_SIZE=20971520
export LITEFS_DEFAULT_PAGE="index,index.html"
```

使用环境变量：

```python
from litefs import Litefs

app = Litefs()
app.run()
```

## 3. WSGI 部署

### 3.1 创建 WSGI 应用文件

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

### 3.2 使用 Gunicorn 部署

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

### 3.3 使用 uWSGI 部署

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

### 3.4 使用 Waitress 部署（Windows 推荐）

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

### 3.5 Nginx 反向代理配置

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

### 3.6 Systemd 服务配置

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

### 3.7 Docker 部署

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

## 4. 中间件使用

### 4.1 内置中间件

```python
from litefs import Litefs
from litefs.middleware import LoggingMiddleware, SecurityMiddleware, CORSMiddleware, RateLimitMiddleware, HealthCheck

app = Litefs()

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 添加安全中间件
app.add_middleware(SecurityMiddleware)

# 添加 CORS 中间件
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_methods=["GET", "POST", "PUT", "DELETE"],
                   allow_headers=["Content-Type", "Authorization"])

# 添加限流中间件
app.add_middleware(RateLimitMiddleware,
                   max_requests=100,
                   window_seconds=60,
                   block_duration=120)

# 添加健康检查中间件
app.add_middleware(HealthCheck,
                   path='/health',
                   ready_path='/health/ready')

app.run()
```

### 4.2 自定义中间件

```python
from litefs.middleware import Middleware

class CustomMiddleware(Middleware):
    def process_request(self, request_handler):
        print(f"请求: {request_handler.path_info}")
        return None
    
    def process_response(self, request_handler, response):
        print(f"响应: {len(response)} bytes")
        return response

app.add_middleware(CustomMiddleware)
```

## 5. 健康检查

### 5.1 添加健康检查

```python
from litefs import Litefs

app = Litefs()

# 添加健康检查
def check_database():
    try:
        db.connect()
        return True
    except Exception:
        return False

app.add_health_check('database', check_database)

# 添加就绪检查
def check_migrations():
    return migration_status.is_complete()

app.add_ready_check('migrations', check_migrations)

app.run()
```

### 5.2 健康检查端点

- 健康检查：`GET /health`
- 就绪检查：`GET /health/ready`

## 6. 缓存使用

### 6.1 内存缓存

```python
from litefs.cache import MemoryCache

cache = MemoryCache(max_size=10000)

# 添加缓存项
cache.put('key', 'value')

# 获取缓存项
value = cache.get('key')

# 删除缓存项
cache.delete('key')

# 清空缓存
cache.clear()

# 获取缓存大小
size = cache.size()
```

### 6.2 树缓存

```python
from litefs.cache import TreeCache

cache = TreeCache(max_size=10000)

# 添加缓存项
cache.put('user:1:name', 'John')

# 获取缓存项
name = cache.get('user:1:name')

# 删除缓存项
cache.delete('user:1:name')

# 清空缓存
cache.clear()

# 获取缓存大小
size = cache.size()
```

## 7. 会话管理

```python
from litefs import Litefs

app = Litefs()

# 在请求处理中使用会话
def handler(self):
    # 获取会话
    session = self.session
    
    # 设置会话数据
    session.set('user_id', 1)
    session.set('username', 'john')
    
    # 获取会话数据
    user_id = session.get('user_id')
    username = session.get('username')
    
    # 删除会话数据
    session.delete('user_id')
    
    # 清空会话
    # session.clear()
    
    return f"Hello, {username}!"
```

## 8. 模板使用

### 8.1 Mako 模板

创建 `site/templates/index.html`：

```html
<!DOCTYPE html>
<html>
<head>
    <title>${title}</title>
</head>
<body>
    <h1>${title}</h1>
    <p>Welcome, ${name}!</p>
    <ul>
    % for item in items:
        <li>${item}</li>
    % endfor
    </ul>
</body>
</html>
```

使用模板：

```python
from litefs import Litefs

app = Litefs()

def handler(self):
    # 渲染模板
    return self.render_template('templates/index.html',
                               title='Welcome',
                               name='John',
                               items=['Item 1', 'Item 2', 'Item 3'])
```

## 9. 静态文件服务

### 9.1 静态文件目录

将静态文件放在 `webroot/static/` 目录下，Litefs 会自动提供静态文件服务。

### 9.2 访问静态文件

```
http://localhost:8080/static/css/style.css
http://localhost:8080/static/js/script.js
http://localhost:8080/static/images/logo.png
```

## 10. 错误处理

### 10.1 404 页面

创建 `site/not_found.py` 文件：

```python
def handler(self):
    self.start_response(404, [('Content-Type', 'text/html')])
    return "<h1>404 Not Found</h1><p>The requested resource was not found.</p>"
```

### 10.2 自定义错误页面

```python
from litefs import Litefs
from litefs.exceptions import HttpError

app = Litefs()

def handler(self):
    # 抛出 HTTP 错误
    raise HttpError(401, 'Unauthorized')

# 自定义错误处理
def error_handler(self, status_code, message):
    self.start_response(status_code, [('Content-Type', 'text/html')])
    return f"<h1>{status_code} Error</h1><p>{message}</p>"

app.error_handler = error_handler
```

## 11. 最佳实践

### 11.1 代码结构

推荐的项目结构：

```
project/
├── app.py           # 应用入口
├── wsgi.py          # WSGI 应用
├── site/            # Web 根目录
│   ├── index.py     # 首页
│   ├── static/      # 静态文件
│   ├── templates/   # 模板文件
│   └── not_found.py # 404 页面
├── config/          # 配置文件
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
└── requirements.txt # 依赖文件
```

### 11.2 部署建议

1. **使用 WSGI 服务器**：在生产环境中使用 Gunicorn 或 uWSGI
2. **使用反向代理**：使用 Nginx 作为反向代理
3. **使用环境变量**：在容器化部署中使用环境变量
4. **配置监控**：添加健康检查和监控
5. **安全措施**：使用 HTTPS，限制访问，定期更新

### 11.3 性能优化

1. **使用缓存**：合理使用缓存减少重复计算
2. **优化静态文件**：启用 gzip 压缩，设置缓存头
3. **调整工作进程**：根据服务器配置调整工作进程数
4. **使用异步**：对于 I/O 密集型任务，使用 gevent worker
5. **数据库优化**：合理使用数据库索引，避免 N+1 查询

### 11.4 安全性

1. **输入验证**：验证所有用户输入
2. **防止 XSS**：对输出进行转义
3. **防止 CSRF**：使用 CSRF 令牌
4. **密码安全**：使用安全的密码哈希算法
5. **HTTPS**：在生产环境中使用 HTTPS
6. **权限控制**：实现适当的权限控制

## 12. 故障排查

### 12.1 查看日志

```bash
# 应用日志
tail -f default.log

# Gunicorn 日志
tail -f access.log error.log

# uWSGI 日志
tail -f /var/log/uwsgi.log

# Systemd 日志
journalctl -u litefs -f
```

### 12.2 检查进程

```bash
ps aux | grep gunicorn
ps aux | grep uwsgi
```

### 12.3 测试连接

```bash
curl -I http://localhost:8000/
```

### 12.4 常见问题

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

## 13. 相关文档

- [API 文档](api.md)
- [系统设计文档](system_design.md)
- [单元测试文档](unit-tests.md)
- [性能测试文档](performance-stress-tests.md)