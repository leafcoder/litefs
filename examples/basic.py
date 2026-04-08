#!/usr/bin/env python
# coding: utf-8
"""
基本示例

展示 Litefs 框架的基本使用
"""

import sys
import os

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=9090,
    debug=True
)

# 添加路由
@app.add_get('/', name='index')
def index(request):
    """首页"""
    return 'Hello, Litefs!'

@app.add_get('/user/{id}', name='user')
def get_user(request, id):
    """获取用户信息"""
    return f'User ID: {id}'

@app.add_post('/user', name='create_user')
def create_user(request):
    """创建用户"""
    username = request.post.get('username', '')
    return f'Create user: {username}'

# 运行服务器
if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 基本示例")
    print("=" * 60)
    print("访问地址: http://localhost:9090")
    print("=" * 60)
    print("可用路由:")
    print("  GET  /         - 首页")
    print("  GET  /user/{id} - 用户信息")
    print("  POST /user     - 创建用户")
    print("=" * 60)
    
    app.run(processes=6)
