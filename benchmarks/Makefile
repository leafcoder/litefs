.PHONY: install benchmark clean report help

# 颜色定义
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
NC     := \033[0m

# 简化 PATH，避免参数过长
PATH_PREFIX := PATH=$$HOME/.pyenv/shims:$$HOME/.pyenv/bin:$$HOME/Installed:/usr/local/bin:/usr/bin:/bin

help:
	@echo "$(BLUE)LiteFS 性能基准测试套件$(NC)"
	@echo ""
	@echo "可用命令:"
	@echo "  $(GREEN)make install$(NC)    - 安装测试依赖"
	@echo "  $(GREEN)make benchmark$(NC)  - 运行基准测试（10s，1/6进程，500/1000并发）"
	@echo "  $(GREEN)make report$(NC)     - 查看最新测试报告"
	@echo "  $(GREEN)make clean$(NC)      - 清理测试结果"
	@echo ""

install:
	@echo "$(BLUE)安装测试依赖...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)依赖安装完成!$(NC)"
	@echo "注意: 如果 wrk 未安装，请运行: sudo apt install wrk 或从源码编译"

benchmark:
	@echo "$(BLUE)运行性能基准测试...$(NC)"
	$(PATH_PREFIX) python run_benchmark.py

clean:
	@echo "$(YELLOW)清理测试结果...$(NC)"
	rm -rf results/
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)清理完成!$(NC)"

report:
	@echo "$(BLUE)查看最新测试报告...$(NC)"
	@if [ -L results/latest ]; then \
		open results/latest/report.html 2>/dev/null || echo "报告路径: $$(pwd)/results/latest/report.html"; \
	elif [ -d results/ ]; then \
		latest=$$(ls -td results/*/ 2>/dev/null | grep -v latest | head -1); \
		if [ -n "$$latest" ]; then \
			open "$$latest/report.html" 2>/dev/null || echo "报告路径: $$(pwd)/$$latest/report.html"; \
		else \
			echo "没有找到测试报告，请先运行 make benchmark"; \
		fi; \
	else \
		echo "没有找到测试报告，请先运行 make benchmark"; \
	fi
