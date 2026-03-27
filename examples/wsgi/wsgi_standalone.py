#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True

def main():
    print("=" * 60)
    print("Litefs WSGI Application")
    print("=" * 60)
    
    try:
        import litefs
        print("Version:", litefs.__version__)
        
        app = litefs.Litefs(
            webroot='examples/basic/site',
            debug=False,
            log='./wsgi_access.log'
        )
        
        print("Webroot:", app.config.webroot)
        print("Debug:", app.config.debug)
        print("=" * 60)
        print("\nStarting WSGI server on http://localhost:9090")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        application = app.wsgi()
        
        from wsgiref.simple_server import make_server
        httpd = make_server('localhost', 9090, application)
        httpd.serve_forever()
        
    except ImportError as e:
        print(f"\nImport Error: {e}")
        print("\nNote: litefs requires Linux for the built-in epoll server.")
        print("However, WSGI interface can be used on Windows with:")
        print("  - Python 3.8-3.12 (greenlet compatible)")
        print("  - A WSGI server (Waitress, Gunicorn, etc.)")
        print("\nFor production deployment on Linux:")
        print("  gunicorn -w 4 -b :9090 wsgi_example:application")
        return 1
    except KeyboardInterrupt:
        print("\nServer stopped.")
        return 0
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
