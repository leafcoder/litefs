PYTHON=python
PYTHONPATH=src
WEBROOT=examples/basic/site
HOST=localhost
PORT=9090

.PHONY: help install dev-install dev-uninstall clean build wheel test \
	test-serve serve dev-serve wsgi-gunicorn wsgi-uwsgi wsgi-waitress \
	format lint type-check check-all \
	ex-basic ex-health-check ex-middleware ex-config \
	ex-wsgi ex-wsgi-simple ex-wsgi-standalone

help:
	@echo "Litefs 开发命令"
	@echo ""
	@echo "安装相关:"
	@echo "  make install          - 安装包到当前环境"
	@echo "  make dev-install       - 开发模式安装（可编辑）"
	@echo "  make dev-uninstall     - 卸载开发模式安装"
	@echo ""
	@echo "开发相关:"
	@echo "  make format            - 格式化代码（black + isort）"
	@echo "  make lint              - 代码检查（ruff）"
	@echo "  make type-check        - 类型检查（mypy）"
	@echo "  make check-all         - 运行所有检查（format + lint + type-check）"
	@echo ""
	@echo "测试相关:"
	@echo "  make test              - 运行所有测试"
	@echo "  make test-unit        - 运行单元测试"
	@echo "  make test-cov         - 运行测试并生成覆盖率报告"
	@echo ""
	@echo "示例相关:"
	@echo "  make ex-basic            - 运行基础示例"
	@echo "  make ex-health-check     - 运行健康检查示例"
	@echo "  make ex-middleware       - 运行中间件示例"
	@echo "  make ex-config           - 运行配置管理示例"
	@echo "  make ex-wsgi             - 运行 WSGI 示例"
	@echo "  make ex-wsgi-simple      - 运行 WSGI 简单示例（带中间件）"
	@echo "  make ex-wsgi-standalone  - 运行 WSGI 独立服务器示例"
	@echo ""
	@echo "服务器相关:"
	@echo "  make serve             - 启动开发服务器（默认端口 9090）"
	@echo "  make dev-serve         - 启动开发服务器（开发模式）"
	@echo "  make wsgi-gunicorn     - 使用 Gunicorn 启动 WSGI 服务器"
	@echo "  make wsgi-uwsgi        - 使用 uWSGI 启动 WSGI 服务器"
	@echo "  make wsgi-waitress    - 使用 Waitress 启动 WSGI 服务器"
	@echo ""
	@echo "构建相关:"
	@echo "  make build             - 构建源码包"
	@echo "  make wheel             - 构建 wheel 包"
	@echo "  make clean             - 清理构建文件"
	@echo ""
	@echo "发布相关:"
	@echo "  make upload-test       - 上传到测试 PyPI"
	@echo "  make upload            - 上传到 PyPI"

install:
	$(PYTHON) setup.py install

dev-install:
	$(PYTHON) -m pip install -e .

dev-uninstall:
	$(PYTHON) -m pip uninstall -y litefs

