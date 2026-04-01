# Litefs 路由系统

Litefs 提供了一个现代、灵活的路由系统，支持多种路由定义方式和功能特性。

## 功能特性

- ✅ 装饰器风格路由定义
- ✅ 方法链风格路由定义
- ✅ 路径参数支持（如 `/user/{id}`）
- ✅ 多种 HTTP 方法支持（GET, POST, PUT, DELETE 等）
- ✅ 路由命名与反向解析
- ✅ 优先级路由匹配
- ✅ 静态文件路由支持
- ✅ 安全防护（防止路径遍历攻击）

## 快速开始

### 1. 基本路由定义

#### 装饰器风格

```python
from litefs import Litefs
from litefs.routing import get, post

app = Litefs()

# 定义 GET 路由
@get('/hello', name='hello')
def hello_handler(request):
    return 'Hello, World!'

# 定义 POST 路由
@post('/form', name='form')
def form_handler(request):
    return {'status': 'success', 'message': 'Form submitted'}

# 注册路由
app.register_routes(__name__)

app.run()
```

#### 方法链风格

```python
from litefs import Litefs

app = Litefs()

# 定义 GET 路由
def hello_handler(request):
    return 'Hello, World!'

# 定义 POST 路由
def form_handler(request):
    return {'status': 'success', 'message': 'Form submitted'}

# 使用方法链添加路由
app.add_get('/hello', hello_handler, name='hello')
app.add_post('/form', form_handler, name='form')

app.run()
```

### 2. 路径参数

```python
from litefs.routing import get

@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return f'User ID: {id}'

@get('/user/{id}/posts/{post_id}', name='user_post')
def user_post_handler(request, id, post_id):
    return f'User ID: {id}, Post ID: {post_id}'
```

### 3. 路由注册

```python
# 注册当前模块的路由
app.register_routes(__name__)

# 注册其他模块的路由
import routes_module
app.register_routes(routes_module)

# 注册模块名称字符串
app.register_routes('myapp.routes')
```

## 核心概念

### 1. 路由匹配

Litefs 路由系统使用正则表达式进行路径匹配，支持：
- 精确匹配（如 `/hello`）
- 路径参数（如 `/user/{id}`）
- 优先级排序（更具体的路由优先匹配）

### 2. HTTP 方法支持

支持以下 HTTP 方法：
- GET
- POST
- PUT
- DELETE
- PATCH
- OPTIONS
- HEAD

### 3. 路由命名与反向解析

```python
# 定义命名路由
@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    pass

# 反向解析 URL
url = app.router.url_for('user_detail', id=123)  # 生成 '/user/123'
```

### 4. 静态文件路由

Litefs 提供了静态文件路由功能，可以轻松地提供静态资源（如 CSS、JavaScript、图片等）。

```python
from litefs import Litefs

app = Litefs()

# 添加静态文件路由
app.add_static('/static', './static', name='static')

# 访问静态文件
# http://localhost:8080/static/css/style.css
# http://localhost:8080/static/js/app.js
# http://localhost:8080/static/images/logo.png
```

**安全特性**：
- 自动防止路径遍历攻击（如 `../../../etc/passwd`）
- 自动检测 MIME 类型
- 支持 HEAD 和 GET 方法
- 自动处理 404 和 403 错误

**目录结构示例**：
```
project/
├── app.py
└── static/
    ├── css/
    │   └── style.css
    ├── js/
    │   └── app.js
    └── images/
        └── logo.png
```

## 请求属性

在路由处理函数中，`request` 对象提供了以下属性：

- **request.params**：GET 参数（字典）
- **request.data**：POST 参数（字典）
- **request.files**：上传的文件（字典）
- **request.body**：原始请求体（字节）
- **request.environ**：WSGI 环境变量
- **request.request_method**：HTTP 方法
- **request.path**：请求路径
- **request.headers**：请求头
- **request.route_params**：路由路径参数

## 最佳实践

### 1. 路由组织

- **模块化**：将路由按功能模块组织到不同文件中
- **命名规范**：使用清晰、一致的路由命名
- **路径设计**：使用 RESTful 风格的路径设计

### 2. 性能优化

- **路由顺序**：将常用路由放在前面
- **路径复杂度**：避免过于复杂的路径模式
- **缓存**：路由系统内部使用缓存提高匹配速度

### 3. 错误处理

```python
from litefs.exceptions import RouteNotFound

try:
    route_match = app.router.match(path, method)
except RouteNotFound:
    # 处理路由未找到的情况
    pass
```

## 示例代码

### 完整示例

```python
from litefs import Litefs
from litefs.routing import get, post

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

# 装饰器风格路由
@get('/', name='index')
def index_handler(request):
    return 'Home Page'

@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return f'User: {id}'

@post('/login', name='login')
def login_handler(request):
    username = request.data.get('username')
    password = request.data.get('password')
    return {'status': 'success', 'username': username}

# 方法链风格路由
def about_handler(request):
    return 'About Page'

app.add_get('/about', about_handler, name='about')

# 注册路由
app.register_routes(__name__)

# 运行应用
app.run()
```

### 测试示例

```python
import requests

# 测试 GET 路由
response = requests.get('http://localhost:8080/')
print(response.text)  # 输出: Home Page

# 测试路径参数
response = requests.get('http://localhost:8080/user/123')
print(response.text)  # 输出: User: 123

# 测试 POST 路由
response = requests.post('http://localhost:8080/login', data={'username': 'test', 'password': 'pass'})
print(response.json())  # 输出: {'status': 'success', 'username': 'test'}
```

## 兼容性

- **WSGI 兼容**：支持在 WSGI 服务器中使用
- **ASGI 准备**：为未来的 ASGI 支持做好准备

## 常见问题

### 1. 路由冲突

如果两个路由路径模式冲突，更具体的路由会优先匹配。例如：
- `/user/{id}` 会匹配 `/user/123`
- `/user/admin` 会优先匹配精确路径

### 2. 路径参数类型

路径参数默认是字符串类型，需要在处理函数中进行类型转换：

```python
@get('/user/{id}')
def user_handler(request, id):
    user_id = int(id)  # 转换为整数
    # 处理逻辑...
```

### 3. 静态文件访问

静态文件路由支持子路径访问，例如：

```python
app.add_static('/static', './static')

# 可以访问：
# /static/css/style.css
# /static/js/app.js
# /static/images/logo.png
```

**安全注意事项**：
- 静态文件路由会自动阻止路径遍历攻击
- 确保静态文件目录权限正确
- 不要将敏感文件放在静态文件目录中

### 4. 路由注册失败

确保：
- 路由装饰器正确导入
- 路由处理函数正确定义
- `register_routes` 方法被调用
- 模块名称或对象正确传递

## 总结

Litefs 路由系统提供了一种现代、灵活的方式来定义和管理 HTTP 路由，支持多种路由定义方式和功能特性，同时保持与传统文件系统路由的兼容性。通过使用装饰器风格或方法链风格的路由定义，开发者可以更清晰、更高效地组织应用的路由结构。