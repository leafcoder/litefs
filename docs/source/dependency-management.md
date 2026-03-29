# 依赖管理说明

本项目使用现代 Python 依赖管理方式，通过 `pyproject.toml` 文件统一管理所有依赖。

## 核心依赖

项目的核心依赖已在 `pyproject.toml` 文件的 `[project.dependencies]` 部分定义，包括：

- argh>=0.26.2
- greenlet>=0.4.13,<4.0
- Mako>=1.0.6
- MarkupSafe>=1.1.1
- pathtools>=0.1.2
- PyYAML>=5.1
- watchdog>=0.8.3

## 可选依赖组

项目提供以下可选依赖组：

### 1. WSGI 服务器支持
```bash
pip install "litefs[wsgi]"
```
包括：
- gunicorn>=20.1.0
- uwsgi>=2.0.20
- waitress>=2.1.0

### 2. 开发依赖
```bash
pip install "litefs[dev]"
```
包括：
- pytest>=7.0.0
- pytest-cov>=4.0.0
- black>=23.0.0
- isort>=5.12.0
- mypy>=1.0.0
- ruff>=0.1.0

### 3. 文档依赖
```bash
pip install "litefs[docs]"
```
包括：
- sphinx>=9.0.0
- sphinx-rtd-theme>=3.0.0
- myst-parser>=3.0.0
- sphinx-autodoc-typehints>=3.0.0

### 4. 性能测试依赖
```bash
pip install "litefs[performance]"
```
包括：
- memory-profiler>=0.60.0
- line-profiler>=3.5.0
- locust>=2.15.0
- pytest-benchmark>=4.0.0
- psutil>=5.9.0
- py-spy>=0.3.14
- pytest-xdist>=3.0.0

## 安装所有依赖

如果需要安装所有可选依赖：

```bash
pip install "litefs[wsgi,dev,docs,performance]"
```

## 开发环境设置

1. 克隆仓库：
   ```bash
   git clone https://github.com/leafcoder/litefs.git
   cd litefs
   ```

2. 创建虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   ```

3. 安装开发依赖：
   ```bash
   pip install -e "[dev]"
   ```

4. 运行测试：
   ```bash
   pytest
   ```

## 依赖管理最佳实践

1. **统一管理**：所有依赖都在 `pyproject.toml` 中定义，避免使用多个 `requirements.txt` 文件
2. **版本锁定**：使用精确的版本范围，确保依赖的稳定性
3. **可选依赖**：将非核心依赖组织成可选依赖组，减少安装包大小
4. **开发流程**：使用 `pip install -e "[dev]"` 进行开发，确保所有开发工具可用
5. **依赖更新**：定期使用 `pip check` 和 `pip list --outdated` 检查依赖状态

## 注意事项

- 项目支持 Python 3.8+，请确保使用兼容的 Python 版本
- 生产环境建议使用 `pip install litefs` 或 `pip install "litefs[wsgi]"` 安装
- 开发环境建议使用 `-e` 模式安装，以便修改代码后立即生效