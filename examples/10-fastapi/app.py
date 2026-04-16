#!/usr/bin/env python
# coding: utf-8
"""
FastAPI 测试示例

用于与 Litefs ASGI 性能对比
"""

from fastapi import FastAPI, Path, Query
import asyncio
import time

app = FastAPI()


@app.get('/')
async def index():
    """首页"""
    return 'Hello from FastAPI!'


@app.get('/async')
async def async_example():
    """异步处理示例"""
    await asyncio.sleep(0.01)  # 模拟异步操作
    return {
        'message': 'Hello from async handler!',
        'timestamp': time.time(),
        'async': True
    }


@app.get('/user/{id}')
async def user_detail(id: int = Path(...)):
    """路径参数示例"""
    return {
        'user_id': id,
        'message': f'User details for ID: {id}'
    }


@app.get('/query')
async def query_example(name: str = Query('Guest'), age: str = Query('Unknown')):
    """查询参数示例"""
    return f'Hello {name}, you are {age} years old!'


if __name__ == '__main__':
    import uvicorn
    print("Starting FastAPI server...")
    print("Available endpoints:")
    print("  GET  /              - 首页")
    print("  GET  /async         - 异步处理示例")
    print("  GET  /user/{id}     - 路径参数示例")
    print("  GET  /query?name=...&age=... - 查询参数示例")
    print("\nRunning on http://127.0.0.1:8001")
    uvicorn.run('app:app', 
                host='127.0.0.1', 
                port=8001, 
                reload=True)
