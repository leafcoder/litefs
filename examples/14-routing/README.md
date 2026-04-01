# 路由系统示例

本示例演示了如何使用 Litefs 新的路由系统。

## 功能特性

- 支持装饰器风格的路由定义
- 支持路径参数（如 `/user/{id}`）
- 支持多种 HTTP 方法（GET, POST, PUT, DELETE 等）
- 支持路由命名和反向解析
- 保持向后兼容，路由未匹配时使用传统文件系统路由

## 使用方法

### 1. 安装依赖

```bash
pip install litefs
```

### 2. 运行示例

```bash
python example.py
```

### 3. 测试路由

启动服务器后，可以使用以下 URL 测试路由：

- `GET http://localhost:9090/hello` - 简单的 Hello World 响应
- `GET http://localhost:9090/user/123` - 带路径参数的响应
- `POST http://localhost:9090/user` - 创建用户
- `PUT http://localhost:9090/user/123` - 更新用户
- `DELETE http://localhost:9090/user/123` - 删除用户
- `GET http://localhost:9090/api/status` - API 状态检查

## 路由定义方法

### 方法 1: 使用装饰器

```python
from litefs.routing import get, post

@get('/hello', name='hello')
def hello_handler(request):
    return {'message': 'Hello, World!'}

@post('/user', name='create_user')
def create_user_handler(request):
    return {'message': 'User created'}
```

### 方法 2: 使用方法链

```python
app = litefs.Litefs()

@app.add_get('/api/status', name='api_status')
def api_status_handler(request):
    return {'status': 'ok'}
```

### 方法 3: 批量注册

```python
# 注册装饰器定义的路由
app.register_routes(__name__)
```

## 路由参数

路由可以包含路径参数，如 `/user/{id}`，参数会作为关键字参数传递给处理函数：

```python
@get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    return {'user_id': id}
```

## 路由反向解析

可以使用 `url_for` 方法根据路由名称生成 URL：

```python
url = app.url_for('user_detail', id=123)  # 返回 '/user/123'
```

## 注意事项

- 路由系统优先于传统文件系统路由
- 路由匹配按添加顺序进行，先添加的路由优先级更高
- 支持正则表达式风格的路径参数
