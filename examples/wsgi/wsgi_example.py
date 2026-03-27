#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True

import litefs

# 配置 Litefs 应用
app = litefs.Litefs(
    webroot='examples/basic/site',
    debug=False,
    log='./wsgi_access.log'
)

# 获取 WSGI application callable
application = app.wsgi()

# 打印启动信息
print("=" * 60)
print("Litefs WSGI Application")
print("=" * 60)
print("Version:", litefs.__version__)
print("Webroot:", app.config.webroot)
print("Debug:", app.config.debug)
print("=" * 60)
print("\nUsage:")
print(f"  Gunicorn: gunicorn -w 4 -b :{app.port} wsgi_example:application")
print(f"  uWSGI:    uwsgi --http :{app.port} --wsgi-file wsgi_example.py")
print(f"  Waitress: waitress-serve --port={app.port} wsgi_example:application")
print("=" * 60)

