.PHONY: docs-serve docs-build docs-check docs-clean docs-stats build publish-test publish clean-build release publish-help sync-deps lint lint-fix test test-unit test-cov benchmark benchmark-check audit help

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

# 静态检查命令

# 全量静态检查（flake8 + ruff + mypy），任一失败即返回非零退出码
lint:
	@echo ">>> flake8（PEP 8 规范检查）"
	python -m flake8 src
	@echo ">>> ruff（快速静态检查）"
	python -m ruff check src
	@echo ">>> mypy（类型检查）"
	python -m mypy src
	@echo "静态检查全部通过"

# 应用 ruff 安全自动修复（仅 src 范围，不改变运行时行为）
lint-fix:
	@echo ">>> ruff 安全自动修复"
	python -m ruff check src --fix
	@echo "自动修复完成，请复核 diff 后再提交"

# 测试命令

# 全量测试（单元 + 集成 + 回归），静默输出仅显示进度与摘要
test:
	@echo ">>> 运行全量测试"
	python -m pytest tests/ -q
	@echo "全量测试通过"

# 仅运行单元测试
test-unit:
	@echo ">>> 运行单元测试"
	python -m pytest tests/unit -q
	@echo "单元测试通过"

# 带覆盖率报告的测试（生成终端摘要与 HTML 报告 htmlcov/index.html）
test-cov:
	@echo ">>> 运行测试并统计覆盖率"
	python -m pytest tests/ -q --cov=src/litefs --cov-report=term-missing --cov-report=html
	@echo "覆盖率报告已生成：htmlcov/index.html"

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
	@python scripts/sync_deps.py
	@echo "Dependencies synced successfully!"

# 性能回归门禁：运行压测并比对已固化的阈值基线
# 压测需独占 CPU，务必在专用压测机上执行
benchmark:
	@echo ">>> 运行性能基准测试"
	@$(MAKE) -C benchmarks benchmark
	@echo "性能基准测试完成"

# 性能回归门禁：比对最新压测结果与已固化的阈值基线
# 退出码 0 通过 / 1 存在性能回退 / 2 输入缺失（严格模式）
benchmark-check:
	@echo ">>> 性能回归阈值比对"
	@python benchmarks/compare_benchmark.py
	@echo "性能回归检查完成"

# 依赖安全审计：pip-audit 扫描运行时依赖清单
# 退出码 0 无漏洞 / 1 发现漏洞 / 2 工具不可用
audit:
	@echo ">>> 依赖安全审计（pip-audit）"
	@python scripts/audit_deps.py
	@echo "依赖安全审计完成"

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
	@echo "静态检查:"
	@echo "  make lint          - 全量静态检查（flake8 + ruff + mypy）"
	@echo "  make lint-fix      - 应用 ruff 安全自动修复"
	@echo ""
	@echo "测试:"
	@echo "  make test          - 运行全量测试"
	@echo "  make test-unit     - 仅运行单元测试"
	@echo "  make test-cov      - 运行测试并生成覆盖率报告（HTML）"
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
	@echo "性能与安全:"
	@echo "  make benchmark      - 运行性能基准测试（需独占 CPU）"
	@echo "  make benchmark-check - 比对压测结果与性能回归阈值基线"
	@echo "  make audit          - pip-audit 依赖安全审计"
	@echo ""
	@echo "运行 'make <command>' 执行相应命令"
