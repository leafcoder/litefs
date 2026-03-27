# Litefs 项目结构

这是一个专业的 Python 项目目录结构，遵循 Python 社区最佳实践。

## 目录结构

```
litefs/
├── src/                          # 源代码目录
│   └── litefs/                   # 主包
│       ├── __init__.py            # 包初始化文件
│       ├── core.py                # 核心功能
│       ├── exceptions.py          # 异常定义
│       ├── cache/                # 缓存模块
│       │   ├── __init__.py
│       │   └── cache.py        # 缓存实现
│       ├── handlers/             # 请求处理器
│       │   ├── __init__.py
│       │   └── request.py      # 请求处理
│       ├── middleware/           # 中间件（预留）
│       │   └── __init__.py
│       ├── server/              # 服务器实现
│       │   ├── __init__.py
│       │   └── http_server.py # HTTP 服务器
│       ├── session/             # 会话管理
│       │   ├── __init__.py
│       │   └── session.py     # 会话实现
│       └── utils/              # 工具函数
│           ├── __init__.py
│           └── utils.py       # 工具函数
├── tests/                       # 测试目录
│   ├── __init__.py
│   ├── unit/                  # 单元测试
│   │   ├── test_*.py
│   ├── integration/           # 集成测试（预留）
│   └── fixtures/             # 测试夹具（预留）
├── examples/                   # 示例代码
│   ├── basic/                # 基础示例
│   │   └── site/
│   ├── wsgi/                 # WSGI 示例
│   │   ├── wsgi_example.py
│   │   ├── wsgi_example_advanced.py
│   │   ├── wsgi_simple.py
│   │   └── wsgi_standalone.py
│   └── advanced/             # 高级示例（预留）
├── docs/                      # 文档
│   ├── auto-generated/        # 自动生成的文档
│   ├── README.md
│   └── index.html
├── scripts/                   # 脚本目录（预留）
├── .gitignore               # Git 忽略文件
├── .python-version          # Python 版本
├── LICENSE                 # 许可证
├── MANIFEST.in            # 包清单
├── pyproject.toml         # 项目配置（PEP 518）
├── README.md             # 项目说明
├── requirements.txt      # 依赖列表
├── setup.py            # 安装脚本（向后兼容）
└── tox.ini            # tox 配置
```

## 模块说明

### 核心模块 (src/litefs/)

- **core.py**: 包含 `Litefs` 主类和配置管理
- **exceptions.py**: 定义所有自定义异常

### 缓存模块 (src/litefs/cache/)

- **cache.py**: 实现树缓存和内存缓存，以及文件事件处理

### 请求处理 (src/litefs/handlers/)

- **request.py**: 实现 `RequestHandler` 和 `WSGIRequestHandler`

### 服务器模块 (src/litefs/server/)

- **http_server.py**: 实现 `TCPServer`、`HTTPServer`、`WSGIServer`

### 会话管理 (src/litefs/session/)

- **session.py**: 实现 `Session` 类

### 工具模块 (src/litefs/utils/)

- **utils.py**: 日志、错误处理、日期格式化等工具函数

## 安装和使用

### 开发模式安装

```bash
pip install -e .
```

### 生产模式安装

```bash
pip install .
```

### 运行测试

```bash
pytest
```

### 运行示例

```bash
# 基础示例
python examples/basic/example.py

# WSGI 示例
gunicorn examples.wsgi.wsgi_example:application
```

## 配置

项目使用 `pyproject.toml` 作为主要配置文件，包含：

- 项目元数据
- 依赖管理
- 工具配置（black、isort、mypy、pytest）
- 构建系统配置

## 开发指南

### 代码风格

项目使用以下工具确保代码质量：

- **Black**: 代码格式化
- **isort**: 导入排序
- **mypy**: 类型检查
- **pytest**: 单元测试
- **ruff**: 快速 linting

### 提交代码前

```bash
# 格式化代码
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/

# 运行测试
pytest --cov=src --cov-report=html
```

## 依赖管理

### 生产依赖

见 `requirements.txt` 或 `pyproject.toml` 的 `dependencies` 部分。

### 开发依赖

```bash
pip install -e ".[dev]"
```

## WSGI 部署

### Gunicorn

```bash
gunicorn -w 4 -b :8000 examples.wsgi.wsgi_example:application
```

### uWSGI

```bash
uwsgi --http :8000 --wsgi-file examples/wsgi/wsgi_example.py
```

### Waitress

```bash
waitress-serve --port=8000 examples.wsgi.wsgi_example:application
```

## 许可证

MIT License - 见 LICENSE 文件
