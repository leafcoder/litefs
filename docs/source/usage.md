# 使用文档

## 1. 快速开始

### 1.1 安装

```bash
pip install litefs
```

### 1.2 使用脚手架创建项目

Litefs 提供了脚手架命令，可以快速创建项目结构：

```bash
# 创建新项目
litefs startproject myproject

# 进入项目目录
cd myproject

# 查看项目结构
tree
```

生成的项目结构：

```
myproject/
├── app.py              # 主应用文件
├── config.yaml         # 配置文件
├── requirements.txt    # 依赖文件
├── README.md          # 项目说明
├── wsgi.py            # WSGI 应用文件
├── templates/         # 模板目录
│   ├── index.html     # 首页模板
│   └── about.html     # 关于页面模板
└── static/            # 静态文件目录
    ├── css/
    │   └── style.css  # 样式文件
    ├── js/            # JavaScript 文件目录
    └── images/        # 图片文件目录
```

### 1.3 运行开发服务器

```bash
# 方式一：直接运行 app.py
python app.py

# 方式二：使用 CLI 命令
litefs runserver
```

访问 `http://localhost:9090/` 查看结果。

### 1.4 基本使用示例

#### 方式一：使用装饰器定义路由

```python
from litefs import Litefs
from litefs.routing import get, post

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)

@get('/', name='index')
def index_handler(request):
    """首页处理函数"""
    return {'message': 'Hello, World!'}

@get('/user/{id}', name='user_detail')
def user_handler(request, id):
    """用户详情处理函数"""
    return {'user_id': id, 'message': f'User details for ID {id}'}

@post('/form', name='form_submit')
def form_handler(request):
    """表单处理函数"""
    return {'message': 'Form submitted', 'data': request.data}

# 注册装饰器定义的路由
app.register_routes(__name__)

app.run()
```

#### 方式二：使用方法链添加路由

```python
from litefs import Litefs

app = Litefs()

@app.add_get('/hello', name='hello')
def hello_handler(request):
    return {'message': 'Hello from route!'}

@app.add_post('/api/data', name='api_data')
def api_data_handler(request):
    return {'data': request.data}

app.run()
```

#### 方式三：传统方式添加路由

```python
from litefs import Litefs

app = Litefs()

def index_handler(request):
    return 'Hello, World!'

def user_detail_handler(request, id):
    return f'User ID: {id}'

app.add_get('/', index_handler, name='index')
app.add_get('/user/{id}', user_detail_handler, name='user_detail')

app.run()
```

### 1.5 返回 HTML 页面

当需要返回 HTML 页面时，使用 `request.start_response` 设置 Content-Type：

```python
@get('/page', name='page')
def page_handler(request):
    """返回 HTML 页面"""
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>My Page</title></head>
    <body><h1>Hello, World!</h1></body>
    </html>
    '''
```

从文件读取模板：

```python
@get('/', name='index')
def index_handler(request):
    """首页处理函数"""
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        content = f.read().replace('${project_name}', 'My Project')
    return content
```

### 1.6 示例应用

Litefs 提供了丰富的示例，帮助您快速上手和深入学习。

#### 示例目录结构

```
examples/
├── 01-quickstart/              # 快速入门
├── 02-basic-handlers/          # 基础处理器
├── 03-configuration/          # 配置管理
├── 04-middleware/             # 中间件
├── 05-session/                # 会话管理
├── 06-cache/                  # 缓存
├── 07-health-check/           # 健康检查
├── 09-fullstack/              # 完整应用
├── 10-cache-backends-web/     # 缓存后端 Web
├── 11-cache-usage/            # 缓存使用
├── 12-session-backends/       # 会话后端
├── 14-routing/                # 路由系统
├── 15-static-files/           # 静态文件
└── common/                    # 公共资源
```

#### 学习路径

