.PHONY: install test hello sql clean help

# 颜色定义
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
NC     := \033[0m

help:
	@echo "$(BLUE)LiteFS 性能测试套件$(NC)"
	@echo ""
	@echo "可用命令:"
	@echo "  $(GREEN)make install$(NC)   - 安装测试依赖"
	@echo "  $(GREEN)make test$(NC)      - 运行所有测试"
	@echo "  $(GREEN)make hello$(NC)     - 运行 Hello World 测试"
	@echo "  $(GREEN)make sql$(NC)       - 运行 SQL 查询测试"
	@echo "  $(GREEN)make clean$(NC)     - 清理测试结果"
	@echo ""

install:
	@echo "$(BLUE)安装测试依赖...$(NC)"
	pip install -r requirements.txt
	@echo "$(GREEN)依赖安装完成!$(NC)"
	@echo "注意: 如果 wrk 未安装，请运行: sudo apt install wrk"

test: hello sql
	@echo "$(GREEN)所有测试完成!$(NC)"

hello:
	@echo "$(BLUE)运行 Hello World 性能测试...$(NC)"
	cd $(shell pwd) && pytest tests/test_hello_world.py -v -s

sql:
	@echo "$(BLUE)运行 SQL 查询性能测试...$(NC)"
	cd $(shell pwd) && pytest tests/test_sql_query.py -v -s

clean:
	@echo "$(YELLOW)清理测试结果...$(NC)"
	rm -rf results/
	rm -rf __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)清理完成!$(NC)"

report:
	@echo "$(BLUE)查看最新测试报告...$(NC)"
	@latest=$$(ls -td results/*/ 2>/dev/null | head -1); \
	if [ -n "$$latest" ]; then \
		open "$$latest/report.html" 2>/dev/null || echo "报告路径: $$latest/report.html"; \
	else \
		echo "没有找到测试报告"; \
	fi
