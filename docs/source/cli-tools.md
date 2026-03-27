# CLI 工具

Litefs 提供了强大的命令行工具（CLI），帮助您快速创建项目和启动开发服务器。

## 安装

安装 Litefs 后，`litefs` 命令会自动添加到系统路径：

```bash
pip install litefs
```

## 命令概览

```bash
litefs --help
```

输出：

```
usage: litefs [-h] {startproject,runserver,version} ...

positional arguments:
  {startproject,runserver,version}
    startproject        创建一个新的 Litefs 项目
    runserver           启动开发服务器
    version             显示版本信息

options:
  -h, --help            show this help message and exit
```

## startproject - 创建项目

创建一个新的 Litefs 项目脚手架。

### 基本用法

```bash
litefs startproject <project_name>
```

### 示例

```bash
litefs startproject myapp
```

### 参数

- `project_name` (必需): 项目名称，必须是有效的 Python 标识符
- `--directory` (可选): 目标目录，默认为当前目录

### 项目结构

创建的项目包含以下结构：

```
myapp/
├── app.py              # 应用入口
├── config.yaml         # 配置文件
├── requirements.txt    # Python 依赖
├── README.md          # 项目说明
├── .gitignore         # Git 忽略文件
├── site/              # Web 根目录（包含静态文件和动态文件）
│   ├── static/        # 静态文件
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── *.py          # 动态文件（可选）
├── templates/         # 模板文件
│   └── index.html
├── apps/             # 应用模块
│   ├── __init__.py
│   └── home/         # 首页应用
│       ├── __init__.py
│       └── handlers.py
└── config/           # 配置模块
    ├── __init__.py
    ├── settings.py     # 应用配置
    └── routes.py      # 路由定义
```

**说明：**
- `site/` 是 Web 根目录（webroot），包含所有可通过 HTTP 访问的文件
- `site/static/` 存放静态文件（CSS、JS、图片等）
- `site/*.py` 可以放置动态 Python 文件，会作为 CGI 脚本执行
- `templates/` 存放模板文件，用于服务端渲染
- `apps/` 存放应用模块，按功能模块组织代码
- `config/` 存放配置和路由定义，集中管理应用配置

### 生成的文件说明

#### app.py

应用入口文件，包含 `create_app()` 函数：

```python
from litefs import Litefs
from litefs.middleware import (
    CORSMiddleware,
    LoggingMiddleware,
    SecurityMiddleware,
    HealthCheck,
)
from litefs.config import load_config


def create_app():
    config = load_config(config_file="config.yaml")
    
    litefs = (
        Litefs(**config.to_dict())
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
        .add_middleware(HealthCheck)
    )
    
    return litefs


if __name__ == "__main__":
    app = create_app()
    app.run()
```

#### config.yaml

配置文件，包含服务器、日志、CORS 等配置：

```yaml
# Litefs 配置文件

# 服务器配置
host: "0.0.0.0"
port: 9090
workers: 1
debug: true

# Web 根目录
webroot: "./site"

# 模板目录
template_dir: "./templates"

# 上传配置
max_upload_size: 52428800  # 50MB

# 日志配置
log_level: "INFO"
log_file: "app.log"

# CORS 配置
cors:
  allow_origins: ["*"]
  allow_methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  allow_headers: ["Content-Type", "Authorization"]
  allow_credentials: true
  max_age: 3600

# 健康检查配置
health_check:
  enabled: true
  path: "/health"
  ready_path: "/health/ready"
```

**说明：**
- `webroot: "./site"` 指定 Web 根目录为 `site/`
- `site/` 目录可以包含：
  - `static/` 子目录：存放静态文件（CSS、JS、图片等）
  - `*.py` 文件：动态 Python 文件，会作为 CGI 脚本执行
- `template_dir: "./templates"` 指定模板目录，用于服务端渲染

#### requirements.txt

项目依赖文件：