1. **快速入门** - 从 [01-quickstart](../examples/01-quickstart/) 开始，了解 Litefs 的基本用法
2. **基础处理器** - 学习 [02-basic-handlers](../examples/02-basic-handlers/)，掌握各种响应类型
3. **配置管理** - 了解 [03-configuration](../examples/03-configuration/)，学习配置方式
4. **中间件** - 探索 [04-middleware](../examples/04-middleware/)，使用中间件增强功能
5. **会话管理** - 学习 [05-session](../examples/05-session/)，管理用户会话状态
6. **缓存** - 了解 [06-cache](../examples/06-cache/)，使用缓存提高性能
7. **健康检查** - 学习 [07-health-check](../examples/07-health-check/)，实现健康监控
8. **路由系统** - 掌握 [14-routing](../examples/14-routing/)，使用现代路由系统
9. **静态文件** - 学习 [15-static-files](../examples/15-static-files/)，提供静态资源
10. **完整应用** - 参考 [09-fullstack](../examples/09-fullstack/)，构建完整应用

#### 运行示例

每个示例都可以独立运行：

```bash
cd examples/<example-directory>
python <example-file>.py
```

#### 完整示例应用

[09-fullstack](../examples/09-fullstack/) 是一个完整的 Web 应用示例，展示了框架的核心功能和最佳实践。

##### 目录结构

```
examples/09-fullstack/
├── app.py          # 应用主文件
├── wsgi.py         # WSGI 应用文件
└── README.md       # 说明文档
```

##### 功能特性

- **路由处理**：基本的页面路由和处理
- **表单处理**：联系表单提交和验证
- **会话管理**：用户会话和访问历史记录
- **缓存使用**：内存缓存示例
- **中间件集成**：日志、安全、CORS、限流中间件
- **静态文件服务**：CSS 样式和静态资源
- **健康检查**：应用健康状态和就绪检查
- **响应式设计**：适配不同屏幕尺寸

##### 运行示例

```bash
# 进入示例目录
cd examples/09-fullstack

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

##### 生产部署

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

## 2. 路由系统

### 2.1 装饰器风格

```python
from litefs import Litefs
from litefs.routing import get, post, put, delete

app = Litefs()

@get('/', name='index')
def index_handler(request):
    return 'Hello, World!'

@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return f'User ID: {id}'

@post('/login', name='login')
def login_handler(request):
    username = request.data.get('username')
    password = request.data.get('password')
    return {'status': 'success', 'username': username}

# 注册装饰器定义的路由
app.register_routes(__name__)
app.run()
```

### 2.2 方法链风格

```python
from litefs import Litefs

app = Litefs()

@app.add_get('/hello', name='hello')
def hello_handler(request):
    return {'message': 'Hello from route!'}

@app.add_post('/api/data', name='api_data')
def api_data_handler(request):
    return {'data': request.data}

app.run()
```

### 2.3 传统方式

```python
from litefs import Litefs

app = Litefs()

def index_handler(request):
    return 'Hello, World!'

def user_detail_handler(request, id):
    return f'User ID: {id}'

app.add_get('/', index_handler, name='index')
app.add_get('/user/{id}', user_detail_handler, name='user_detail')

app.run()
```

### 2.4 路径参数

```python
@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return f'User ID: {id}'

@get('/user/{id}/posts/{post_id}', name='user_post')
def user_post_handler(request, id, post_id):
    return f'User ID: {id}, Post ID: {post_id}'
```

### 2.5 HTTP 方法

支持以下 HTTP 方法：

* GET
* POST
* PUT
* DELETE
* PATCH
* OPTIONS
* HEAD

```python
from litefs.routing import get, post, put, delete, patch, options, head

@get('/resource', name='get_resource')
def get_resource_handler(request):
    return {'method': 'GET'}

@post('/resource', name='create_resource')
def create_resource_handler(request):
    return {'method': 'POST'}

@put('/resource/{id}', name='update_resource')
def update_resource_handler(request, id):
    return {'method': 'PUT', 'id': id}

@delete('/resource/{id}', name='delete_resource')
def delete_resource_handler(request, id):
    return {'method': 'DELETE', 'id': id}
