# 开发指南

**文档版本**: 1.0  
**最后更新**: 2026-04-14

---

## 概述

本文档为 Litefs 项目贡献者提供开发环境搭建、代码规范、提交流程和发布流程的详细指南。

---

## 1. 开发环境搭建

### 1.1 系统要求

- Python 3.8+
- Git
- Make（可选）

### 1.2 克隆仓库

```bash
git clone https://github.com/leafcoder/litefs.git
cd litefs
```

### 1.3 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 或使用 pyenv
pyenv virtualenv 3.10.9 litefs
pyenv activate litefs
```

### 1.4 安装依赖

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 安装文档依赖
pip install -e ".[docs]"

# 安装性能测试依赖
pip install -e ".[performance]"

# 或安装所有依赖
pip install -e ".[dev,docs,performance]"
```

### 1.5 验证安装

```bash
# 运行测试
make test

# 或
python -m pytest tests/

# 检查代码风格
make lint

# 类型检查
make type-check
```

---

## 2. 项目结构

```
litefs/
├── src/
│   └── litefs/           # 源代码
│       ├── cache/        # 缓存模块
│       ├── database/     # 数据库模块
│       ├── handlers/     # 请求处理器
│       ├── middleware/   # 中间件
│       ├── plugins/      # 插件系统
│       ├── routing/      # 路由系统
│       ├── server/       # 服务器实现
│       ├── session/      # 会话管理
│       ├── templates/    # 模板文件
│       ├── utils/        # 工具函数
│       ├── __init__.py   # 包初始化
│       ├── cli.py        # 命令行工具
│       ├── config.py     # 配置管理
│       ├── core.py       # 核心模块
│       ├── error_pages.py # 错误页面
│       ├── exceptions.py # 异常定义
│       ├── security.py   # 安全功能
│       └── validators.py # 验证器
├── tests/                # 测试代码
│   ├── integration/      # 集成测试
│   ├── performance/      # 性能测试
│   ├── stress/           # 压力测试
│   └── unit/             # 单元测试
├── examples/             # 示例代码
├── docs/                 # 文档
│   └── source/           # Sphinx 源文件
├── .trae/                # Trae 配置
├── pyproject.toml        # 项目配置
├── setup.py              # 安装脚本
├── Makefile              # Make 命令
└── README.md             # 项目说明
```

---

## 3. 代码规范

### 3.1 Python 代码规范

遵循 PEP 8 规范，使用以下工具自动格式化：

```bash
# 格式化代码
make format

# 或手动运行
black src/ tests/ examples/
isort src/ tests/ examples/
```

### 3.2 类型注解

使用类型注解提高代码可读性：

```python
from typing import Optional, List, Dict, Any

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户信息"""
    pass

def process_items(items: List[str]) -> Dict[str, int]:
    """处理项目列表"""
    pass
```

### 3.3 文档字符串

使用 Google 风格的文档字符串：

```python
def calculate_total(items: List[Dict[str, float]]) -> float:
    """计算项目总价。
    
    Args:
        items: 项目列表，每个项目包含 name 和 price 字段
    
    Returns:
        float: 所有项目的总价
    
    Raises:
        ValueError: 如果 items 为空
    
    Examples:
        >>> items = [{'name': 'apple', 'price': 1.5}, {'name': 'banana', 'price': 2.0}]
        >>> calculate_total(items)
        3.5
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    
    return sum(item['price'] for item in items)
```

### 3.4 代码注释

```python
# 单行注释：解释复杂逻辑
result = complex_calculation(data)

# TODO: 待实现的功能
# TODO(username): 指定负责人的待办事项

# FIXME: 需要修复的问题
# FIXME: 这里有性能问题，需要优化

# NOTE: 重要说明
# NOTE: 这个函数有副作用，会修改全局状态
```

---

## 4. Git 工作流

### 4.1 分支策略

- `main`: 主分支，稳定版本
- `develop`: 开发分支，最新功能
- `feature/*`: 功能分支
- `bugfix/*`: Bug 修复分支
- `release/*`: 发布分支

### 4.2 提交规范

使用 Conventional Commits 规范：

```bash
# 功能
git commit -m "feat: 添加 WebSocket 支持"

# 修复
git commit -m "fix: 修复会话内存泄漏问题"

# 文档
git commit -m "docs: 更新部署指南"

# 重构
git commit -m "refactor: 重构路由匹配算法"

# 测试
git commit -m "test: 添加缓存模块单元测试"

# 性能优化
git commit -m "perf: 优化数据库查询性能"

# 其他
git commit -m "chore: 更新依赖版本"
```

### 4.3 Pull Request 流程

1. **创建分支**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **开发功能**
   ```bash
   # 编写代码
   # 编写测试
   # 运行测试
   make test
   ```

3. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   ```

4. **推送到远程**
   ```bash
   git push origin feature/new-feature
   ```

5. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待代码审查

6. **代码审查**
   - 回复审查意见
   - 修改代码
   - 通过所有检查

7. **合并代码**
   - Squash and merge
   - 删除功能分支

---

## 5. 测试指南

### 5.1 运行测试

```bash
# 运行所有测试
make test

# 运行单元测试
make test-unit

# 运行测试并生成覆盖率报告
make test-cov

# 运行特定测试
python -m pytest tests/unit/test_cache.py -v

# 运行特定测试类
python -m pytest tests/unit/test_cache.py::TestMemoryCache -v

