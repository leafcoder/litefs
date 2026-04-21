# 认证授权系统

## 概述

Litefs 提供完整的用户认证授权解决方案，支持 JWT Token 认证、角色权限管理（RBAC）、密码加密等功能。

## 安装依赖

```bash
pip install bcrypt
```

> 注：如果未安装 bcrypt，系统会自动降级使用 PBKDF2 算法。

## 快速开始

### 基本配置

```python
from litefs import Litefs
from litefs.auth import Auth

app = Litefs()
auth = Auth(
    app,
    secret_key='your-secret-key-here',
    algorithm='HS256',
    access_token_expires=3600,
    refresh_token_expires=604800,
)
```

### 保护路由

```python
from litefs.auth.middleware import login_required, role_required
from litefs.auth.decorators import permission_required, admin_required

@app.route('/profile')
@login_required
def profile(request):
    return {'user': request.user.username}

@app.route('/admin')
@admin_required
def admin_panel(request):
    return {'message': 'Admin panel'}

@app.route('/users')
@permission_required('user:read')
def list_users(request):
    return {'users': []}
```

## 模块详解

### OAuth2 社交登录

Litefs 支持 OAuth2 社交登录，目前支持以下提供商：
- GitHub
- Google
- 微信
- 企业微信

#### 配置 OAuth2

```python
from litefs import Litefs
from litefs.auth.oauth2 import OAuth2
from litefs.auth.providers import GitHubProvider, GoogleProvider

app = Litefs()

oauth2 = OAuth2(app)

oauth2.register(
    name='github',
    provider=GitHubProvider,
    client_id='your-github-client-id',
    client_secret='your-github-client-secret',
    redirect_uri='http://localhost:8080/auth/callback/github',
)

oauth2.register(
    name='google',
    provider=GoogleProvider,
    client_id='your-google-client-id',
    client_secret='your-google-client-secret',
    redirect_uri='http://localhost:8080/auth/callback/google',
)
```

#### 使用 OAuth2 登录

```python
from litefs.routing import get

@get('/auth/login/github')
def github_login(request):
    return oauth2.authorize_redirect('github')

@get('/auth/callback/github')
def github_callback(request):
    code = request.args.get('code')
    state = request.args.get('state')
    
    user_info = oauth2.authorize_user('github', code, state)
    
    return {
        'username': user_info.username,
        'email': user_info.email,
        'avatar': user_info.avatar_url,
    }
```

#### 微信登录示例

```python
from litefs.auth.providers import WeChatProvider

oauth2.register(
    name='wechat',
    provider=WeChatProvider,
    client_id='your-wechat-appid',
    client_secret='your-wechat-secret',
    redirect_uri='http://yourdomain.com/auth/callback/wechat',
)

@get('/auth/login/wechat')
def wechat_login(request):
    return oauth2.authorize_redirect('wechat')

@get('/auth/callback/wechat')
def wechat_callback(request):
    code = request.args.get('code')
    state = request.args.get('state')
    
    user_info = oauth2.authorize_user('wechat', code, state)
    
    return {
        'username': user_info.username,
        'avatar': user_info.avatar_url,
    }
```

#### OAuth2 用户信息

`OAuth2UserInfo` 对象包含以下属性：

| 属性 | 类型 | 描述 |
|------|------|------|
| `provider` | str | 提供商名称 |
| `provider_user_id` | str | 提供商用户 ID |
| `username` | str | 用户名 |
| `email` | str | 邮箱（可选） |
| `name` | str | 显示名称（可选） |
| `avatar_url` | str | 头像 URL（可选） |
| `raw_data` | dict | 原始数据（可选） |

### JWT Token 管理

```python
from litefs.auth.jwt import JWTManager

jwt = JWTManager(
    secret_key='your-secret-key',
    algorithm='HS256',
    access_token_expires=3600,
    refresh_token_expires=604800,
)

payload = {'sub': 1, 'username': 'test'}
access_token = jwt.create_access_token(payload)
refresh_token = jwt.create_refresh_token(payload)

decoded = jwt.decode_token(access_token)
```

### 密码哈希

```python
from litefs.auth.password import hash_password, verify_password, validate_password_strength

password_hash = hash_password('my-password-123')

if verify_password('my-password-123', password_hash):
    print('Password correct')

valid, errors = validate_password_strength('WeakPass')
if not valid:
    print(f'Password errors: {errors}')
```

### 用户模型

```python
from litefs.auth.models import User, Role, Permission, init_default_roles_and_permissions

init_default_roles_and_permissions()

perm = Permission.create('post:write', '发布文章')
role = Role.create('editor', '编辑', [perm])

user = User.create(
    username='john',
    password_hash=hash_password('password'),
    email='john@example.com',
    roles=[role],
)

if user.has_permission('post:write'):
    print('User can write posts')
```

### 认证中间件

```python
from litefs.auth.middleware import AuthMiddleware

middleware = AuthMiddleware(
    jwt_manager=jwt,
    exclude_paths=['/login', '/register', '/health'],
    header_name='Authorization',
    token_prefix='Bearer',
)

app.add_middleware(middleware)
```

### 装饰器