```

### 2.6 请求属性

在路由处理函数中，`request` 对象提供了以下属性：

* **request.params**：GET 参数（字典）
* **request.data**：POST 参数（字典）
* **request.files**：上传的文件（字典）
* **request.body**：原始请求体（字节）
* **request.environ**：WSGI 环境变量
* **request.method**：HTTP 方法
* **request.path_info**：请求路径
* **request.headers**：请求头
* **request.route_params**：路由路径参数

```python
@get('/search', name='search')
def search_handler(request):
    query = request.params.get('query', '')
    page = int(request.params.get('page', '1'))
    return {'query': query, 'page': page}

@post('/form', name='form')
def form_handler(request):
    name = request.data.get('name')
    email = request.data.get('email')
    return {'name': name, 'email': email}
```

### 2.7 设置响应头部

使用 `request.start_response` 方法设置响应状态码和头部：

```python
@get('/html', name='html_page')
def html_page_handler(request):
    """返回 HTML 页面"""
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    return '<h1>Hello, World!</h1>'

@get('/json', name='json_data')
def json_data_handler(request):
    """返回 JSON 数据"""
    import json
    request.start_response(200, [('Content-Type', 'application/json; charset=utf-8')])
    return json.dumps({'message': 'Hello'})
```

## 3. 静态文件

### 3.1 基本使用

```python
from litefs import Litefs

app = Litefs()

# 添加静态文件路由
app.add_static('/static', './static', name='static')

app.run()
```

### 3.2 访问静态文件

```
http://localhost:8080/static/css/style.css
http://localhost:8080/static/js/app.js
http://localhost:8080/static/images/logo.png
```

### 3.3 目录结构

推荐的静态文件目录结构：

```
project/
├── app.py
└── static/
    ├── css/           # CSS 样式文件
    ├── js/            # JavaScript 文件
    ├── images/        # 图片文件
    ├── fonts/         # 字体文件
    └── assets/        # 其他资源
```

### 3.4 安全特性

* 自动防止路径遍历攻击
* 自动检测 MIME 类型
* 支持 HEAD 和 GET 方法
* 自动处理 404 和 403 错误

## 4. 配置管理

### 4.1 配置来源

Litefs 支持多种配置来源，按优先级从高到低排列：

1. **代码配置** - 通过代码直接设置配置项
2. **环境变量** - 通过环境变量设置配置（前缀：`LITEFS_`）
3. **配置文件** - 通过 YAML、JSON 或 TOML 文件设置配置
4. **默认配置** - 系统内置的默认值

### 4.2 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|---------|------|
| `host` | str | `localhost` | 服务器监听地址 |
| `port` | int | `9090` | 服务器监听端口 |
| `debug` | bool | `false` | 调试模式 |
| `log` | str | `./default.log` | 日志文件路径 |
| `listen` | int | `1024` | 服务器监听队列大小 |
| `max_request_size` | int | `10485760` | 最大请求体大小（字节，默认 10MB） |
| `max_upload_size` | int | `52428800` | 最大上传文件大小（字节，默认 50MB） |
| `config_file` | str | `None` | 配置文件路径 |
| `session_backend` | str | `memory` | 会话后端（memory/redis/database/memcache） |
| `session_expiration_time` | int | `3600` | 会话过期时间（秒） |
| `session_name` | str | `litefs_session` | 会话 cookie 名称 |
| `session_secure` | bool | `false` | 是否使用安全 cookie |
| `session_http_only` | bool | `true` | 是否仅 HTTP 访问 cookie |
| `session_same_site` | str | `Lax` | SameSite 策略（Strict, Lax, None） |
| `cache_backend` | str | `tree` | 缓存后端（memory, tree, redis, database, memcache） |

### 4.3 使用方法

#### 4.3.1 使用代码配置

```python
from litefs import Litefs

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    max_request_size=20971520,
)

app.run()
```

#### 4.3.2 使用配置文件

创建 `config.yaml`：

```yaml
host: localhost
port: 9090
debug: false
log: ./default.log
listen: 1024
max_request_size: 10485760
max_upload_size: 52428800
session_backend: memory
session_expiration_time: 3600
session_name: my_session
session_secure: false
session_http_only: true
session_same_site: Lax
cache_backend: tree
```

使用配置文件：

```python
from litefs import Litefs

