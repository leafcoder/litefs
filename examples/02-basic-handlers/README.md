# 基础处理器示例

Litefs 基础处理器示例，展示不同类型的 HTTP 响应处理和新的路由系统。

## 目录结构

```
02-basic-handlers/
├── site/             # 处理函数
│   ├── error.py      # 错误处理
│   ├── form.py       # 表单处理
│   ├── generator.py  # 生成器响应
│   ├── html.py       # HTML 响应
│   ├── json.py       # JSON 响应
│   ├── json_complex.py  # 复杂 JSON 响应
│   ├── json_custom_header.py  # 带自定义头部的 JSON
│   ├── json_error.py  # JSON 错误响应
│   ├── json_html.py   # JSON 和 HTML 混合
│   ├── mixed.py      # 混合响应
│   ├── mixed_tuple.py  # 元组形式响应
│   ├── mixed_tuple_text.py  # 文本元组响应
│   └── text.py       # 文本响应
├── README.md         # 本说明文件
├── basic_handlers_example.py  # 启动文件
└── wsgi.py           # WSGI 应用文件
```

## 功能特性

- ✅ 多种响应类型
- ✅ JSON 响应
- ✅ HTML 响应
- ✅ 文本响应
- ✅ 生成器响应
- ✅ 错误处理
- ✅ 表单处理
- ✅ **新的路由系统**（装饰器风格）
- ✅ 完整的 WSGI 支持

## 快速开始

### 1. 安装依赖

```bash
pip install "litefs[wsgi]"
```

### 2. 运行示例

#### 方式 1: 使用内置服务器

```bash
python basic_handlers_example.py
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

- **首页**: http://localhost:8080/
- **HTML 响应**: http://localhost:8080/html
- **文本响应**: http://localhost:8080/text
- **JSON 响应**: http://localhost:8080/json
- **表单处理**: http://localhost:8080/form
- **错误处理**: http://localhost:8080/error

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

### 1. 启动文件 (`basic_handlers_example.py`)

创建 Litefs 应用实例，配置基本参数，启动内置服务器。同时展示了新的路由系统的使用方法：

- **装饰器风格路由定义**：使用 `@get`、`@post` 等装饰器
- **路由注册**：使用 `app.register_routes()` 注册路由

### 2. 处理函数

- **html.py**: 返回 HTML 响应
- **text.py**: 返回文本响应
- **json.py**: 返回 JSON 响应
- **form.py**: 处理表单提交
- **error.py**: 处理错误情况
- **generator.py**: 使用生成器返回响应
- **mixed.py**: 混合多种响应类型

### 3. WSGI 应用 (`wsgi.py`)

创建 WSGI 应用实例，用于部署到 WSGI 服务器。