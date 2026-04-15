.PHONY: docs-serve docs-build docs-check docs-clean docs-stats

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
