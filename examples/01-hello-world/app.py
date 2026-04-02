#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hello World 示例 - 最简单的 Litefs 应用

这个示例展示了如何创建一个最基本的 Litefs 应用，
包含一个简单的路由和处理函数。
"""

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

# 定义首页处理函数
@app.add_get('/', name='index')
def index_handler(request):
    """首页处理函数 - 返回简单的问候语"""
    return {"Hello": "World"}

# 定义关于页面处理函数
@app.add_get('/about', name='about')
def about_handler(request):
    """关于页面处理函数"""
    return {
        'name': 'Litefs',
        'description': 'A lightweight Python web framework',
        'features': [
            'Simple and intuitive API',
            'Flexible routing system',
            'Built-in middleware support',
            'Session and cache management'
        ]
    }


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs Hello World Example")
    print("=" * 60)
    print("访问地址: http://localhost:8080")
    print("=" * 60)
    print("可用路由:")
    print("  GET /       - 首页")
    print("  GET /about  - 关于页面")
    print("=" * 60)
    
    app.run(processes=8)
