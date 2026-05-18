# 项目结构

**文档版本**: 1.0  
**最后更新**: 2026-04-14

---

## 概述

本文档详细说明 Litefs 项目的目录结构、模块职责和文件组织，帮助开发者快速理解项目架构。

---

## 1. 项目根目录

```
litefs/
├── src/                    # 源代码目录
│   └── litefs/            # 主包目录
├── tests/                  # 测试代码目录
├── examples/               # 示例代码目录
├── docs/                   # 文档目录
├── .trae/                  # Trae AI 配置
├── .scannerwork/           # SonarQube 扫描结果
├── pyproject.toml          # 项目配置文件
├── setup.py                # 安装脚本
├── requirements.txt        # 依赖列表
├── Makefile                # 构建命令
├── README.md               # 项目说明
├── LICENSE                 # 许可证
└── MANIFEST.in             # 打包清单
```

---

## 2. 源代码结构

### 2.1 主包目录 (`src/litefs/`)

```
src/litefs/
├── __init__.py             # 包初始化，导出公共 API
├── __main__.py             # 命令行入口
├── _version.py             # 版本信息
├── cli.py                  # 命令行工具
├── config.py               # 配置管理
├── core.py                 # 核心类 Litefs
├── error_pages.py          # 错误页面
├── exceptions.py           # 异常定义
├── security.py             # 安全工具
├── validators.py           # 验证器
│
├── cache/                  # 缓存模块
│   ├── __init__.py
│   ├── cache.py            # 缓存基类
│   ├── db.py               # 数据库缓存
│   ├── factory.py          # 缓存工厂
│   ├── form_cache.py       # 表单缓存
│   ├── manager.py          # 缓存管理器
│   ├── memcache.py         # Memcache 缓存
│   └── redis.py            # Redis 缓存
│
├── database/               # 数据库模块
│   ├── __init__.py
│   ├── core.py             # 数据库核心
│   └── models.py           # 数据模型
│
├── handlers/               # 请求处理器
│   ├── __init__.py
│   ├── base.py             # 请求处理器基类
│   ├── wsgi.py             # WSGI 请求处理器
│   ├── asgi.py             # ASGI 请求处理器
│   ├── socket.py           # Socket 请求处理器
│   ├── response.py         # HTTP 响应对象
│   ├── form.py             # 表单数据解析
│   └── enhanced.py         # 增强请求处理
│
├── middleware/             # 中间件
│   ├── __init__.py
│   ├── base.py             # 中间件基类
│   ├── cors.py             # CORS 中间件
│   ├── csrf.py             # CSRF 中间件
│   ├── health_check.py     # 健康检查
│   ├── logging.py          # 日志中间件
│   ├── rate_limit.py       # 限流中间件
│   └── security.py         # 安全中间件
│
├── plugins/                # 插件系统
│   ├── __init__.py
│   ├── base.py             # 插件基类
│   └── loader.py           # 插件加载器
│
├── routing/                # 路由系统
│   ├── __init__.py
│   ├── radix_tree.py       # 基数树实现
│   └── router.py           # 路由器
│
├── server/                 # 服务器实现
│   ├── __init__.py
│   ├── asgi.py             # ASGI 服务器
│   ├── asyncio.py          # AsyncIO 服务器
│   └── greenlet.py         # Greenlet 服务器
│
├── session/                # 会话管理
│   ├── __init__.py
│   ├── cache_session.py    # 缓存会话
│   ├── db.py               # 数据库会话
│   ├── factory.py          # 会话工厂
│   ├── manager.py          # 会话管理器
│   ├── memcache.py         # Memcache 会话
│   ├── redis.py            # Redis 会话
│   └── session.py          # 会话基类
│
├── templates/              # 模板文件
│   └── scaffold/           # 脚手架模板
│       ├── site/           # 站点模板
│       └── __init__.py
│
└── utils/                  # 工具函数
    ├── __init__.py
    └── utils.py            # 工具函数实现
```

### 2.2 模块职责

#### 核心模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 主入口 | `__init__.py` | 导出公共 API，版本信息 |
| 核心类 | `core.py` | Litefs 主类，应用初始化 |
| 配置 | `config.py` | 配置加载和管理 |
| CLI | `cli.py` | 命令行工具实现 |

#### 服务器模块

| 模块 | 文件 | 职责 |
|------|------|------|
| ASGI | `server/asgi.py` | ASGI 服务器实现 |
| AsyncIO | `server/asyncio.py` | AsyncIO 服务器实现 |
| Greenlet | `server/greenlet.py` | Greenlet 服务器实现 |

#### 路由模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 路由器 | `routing/router.py` | 路由注册和匹配 |
| 基数树 | `routing/radix_tree.py` | 高效路由匹配算法 |

