# Litefs 核心功能示例

本示例展示 Litefs 框架的核心功能，包括统一异常处理、请求上下文管理和表单验证系统。

## 功能特性

### 1. 统一异常处理体系

提供完整的 HTTP 异常类和错误处理机制：

- **HTTP 异常类**：BadRequest, Unauthorized, Forbidden, NotFound, InternalServerError 等
- **错误处理器**：支持自定义错误处理函数
- **abort() 函数**：快速抛出 HTTP 异常

### 2. 请求上下文管理

类似 Flask 的 `g` 对象，用于在请求生命周期内存储数据：

- **线程安全**：使用线程本地存储
- **简单易用**：像使用普通对象一样存储和获取数据
- **自动清理**：请求结束后自动清理上下文

### 3. 表单验证系统

强大的表单验证功能：

- **内置验证器**：Required, Length, Email, URL, Number, Regex, Choice 等
- **自定义验证**：支持自定义验证函数
- **错误收集**：自动收集所有验证错误

## 运行示例

```bash
cd examples/13-core-features
python app.py
```

服务器将在 `http://localhost:8080` 启动。

## 示例端点

### 首页
```
GET http://localhost:8080/
```

### 异常处理示例

#### 404 Not Found
```
GET http://localhost:8080/error/404
```

#### 400 Bad Request
```
GET http://localhost:8080/error/400
```

#### 401 Unauthorized
```
GET http://localhost:8080/error/401
```

#### 403 Forbidden
```
GET http://localhost:8080/error/403
```

#### 500 Internal Server Error
```
GET http://localhost:8080/error/500
```

#### abort() 函数示例
```
GET http://localhost:8080/error/abort
```

### 上下文管理示例

#### 设置上下文数据
```
GET http://localhost:8080/context/set
```

#### 获取上下文数据
```
GET http://localhost:8080/context/get
```

#### 查看上下文信息
```
GET http://localhost:8080/context/info
```

### 表单验证示例

#### 表单示例页面
```
GET http://localhost:8080/form/example
```

#### 表单验证
```bash
# 成功示例
curl -X POST -d 'username=john&email=john@example.com&age=25' http://localhost:8080/form/validate

# 失败示例（用户名太短）
curl -X POST -d 'username=jo&email=john@example.com' http://localhost:8080/form/validate

# 失败示例（邮箱格式错误）
curl -X POST -d 'username=john&email=invalid-email' http://localhost:8080/form/validate
```

### 综合示例

#### 创建用户
```bash
curl -X POST -d 'username=jane&email=jane@example.com' http://localhost:8080/user/create
```

## 使用指南

### 1. 异常处理

#### 抛出异常

```python
from litefs.exceptions import NotFound, BadRequest

# 方式 1：直接抛出异常
raise NotFound(
    message='User not found',
    description='The requested user does not exist'
)

# 方式 2：使用 abort() 函数
from litefs.exceptions import abort

abort(404, message='User not found', description='User ID: 123')
```

#### 自定义错误处理

```python
from litefs.exceptions import error_handler, NotFound

@error_handler.register(404)
def handle_404(error, request_handler):
    return {
        'error': 'Not Found',
        'message': error.message,
        'path': request_handler.path_info
    }, 404
```

### 2. 请求上下文管理

#### 存储数据

```python
from litefs.context import g

# 存储数据
g.user_id = 12345
g.username = 'john_doe'
g.role = 'admin'
```

#### 获取数据

```python
from litefs.context import g, has_request_context

# 检查上下文是否存在
if has_request_context():
    # 获取数据
    user_id = g.user_id
    username = g.get('username', 'guest')
    
    # 检查数据是否存在
    if 'user_id' in g:
        print(f"User ID: {g.user_id}")
```

#### 获取当前请求

```python
from litefs.context import get_current_request

request = get_current_request()
if request:
    print(f"Request path: {request.path_info}")
```

### 3. 表单验证

#### 定义表单

```python
from litefs.forms import Form, Field, Email, Length, Required

class UserForm(Form):
    username = Field(
        label='Username',
        required=True,
        validators=[Length(min_length=3, max_length=20)]
    )
    
    email = Field(
        label='Email',
        required=True,
        validators=[Email()]
    )
    
    age = Field(
        label='Age',
        required=False
    )
```

#### 验证表单

```python
# 获取表单数据
form_data = {
    'username': request.form.get('username'),
    'email': request.form.get('email'),
    'age': request.form.get('age')
}

# 创建表单实例并验证
form = UserForm(data=form_data)

if form.validate():
    # 验证成功
    user_data = form.data
else:
    # 验证失败
    errors = form.errors
```

## 内置验证器

### Required
验证字段是否为空

```python
from litefs.forms import Required

field = Field(validators=[Required()])
```

### Length
验证字符串长度

```python
from litefs.forms import Length

# 最小长度
field = Field(validators=[Length(min_length=3)])

# 最大长度
field = Field(validators=[Length(max_length=20)])

# 范围
field = Field(validators=[Length(min_length=3, max_length=20)])
```

### Email
验证邮箱格式

```python
from litefs.forms import Email

field = Field(validators=[Email()])
```

### URL
验证 URL 格式

```python
from litefs.forms import URL

field = Field(validators=[URL()])
```

### Number
验证数字范围

```python
from litefs.forms import Number

# 最小值
field = Field(validators=[Number(min_value=0)])

# 最大值
field = Field(validators=[Number(max_value=100)])

# 范围
field = Field(validators=[Number(min_value=0, max_value=100)])
```

### Regex
正则表达式验证

```python
from litefs.forms import Regex

field = Field(validators=[
    Regex(r'^[a-zA-Z0-9_]+$', message="Only letters, numbers and underscores")
])
```

### Choice
选择验证

```python
from litefs.forms import Choice

field = Field(validators=[Choice(['admin', 'user', 'guest'])])
```

### Function
自定义验证函数

```python
from litefs.forms import Function

def validate_username(value):
    return value and value[0].isalpha()

field = Field(validators=[
    Function(validate_username, message="Username must start with a letter")
])
```

## 最佳实践

### 1. 异常处理

- 使用具体的异常类（如 NotFound）而不是通用的 HTTPException
- 提供详细的错误描述，帮助调试
- 为 API 返回 JSON 格式的错误信息
- 为网页返回友好的错误页面

### 2. 请求上下文

- 只在请求处理函数中使用 `g` 对象
- 不要在请求外部访问 `g` 对象
- 使用 `has_request_context()` 检查上下文是否存在
- 及时清理不需要的数据

### 3. 表单验证

- 将表单类定义在单独的文件中
- 为每个字段提供清晰的标签
- 使用多个验证器组合验证规则
- 自定义验证逻辑放在表单的 `validate()` 方法中

## 相关文档

- [统一异常处理文档](../../docs/exception-handling.md)
- [请求上下文管理文档](../../docs/request-context.md)
- [表单验证系统文档](../../docs/form-validation.md)

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 实现统一异常处理体系
- 实现请求上下文管理
- 实现表单验证系统
