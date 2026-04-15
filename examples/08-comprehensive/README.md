# 综合示例

本示例展示了 Litefs 框架的核心功能。

## 功能特性

- 路由系统（装饰器和方法链风格）
- 中间件系统（日志、安全、CORS、限流）
- 会话管理
- 缓存系统（MemoryCache + TreeCache）
- 请求验证
- 静态文件服务
- 错误处理（404 + 500）
- 健康检查

## 运行示例

```bash
cd examples/08-comprehensive
python app.py
```

然后访问：http://localhost:8080

## 可用路由

- GET `/` - 首页
- GET `/cache` - 缓存示例
- GET `/session` - 会话示例
- GET `/form` - 表单验证示例
- POST `/validate` - 表单验证
- GET `/user/{id}` - 用户详情
- GET `/users` - 用户列表
- POST `/user` - 创建用户
- PUT `/user/{id}` - 更新用户
- DELETE `/user/{id}` - 删除用户
- GET `/health` - 健康检查
- GET `/static/*` - 静态文件

## 中间件

- LoggingMiddleware - 日志中间件
- SecurityMiddleware - 安全中间件
- CORSMiddleware - CORS 中间件
- RateLimitMiddleware - 限流中间件
- HealthCheck - 健康检查中间件
