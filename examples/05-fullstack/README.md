# 全栈应用示例

一个综合展示 Litefs 所有功能的完整 Web 应用。

## 功能特性

- 🚀 **现代路由系统** - 装饰器和方法链两种风格
- 🔐 **会话管理** - 完整的用户认证系统
- ⚡ **缓存支持** - 内存缓存提高性能
- 🛡️ **中间件集成** - 日志、安全、CORS、限流、健康检查
- 🎨 **美观界面** - 响应式设计，支持移动端
- 📱 **API 接口** - RESTful API 支持
- 🖼️ **静态文件服务** - 自动处理静态资源

## 项目结构

```
05-fullstack/
├── app.py              # 主应用文件
├── static/
│   ├── css/
│   │   └── style.css   # 样式文件
│   └── js/
│       └── app.js      # JavaScript 文件
└── README.md
```

## 运行方式

```bash
python app.py
```

访问 http://localhost:8080 查看应用。

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| user1 | user123 | 普通用户 |

## 可用页面

### Web 页面

- `/` - 首页，展示应用特性
- `/posts` - 文章列表
- `/posts/{id}` - 文章详情
- `/about` - 关于页面
- `/login` - 登录页面
- `/logout` - 退出登录
- `/dashboard` - 用户控制台（需登录）
- `/api/docs` - API 文档

### API 端点

- `GET /api/posts` - 获取文章列表
- `GET /api/posts/{id}` - 获取文章详情

### 健康检查

- `GET /health` - 健康检查
- `GET /health/ready` - 就绪检查

## 功能演示

### 1. 浏览文章

无需登录即可浏览所有文章，点击文章标题查看详情。

### 2. 用户登录

点击导航栏的"登录"链接，使用默认账号登录。

### 3. 用户控制台

登录后，点击用户名进入控制台，查看个人信息和文章。

### 4. API 接口

访问 `/api/docs` 查看 API 文档，使用 curl 或其他工具测试 API。

```bash
# 获取文章列表
curl http://localhost:8080/api/posts

# 获取文章详情
curl http://localhost:8080/api/posts/1
```

## 技术栈

- **后端**: Python 3.8+, Litefs Framework
- **前端**: HTML5, CSS3, Vanilla JavaScript
- **会话**: Memory Backend
- **缓存**: Memory Cache

## 中间件

本示例使用了以下中间件：

1. **LoggingMiddleware** - 请求日志记录
2. **SecurityMiddleware** - 安全头部设置
3. **CORSMiddleware** - 跨域支持
4. **RateLimitMiddleware** - 请求限流
5. **HealthCheck** - 健康检查
