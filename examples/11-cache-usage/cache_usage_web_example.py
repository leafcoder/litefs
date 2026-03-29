#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs


def main():
    """缓存使用 Web 示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8083,
        webroot='./examples/11-cache-usage/site',
        debug=True
    )

    print("=" * 60)
    print("Litefs 缓存使用 Web 示例")
    print("=" * 60)
    print(f"访问地址: http://localhost:8083/cache-demo")
    print("=" * 60)
    print("\n功能演示:")
    print("  - 基本缓存操作（设置、获取、删除）")
    print("  - 用户数据缓存")
    print("  - 商品列表缓存")
    print("  - 系统配置缓存")
    print("  - 全局缓存共享")
    print("=" * 60)

    app.run()


if __name__ == '__main__':
    main()
