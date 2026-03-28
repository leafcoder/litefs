#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs

app = litefs.Litefs(
    webroot='examples/01-quickstart/site',
    debug=True,
    log='./wsgi_access.log'
)

application = app.wsgi()

print("=" * 60)
print("Litefs WSGI Application (Debug Mode)")
print("=" * 60)
print("Version:", litefs.__version__)
print("Webroot:", app.config.webroot)
print("Debug:", app.config.debug)
print("=" * 60)
print("\nUsage:")
print(f"  Gunicorn: gunicorn -w 4 -b :{app.port} wsgi_simple:application")
print(f"  uWSGI:    uwsgi --http :{app.port} --wsgi-file wsgi_simple.py")
print(f"  Waitress: waitress-serve --port={app.port} wsgi_simple:application")
print("=" * 60)