app = Litefs(config_file='config.yaml')
app.run()
```

#### 4.3.3 使用环境变量

设置环境变量：

```bash
export LITEFS_HOST=0.0.0.0
export LITEFS_PORT=8080
export LITEFS_DEBUG=true
export LITEFS_MAX_REQUEST_SIZE=20971520
```

使用环境变量：

```python
from litefs import Litefs

app = Litefs()
app.run()
```

## 5. WSGI 部署

### 5.1 创建 WSGI 应用文件

创建 `wsgi.py` 文件：

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.dont_write_bytecode = True

from litefs import Litefs

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=9090,
    debug=False,
    config_file='config.yaml'
)

# 挂载静态文件目录
app.add_static('/static', 'static')

# 定义处理函数
def index_handler(request):
    """首页处理函数"""
    request.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    return content

# 添加路由
app.add_get('/', index_handler, name='index')

# 创建 WSGI 应用
application = app.wsgi()
```

### 5.2 使用 Gunicorn 部署

#### 安装 Gunicorn

```bash
pip install gunicorn
```

#### 启动服务器

```bash
# 基本启动
gunicorn -w 4 -b :8000 wsgi:application

# 生产环境推荐配置
gunicorn -w 4 -k gevent -b 0.0.0.0:8000 \
  --access-logfile access.log \
  --error-logfile error.log \
  --log-level info \
  --timeout 30 \
  --keepalive 5 \
  wsgi:application
```

### 5.3 使用 uWSGI 部署

#### 安装 uWSGI

```bash
pip install uwsgi
```

#### 启动服务器

```bash
# 基本启动
uwsgi --http :8000 --wsgi-file wsgi.py

# 生产环境推荐配置
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

### 5.4 使用 Waitress 部署（Windows 推荐）

#### 安装 Waitress

```bash
pip install waitress
```

#### 启动服务器

```bash
# 基本启动
waitress-serve --port=8000 wsgi:application

# 生产环境推荐配置
waitress-serve --port=8000 \
  --threads=4 \
  --url-prefix=/ \
  --log-untrusted-proxy-headers=true \
  wsgi:application
```

### 5.5 Nginx 反向代理配置

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
        alias /path/to/your/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 5.6 Systemd 服务配置

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
    wsgi:application
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

### 5.7 Docker 部署

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
     "wsgi:application"]
```

构建和运行：

```bash
docker build -t litefs .
docker run -d -p 8000:8000 -v $(pwd)/static:/app/static litefs
```

## 6. 中间件使用

### 6.1 内置中间件

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

### 6.2 自定义中间件

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

## 7. 健康检查

### 7.1 添加健康检查

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

### 7.2 健康检查端点

- 健康检查：`GET /health`
- 就绪检查：`GET /health/ready`

## 8. 缓存使用

### 8.1 内存缓存

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

### 8.2 树缓存

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

## 9. 会话管理

```python
from litefs import Litefs

app = Litefs()

# 在请求处理中使用会话
@get('/session', name='session')
def session_handler(request):
    # 获取会话
    session = request.session
    
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

## 10. 错误处理

### 10.1 自定义错误处理

```python
from litefs import Litefs
from litefs.exceptions import HttpError

app = Litefs()

@get('/error', name='error')
def error_handler(request):
    # 抛出 HTTP 错误
    raise HttpError(401, 'Unauthorized')

# 自定义错误处理
def error_handler_func(self, status_code, message):
    self.start_response(status_code, [('Content-Type', 'text/html')])
    return f"<h1>{status_code} Error</h1><p>{message}</p>"

app.error_handler = error_handler_func
```

## 11. 最佳实践

### 11.1 代码结构

推荐的项目结构：

```
project/
├── app.py           # 应用入口
├── wsgi.py          # WSGI 应用
├── config.yaml      # 配置文件
├── requirements.txt # 依赖文件
├── routes/          # 路由模块（可选）
│   ├── __init__.py
│   ├── users.py
│   └── posts.py
├── static/          # 静态文件
│   ├── css/
│   ├── js/
│   └── images/
├── templates/       # 模板文件
│   ├── index.html
│   └── about.html
└── README.md        # 项目说明
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
gunicorn -w 2 wsgi:application
```
