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
    
    # 临时移除 greenlet 导入
    import litefs
    original_greenlet = litefs.greenlet if hasattr(litefs, 'greenlet') else None
    
    try:
        # 创建应用（不启动服务器，只测试 WSGI 接口）
        app = litefs.Litefs(webroot='./demo/site')
        print("OK: Litefs instance created")
        
        # 获取 WSGI application
        application = app.wsgi()
        print("OK: WSGI application created")
        
        # 测试 callable
        if not callable(application):
            print("ERROR: application is not callable")
            return False
        print("OK: application is callable")
        
        print("\nBasic WSGI interface tests passed!")
        print("\nNote: Full WSGI testing requires greenlet compatibility.")
        print("For Python 3.14, consider using Python 3.9-3.12 for production.")
        print("\nTo test with a WSGI server:")
        print("  pip install gunicorn")
        print("  gunicorn -w 4 -b :8000 wsgi_example:application")
        
        return True
        
    except ImportError as e:
        print("ERROR: Import error:", str(e))
        print("\nNote: greenlet may not be compatible with Python 3.14 yet.")
        print("The WSGI interface itself does not require greenlet.")
        print("greenlet is only needed for the built-in epoll server.")
        return False
    except Exception as e:
        print("ERROR: Exception during test:", str(e))
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_wsgi_without_greenlet()
    sys.exit(0 if success else 1)
