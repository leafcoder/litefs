#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib.request
import sys

try:
    print("Testing WSGI server at http://localhost:9090")
    print("-" * 50)
    
    response = urllib.request.urlopen('http://localhost:9090/index.html.py', timeout=5)
    status = response.status
    content = response.read().decode('utf-8')
    
    print(f"Status: {status}")
    print(f"Content: {content}")
    print("-" * 50)
    print("SUCCESS: WSGI server is working!")
    
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} - {e.reason}")
    sys.exit(1)
except urllib.error.URLError as e:
    print(f"URL Error: {e.reason}")
    print("Make sure the WSGI server is running on port 9090")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
