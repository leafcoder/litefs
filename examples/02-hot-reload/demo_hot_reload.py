#!/usr/bin/env python
# coding: utf-8

"""
热重载功能演示

这个示例展示了 LiteFS 的热重载功能：
1. 修改 Python 文件后，服务器会自动重新加载应用
2. 路由、中间件等变更会被正确感知
3. 无需手动重启服务器

使用方法：
1. 运行此脚本：python demo_hot_reload.py
2. 访问 http://localhost:8080
3. 修改此文件中的 index_handler 函数（例如修改返回值）
4. 保存文件后，刷新浏览器查看变化
"""

import sys
import os

# 添加 litefs 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs
from litefs.routing import get, post

# 创建应用
app = Litefs(host='0.0.0.0', port=8080, debug=True)

# 添加路由
@get('/', name='index')
def index_handler(request):
    """首页处理函数"""
    return {
        'message': 'Hello, Hot Reload!',
        'version': '1.0',
        'tip': 'Try modifying this file and saving it to see hot reload in action!'
    }

@get('/hello', name='hello')
def hello_handler(request):
    """Hello 处理函数"""
    return {'message': 'Hello World'}

@post('/echo', name='echo')
def echo_handler(request):
    """Echo 处理函数"""
    return {
        'method': request.method,
        'body': request.body
    }

# 注册路由
app.register_routes(__name__)

if __name__ == '__main__':
    print("=" * 60)
    print("LiteFS Hot Reload Demo")
    print("=" * 60)
    print("Server starting on http://0.0.0.0:8080")
    print("Try modifying this file and saving it to see hot reload!")
    print("=" * 60)
    
    # 启动服务器（poll_interval 设置得小一些以便快速响应文件变化）
    app.run(poll_interval=0.1, processes=1)