```txt
# 项目依赖
litefs>=0.4.0

# 可选依赖
# gunicorn>=20.1.0  # 生产环境 WSGI 服务器
# uwsgi>=2.0.20     # 生产环境 WSGI 服务器
# waitress>=2.1.0   # Windows 生产环境 WSGI 服务器
```

#### templates/index.html

服务端模板文件，用于服务端渲染。

#### site/index.html

默认首页页面，包含完整的 HTML 结构和样式。访问 `http://localhost:9090/` 时会显示此页面。

#### static/css/style.css

默认样式文件，提供响应式设计。

#### wsgi.py

WSGI 入口文件，用于生产环境部署。包含：

```python
#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.dont_write_bytecode = True

import litefs

# 配置 Litefs 应用
app = litefs.Litefs(
    webroot='./site',
    debug=False,
    log='./wsgi_access.log'
)

# 获取 WSGI application callable
application = app.wsgi()
```

**使用方法：**

```bash
# Gunicorn
gunicorn -w 4 -b :9090 wsgi:application

# uWSGI
uwsgi --http :9090 --wsgi-file wsgi.py

# Waitress (Windows)
waitress-serve --port=9090 wsgi:application
```

## 目录结构说明

### apps/ 目录

`apps/` 目录用于存放应用模块，按功能模块组织代码。

#### 目录结构

```
apps/
├── __init__.py
├── home/              # 首页模块
│   ├── __init__.py
│   └── handlers.py    # 处理函数
├── user/              # 用户模块（示例）
│   ├── __init__.py
│   └── handlers.py
└── api/               # API 模块（示例）
    ├── __init__.py
    └── handlers.py
```

#### 使用示例

**创建新模块：**

```bash
# 创建 user 模块
mkdir -p apps/user
touch apps/user/__init__.py
touch apps/user/handlers.py
```

**定义处理函数：**

```python
# apps/user/handlers.py
def profile_handler(self):
    """用户资料页面"""
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>用户资料</title>
    </head>
    <body>
        <h1>用户资料</h1>
        <p>这是用户资料页面</p>
    </body>
    </html>
    '''
    
    return [html]
```

**注册路由：**

```python
# config/routes.py
from apps.user.handlers import profile_handler

routes = {
    '/': home_handler,
    '/about': about_handler,
    '/user/profile': profile_handler,  # 新增路由
}
```

### config/ 目录

`config/` 目录用于存放配置和路由定义，集中管理应用配置。

#### 目录结构

```
config/
├── __init__.py
├── settings.py    # 应用配置
└── routes.py     # 路由定义
```

#### config/settings.py

应用配置文件，集中管理所有配置项：

```python
class Settings:
    """应用配置类"""
    
    # 应用信息
    APP_NAME = "Litefs Application"
    APP_VERSION = "1.0.0"
    
    # 数据库配置
    DATABASE_URL = "sqlite:///app.db"
    
    # 缓存配置
    CACHE_ENABLED = True
    CACHE_TTL = 3600
    
    # 邮件配置
    MAIL_ENABLED = False
    MAIL_FROM = "noreply@example.com"
    
    # 第三方服务配置
    API_KEY = ""
    API_SECRET = ""
    
    @classmethod
    def load_from_env(cls):
        """从环境变量加载配置"""
        import os
        
        cls.DATABASE_URL = os.getenv("DATABASE_URL", cls.DATABASE_URL)
        cls.API_KEY = os.getenv("API_KEY", cls.API_KEY)
        cls.API_SECRET = os.getenv("API_SECRET", cls.API_SECRET)
        
        return cls


# 创建全局配置实例
settings = Settings()
settings.load_from_env()
```

**使用配置：**

```python
# 在任何地方使用配置
from config import settings

print(f"应用名称: {settings.APP_NAME}")
print(f"数据库: {settings.DATABASE_URL}")
```

#### config/routes.py

路由定义文件，集中管理所有路由：

