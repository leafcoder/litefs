#!/usr/bin/env python
# coding: utf-8
"""
测试 asyncio HTTP 服务器是否能正常工作
"""

import sys
import os
import asyncio
import time

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs
from litefs.server.asyncio import run_asyncio

# 创建应用
app = Litefs(
    host='127.0.0.1',
    port=9998,
    debug=True
)


@app.add_get('/', name='index')
async def index_handler(request):
    """首页"""
    return 'Hello from Litefs AsyncIO!'


@app.add_get('/async', name='async_example')
async def async_handler(request):
    """异步处理示例"""
    await asyncio.sleep(0.01)
    return {
        'message': 'Hello from async handler!',
        'timestamp': time.time(),
        'async': True
    }


@app.add_get('/user/{id}', name='user_detail')
async def user_detail_handler(request, id):
    """路径参数示例"""
    return {
        'user_id': id,
        'message': f'User details for ID: {id}'
    }


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs AsyncIO HTTP Server Test")
    print("=" * 60)
    print("Testing endpoints:")
    print("  GET /         - Index")
    print("  GET /async    - Async handler")
    print("  GET /user/{id} - Path parameter")
    print("=" * 60)
    print("Server running on http://127.0.0.1:9998")
    print("=" * 60)
    
    run_asyncio(app, host='127.0.0.1', port=9998, processes=1)
