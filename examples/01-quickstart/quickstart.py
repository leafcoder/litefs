#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs


def main():
    """快速入门示例 - 最简单的 Litefs 应用"""
    app = litefs.Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='./examples/01-quickstart/site',
        debug=True
    )
    
    print("=" * 60)
    print("Litefs Quick Start Example")
    print("=" * 60)
    print(f"Version: {litefs.__version__}")
    print(f"访问地址: http://localhost:8080")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
