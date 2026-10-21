#!/usr/bin/env python
# coding: utf-8

"""
Prometheus 监控示例

展示 Litefs 的 Prometheus 监控中间件：

- HTTP 请求总数 / 错误数 / 延迟直方图 / 响应体大小
- 数据库连接池状态（pool_size / checked_out / overflow）
- 缓存命中率与条目数
- /metrics 端点（Prometheus 文本格式）

运行::

    pip install 'litefs[prometheus]'
    python app.py

验证::

    curl http://127.0.0.1:8083/api/items/1
    curl http://127.0.0.1:8083/metrics

注意：/metrics 暴露了内部路径与状态码分布，不要直接暴露到公网。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.core import Litefs
from litefs.handlers import Response
from litefs.routing import get

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 应用配置
# ============================================================================

app = Litefs(
    host='0.0.0.0',
    port=8083,
    debug=True,
    database_url='sqlite:///:memory:',
    # 配置驱动方式启用监控：构造阶段自动挂载 PrometheusMiddleware
    prometheus_enabled=True,
    prometheus_path='/metrics',
    prometheus_namespace='litefs',
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))


# ============================================================================
# 业务路由
# ============================================================================

@get('/', name='index')
def index(request):
    """首页：给出各监控端点的说明"""
    return request.render_template('index.html', **{
        'title': 'Litefs Prometheus 监控示例',
        'endpoints': [
            {'path': '/api/items/{id}', 'desc': '路径参数路由，指标标签为路由模板 /api/items/{id}'},
            {'path': '/api/cache/{key}', 'desc': '缓存读写，产生 cache hit/miss 计数'},
            {'path': '/api/error', 'desc': '返回 500，产生错误计数'},
            {'path': '/metrics', 'desc': 'Prometheus 指标暴露端点'},
        ],
    })


@get('/api/items/{id}', name='api_item')
def api_item(request, id):
    """路径参数路由

    指标中的 path 标签使用**路由模板** `/api/items/{id}`，
    而非原始路径 `/api/items/1`，从而保证标签基数可控。
    """
    return Response.json({
        'id': int(id),
        'name': f'示例条目 {id}',
        'category': ['工具', '文档', '服务'][int(id) % 3],
    })


@get('/api/cache/{key}', name='api_cache')
def api_cache(request, key):
    """缓存读写路由

    首次访问为 miss，第二次起为 hit，
    对应指标 ``litefs_cache_operations_total{result="hit"|"miss"}``。
    """
    cached = app.caches.get(key)
    if cached is None:
        payload = {'key': key, 'value': f'生成于第 {id(key) % 7} 次计算'}
        app.caches.put(key, payload)
        hit = False
    else:
        payload = cached
        hit = True

    return Response.json({'hit': hit, 'data': payload})


@get('/api/error', name='api_error')
def api_error(request):
    """错误路由：返回 500 状态码，用于验证错误计数指标"""
    return Response.json({'error': '内部错误演示'}, status_code=500)


app.register_routes(__name__)


if __name__ == '__main__':
    print('=' * 60)
    print('Litefs Prometheus 监控示例')
    print('=' * 60)
    print()
    print('应用地址: http://localhost:8083')
    print('指标端点: http://localhost:8083/metrics')
    print()
    print('建议操作:')
    print('  1) curl http://localhost:8083/api/items/1')
    print('  2) curl http://localhost:8083/api/cache/demo   # 第一次 miss')
    print('  3) curl http://localhost:8083/api/cache/demo   # 第二次 hit')
    print('  4) curl http://localhost:8083/api/error        # 产生错误计数')
    print('  5) curl http://localhost:8083/metrics          # 查看指标')
    print('=' * 60)

    app.run()