clean:
	rm -rf build dist *.egg-info __pycache__ src/__pycache__ \
		tests/__pycache__ tests/*.pyc .coverage htmlcov \
		.mypy_cache .ruff_cache .pytest_cache

build: wheel
	$(PYTHON) setup.py build sdist

wheel:
	$(PYTHON) setup.py bdist_wheel

upload-test:
	pip install twine; \
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

upload:
	pip install twine; \
	twine upload dist/*

format:
	@echo "格式化代码..."
	black src/ tests/ examples/
	isort src/ tests/ examples/
	@echo "代码格式化完成"

lint:
	@echo "运行代码检查..."
	ruff check src/ tests/ examples/
	@echo "代码检查完成"

type-check:
	@echo "运行类型检查..."
	mypy src/
	@echo "类型检查完成"

check-all: format lint type-check
	@echo "所有检查完成"

test:
	@echo "运行所有测试..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests/ -v

test-unit:
	@echo "运行单元测试..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests/unit/ -v

test-cov:
	@echo "运行测试并生成覆盖率报告..."
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest tests/ \
		--cov=src --cov-report=html --cov-report=term
	@echo "覆盖率报告已生成: htmlcov/index.html"

test-serve:
	@echo "启动开发服务器（调试模式）..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	cd examples/basic && PYTHONPATH=../../$(PYTHONPATH) $(PYTHON) example.py

ex-basic:
	@echo "运行基础示例..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	cd examples/basic && PYTHONPATH=../../$(PYTHONPATH) $(PYTHON) example.py

serve:
	@echo "启动开发服务器..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m litefs \
		--host $(HOST) --port $(PORT) --webroot $(WEBROOT)

dev-serve:
	@echo "启动开发服务器（调试模式）..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m litefs \
		--host $(HOST) --port $(PORT) --webroot $(WEBROOT) --debug

wsgi-gunicorn:
	@echo "使用 Gunicorn 启动 WSGI 服务器..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	@echo ""
	@echo "安装 Gunicorn: pip install gunicorn"
	PYTHONPATH=$(PYTHONPATH) gunicorn -w 4 -b $(HOST):$(PORT) \
		--access-logfile /dev/null --error-logfile /dev/null \
		--log-level critical \
		examples.wsgi.wsgi_example:application

wsgi-uwsgi:
	@echo "使用 uWSGI 启动 WSGI 服务器..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	@echo ""
	@echo "安装 uWSGI: pip install uwsgi"
	PYTHONPATH=$(PYTHONPATH) uwsgi --http $(HOST):$(PORT) \
		--wsgi-file examples/wsgi/wsgi_example.py \
		--master \
		--processes 4 \
		--enable-threads \
		--threads 2

wsgi-waitress:
	@echo "使用 Waitress 启动 WSGI 服务器..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "按 Ctrl+C 停止服务器"
	@echo ""
	@echo "安装 Waitress: pip install waitress"
	PYTHONPATH=$(PYTHONPATH) waitress-serve --port=$(PORT) \
		--threads=4 \
		examples.wsgi.wsgi_example:application

ex-health-check:
	@echo "运行健康检查示例..."
	@echo "访问地址: http://$(HOST):$(PORT)/"
	@echo "健康检查端点: http://$(HOST):$(PORT)/health"
	@echo "就绪检查端点: http://$(HOST):$(PORT)/health/ready"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) examples/health_check_example.py

ex-middleware:
	@echo "运行中间件示例..."
	@echo "此示例展示各种中间件的使用方法"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) examples/middleware_example.py

ex-config:
	@echo "运行配置管理示例..."
	@echo "此示例展示配置管理的各种用法"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) examples/config_example.py

ex-wsgi:
	@echo "运行 WSGI 示例..."
	@echo "此示例创建 WSGI 应用，可与 Gunicorn/uWSGI/Waitress 一起使用"
	@echo "使用 Gunicorn: gunicorn -w 4 -b :$(PORT) examples/wsgi/wsgi_example:application"
	@echo "使用 uWSGI: uwsgi --http :$(PORT) --wsgi-file examples/wsgi/wsgi_example.py"
	@echo "使用 Waitress: waitress-serve --port=$(PORT) examples/wsgi/wsgi_example:application"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) examples/wsgi/wsgi_example.py

ex-wsgi-simple:
	@echo "运行 WSGI 简单示例（带中间件）..."
	@echo "此示例展示如何在 WSGI 模式下使用中间件"
	@echo "访问地址: http://$(HOST):9090"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) examples/wsgi/wsgi_simple.py

ex-wsgi-standalone:
	@echo "运行 WSGI 独立服务器示例..."
	@echo "此示例使用 wsgiref.simple_server 运行 WSGI 应用"
	@echo "访问地址: http://$(HOST):9090"
	@echo "按 Ctrl+C 停止服务器"
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) examples/wsgi/wsgi_standalone.py
