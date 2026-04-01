# 快速入门示例

Litefs 快速入门示例，展示基本的 HTTP 服务器功能和新的路由系统。

## 目录结构

```
01-quickstart/
├── README.md         # 本说明文件
├── quickstart.py     # 启动文件
└── wsgi.py           # WSGI 应用文件
```

## 功能特性

- ✅ 基本 HTTP 服务器
- ✅ **新的路由系统**（装饰器风格和方法链风格）
- ✅ 路径参数支持
- ✅ 多种 HTTP 方法支持
- ✅ 静态文件服务
- ✅ 模板渲染
- ✅ JSON 响应
- ✅ 完整的 WSGI 支持

## 快速开始

### 1. 安装依赖

```bash
pip install "litefs[wsgi]"
```

### 2. 运行示例

#### 方式 1: 使用内置服务器

```bash
python quickstart.py
```

访问: http://localhost:8080

#### 方式 2: 使用 WSGI 服务器

```bash
# 使用 Gunicorn
gunicorn -w 4 -b :8000 wsgi:application

# 使用 uWSGI
uwsgi --http :8000 --wsgi-file wsgi.py

# 使用 Waitress
waitress-serve --port=8000 wsgi:application
```

### 3. 访问端点

- **Hello World 路由**（装饰器风格）: http://localhost:8080/hello
- **用户详情路由**（带路径参数）: http://localhost:8080/user/123
- **表单提交路由**（POST）: http://localhost:8080/form
- **Hello World 路由**（方法链风格）: http://localhost:8080/hello_route

## WSGI 部署

本示例包含 `wsgi.py` 文件，可直接用于 WSGI 服务器部署。

### 配置文件

使用项目根目录下的 `examples/wsgi-configs/` 目录中的配置文件：

```bash
# 使用 Gunicorn 配置
gunicorn -c ../wsgi-configs/gunicorn.conf.py wsgi:application

# 使用 uWSGI 配置
uwsgi --ini ../wsgi-configs/uwsgi.ini

# 使用 Waitress 配置
waitress-serve --config ../wsgi-configs/waitress.ini wsgi:application
```

## 代码说明

### 1. 启动文件 (`quickstart.py`)

创建 Litefs 应用实例，配置基本参数，启动内置服务器。同时展示了新的路由系统的使用方法：

- **装饰器风格路由定义**：使用 `@get`、`@post` 等装饰器
- **方法链风格路由定义**：使用 `@app.add_get`、`@app.add_post` 等方法
- **路径参数**：支持 `/user/{id}` 这样的路径参数



### 3. WSGI 应用 (`wsgi.py`)

创建 WSGI 应用实例，用于部署到 WSGI 服务器。