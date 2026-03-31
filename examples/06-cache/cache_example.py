#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.cache import MemoryCache, TreeCache


def main():
    """缓存管理示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='./site',
        debug=True
    )
    
    print("=" * 60)
    print("Litefs Cache Management Example")
    print("=" * 60)
    print(f"访问地址: http://localhost:8080/cache")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
