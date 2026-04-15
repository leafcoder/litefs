# 文档更新记录

## 2026-04-15 - 文档系统迁移

### 变更说明

本次更新将文档系统从 Sphinx 迁移到 Docsify，主要变更包括：

#### 新增文件
- `README.md` - 根目录文档导航（主入口）
- `_sidebar.md` - Docsify 侧边栏导航
- `index.html` - 更新为 Docsify 配置（已在根目录）
- `docs/README.md` - 文档目录导航

#### 更新文件
- `README.md` - 完全重写，使用中文，链接到 Docsify 文档
- `index.html` - 添加完整的 Docsify 配置（搜索、分页、插件等）

#### 文档结构

**Sphinx 文档（保留但不再更新）：**
```
docs/source/
├── index.rst              # Sphinx 主索引（保留）
├── *.md                   # 所有 Markdown 文档（保留）
└── api/                   # API 文档（保留）
```

**Docsify 文档（新的主文档系统）：**
```
/
├── index.html             # Docsify 入口
├── _sidebar.md            # 侧边栏
├── README.md              # 首页
└── docs/
    └── README.md          # 文档导航
```

### 迁移原因

1. **简化文档构建** - Docsify 无需构建，实时渲染
2. **更好的用户体验** - 支持搜索、分页、实时编辑
3. **GitHub Pages 友好** - 纯静态，无需构建步骤
4. **易于维护** - Markdown 格式，与代码同仓库

### 文档访问

**在线访问：**
- 主入口：https://leafcoder.github.io/litefs/
- 文档导航：https://leafcoder.github.io/litefs/#/docs/README

**本地访问：**
```bash
# 使用 docsify-cli
docsify serve .

# 或使用 Python HTTP 服务器
python -m http.server 8000
```

### 保留的 Sphinx 文档

以下 Sphinx 生成的 HTML 文档仍然保留在 `docs/build/html/` 目录：
- API 参考文档
- 自动生成的模块文档

这些文档可以通过 `make docs-build` 重新生成。

### 过时的文档

以下文档已不再更新，但保留供参考：
- `docs/quality-assurance-report.md` - 质量保证报告
- `docs/final-report.md` - 最终报告
- `docs/source/analysis-report.md` - 分析报告

### 文档维护指南

**添加新文档：**
1. 在 `docs/source/` 创建 `.md` 文件
2. 在 `_sidebar.md` 添加链接
3. 在 `docs/README.md` 更新导航

**更新现有文档：**
- 直接编辑 `docs/source/` 下的 `.md` 文件
- 提交更改后 GitHub Pages 自动更新

**本地测试：**
```bash
docsify serve . --port 8000
```

### 注意事项

1. 所有新文档应使用 Markdown 格式
2. 文档路径使用相对路径
3. 保持文档命名一致性（小写，连字符分隔）
4. 定期清理过时的报告文件

---

## 历史文档说明

### Sphinx 文档构建（已弃用）

```bash
# 构建 Sphinx 文档（不再使用）
cd docs
make html

# 查看文档
make serve
```

### 文档目录结构

- `source/` - 文档源文件
- `build/` - 构建输出（已弃用）
- `conf.py` - Sphinx 配置（保留用于 API 文档）

---

最后更新：2026-04-15