#### 中间件模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 基类 | `middleware/base.py` | 中间件基类和接口 |
| CORS | `middleware/cors.py` | 跨域资源共享 |
| CSRF | `middleware/csrf.py` | CSRF 保护 |
| 健康检查 | `middleware/health_check.py` | 健康检查端点 |
| 日志 | `middleware/logging.py` | 请求日志记录 |
| 限流 | `middleware/rate_limit.py` | 请求限流 |
| 安全 | `middleware/security.py` | 安全头部和防护 |

#### 缓存模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 基类 | `cache/cache.py` | 缓存接口定义 |
| 内存缓存 | `cache/cache.py` | 内存缓存实现 |
| 数据库缓存 | `cache/db.py` | 数据库缓存实现 |
| Redis | `cache/redis.py` | Redis 缓存实现 |
| Memcache | `cache/memcache.py` | Memcache 缓存实现 |
| 管理器 | `cache/manager.py` | 缓存管理器 |

#### 会话模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 基类 | `session/session.py` | 会话接口定义 |
| 缓存会话 | `session/cache_session.py` | 基于缓存的会话 |
| 数据库会话 | `session/db.py` | 数据库会话存储 |
| Redis 会话 | `session/redis.py` | Redis 会话存储 |
| Memcache 会话 | `session/memcache.py` | Memcache 会话存储 |
| 管理器 | `session/manager.py` | 会话管理器 |

---

## 3. 测试结构

### 3.1 测试目录 (`tests/`)

```
tests/
├── __init__.py             # 测试包初始化
├── run_tests.py            # 测试运行脚本
├── README.md               # 测试说明
│
├── unit/                   # 单元测试
│   ├── __init__.py
│   ├── test_basic.py       # 基础功能测试
│   ├── test_cache.py       # 缓存测试
│   ├── test_cache_manager.py
│   ├── test_cache_backends_web.py
│   ├── test_config.py      # 配置测试
│   ├── test_core.py        # 核心类测试
│   ├── test_database_cache.py
│   ├── test_database_session.py
│   ├── test_default_page.py
│   ├── test_environ.py
│   ├── test_error_pages.py
│   ├── test_examples_basic.py
│   ├── test_form.py
│   ├── test_health_check.py
│   ├── test_max_request_size.py
│   ├── test_memorycache.py
│   ├── test_middleware.py
│   ├── test_middleware_params.py
│   ├── test_rate_limit_*.py
│   ├── test_routing.py     # 路由测试
│   ├── test_scaffold.py
│   ├── test_session.py
│   ├── test_streaming.py
│   ├── test_treecache.py
│   ├── test_validators.py
│   ├── test_wsgi*.py       # WSGI 测试
│   └── ...
│
├── integration/            # 集成测试
│   └── test_starlette_integration.py
│
├── performance/            # 性能测试
│   ├── test_deployment_modes.py
│   ├── test_greenlet_vs_asyncio.py
│   ├── test_performance.py
│   ├── test_worker_performance.py
│   └── run_test.sh
│
├── stress/                 # 压力测试
│   └── test_stress.py
│
├── test_asyncio_server.py
├── test_form_cache.py
├── test_hot_reload.py
├── test_keepalive.py
├── test_process_server.py
├── test_security.py
└── test_session_optimization.py
```

### 3.2 测试分类

| 类型 | 目录 | 说明 |
|------|------|------|
| 单元测试 | `unit/` | 测试单个函数和类 |
| 集成测试 | `integration/` | 测试模块间交互 |
| 性能测试 | `performance/` | 测试性能指标 |
| 压力测试 | `stress/` | 测试高并发场景 |

---

## 4. 示例结构

### 4.1 示例目录 (`examples/`)

```
examples/
├── README.md               # 示例说明
├── basic.py                # 基础示例
├── advanced.py             # 高级示例
├── asgi_example.py         # ASGI 示例
├── fastapi_example.py      # FastAPI 集成示例
│
├── 01-hello-world/         # Hello World 示例
│   ├── README.md
│   ├── app.py
│   └── wsgi.py
│
├── 02-routing/             # 路由示例
│   ├── README.md
│   └── app.py
│
├── 03-blog/                # 博客示例
│   ├── README.md
│   ├── app.py
│   └── static/
│
├── 04-api-service/         # API 服务示例
│   ├── README.md
│   └── app.py
│
├── 05-fullstack/           # 全栈应用示例
│   ├── README.md
│   ├── app.py
│   └── static/
│
├── 06-sqlalchemy/          # SQLAlchemy 示例
│   ├── README.md
│   ├── app.py
│   ├── models.py
│   └── templates/
│
└── 07-streaming/           # 流式响应示例
    ├── README.md
    ├── app.py
    └── wsgi.py
```

### 4.2 示例分类