```python
from litefs.auth.decorators import (
    login_required,
    role_required,
    permission_required,
    admin_required,
    owner_or_admin_required,
)

@login_required
def protected_view(request):
    return {'user': request.user.username}

@role_required('admin', 'editor')
def editor_view(request):
    return {'message': 'Editor access'}

@permission_required('user:read', 'user:write')
def user_management(request):
    return {'message': 'User management'}

@admin_required
def admin_only(request):
    return {'message': 'Admin only'}

def get_post_owner_id(request):
    post_id = request.path_params.get('id')
    return get_post(post_id).author_id

@owner_or_admin_required(get_post_owner_id)
def edit_post(request):
    return {'message': 'Can edit post'}
```

## API 端点

启用 Auth 后，自动注册以下端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/auth/login` | POST | 用户登录 |
| `/auth/register` | POST | 用户注册 |
| `/auth/refresh` | POST | 刷新 Token |
| `/auth/logout` | POST | 用户登出 |

### 登录请求

```json
POST /auth/login
Content-Type: application/json

{
    "username": "john",
    "password": "password123"
}
```

响应：

```json
{
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

### 注册请求

```json
POST /auth/register
Content-Type: application/json

{
    "username": "john",
    "password": "password123",
    "email": "john@example.com"
}
```

### 刷新 Token

```json
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### 登出

```json
POST /auth/logout
Authorization: Bearer <access_token>
```

## 完整示例

```python
from litefs import Litefs
from litefs.auth import Auth
from litefs.auth.models import User, Role, Permission, init_default_roles_and_permissions
from litefs.auth.password import hash_password
from litefs.auth.middleware import login_required, role_required
from litefs.auth.decorators import permission_required

app = Litefs()
auth = Auth(app, secret_key='dev-secret-key-change-in-production')

init_default_roles_and_permissions()

admin_role = Role.get_by_name('admin')
User.create(
    username='admin',
    password_hash=hash_password('admin123'),
    roles=[admin_role],
)

@app.route('/')
def index(request):
    return {'message': 'Welcome to Litefs Auth Demo'}

@app.route('/profile')
@login_required
def profile(request):
    return {
        'username': request.user.username,
        'roles': [r.name for r in request.user.roles],
    }

@app.route('/admin')
@role_required('admin')
def admin_panel(request):
    return {'message': 'Admin Panel'}

@app.route('/users')
@permission_required('user:read')
def list_users(request):
    users = User.list_all()
    return {
        'users': [
            {'id': u.id, 'username': u.username}
            for u in users
        ]
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

## 配置选项

| 选项 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `secret_key` | str | 必填 | JWT 签名密钥 |
| `algorithm` | str | HS256 | JWT 签名算法 |
| `access_token_expires` | int | 3600 | Access Token 过期时间（秒） |
| `refresh_token_expires` | int | 604800 | Refresh Token 过期时间（秒） |
| `token_prefix` | str | Bearer | Token 前缀 |
| `header_name` | str | Authorization | Token 头部名称 |

## 安全建议

1. **密钥管理**：生产环境必须使用强随机密钥，不要硬编码
2. **HTTPS**：生产环境必须使用 HTTPS
3. **Token 存储**：客户端应安全存储 Token（如 HttpOnly Cookie）
4. **密码策略**：使用 `validate_password_strength()` 验证密码强度
5. **Token 撤销**：用户登出时调用 `revoke_token()` 撤销 Token

## 扩展存储

默认使用内存存储，生产环境建议扩展为数据库存储：

```python
from litefs.auth.models import User, Role, Permission

class DatabaseUser(User):
    _db = None
    
    @classmethod
    def get_by_id(cls, user_id):
        return cls._db.query(User).filter_by(id=user_id).first()
    
    @classmethod
    def get_by_username(cls, username):
        return cls._db.query(User).filter_by(username=username).first()
    
    def save(self):
        cls._db.add(self)
        cls._db.commit()
```

## API 参考

### litefs.auth.Auth

主认证类，整合所有认证组件。

### litefs.auth.jwt.JWTManager

JWT Token 管理器。

**方法**：
- `create_access_token(payload)` - 创建 Access Token
- `create_refresh_token(payload)` - 创建 Refresh Token
- `decode_token(token)` - 解码并验证 Token
- `revoke_token(token)` - 撤销 Token

### litefs.auth.password

密码处理模块。

**函数**：
- `hash_password(password, rounds=12)` - 哈希密码
- `verify_password(password, password_hash)` - 验证密码
- `generate_password(length=16)` - 生成随机密码
- `validate_password_strength(password)` - 验证密码强度

### litefs.auth.models

数据模型模块。

**类**：
- `Permission` - 权限模型
- `Role` - 角色模型
- `User` - 用户模型

### litefs.auth.middleware

中间件模块。

**类**：
- `AuthMiddleware` - 认证中间件

**装饰器**：
- `login_required` - 登录验证
- `role_required(*roles)` - 角色验证

### litefs.auth.decorators

装饰器模块。

**装饰器**：
- `permission_required(*permissions)` - 权限验证
- `admin_required` - 管理员验证
- `owner_or_admin_required(get_owner_id)` - 所有者或管理员验证
