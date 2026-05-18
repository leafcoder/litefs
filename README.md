<div align="center">

# Litefs

<p>
    <!-- Place this tag where you want the button to render. -->
    <a class="github-button" href="https://github.com/leafcoder/litefs/subscription" data-color-scheme="no-preference: light; light: light; dark: dark;" data-show-count="true" aria-label="Watch leafcoder/litefs on GitHub">
        <img alt="GitHub forks" src="https://img.shields.io/github/watchers/leafcoder/litefs?style=social">
    </a>
    <a class="github-button" href="https://github.com/leafcoder/litefs" data-color-scheme="no-preference: light; light: light; dark: dark;" data-show-count="true" aria-label="Star leafcoder/litefs on GitHub">
        <img alt="GitHub forks" src="https://img.shields.io/github/stars/leafcoder/litefs?style=social">
    </a>
    <a class="github-button" href="https://github.com/leafcoder/litefs/fork" data-color-scheme="no-preference: light; light: light; dark: dark;" data-show-count="true" aria-label="Fork leafcoder/litefs on GitHub">
        <img alt="GitHub forks" src="https://img.shields.io/github/forks/leafcoder/litefs?style=social">
    </a>
</p>

<p>
    <img src="https://img.shields.io/github/v/release/leafcoder/litefs" data-origin="https://img.shields.io/github/v/release/leafcoder/litefs" alt="GitHub release (latest by date)">
    <img src="https://img.shields.io/github/languages/top/leafcoder/litefs" data-origin="https://img.shields.io/github/languages/top/leafcoder/litefs" alt="GitHub top language">
    <img src="https://img.shields.io/github/languages/code-size/leafcoder/litefs" data-origin="https://img.shields.io/github/languages/code-size/leafcoder/litefs" alt="GitHub code size in bytes">
    <img src="https://img.shields.io/github/commit-activity/w/leafcoder/litefs" data-origin="https://img.shields.io/github/commit-activity/w/leafcoder/litefs" alt="GitHub commit activity">
    <img src="https://img.shields.io/pypi/dm/litefs" data-origin="https://img.shields.io/pypi/dm/litefs" alt="PyPI - Downloads">
</p>

</div>

Litefs 是一个轻量级的 Python Web 框架，提供高性能的 HTTP 服务器、现代路由系统、WSGI/ASGI 支持、中间件系统、缓存管理等功能。

## 🌟 特性亮点

- **高性能 HTTP 服务器** - 支持 epoll、greenlet 和 asyncio
- **现代路由系统** - 装饰器风格、方法链风格，支持路径参数
- **WSGI/ASGI 兼容** - 支持 Gunicorn、Uvicorn、UWSGI 等服务器
- **中间件系统** - 日志、安全、CORS、限流、健康检查
- **多级缓存** - Memory、Tree、Redis、Database、Memcache 后端
- **会话管理** - Database、Redis、Memcache 后端支持
- **认证授权** - JWT Token、OAuth2 社交登录（GitHub、Google、微信、企业微信）
- **WebSocket 支持** - 实时通信、房间管理、心跳检测
- **Celery 集成** - 异步任务队列、定时任务
- **OpenAPI 文档** - 自动生成 Swagger UI 文档
- **静态文件服务** - 自动 MIME 类型、安全防护、子路径访问
- **健康检查** - 内置健康检查端点
- **文件监控** - 热重载支持
- **Python 3.8+ 支持** - 兼容多个 Python 版本

## 📖 文档

**完整文档已迁移至 Docsify：**

