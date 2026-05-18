.PHONY: docs-serve docs-build docs-check docs-clean docs-stats build publish-test publish clean-build release publish-help sync-deps

# 文档相关命令

# 本地运行文档服务器
docs-serve:
	@echo "Starting Docsify server..."
	@if command -v docsify > /dev/null; then \
		docsify serve . -p 8000; \
	else \
		echo "docsify-cli not found, using Python HTTP server..."; \
		python -m http.server 8000; \
	fi

# 构建文档（如果需要生成 API 文档）
docs-build:
	@echo "Building Sphinx API documentation..."
	cd docs && make html
	@echo "Sphinx documentation built in docs/build/html/"

# 检查文档链接
docs-check:
	@echo "Checking documentation links..."
	@find docs/source -name "*.md" -exec grep -l "^#" {} \; | head -20
	@echo ""
	@echo "文档文件列表:"
	@find docs/source -name "*.md" | wc -l
	@echo "个 Markdown 文件"

# 清理构建文件
docs-clean:
	@echo "Cleaning build files..."
	rm -rf docs/build
	rm -rf docs/source/_build
	@echo "Build files cleaned"

# 显示文档统计
docs-stats:
	@echo "=== 文档统计 ==="
	@echo "Markdown 文件数量:"
	@find docs/source -name "*.md" | wc -l
	@echo ""
	@echo "文档目录结构:"
	@tree -L 2 docs/source 2>/dev/null || find docs/source -maxdepth 2 -type f -name "*.md" | sort

# 帮助信息
docs-help:
	@echo "文档管理命令:"
	@echo "  make docs-serve    - 本地运行文档服务器"
	@echo "  make docs-build    - 构建 Sphinx API 文档"
	@echo "  make docs-check    - 检查文档链接"
	@echo "  make docs-clean    - 清理构建文件"
	@echo "  make docs-stats    - 显示文档统计"
	@echo "  make docs-help     - 显示帮助信息"

# 打包和发布命令

# 打包（构建sdist和wheel）
build:
	@echo "Building package..."
	python -m build
	@echo "Package built successfully!"

# 发布到测试PyPI
publish-test:
	@echo "Publishing to Test PyPI..."
	twine upload --repository testpypi dist/*
	@echo "Published to Test PyPI successfully!"

# 发布到正式PyPI
publish:
	@echo "Publishing to PyPI..."
	twine upload dist/*
	@echo "Published to PyPI successfully!"

# 清理构建产物
clean-build:
	@echo "Cleaning build artifacts..."
	rm -rf dist build *.egg-info
	@echo "Build artifacts cleaned!"

# 完整发布流程（清理→构建→发布）
release:
	@echo "Starting release process..."
	make clean-build
	make build
	make publish
	@echo "Release process completed!"

# 发布帮助信息
publish-help:
	@echo "打包和发布命令:"
	@echo "  make build         - 构建sdist和wheel包"
	@echo "  make publish-test  - 发布到测试PyPI"
	@echo "  make publish       - 发布到正式PyPI"
	@echo "  make clean-build   - 清理构建产物"
	@echo "  make release       - 完整发布流程（清理→构建→发布）"
	@echo "  make publish-help  - 显示发布帮助信息"

# 同步依赖命令
sync-deps:
	@echo "Syncing dependencies from pyproject.toml to requirements.txt..."
	@python -c """
import tomli

# 读取pyproject.toml
with open('pyproject.toml', 'rb') as f:
    config = tomli.load(f)

# 提取核心依赖
dependencies = config.get('project', {}).get('dependencies', [])

# 读取现有的requirements.txt内容
with open('requirements.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 分离注释和依赖部分
comment_lines = []
dep_lines = []

for line in lines:
    if line.strip().startswith('#') or not line.strip():
        comment_lines.append(line)
    else:
        dep_lines.append(line)

# 创建新的依赖部分
new_dep_lines = []
new_dep_lines.append('# Litefs 核心依赖\n')
for dep in dependencies:
    new_dep_lines.append(f'{dep}\n')
new_dep_lines.append('\n')

# 保留其他注释部分
core_comment_end = False
for line in comment_lines:
    if not core_comment_end:
        if line.strip() == '# Litefs 核心依赖':
            core_comment_end = True
    else:
        if line.strip() and not line.strip().startswith('#'):
            core_comment_end = False
        elif line.strip().startswith('# WSGI 服务器（可选）'):
            new_dep_lines.append(line)
        elif core_comment_end:
            continue
        else:
            new_dep_lines.append(line)

# 写入更新后的requirements.txt
with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.writelines(new_dep_lines)

print('Dependencies synced successfully!')
"""
	@echo "Dependencies synced successfully!"

# 帮助信息
help:
	@echo "=== Litefs 项目管理命令 ==="
	@echo "文档管理:"
	@echo "  make docs-serve    - 本地运行文档服务器"
	@echo "  make docs-build    - 构建 Sphinx API 文档"
	@echo "  make docs-check    - 检查文档链接"
	@echo "  make docs-clean    - 清理构建文件"
	@echo "  make docs-stats    - 显示文档统计"
	@echo "  make docs-help     - 显示文档帮助信息"
	@echo ""
	@echo "打包和发布:"
	@echo "  make build         - 构建sdist和wheel包"
	@echo "  make publish-test  - 发布到测试PyPI"
	@echo "  make publish       - 发布到正式PyPI"
	@echo "  make clean-build   - 清理构建产物"
	@echo "  make release       - 完整发布流程（清理→构建→发布）"
	@echo "  make publish-help  - 显示发布帮助信息"
	@echo ""
	@echo "依赖管理:"
	@echo "  make sync-deps     - 从pyproject.toml同步依赖到requirements.txt"
	@echo ""
	@echo "运行 'make <command>' 执行相应命令"
