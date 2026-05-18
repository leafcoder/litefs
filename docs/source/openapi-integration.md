# OpenAPI/Swagger 文档自动生成

Litefs 提供了 OpenAPI 3.0 规范的自动生成功能，并集成 Swagger UI 界面。

## 快速开始

### 1. 初始化 OpenAPI

```python
from litefs.core import Litefs
from litefs.openapi import OpenAPI

app = Litefs(host='0.0.0.0', port=8080)

openapi = OpenAPI(
    app,
    title='My API',
    version='1.0.0',
    description='API 描述',
)
```

### 2. 添加 API 文档

```python
from litefs.routing import get, post

@get('/users')
@openapi.doc(
    summary='获取用户列表',
    tags=['users'],
)
def list_users(request):
    return {'users': []}
```

### 3. 访问文档

启动应用后访问：
- Swagger UI: `http://localhost:8080/docs`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## 文档装饰器

### 基本用法

```python
@openapi.doc(
    summary='API 摘要',
    description='API 详细描述',
    tags=['标签名'],
)
def my_api(request):
    pass
```

### 完整选项

```python
@openapi.doc(
    summary='获取用户详情',
    description='根据 ID 获取单个用户信息',
    tags=['users'],
    parameters=[
        {
            'name': 'user_id',
            'in': 'path',
            'required': True,
            'description': '用户 ID',
            'schema': {'type': 'integer'}
        }
    ],
    request_body={
        'required': True,
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/CreateUser'}
            }
        }
    },
    response={
        'description': '用户详情',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/User'}
            }
        }
    },
    security=[{'bearerAuth': []}],
    deprecated=False,
)
def get_user(request, user_id):
    pass
```

## Schema 定义

### 使用装饰器

```python
@openapi.schema('User')
class User:
    id: int
    name: str
    email: str
    age: int = 0
```

### 在响应中引用

```python
@openapi.doc(
    response={
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/User'}
            }
        }
    }
)
```

## 标签管理

```python
openapi.add_tag('users', '用户管理')
openapi.add_tag('orders', '订单管理')
```

## 服务器配置

```python
openapi.add_server('http://localhost:8080', '开发服务器')
openapi.add_server('https://api.example.com', '生产服务器')
```

## 认证配置

```python
openapi.add_security_scheme('bearerAuth', {
    'type': 'http',
    'scheme': 'bearer',
    'bearerFormat': 'JWT',
})

openapi.add_security_scheme('apiKey', {
    'type': 'apiKey',
    'in': 'header',
    'name': 'X-API-Key',
})
```

## API 参考

### OpenAPI 类

| 方法 | 说明 |
|------|------|
| `doc(summary, description, ...)` | API 文档装饰器 |
| `schema(name)` | Schema 定义装饰器 |
| `add_tag(name, description)` | 添加标签 |
| `add_server(url, description)` | 添加服务器 |
| `add_security_scheme(name, scheme)` | 添加安全方案 |

### 配置选项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `title` | `'Litefs API'` | API 标题 |
| `version` | `'1.0.0'` | API 版本 |
| `description` | `''` | API 描述 |
| `docs_url` | `'/docs'` | Swagger UI 路径 |
| `openapi_url` | `'/openapi.json'` | OpenAPI JSON 路径 |

## 完整示例

参见 [examples/17-openapi-docs/app.py](../examples/17-openapi-docs/app.py)
