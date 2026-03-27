# Litefs 开发指南

## 快速开始

### 安装开发依赖

```bash
pip install -r requirements.txt
```

### 开发模式安装

```bash
# Windows
.\make.bat dev-install

# Linux/Mac
make dev-install
```

## 开发命令

### 启动服务器

#### 开发服务器

```bash
# Windows
.\make.bat serve

# Linux/Mac
make serve
```

#### 调试模式服务器

```bash
# Windows
.\make.bat dev-serve

# Linux/Mac
make dev-serve
```

#### WSGI 服务器

**使用 Gunicorn**

```bash
# 先安装 Gunicorn
pip install gunicorn

# 启动服务器
# Windows
.\make.bat wsgi-gunicorn

# Linux/Mac
make wsgi-gunicorn
```

**使用 uWSGI**

```bash
# 先安装 uWSGI
pip install uwsgi

# 启动服务器
# Windows
.\make.bat wsgi-uwsgi

# Linux/Mac
make wsgi-uwsgi
```

**使用 Waitress**

```bash
# 先安装 Waitress
pip install waitress

# 启动服务器
# Windows
.\make.bat wsgi-waitress

# Linux/Mac
make wsgi-waitress
```

### 测试

```bash
# Windows
.\make.bat test              # 运行所有测试
.\make.bat test-unit        # 运行单元测试
.\make.bat test-cov         # 运行测试并生成覆盖率报告

# Linux/Mac
make test
make test-unit
make test-cov
```

### 代码质量

```bash
# Windows
.\make.bat format            # 格式化代码
.\make.bat lint              # 代码检查
.\make.bat type-check        # 类型检查
.\make.bat check-all         # 运行所有检查

# Linux/Mac
make format
make lint
make type-check
make check-all
```

### 构建

```bash
# Windows
.\make.bat build             # 构建源码包
.\make.bat wheel             # 构建 wheel 包
.\make.bat clean             # 清理构建文件

# Linux/Mac
make build
make wheel
make clean
```

### 安装

```bash
# Windows
.\make.bat install          # 安装包到当前环境
.\make.bat dev-install       - 开发模式安装（可编辑）
.\make.bat dev-uninstall     - 卸载开发模式安装

# Linux/Mac
make install
make dev-install
make dev-uninstall
```

### 发布

```bash
# Windows
.\make.bat upload-test       - 上传到测试 PyPI
.\make.bat upload            - 上传到 PyPI

# Linux/Mac
make upload-test
make upload
```

## 项目结构

```
litefs/
├── src/                      # 源代码根目录
│   └── litefs/             # 主包
│       ├── cache/            # 缓存模块
│       ├── handlers/         # 请求处理器
│       ├── middleware/       # 中间件
│       ├── server/           # 服务器实现
│       ├── session/          # 会话管理
│       └── utils/           # 工具函数
├── tests/                   # 测试目录
│   └── unit/               # 单元测试
├── examples/                # 示例代码
│   ├── basic/              # 基础示例
│   └── wsgi/               # WSGI 示例
└── docs/                    # 文档
```

## 配置

### 服务器配置

服务器可以通过命令行参数配置：

```bash
python -m litefs --host localhost --port 9090 --webroot examples\basic\site
```

参数说明：
- `--host`: 服务器监听地址（默认：localhost）
- `--port`: 服务器监听端口（默认：9090）
- `--webroot`: Web 根目录（默认：examples/basic/site）
- `--debug`: 启用调试模式

### WSGI 服务器配置

#### Gunicorn

```bash
gunicorn -w 4 -b localhost:9090 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  examples.wsgi.wsgi_example:application
```

参数说明：
- `-w 4`: 4 个工作进程
- `-b localhost:9090`: 绑定地址和端口
- `--access-logfile -`: 访问日志输出到标准输出
- `--error-logfile -`: 错误日志输出到标准输出
- `--log-level info`: 日志级别

#### uWSGI

```bash
uwsgi --http localhost:9090 \
  --wsgi-file examples/wsgi/wsgi_example.py \
  --master \
  --processes 4 \
  --enable-threads \
  --threads 2
```

参数说明：
- `--http localhost:9090`: HTTP 服务器地址和端口
- `--wsgi-file`: WSGI 应用文件
- `--master`: 启用主进程
- `--processes 4`: 4 个工作进程
- `--enable-threads`: 启用线程支持
- `--threads 2`: 每个工作进程 2 个线程

#### Waitress

```bash
waitress-serve --port=9090 \
  --threads=4 \
  examples.wsgi.wsgi_example:application
```

参数说明：
- `--port=9090`: 监听端口
- `--threads=4`: 4 个工作线程

## 开发工作流

1. 创建功能分支
2. 进行开发
3. 运行测试：`make test-unit`
4. 运行代码检查：`make check-all`
5. 提交代码
6. 推送到远程仓库

## 故障排除

### 依赖问题

如果遇到依赖问题，尝试重新安装：

```bash
pip install -r requirements.txt --force-reinstall
```

### 测试失败

确保在项目根目录运行测试，并且 PYTHONPATH 设置正确：

```bash
# Windows
set PYTHONPATH=src
python -m pytest tests/unit/ -v

# Linux/Mac
export PYTHONPATH=src
python -m pytest tests/unit/ -v
```

### 服务器启动失败

检查端口是否被占用：

```bash
# Windows
netstat -ano | findstr :9090

# Linux/Mac
lsof -i :9090
```

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
