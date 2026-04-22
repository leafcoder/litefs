#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_wsgi_without_greenlet():
    """
    测试 WSGI 接口（不依赖 greenlet）
    """
    print("Testing WSGI interface without greenlet...")
    
    # 创建应用（不启动服务器，只测试 WSGI 接口）
    from litefs.core import Litefs
    app = Litefs(webroot='./demo/site')
    print("OK: Litefs instance created")
    
    # 获取 WSGI application
    application = app.wsgi()
    print("OK: WSGI application created")
    
    # 测试 callable
    assert callable(application), "application is not callable"
    print("OK: application is callable")
    
    print("\nBasic WSGI interface tests passed!")
    print("\nNote: Full WSGI testing requires greenlet compatibility.")
    print("For Python 3.14, consider using Python 3.9-3.12 for production.")
    print("\nTo test with a WSGI server:")
    print("  pip install gunicorn")
    print("  gunicorn -w 4 -b :8000 wsgi_example:application")

if __name__ == '__main__':
    test_wsgi_without_greenlet()
