# Litefs 文档

Litefs 是一个轻量级的 Python Web 框架，提供高性能的 HTTP 服务器、现代路由系统、WSGI/ASGI 支持、中间件系统、缓存管理等功能。

## 📖 文档导航

### 快速开始

- [快速开始](source/getting-started.md) - 安装和基本使用
- [路由系统](source/routing-guide.md) - 装饰器和方法链风格路由
- [静态文件](source/static-files-guide.md) - 静态文件路由指南
- [配置管理](source/configuration.md) - 配置项和使用方法

### 核心功能

- [中间件系统](source/middleware-guide.md) - 内置和自定义中间件
- [缓存系统](source/cache-system.md) - 多级缓存管理
- [会话管理](source/session-management.md) - Session 后端和使用
- [WSGI 部署](source/wsgi-deployment.md) - Gunicorn、uWSGI 部署
- [ASGI 部署](source/asgi-deployment.md) - Uvicorn、Daphne 部署

### 测试文档

- [单元测试](source/unit-tests.md) - 单元测试指南
- [性能和压力测试](source/performance-stress-tests.md) - 性能测试报告

### 进阶指南

- [Keep-Alive 支持](source/keep-alive.md) - HTTP 长连接
- [Greenlet vs asyncio](source/performance-greenlet-vs-asyncio.md) - 性能对比
- [ASGI 服务器实现](source/asyncio-server.md) - 异步服务器

### 项目文档

- [改进分析](source/improvement-analysis.md) - 项目改进计划
- [Bug 修复](source/bug-fixes.md) - Bug 修复记录
- [Linux 服务器指南](source/linux-server-guide.md) - 部署指南
- [开发指南](source/development.md) - 开发规范
- [项目结构](source/project-structure.md) - 目录结构
- [待办事项](source/todolist.md) - 功能规划

### API 文档

- [API 参考](source/api/litefs.rst) - 完整 API 文档

## 🚀 快速示例

```python
from litefs import Litefs
from litefs.routing import get, post

app = Litefs(host='0.0.0.0', port=8080, debug=True)

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

## 📦 安装

```bash
pip install litefs
```

或从源码安装：

```bash
git clone https://github.com/leafcoder/litefs.git
cd litefs
pip install -r requirements.txt
python setup.py install
```

## ✨ 功能特性

- **高性能 HTTP 服务器** - 支持 epoll 和 greenlet
- **现代路由系统** - 装饰器风格、方法链风格
- **WSGI/ASGI 兼容** - 支持 Gunicorn、Uvicorn 等
- **中间件系统** - 日志、安全、CORS、限流
- **多级缓存** - Memory、Tree、Redis、Database、Memcache
- **会话管理** - Database、Redis、Memcache 后端
- **静态文件服务** - 自动 MIME 类型、安全防护
- **健康检查** - 内置健康检查端点
- **文件监控** - 热重载支持

## 🔗 相关链接

- [GitHub 仓库](https://github.com/leafcoder/litefs)
- [PyPI 包](https://pypi.org/project/litefs/)
- [在线文档](https://leafcoder.github.io/litefs/)
- [示例代码](../examples/)

## 📝 文档说明

本文档使用 [Docsify](https://docsify.js.org/) 构建，支持实时渲染和搜索。

**本地预览文档：**

```bash
# 使用 docsify-cli
docsify serve docs

# 或使用 Python HTTP 服务器
cd docs
python -m http.server 8000
```

然后访问 http://localhost:8000 查看文档。

## 📄 License

MIT License - 详见 [LICENSE](../LICENSE)
