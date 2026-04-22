#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_wsgi_import():
    """
    测试 WSGI 接口是否可以正常导入
    """
    print("Testing WSGI interface import...")
    
    try:
        from litefs.core import Litefs
        print("OK: litefs.core module imported successfully")
    except ImportError as e:
        print("ERROR: Failed to import litefs.core:", str(e))
        return False
    
    try:
        app = Litefs(webroot='./demo/site')
        print("OK: Litefs instance created")
    except Exception as e:
        print("ERROR: Failed to create Litefs instance:", str(e))
        import traceback
        traceback.print_exc()
        return False
    
    try:
        application = app.wsgi()
        print("OK: WSGI application created")
    except Exception as e:
        print("ERROR: Failed to create WSGI application:", str(e))
        import traceback
        traceback.print_exc()
        return False
    
    # 测试 application 是否可调用
    if not callable(application):
        print("ERROR: application is not callable")
        return False
    
    print("OK: application is callable")
    
    print("\nBasic WSGI interface tests passed!")
    print("\nNote: Full WSGI testing requires installing dependencies:")
    print("  pip install -r requirements.txt")
    print("\nThen test with:")
    print("  gunicorn -w 4 -b :8000 wsgi_example:application")
    print("  uwsgi --http :8000 --wsgi-file wsgi_example.py")
    
    return True

if __name__ == '__main__':
    success = test_wsgi_import()
    sys.exit(0 if success else 1)
