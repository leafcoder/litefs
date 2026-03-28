#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WSGI 应用文件

用于在 Gunicorn、uWSGI 等 WSGI 服务器中部署应用
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from fullstack_example.app import FullStackApp

# 创建应用实例
app = FullStackApp()

# 获取 WSGI application callable
application = app.get_wsgi_application()

# 打印启动信息
print("=" * 80)
print("Litefs Full Stack WSGI Application")
print("=" * 80)
print(f"Webroot: {app.app.config.webroot}")
print(f"Debug: {app.app.config.debug}")
print("=" * 80)
print("Usage:")
print("  Gunicorn: gunicorn -w 4 -k gevent -b :8000 wsgi:application")
print("  uWSGI:    uwsgi --http :8000 --wsgi-file wsgi.py")
print("  Waitress: waitress-serve --port=8000 wsgi:application")
print("=" * 80)
