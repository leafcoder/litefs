#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs


def main():
    """会话管理示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='./examples/05-session/site',
        debug=True
    )
    
    print("=" * 60)
    print("Litefs Session Management Example")
    print("=" * 60)
    print(f"访问地址: http://localhost:8080/session")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
