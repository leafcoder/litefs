#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs

app = litefs.Litefs(
    webroot='examples/01-quickstart/site',
    debug=False,
    log='./wsgi_access.log'
)

application = app.wsgi()

print("=" * 60)
print("Litefs WSGI Application (Standalone)")
print("=" * 60)
print("Version:", litefs.__version__)
print("Webroot:", app.config.webroot)
print("Debug:", app.config.debug)
print("=" * 60)
print("\nStarting WSGI server on http://localhost:9090")
print("Press Ctrl+C to stop")
print("=" * 60)

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    
    try:
        httpd = make_server('localhost', 9090, application)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
