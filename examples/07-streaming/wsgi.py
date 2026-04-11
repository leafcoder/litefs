#!/usr/bin/env python
# coding: utf-8

"""
WSGI 入口文件

用于在 WSGI 服务器（如 gunicorn、uWSGI）中运行应用
"""

from app import app

# 导出 WSGI application
application = app.wsgi()