- 🌐 [在线文档](https://leafcoder.github.io/litefs/) - 基于 Docsify 的完整文档
- 📚 [文档目录](docs/README.md) - 本地文档导航
- 📝 [快速开始](docs/source/getting-started.md) - 安装和基本使用
- 🗺️ [路由系统](docs/source/routing-guide.md) - 装饰器和方法链风格路由
- 🛠️ [中间件](docs/source/middleware-guide.md) - 内置和自定义中间件
- 💾 [缓存系统](docs/source/cache-system.md) - 多级缓存管理
- 🔐 [认证授权](docs/source/auth-system.md) - JWT 和 OAuth2 社交登录
- 🔄 [WebSocket](docs/source/websocket.md) - 实时通信
- ⚡ [Celery 集成](docs/source/celery-integration.md) - 异步任务队列
- 📖 [OpenAPI 文档](docs/source/openapi-integration.md) - 自动生成 API 文档
- 🛡️ [会话管理](docs/source/session-management.md) - Session 后端和使用
- 🚀 [WSGI 部署](docs/source/wsgi-deployment.md) - Gunicorn、uWSGI 部署
- ⚡ [ASGI 部署](docs/source/asgi-deployment.md) - Uvicorn、Daphne 部署

## 🚀 快速开始

### 安装

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

### 基本示例

#### 装饰器风格

```python
from litefs.core import Litefs
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

#### 方法链风格

```python
from litefs.core import Litefs

app = Litefs()

def index_handler(request):
    return 'Hello, World!'

def user_detail_handler(request, id):
    return f'User ID: {id}'

app.add_get('/', index_handler, name='index')
app.add_get('/user/{id}', user_detail_handler, name='user_detail')

app.run()
```

### WSGI 部署

创建 `wsgi.py`：

```python
from litefs.core import Litefs

app = Litefs()

@get('/', name='index')
def index_handler(request):
    return 'Hello, World!'

application = app.wsgi()
```

使用 Gunicorn：

```bash
gunicorn -w 4 -b :8000 wsgi:application
```

使用 Uvicorn (ASGI)：

```bash
uvicorn asgi:application --host 0.0.0.0 --port 8000 --workers 4
```

## 📁 项目结构

```
litefs/
├── README.md              # 项目说明
├── pyproject.toml         # 项目配置
├── setup.py               # 安装脚本
├── docs/                  # 文档目录
│   ├── README.md         # 文档导航
│   └── source/           # 文档源文件
│       ├── getting-started.md
│       ├── routing-guide.md
│       ├── middleware-guide.md
│       ├── auth-system.md
│       ├── websocket.md
│       ├── celery-integration.md
│       ├── openapi-integration.md
│       └── ...
├── examples/              # 示例代码
│   ├── 01-quickstart/
│   ├── 02-rest-api/
│   ├── 03-web-app/
│   ├── 04-realtime/
│   └── 05-production/
├── src/litefs/            # 源代码
│   ├── __init__.py
│   ├── core.py
│   ├── routing/
│   ├── middleware/
│   ├── auth/
│   ├── websocket/
│   ├── tasks/
│   ├── openapi/
│   ├── cache/
│   ├── session/
│   └── ...
└── tests/                 # 测试代码
    ├── unit/
    ├── integration/
    └── performance/
```

## 📚 示例代码

Litefs 提供了丰富的示例，按照功能模块组织：

- [01-quickstart](examples/01-quickstart/) - 快速入门示例
- [02-rest-api](examples/02-rest-api/) - REST API 示例
- [03-web-app](examples/03-web-app/) - 完整的 Web 应用示例（博客系统）
- [04-realtime](examples/04-realtime/) - 实时通信示例（WebSocket 聊天室）
- [05-production](examples/05-production/) - 生产环境部署示例（Docker + Celery）

每个示例都包含详细的 README 文档和可运行的代码，请参考 [examples/README.md](examples/README.md) 了解更多。

## 📊 性能测试

LiteFS 提供完整的性能测试套件，支持多种服务器模式和部署方案的对比测试。

### v0.8.2 基准测试结果（2026-05-18）

> 测试工具: Apache Benchmark (ab) | 总请求: 10000 | 预热: 1000 | 迭代: 3 (取中位数)
> 测试环境: Linux 6.18.27 / 12 核 CPU / Python 3.10.9
> 响应内容: 纯文本 "Hello world" | Keep-Alive: 启用

#### 1 Worker

| 并发 | LiteFS+HttpServer | LiteFS+Gunicorn | FastAPI+Gunicorn+Uvicorn | FastAPI+Uvicorn |
|------|-------------------|-----------------|--------------------------|-----------------|
| 100  | 9,493             | 9,923           | 12,407                   | 10,783          |
| 500  | 14,014            | 14,119          | 13,724                   | 13,054          |
| 1000 | 13,937            | 15,055          | 14,671                   | 14,694          |

#### 4 Worker

| 并发 | LiteFS+HttpServer | LiteFS+Gunicorn | FastAPI+Gunicorn+Uvicorn | FastAPI+Uvicorn |
|------|-------------------|-----------------|--------------------------|-----------------|
| 100  | **16,393**        | 11,432          | 10,646                   | 13,841          |
| 500  | **15,732**        | 12,427          | 12,966                   | 11,465          |
| 1000 | 15,270            | 13,975          | 15,406                   | 14,784          |

#### 8 Worker

| 并发 | LiteFS+HttpServer | LiteFS+Gunicorn | FastAPI+Gunicorn+Uvicorn | FastAPI+Uvicorn |
|------|-------------------|-----------------|--------------------------|-----------------|
| 100  | 12,561            | 10,141          | 9,725                    | 14,003          |
| 500  | 13,172            | **15,660**      | 12,210                   | 12,162          |
| 1000 | **17,303**        | 13,882          | 12,666                   | 13,943          |

> 单位: req/sec (中位数)，加粗为该行最高值

#### 性能分析

- **多 Worker 优势**: LiteFS+HttpServer 在 4 Worker 下表现最佳，RPS 达 16,393
- **高并发稳定**: 8 Worker / 1000 并发下 LiteFS+HttpServer 达 17,303 req/sec
- **内置服务器优化**: LiteFS 自带 HttpServer 性能优于 Gunicorn 部署
- **公平性保证**: 统一纯文本响应、预热消除冷启动、多迭代取中位数

详细报告见 [性能基准测试文档](docs/source/performance-benchmark.md)

### 测试矩阵

| 服务器形式 | 单进程 | 多进程 | 测试场景 |
|-----------|--------|--------|---------|
| **原生 Greenlet** | ✅ | ✅ | Hello World / SQL 查询 |
| **原生 Asyncio** | ✅ | ✅ | Hello World / SQL 查询 |
| **WSGI + Gunicorn** | ✅ | ✅ | Hello World / SQL 查询 |
| **ASGI + Gunicorn + UvicornWorker** | ✅ | ✅ | Hello World / SQL 查询 |
| **ASGI + Uvicorn** | ✅ | ✅ | Hello World / SQL 查询 |
| **FastAPI + Uvicorn** (对照组) | ✅ | ✅ | Hello World / SQL 查询 |

### 快速开始

```bash
# 进入性能测试目录
cd tests/performance

# 运行所有测试
bash run_test.sh

# 查看报告
cat performance_report.md
```

## 🧪 测试

运行单元测试：

```bash
pytest tests/unit/ -v --cov=litefs --cov-report=html
```

运行性能测试：

```bash
cd tests/performance && bash run_test.sh
```

查看测试覆盖率：

```bash
make coverage
```

## 📊 测试覆盖率

当前测试覆盖率：**52%**

目标：**80%+**

详细测试报告见 [单元测试文档](docs/source/unit-tests.md)。

## 🔧 开发指南

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/leafcoder/litefs.git
cd litefs

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest

# 构建文档
make docs-build

# 运行文档服务器
make docs-serve
```

### 代码规范

- 遵循 PEP8 规范
- 使用类型注解
- 编写单元测试
- 保持文档更新

## 🤝 贡献

欢迎贡献代码、文档和建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件。

## 🔗 相关链接

- [GitHub 仓库](https://github.com/leafcoder/litefs)
- [PyPI 包](https://pypi.org/project/litefs/)
- [在线文档](https://leafcoder.github.io/litefs/)
- [问题反馈](https://github.com/leafcoder/litefs/issues)

---

<div align="center">
    <p>如果这个项目对你有帮助，请给一个 ⭐️ Star 支持！</p>
</div>
