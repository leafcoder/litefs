# Litefs 示例

本目录包含 Litefs 框架的示例代码，展示框架的各种功能。

## 示例列表

### 经典示例目录

#### 1. Hello World (`01-hello-world/`)

最简单的 Litefs 应用，展示基本的路由和响应。

#### 2. 路由示例 (`02-routing/`)

展示 Litefs 框架的路由系统，包括：
- 基本路由
- 带参数的路由
- 正则表达式路由

#### 3. 博客示例 (`03-blog/`)

展示 Litefs 框架的完整功能，包括：
- 路由系统
- 模板渲染
- 静态文件服务

#### 4. API 服务示例 (`04-api-service/`)

展示如何使用 Litefs 框架创建 RESTful API 服务，包括：
- 用户认证
- 用户管理 API
- 文章管理 API
- 分页和过滤
- 统一的 API 响应格式

#### 5. 全栈示例 (`05-fullstack/`)

展示 Litefs 框架与前端技术的集成，包括：
- 后端 API
- 前端 JavaScript
- 静态文件服务

#### 6. SQLAlchemy 示例 (`06-sqlalchemy/`)

展示 Litefs 框架与 SQLAlchemy ORM 的集成，包括：
- 数据库模型定义
- 数据库操作
- 模板渲染
- 表单处理

#### 7. 流式响应示例 (`07-streaming/`)

展示 Litefs 框架的流式响应功能。

#### 8. 综合示例 (`08-comprehensive/`)

展示 Litefs 框架的核心功能，包括：
- 路由系统（装饰器和方法链风格）
- 中间件系统（日志、安全、CORS、限流）
- 会话管理
- 缓存系统（MemoryCache + TreeCache）
- 请求验证
- 静态文件服务
- 错误处理（404 + 500）
- 健康检查

### 独立示例文件

#### ASGI 示例 (`asgi_example.py`)

展示如何使用 Litefs 的 ASGI 功能，包括：
- 基本路由
- 异步处理函数
- JSON 响应
- 路径参数
- 查询参数

## 运行示例

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行经典示例

#### Hello World 示例

```bash
cd examples/01-hello-world
python app.py
```

然后访问：http://localhost:8080

#### 路由示例

```bash
cd examples/02-routing
python app.py
```

然后访问：http://localhost:8080

#### 博客示例

```bash
cd examples/03-blog
python app.py
```

然后访问：http://localhost:8080

#### API 服务示例

```bash
cd examples/04-api-service
python app.py
```

然后访问：http://localhost:8080

#### 全栈示例

```bash
cd examples/05-fullstack
python app.py
```

然后访问：http://localhost:8080

#### SQLAlchemy 示例

```bash
cd examples/06-sqlalchemy
python app.py
```

然后访问：http://localhost:8080

#### 流式响应示例

```bash
cd examples/07-streaming
python app.py
```

然后访问：http://localhost:8080

#### 综合示例

```bash
cd examples/08-comprehensive
python app.py
```

然后访问：http://localhost:8080

### 运行独立示例

#### ASGI 示例

```bash
python examples/asgi_example.py
```

然后访问：http://localhost:9090

## 功能说明

### Hello World 示例路由

- GET `/` - 首页，返回 "Hello, World!"
- GET `/about` - 关于页面，返回框架信息

### API 服务示例路由

#### 认证 API
- POST `/api/auth/login` - 用户登录
- POST `/api/auth/logout` - 用户登出
- GET `/api/auth/me` - 获取当前用户信息

#### 用户 API
- GET `/api/users` - 获取用户列表（管理员）
- GET `/api/users/{id}` - 获取用户详情
- POST `/api/users` - 创建用户（管理员）
- PUT `/api/users/{id}` - 更新用户
- DELETE `/api/users/{id}` - 删除用户（管理员）

#### 文章 API
- GET `/api/posts` - 获取文章列表
- GET `/api/posts/{id}` - 获取文章详情
- POST `/api/posts` - 创建文章
- PUT `/api/posts/{id}` - 更新文章
- DELETE `/api/posts/{id}` - 删除文章

## 默认账号

API 服务示例包含以下默认账号：

- **管理员**: admin / admin123
- **普通用户**: john / john123, jane / jane123

## 注意事项

- 示例代码仅用于演示，实际生产环境中需要根据具体需求进行修改
- API 服务示例中的用户数据存储在内存中，重启后会丢失
- CSRF 保护需要在表单中包含 CSRF 令牌
- 流式响应示例需要浏览器支持 SSE（Server-Sent Events）