| 示例 | 说明 | 难度 |
|------|------|------|
| 01-hello-world | 最简单的应用 | ⭐ |
| 02-routing | 路由系统演示 | ⭐⭐ |
| 03-blog | 完整博客系统 | ⭐⭐⭐ |
| 04-api-service | RESTful API | ⭐⭐⭐ |
| 05-fullstack | 全栈应用 | ⭐⭐⭐⭐ |
| 06-sqlalchemy | 数据库集成 | ⭐⭐⭐ |
| 07-streaming | 流式响应 | ⭐⭐⭐ |

---

## 5. 文档结构

### 5.1 文档目录 (`docs/`)

```
docs/
├── source/                 # Sphinx 源文件
│   ├── index.rst           # 文档首页
│   ├── conf.py             # Sphinx 配置
│   │
│   ├── getting-started.md  # 快速开始
│   ├── routing-guide.md    # 路由指南
│   ├── static-files-guide.md
│   ├── configuration.md    # 配置管理
│   ├── middleware-guide.md # 中间件指南
│   ├── cache-system.md     # 缓存系统
│   ├── session-management.md
│   ├── wsgi-deployment.md  # WSGI 部署
│   ├── asgi-deployment.md  # ASGI 部署
│   ├── unit-tests.md       # 单元测试
│   ├── performance-stress-tests.md
│   ├── improvement-analysis.md
│   ├── bug-fixes.md
│   ├── linux-server-guide.md
│   ├── development.md
│   └── project-structure.md
│
├── build/                  # 构建输出
│   └── html/              # HTML 文档
│
├── Makefile                # 文档构建命令
└── make.bat                # Windows 构建命令
```

### 5.2 文档分类

| 类型 | 文件 | 说明 |
|------|------|------|
| 快速开始 | `getting-started.md` | 入门教程 |
| 核心功能 | `routing-guide.md` 等 | 功能指南 |
| 部署运维 | `wsgi-deployment.md` 等 | 部署指南 |
| 开发文档 | `development.md` 等 | 开发指南 |
| API 文档 | `api/` | API 参考 |

---

## 6. 配置文件

### 6.1 项目配置

| 文件 | 说明 |
|------|------|
| `pyproject.toml` | 项目配置、依赖、工具配置 |
| `setup.py` | 安装脚本 |
| `requirements.txt` | 依赖列表 |
| `Makefile` | 构建命令 |
| `MANIFEST.in` | 打包清单 |

### 6.2 工具配置

| 文件 | 说明 |
|------|------|
| `.gitignore` | Git 忽略规则 |
| `.editorconfig` | 编辑器配置 |
| `pyproject.toml` | Black/isort/mypy 配置 |

---

## 7. 依赖关系

### 7.1 模块依赖图

```
litefs (core)
    ├── cache (缓存)
    ├── session (会话)
    ├── routing (路由)
    ├── middleware (中间件)
    ├── handlers (处理器)
    ├── server (服务器)
    └── utils (工具)
```

### 7.2 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| argh | >=0.26.2 | CLI 参数解析 |
| greenlet | >=0.4.13 | 协程支持 |
| Mako | >=1.0.6 | 模板引擎 |
| MarkupSafe | >=1.1.1 | HTML 转义 |
| pathtools | >=0.1.2 | 路径工具 |
| PyYAML | >=5.1 | YAML 解析 |
| watchdog | >=0.8.3 | 文件监控 |
| SQLAlchemy | >=2.0.0 | ORM 支持 |

---

## 8. 文件命名规范

### 8.1 Python 文件

- **模块**: 小写字母，下划线分隔 (`cache_manager.py`)
- **类**: PascalCase (`MemoryCache`)
- **函数**: snake_case (`get_cache`)
- **常量**: UPPER_SNAKE_CASE (`MAX_SIZE`)

### 8.2 测试文件

- **单元测试**: `test_<module>.py` (`test_cache.py`)
- **集成测试**: `test_<feature>_integration.py`
- **性能测试**: `test_<feature>_performance.py`

### 8.3 文档文件

- **Markdown**: 小写字母，连字符分隔 (`getting-started.md`)
- **Sphinx**: 小写字母，连字符分隔 (`api-guide.rst`)

---

## 9. 开发建议

### 9.1 添加新功能

1. 在相应模块创建文件
2. 实现功能代码
3. 编写单元测试
4. 更新文档
5. 添加示例

### 9.2 修改现有功能

1. 找到对应模块文件
2. 修改代码
3. 更新测试
4. 更新文档
5. 检查兼容性

### 9.3 添加新中间件

1. 在 `middleware/` 创建文件
2. 继承 `BaseMiddleware`
3. 实现 `process_request` 和 `process_response`
4. 在 `__init__.py` 导出
5. 编写测试和文档

---

## 10. 相关资源

- [Python 包结构指南](https://packaging.python.org/tutorials/packaging-projects/)
- [项目目录结构最佳实践](https://docs.python-guide.org/writing/structure/)
- [Sphinx 文档结构](https://www.sphinx-doc.org/en/master/usage/quickstart.html)

---

**文档维护**: 开发团队  
**最后更新**: 2026-04-14
