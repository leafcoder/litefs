# Litefs 文档系统

Litefs 使用 Sphinx 作为文档生成引擎，支持 Markdown 和 reStructuredText 格式。

## 文档结构

```
docs/
├── source/                 # Sphinx 源文件
│   ├── api/             # 自动生成的 API 文档
│   ├── _static/         # 静态文件
│   │   └── css/
│   │       └── custom.css
│   ├── _templates/       # 模板文件
│   ├── conf.py          # Sphinx 配置
│   ├── index.rst        # 主文档
│   └── *.md            # Markdown 文档文件
├── build/               # 构建输出（默认忽略）
├── Makefile            # Sphinx 构建文件
└── .gitignore          # Git 忽略文件
```

## 安装文档依赖

### 方式一：安装所有依赖（包括文档）

```bash
pip install -r requirements.txt
```

### 方式二：仅安装文档依赖

```bash
make install-docs-deps
```

或手动安装：

```bash
pip install -r requirements-docs.txt
```

## 已安装的 Sphinx 包

### 核心包

- **sphinx** (>=9.0.0) - Sphinx 文档生成器
- **sphinx-rtd-theme** (>=3.0.0) - Read the Docs 主题
- **myst-parser** (>=3.0.0) - Markdown 解析器
- **sphinx-autodoc-typehints** (>=3.0.0) - 类型提示支持

### Sphinx 扩展

在 `docs/source/conf.py` 中配置的扩展：

```python
extensions = [
    'sphinx.ext.autodoc',          # 自动从代码生成文档
    'sphinx.ext.viewcode',         # 查看源代码
    'sphinx.ext.napoleon',         # 支持 Google/NumPy 风格的 docstring
    'sphinx.ext.intersphinx',       # 交叉项目引用
    'sphinx.ext.todo',             # 待办事项支持
    'sphinx.ext.coverage',         # 代码覆盖率
    'sphinx.ext.githubpages',      # GitHub Pages 支持
    'myst_parser',                # Markdown 支持
]
```

### 可选的文档增强包

以下包可以增强文档功能，但不是必需的：

- **sphinxcontrib-apidoc** (>=0.3.0) - 用于更好的 API 文档
- **sphinx-autodoc** (>=2.0.0) - 用于自动文档生成
- **sphinx-copybutton** (>=0.5.0) - 用于代码复制按钮
- **sphinx-design** (>=0.5.0) - 用于更好的设计

安装可选包：

```bash
pip install sphinxcontrib-apidoc sphinx-autodoc sphinx-copybutton sphinx-design
```

## 构建文档

### 使用 Makefile

```bash
make docs-build
```

### 直接使用 Sphinx

```bash
cd docs
make html
```

### 其他输出格式

```bash
cd docs
make html       # HTML 格式
make pdf        # PDF 格式（需要 LaTeX）
make epub       # EPUB 格式
make latex      # LaTeX 格式
```

## 查看文档

### 使用 Makefile

```bash
make docs-serve
```

访问 http://localhost:8000

### 直接使用 Python

```bash
cd docs/build/html
python -m http.server 8000
```

## 清理文档

### 使用 Makefile

```bash
make docs-clean
```

### 直接使用 Sphinx

```bash
cd docs
make clean
```

## API 文档自动生成

API 文档使用 `sphinx-apidoc` 自动生成：

```bash
cd docs/source
python -m sphinx.ext.apidoc -o api ../../src/litefs --module-first --force
```

生成的 API 文档位于 `docs/source/api/` 目录。

## 添加新文档

### Markdown 文档

1. 在 `docs/source/` 目录下创建 `.md` 文件
2. 在 `docs/source/index.rst` 中添加引用：

```rst
.. toctree::
   :maxdepth: 2
   :caption: 文档:
   
   your-new-doc
```

### reStructuredText 文档

1. 在 `docs/source/` 目录下创建 `.rst` 文件
2. 在 `docs/source/index.rst` 中添加引用

## 配置 Sphinx

编辑 `docs/source/conf.py` 可以自定义 Sphinx 配置：

### 主题配置

```python
html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False
}
```

### 语言配置

```python
language = 'zh_CN'  # 中文
```

### 项目信息

```python
project = 'Litefs'
copyright = '2026, leafcoder'
author = 'leafcoder'
version = '0.3.0'
release = '0.3.0'
```

## 自定义样式

编辑 `docs/source/_static/css/custom.css` 可以自定义文档样式。

## 部署文档

### GitHub Pages

1. 构建文档：

```bash
make docs-build
```

2. 将 `docs/build/html/` 目录内容推送到 `gh-pages` 分支

### 自定义服务器

将 `docs/build/html/` 目录部署到任何静态文件服务器。

## 常见问题

### Q: 如何更新 API 文档？

A: 运行 `cd docs/source && python -m sphinx.ext.apidoc -o api ../../src/litefs --module-first --force`

### Q: 如何添加新的 Sphinx 扩展？

A: 在 `docs/source/conf.py` 的 `extensions` 列表中添加扩展名称，然后安装对应的包。

### Q: 文档构建失败怎么办？

A: 
1. 确保已安装所有依赖：`make install-docs-deps`
2. 检查 `docs/source/conf.py` 配置是否正确
3. 查看错误信息，根据提示修复

### Q: 如何支持中文搜索？

A: 确保在 `docs/source/conf.py` 中设置了 `language = 'zh_CN'`

## 相关资源

- [Sphinx 官方文档](https://www.sphinx-doc.org/)
- [MyST Parser 文档](https://myst-parser.readthedocs.io/)
- [Read the Docs 主题](https://sphinx-rtd-theme.readthedocs.io/)
- [Sphinx 扩展](https://sphinxext.com/)
