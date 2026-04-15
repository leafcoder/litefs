#!/usr/bin/env python
# coding: utf-8
"""
测试 Litefs 与 Starlette 的集成

验证 Litefs 的 ASGI 实现是否可以与 Starlette 框架集成
"""

import sys
import os

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs

# 创建 Litefs 应用
app = Litefs()


@app.add_get('/', name='index')
async def index_handler(request):
    """首页"""
    return 'Hello from Litefs ASGI!'


@app.add_get('/async', name='async_example')
async def async_handler(request):
    """异步处理示例"""
    import asyncio
    await asyncio.sleep(0.01)
    return {
        'message': 'Hello from async handler!',
        'async': True
    }


@app.add_get('/user/{id}', name='user_detail')
async def user_detail_handler(request, id):
    """路径参数示例"""
    return {
        'user_id': id,
        'message': f'User details for ID: {id}'
    }


# 创建 ASGI 应用
application = app.asgi()


if __name__ == '__main__':
    """测试 ASGI 应用"""
    import uvicorn
    
    print("=" * 60)
    print("Litefs ASGI 测试")
    print("=" * 60)
    print("测试端点:")
    print("  GET /         - 首页")
    print("  GET /async    - 异步处理示例")
    print("  GET /user/{id} - 路径参数示例")
    print("=" * 60)
    
    uvicorn.run(
        'test_starlette_integration:application',
        host='127.0.0.1',
        port=8000,
        reload=True
    )
