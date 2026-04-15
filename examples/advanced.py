#!/usr/bin/env python
# coding: utf-8
"""
高级示例

展示 Litefs 框架的高级功能：
1. 响应对象的使用
2. 配置管理
3. 插件系统
4. 安全特性
"""

import sys
import os

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))  # noqa: E402

from litefs import Litefs, Response  # noqa: E402
from litefs.plugins.base import Plugin  # noqa: E402

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=9090,
    debug=True
)

# 示例插件
class HelloPlugin(Plugin):
    """示例插件"""
    name = 'hello'
    
    def initialize(self):
        print('HelloPlugin initialized')
    
    def shutdown(self):
        print('HelloPlugin shutdown')

# 注册插件
app.register_plugin(HelloPlugin)

# 添加路由
@app.add_get('/', name='index')
def index(request):
    """首页"""
    # 使用 Response 对象返回 JSON 响应
    return Response.json({
        'message': 'Hello, Litefs!',
        'version': '0.5.0',
        'features': ['Response object', 'Config management', 'Plugin system', 'CSRF protection']
    })

@app.add_get('/config', name='config')
def get_config(request):
    """获取配置信息"""
    # 访问配置
    config = request.app.config
    return Response.json({
        'host': config.host,
        'port': config.port,
        'debug': config.debug,
        'cache_backend': config.cache_backend
    })

@app.add_get('/plugins', name='plugins')
def get_plugins(request):
    """获取插件信息"""
    # 访问插件
    plugins = request.app.get_all_plugins()
    plugin_names = [plugin.name for plugin in plugins]
    return Response.json({
        'plugins': plugin_names
    })

@app.add_post('/form', name='form_submit')
def form_submit(request):
    """表单提交（包含 CSRF 保护）"""
    # 表单数据
    data = request.post
    return Response.json({
        'message': 'Form submitted successfully',
        'data': data
    })

# 运行服务器
if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 高级示例")
    print("=" * 60)
    print("访问地址: http://localhost:9090")
    print("=" * 60)
    print("可用路由:")
    print("  GET  /         - 首页")
    print("  GET  /config   - 配置信息")
    print("  GET  /plugins  - 插件信息")
    print("  POST /form     - 表单提交")
    print("=" * 60)
    
    app.run(processes=6)
