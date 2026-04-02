# RESTful API 服务示例

一个完整的 RESTful API 服务，展示了如何使用 Litefs 构建 API 后端。

## 功能特性

- 🔐 用户认证（Token + Session）
- 👥 用户管理（CRUD）
- 📝 文章管理（CRUD）
- 🔒 权限控制（角色权限）
- 📄 分页和过滤
- ✅ 请求验证
- 🎯 统一的 API 响应格式

## 运行方式

```bash
python app.py
```

访问 http://localhost:8080 查看 API 文档。

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| john | john123 | 普通用户 |
| jane | jane123 | 普通用户 |

## API 端点

### 认证

- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/me` - 获取当前用户信息

### 用户管理

- `GET /api/users` - 获取用户列表（管理员）
- `GET /api/users/{id}` - 获取用户详情
- `POST /api/users` - 创建用户（管理员）
- `PUT /api/users/{id}` - 更新用户
- `DELETE /api/users/{id}` - 删除用户（管理员）

### 文章管理

- `GET /api/posts` - 获取文章列表
- `GET /api/posts/{id}` - 获取文章详情
- `POST /api/posts` - 创建文章
- `PUT /api/posts/{id}` - 更新文章
- `DELETE /api/posts/{id}` - 删除文章

## 测试示例

### 1. 登录

```bash
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

响应：
```json
{
  "success": true,
  "data": {
    "token": "your-api-token",
    "user": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com",
      "role": "admin"
    }
  },
  "timestamp": "2024-01-01T10:00:00"
}
```

### 2. 获取文章列表

```bash
curl http://localhost:8080/api/posts
```

### 3. 创建文章

```bash
curl -X POST http://localhost:8080/api/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-token" \
  -d '{"title": "New Post", "content": "This is a new post"}'
```

### 4. 获取用户列表（管理员）

```bash
curl http://localhost:8080/api/users \
  -H "Authorization: Bearer your-api-token"
```

## 认证方式

支持两种认证方式：

1. **Bearer Token**: 在请求头中添加 `Authorization: Bearer <token>`
2. **Session Cookie**: 通过登录接口自动设置

## 响应格式

所有 API 响应都遵循以下格式：

```json
{
  "success": true|false,
  "data": { ... },
  "error": "error message",
  "timestamp": "2024-01-01T10:00:00"
}
```