```python
from apps.home.handlers import home_handler, about_handler
from apps.user.handlers import profile_handler

# 路由映射表
routes = {
    '/': home_handler,
    '/about': about_handler,
    '/user/profile': profile_handler,
}


def get_routes():
    """获取所有路由"""
    return routes


def add_route(path, handler):
    """添加路由"""
    routes[path] = handler


def get_handler(path):
    """根据路径获取处理函数"""
    return routes.get(path)
```

**动态添加路由：**

```python
# 在运行时添加路由
from config.routes import add_route
from apps.user.handlers import login_handler

add_route('/user/login', login_handler)
```

## runserver - 启动开发服务器

启动 Litefs 开发服务器。

### 基本用法

```bash
cd <project_directory>
litefs runserver
```

### 示例

```bash
cd myapp
litefs runserver
```

### 参数

- `--host` (可选): 服务器地址，默认为 `0.0.0.0`
- `-p, --port` (可选): 服务器端口，默认为 `9090`
- `-c, --config` (可选): 配置文件路径

### 示例

```bash
# 使用默认配置
litefs runserver

# 指定端口
litefs runserver --port 8000

# 指定主机和端口
litefs runserver --host 127.0.0.1 --port 8000

# 使用自定义配置文件
litefs runserver --config myconfig.yaml
```

### 注意事项

- 必须在项目根目录下运行（包含 `app.py` 文件）
- 服务器启动后，访问 `http://localhost:9090` 查看应用
- 按 `Ctrl+C` 停止服务器

## version - 显示版本信息

显示 Litefs 版本信息。

### 基本用法

```bash
litefs version
```

### 输出示例

```
Litefs 0.4.0
一个轻量级的 Python Web 框架

使用 'litefs --help' 查看帮助信息
```

## 快速开始

### 1. 创建项目

```bash
litefs startproject myapp
cd myapp
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 启动开发服务器

```bash
litefs runserver
```

### 4. 访问应用

打开浏览器访问: http://localhost:9090

## 开发工作流

### 添加路由

在 `app.py` 中添加路由处理函数：

```python
@app.route("/hello")
def hello(request):
    return "Hello, World!"
```

### 使用模板

```python
@app.route("/")
def index(request):
    return app.render_template("index.html", title="首页")
```

### 添加中间件

```python
from litefs.middleware import YourMiddleware

app.add_middleware(YourMiddleware)
```

## 生产部署

### 使用 Gunicorn

```bash
gunicorn app:app -w 4 -b 0.0.0.0:9090
```

### 使用 uWSGI

```bash
uwsgi --http :9090 --wsgi-file app.py --callable app --processes 4
```

### 使用 Waitress (Windows)

```bash
waitress-serve --port=9090 app:app
```

## 常见问题

### Q: 如何在已存在的项目中使用 CLI？

A: 您可以手动创建 `app.py` 文件，然后使用 `litefs runserver` 启动服务器。

### Q: 如何自定义项目模板？

A: 目前 CLI 工具使用内置模板。您可以创建项目后，根据需要修改文件。

### Q: 如何添加更多中间件？

A: 在 `app.py` 中使用 `add_middleware()` 方法添加中间件：

```python
app.add_middleware(YourMiddleware, option1=value1, option2=value2)
```

### Q: 如何配置不同的环境？

A: 创建多个配置文件（如 `config.dev.yaml`, `config.prod.yaml`），然后使用 `--config` 参数指定：

```bash
litefs runserver --config config.prod.yaml
```

### Q: 如何使用环境变量？

A: 在 `config.yaml` 中使用环境变量，或在 `app.py` 中通过 `os.environ` 读取：

```python
import os

host = os.getenv('LITEFS_HOST', '0.0.0.0')
port = int(os.getenv('LITEFS_PORT', '9090'))
```

## 相关文档

- [配置管理](config-management.html)
- [中间件指南](middleware-guide.html)
- [WSGI 部署](wsgi-deployment.html)
- [开发指南](development.html)
