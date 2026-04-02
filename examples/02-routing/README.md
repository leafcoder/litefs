# 路由系统示例

展示 Litefs 路由系统的完整功能。

## 功能特性

- 装饰器路由定义
- 方法链路由定义
- 路径参数（单参数和多参数）
- 查询参数处理
- POST 数据处理
- 各种 HTTP 方法（GET, POST, PUT, DELETE）

## 运行方式

```bash
python app.py
```

## 可用路由

### 基础路由

- `GET /` - 首页，显示所有可用端点

### 用户管理（RESTful API）

- `GET /users` - 获取用户列表（支持 `?page=` 和 `?limit=` 分页）
- `POST /users` - 创建用户（JSON 数据：`name`, `email`）
- `GET /users/{id}` - 获取用户详情
- `PUT /users/{id}` - 更新用户
- `DELETE /users/{id}` - 删除用户

### 搜索和产品

- `GET /search?q=keyword&category=all` - 搜索功能
- `GET /products/{category}/{id}` - 产品详情（多路径参数）

## 测试示例

```bash
# 获取用户列表
curl http://localhost:8080/users

# 创建用户
curl -X POST http://localhost:8080/users \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "email": "john@example.com"}'

# 获取用户详情
curl http://localhost:8080/users/1

# 搜索
curl "http://localhost:8080/search?q=python&category=tech"

# 产品详情
curl http://localhost:8080/products/electronics/123
```
