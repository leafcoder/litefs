#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs


def main():
    """缓存后端 Web 示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='./examples/10-cache-backends-web/site',
        debug=True
    )
    
    print("=" * 60)
    print("Litefs Cache Backends Web Example")
    print("=" * 60)
    print(f"访问地址: http://localhost:8080/cache-backends-web")
    print("=" * 60)
    print("\n支持的缓存后端:")
    print("  - Memory Cache (内存缓存)")
    print("  - Tree Cache (树形缓存)")
    print("  - Redis Cache (Redis 缓存)")
    print("  - Database Cache (数据库缓存)")
    print("  - Memcache Cache (Memcache 缓存)")
    print("=" * 60)
    print("\n注意:")
    print("  - Redis 需要本地安装并运行在 localhost:6379")
    print("  - Memcache 需要本地安装并运行在 localhost:11211")
    print("  - Database Cache 使用内存数据库，无需额外配置")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
