#!/usr/bin/env python
# coding: utf-8

"""
快速入门示例

展示 Litefs 的核心特性：
- 路由系统（装饰器风格）
- 中间件
- 模板渲染
- 静态文件
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.core import Litefs
from litefs.routing import get, post
from litefs.middleware.logging import LoggingMiddleware
from litefs.session.session import MemorySessionStore

app = Litefs(
    host='0.0.0.0',
    port=8081,
    debug=True,
)

app.add_static('/static', 'static')

app.add_middleware(LoggingMiddleware)

session_store = MemorySessionStore()


@get('/', name='index')
def index(request):
    """首页"""
    cookie = request.cookie
    session_id = None
    if cookie:
        session_id = cookie.get('session_id', {}).value if hasattr(cookie.get('session_id', {}), 'value') else None

    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())

    session = session_store.get(session_id)
    if not session:
        session = session_store.create()
        session.id = session_id

    visits = session.data.get('visits', 0) + 1
    session.data['visits'] = visits
    session_store.save(session)

    return request.render_template('index.html', **{
        'title': 'Litefs 快速入门',
        'visits': visits,
        'features': [
            {'name': '路由系统', 'desc': '装饰器风格，支持路径参数'},
            {'name': '中间件', 'desc': '请求/响应拦截，日志记录'},
            {'name': '模板渲染', 'desc': 'Mako 模板引擎'},
            {'name': '静态文件', 'desc': '自动 MIME 类型检测'},
        ]
    })


@get('/about', name='about')
def about(request):
    """关于页面"""
    return {
        'name': 'Litefs',
        'version': '1.0.0',
        'description': '轻量级 Python Web 框架',
    }


@get('/user/{id}', name='user_detail')
def user_detail(request, id):
    """用户详情 - 路径参数示例"""
    return {
        'user': {
            'id': id,
            'name': f'User {id}',
        }
    }


@post('/api/data', name='api_data')
def api_data(request):
    """API 接口 - POST 示例"""
    data = request.json if hasattr(request, 'json') else {}
    return {
        'status': 'success',
        'received': data,
    }


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 快速入门示例")
    print("=" * 60)
    print()
    print("展示特性:")
    print("  - 路由系统（装饰器风格）")
    print("  - 中间件（日志）")
    print("  - 模板渲染")
    print("  - 静态文件服务")
    print()
    print("访问地址: http://localhost:8081")
    print("=" * 60)

    app.run()