# 运行特定测试方法
python -m pytest tests/unit/test_cache.py::TestMemoryCache::test_put_and_get -v
```

### 5.2 编写测试

**单元测试示例**:
```python
import unittest
from litefs.cache import MemoryCache

class TestMemoryCache(unittest.TestCase):
    """内存缓存测试"""
    
    def setUp(self):
        """测试前准备"""
        self.cache = MemoryCache(max_size=10)
    
    def tearDown(self):
        """测试后清理"""
        self.cache.clear()
    
    def test_put_and_get(self):
        """测试存取操作"""
        self.cache.put('key', 'value')
        self.assertEqual(self.cache.get('key'), 'value')
    
    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        self.assertIsNone(self.cache.get('nonexistent'))
```

**使用 pytest**:
```python
import pytest
from litefs.cache import MemoryCache

@pytest.fixture
def cache():
    """缓存 fixture"""
    cache = MemoryCache(max_size=10)
    yield cache
    cache.clear()

def test_put_and_get(cache):
    """测试存取操作"""
    cache.put('key', 'value')
    assert cache.get('key') == 'value'

def test_get_nonexistent(cache):
    """测试获取不存在的键"""
    assert cache.get('nonexistent') is None
```

### 5.3 测试覆盖率

```bash
# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html

# 查看报告
open htmlcov/index.html
```

---

## 6. 文档编写

### 6.1 构建 API 文档

```bash
# 构建文档
make docs-build

# 清理文档
make docs-clean

# 启动文档服务器
make docs-serve
```

### 6.2 编写文档

**Markdown 文档**:
```markdown
# 功能标题

## 概述

简要描述功能。

## 使用方法

### 基本用法

```python
from litefs import Litefs

app = Litefs()
```

### 高级用法

```python
app = Litefs(
    debug=True,
    cache_backend='redis'
)
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| debug | bool | False | 调试模式 |

## 示例

完整示例代码。

## 注意事项

重要说明。
```

**Sphinx 文档**:
```rst
功能标题
========

概述
----

简要描述功能。

使用方法
--------

基本用法
^^^^^^^^

.. code-block:: python

    from litefs import Litefs
    
    app = Litefs()

参数说明
--------

.. list-table::
   :header-rows: 1
   
   * - 参数
     - 类型
     - 默认值
     - 说明
   * - debug
     - bool
     - False
     - 调试模式
```

---

## 7. 发布流程

### 7.1 版本管理

版本号遵循语义化版本规范：`MAJOR.MINOR.PATCH`

- `MAJOR`: 不兼容的 API 修改
- `MINOR`: 向后兼容的功能新增
- `PATCH`: 向后兼容的问题修复

### 7.2 发布步骤

1. **更新版本号**
   ```bash
   # 编辑 src/litefs/_version.py
   __version__ = "0.8.0"
   ```

2. **更新 CHANGELOG**
   ```markdown
   ## [0.8.0] - 2026-04-14
   
   ### Added
   - WebSocket 支持
   - GraphQL 支持
   
   ### Changed
   - 优化路由匹配性能
   
   ### Fixed
   - 修复会话内存泄漏
   ```

3. **运行测试**
   ```bash
   make test
   make lint
   make type-check
   ```

4. **构建发布包**
   ```bash
   make clean
   make build
   ```

5. **上传到 PyPI**
   ```bash
   # 测试 PyPI
   make upload-test
   
   # 正式 PyPI
   make upload
   ```

6. **创建 Git 标签**
   ```bash
   git tag -a v0.8.0 -m "Release v0.8.0"
   git push origin v0.8.0
   ```

7. **发布 GitHub Release**
   - 在 GitHub 上创建 Release
   - 填写 Release Notes
   - 上传发布包

---

## 8. 贡献指南

### 8.1 贡献流程

1. Fork 项目
2. 创建功能分支
3. 编写代码和测试
4. 提交 Pull Request
5. 等待代码审查
6. 合并代码

### 8.2 代码审查标准

- 代码符合规范
- 测试覆盖率达标
- 文档完整
- 无性能问题
- 无安全问题

### 8.3 行为准则

- 尊重所有贡献者
- 建设性的反馈
- 包容性语言
- 专业态度

---

## 9. 开发工具

### 9.1 IDE 配置

**VS Code**:
```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.testing.pytestEnabled": true
}
```

**PyCharm**:
- 启用 Black 格式化
- 启用 mypy 类型检查
- 配置 pytest 测试运行器

### 9.2 预提交钩子

**安装 pre-commit**:
```bash
pip install pre-commit
pre-commit install
```

**配置文件** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.0
    hooks:
      - id: mypy
```

---

## 10. 常见问题

### 10.1 开发环境问题

**Q: 导入模块失败？**
```bash
# 确保在虚拟环境中
source venv/bin/activate

# 确保安装了开发依赖
pip install -e ".[dev]"
```

**Q: 测试失败？**
```bash
# 清理缓存
find . -type d -name __pycache__ -exec rm -rf {} +

# 重新安装
pip install -e ".[dev]" --force-reinstall
```

### 10.2 文档问题

**Q: 文档构建失败？**
```bash
# 安装文档依赖
pip install -e ".[docs]"

# 清理并重新构建
make docs-clean
make docs-build
```

---

## 11. 相关资源

- [Python 官方文档](https://docs.python.org/3/)
- [PEP 8 风格指南](https://pep8.org/)
- [Google Python 风格指南](https://google.github.io/styleguide/pyguide.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [语义化版本](https://semver.org/)

---

**文档维护**: 开发团队  
**最后更新**: 2026-04-14
