# 路由系统

## 功能特性

* 装饰器风格路由定义
* 方法链风格路由定义
* 路径参数支持（如 ``/user/{id}``）
* 多种 HTTP 方法支持（GET, POST, PUT, DELETE 等）
* 路由命名与反向解析
* 优先级路由匹配
* 安全防护（防止路径遍历攻击）

## 快速开始

### 装饰器风格

```python
from litefs import Litefs
from litefs.routing import get, post

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

app.register_routes(__name__)
app.run()
```

### 方法链风格

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

## 路径参数

```python
@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return f'User ID: {id}'

@get('/user/{id}/posts/{post_id}', name='user_post')
def user_post_handler(request, id, post_id):
    return f'User ID: {id}, Post ID: {post_id}'
```

## HTTP 方法支持

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

## 路由命名与反向解析

```python
@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return f'User ID: {id}'

# 反向解析 URL
url = app.router.url_for('user_detail', id=123)  # 生成 '/user/123'
```

## 最佳实践

* **模块化**：将路由按功能模块组织到不同文件中
* **命名规范**：使用清晰、一致的路由命名
* **路径设计**：使用 RESTful 风格的路径设计

## 常见问题

**Q: 路由冲突怎么办？**

A: 如果两个路由路径模式冲突，更具体的路由会优先匹配。例如，``/user/admin`` 会优先于 ``/user/{id}`` 匹配。

**Q: 如何处理路径参数类型？**

A: 路径参数默认是字符串类型，需要在处理函数中进行类型转换。例如，``user_id = int(id)``。

**Q: 路由注册失败怎么办？**

A: 确保：
* 路由装饰器正确导入
* 路由处理函数正确定义
* ``register_routes`` 方法被调用
* 模块名称或对象正确传递

## 相关文档

* :doc:`static-files-guide` - 静态文件路由指南
* :doc:`middleware-guide` - 中间件指南
* :doc:`configuration` - 配置管理
* :doc:`wsgi-deployment` - WSGI 部署
