#!/usr/bin/env python
# coding: utf-8
"""
Litefs ASGI 示例

展示如何使用 Litefs 的 ASGI 功能，包括：
1. 基本路由
2. 异步处理函数
3. JSON 响应
4. 路径参数
5. 查询参数
"""

from litefs import Litefs
import asyncio
import time

app = Litefs()


@app.add_get('/', name='index')
async def index_handler(request):
    """首页"""
    return 'Hello from Litefs ASGI!'


@app.add_get('/async', name='async_example')
async def async_handler(request):
    """异步处理示例"""
    # 模拟极短的异步操作（1 毫秒延迟，避免影响测试速度）
    await asyncio.sleep(0.001)
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


@app.add_get('/query', name='query_example')
async def query_handler(request):
    """查询参数示例"""
    name = request.get.get('name', 'Guest')
    age = request.get.get('age', 'Unknown')
    return f'Hello {name}, you are {age} years old!'


@app.add_post('/api/data', name='api_data')
async def api_data_handler(request):
    """POST 请求示例"""
    data = request.data
    return {
        'status': 'success',
        'received_data': data,
        'timestamp': time.time()
    }


@app.add_get('/stream', name='stream_example')
async def stream_handler(request):
    """流式响应示例"""
    async def generate():
        for i in range(5):
            await asyncio.sleep(0.5)
            yield f'Chunk {i+1}\n'
    return generate()


# ASGI 应用
application = app.asgi()


if __name__ == '__main__':
    """直接运行示例"""
    import uvicorn
    print("Starting Litefs ASGI server...")
    print("Available endpoints:")
    print("  GET  /              - 首页")
    print("  GET  /async         - 异步处理示例")
    print("  GET  /user/{id}     - 路径参数示例")
    print("  GET  /query?name=...&age=... - 查询参数示例")
    print("  POST /api/data      - POST 请求示例")
    print("  GET  /stream        - 流式响应示例")
    print("\nRunning on http://127.0.0.1:8000")
    uvicorn.run('examples.asgi_example:application', 
                host='127.0.0.1', 
                port=8000, 
                reload=True)
