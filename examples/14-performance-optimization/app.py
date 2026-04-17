#!/usr/bin/env python
# coding: utf-8

"""
性能优化功能综合示例

展示 Litefs 框架的性能优化功能：
- 优化的静态文件服务
- 请求性能监控
- 增强的缓存装饰器
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, post
from litefs.middleware.performance import (
    PerformanceMonitoringMiddleware,
    monitor_performance
)
from litefs.cache_decorators import (
    cached,
    cache_response,
    cache_method,
    cache_property,
    get_cache_stats,
    clear_all_cache
)


app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

# 添加性能监控中间件
app.add_middleware(PerformanceMonitoringMiddleware, slow_request_threshold=0.5)


@route('/', name='index')
def index(request):
    """
    首页 - 展示功能列表
    """
    return {
        'message': 'Litefs 性能优化功能示例',
        'features': {
            'static_files': {
                'description': '优化的静态文件服务',
                'features': [
                    '文件缓存',
                    'Gzip 压缩',
                    'ETag 支持',
                    'Last-Modified',
                    'Range 请求',
                    'MIME 类型识别'
                ]
            },
            'performance_monitoring': {
                'description': '请求性能监控',
                'endpoints': {
                    '/monitor/stats': '性能统计信息',
                    '/monitor/slow': '慢请求列表',
                    '/monitor/recent': '最近请求记录'
                }
            },
            'cache_decorators': {
                'description': '增强的缓存装饰器',
                'endpoints': {
                    '/cache/function': '函数缓存示例',
                    '/cache/response': '响应缓存示例',
                    '/cache/method': '方法缓存示例',
                    '/cache/stats': '缓存统计信息',
                    '/cache/clear': '清空缓存'
                }
            }
        }
    }


# ==================== 性能监控示例 ====================

@route('/monitor/stats', name='monitor_stats')
def monitor_stats(request):
    """性能统计信息"""
    monitor = app.get_middleware(PerformanceMonitoringMiddleware).get_monitor()
    stats = monitor.get_stats()
    
    return {
        'message': '性能统计信息',
        'stats': stats,
        'total_endpoints': len(stats)
    }


@route('/monitor/slow', name='monitor_slow')
def monitor_slow(request):
    """慢请求列表"""
    monitor = app.get_middleware(PerformanceMonitoringMiddleware).get_monitor()
    slow_requests = monitor.get_slow_requests(threshold=0.1, limit=10)
    
    return {
        'message': '慢请求列表',
        'slow_requests': slow_requests,
        'count': len(slow_requests)
    }


@route('/monitor/recent', name='monitor_recent')
def monitor_recent(request):
    """最近请求记录"""
    monitor = app.get_middleware(PerformanceMonitoringMiddleware).get_monitor()
    recent_requests = monitor.get_recent_requests(limit=20)
    
    return {
        'message': '最近请求记录',
        'recent_requests': recent_requests,
        'count': len(recent_requests)
    }


# ==================== 缓存装饰器示例 ====================

@route('/cache/function', name='cache_function')
@cached(ttl=10, key_prefix='expensive')
@monitor_performance(threshold=0.1)
def cache_function_example(request):
    """
    函数缓存示例
    
    这个函数的结果会被缓存 10 秒
    """
    # 模拟耗时操作
    time.sleep(0.2)
    
    return {
        'message': '函数缓存示例',
        'result': '这是一个耗时的计算结果',
        'timestamp': time.time(),
        'note': '结果会被缓存 10 秒，在此期间重复访问会直接返回缓存结果'
    }


@route('/cache/response', name='cache_response')
@cache_response(ttl=15, vary_on=['Accept-Encoding'])
def cache_response_example(request):
    """
    响应缓存示例
    
    这个响应会被缓存 15 秒
    """
    # 模拟耗时操作
    time.sleep(0.3)
    
    return {
        'message': '响应缓存示例',
        'result': '这是一个耗时的 API 响应',
        'timestamp': time.time(),
        'note': '响应会被缓存 15 秒'
    }


# 方法缓存示例
class DataService:
    """数据服务类"""
    
    def __init__(self):
        self.call_count = 0
    
    @cache_method(ttl=20)
    def get_data(self, data_id):
        """
        获取数据（带缓存）
        
        Args:
            data_id: 数据 ID
            
        Returns:
            数据字典
        """
        # 模拟耗时操作
        time.sleep(0.15)
        self.call_count += 1
        
        return {
            'id': data_id,
            'value': f'Data value for {data_id}',
            'call_count': self.call_count,
            'timestamp': time.time()
        }


# 创建数据服务实例
data_service = DataService()


@route('/cache/method', name='cache_method')
def cache_method_example(request):
    """
    方法缓存示例
    
    演示类方法的缓存
    """
    data_id = request.GET.get('id', 'default')
    data = data_service.get_data(data_id)
    
    return {
        'message': '方法缓存示例',
        'data': data,
        'note': '方法结果会被缓存 20 秒'
    }


@route('/cache/stats', name='cache_stats')
def cache_stats(request):
    """缓存统计信息"""
    stats = get_cache_stats()
    
    return {
        'message': '缓存统计信息',
        'stats': stats
    }


@route('/cache/clear', name='cache_clear')
def cache_clear(request):
    """清空缓存"""
    clear_all_cache()
    
    return {
        'message': '缓存已清空',
        'timestamp': time.time()
    }


# ==================== 性能测试端点 ====================

@route('/test/slow', name='test_slow')
@monitor_performance(threshold=0.1)
def test_slow(request):
    """
    慢请求测试端点
    
    这个端点会故意延迟，用于测试性能监控
    """
    delay = float(request.GET.get('delay', '1.0'))
    time.sleep(delay)
    
    return {
        'message': '慢请求测试',
        'delay': delay,
        'timestamp': time.time()
    }


@route('/test/fast', name='test_fast')
def test_fast(request):
    """快速请求测试端点"""
    return {
        'message': '快速请求测试',
        'timestamp': time.time()
    }


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 性能优化功能综合示例")
    print("=" * 60)
    print()
    print("功能特性：")
    print("  ✓ 优化的静态文件服务 - 缓存、压缩、ETag")
    print("  ✓ 请求性能监控 - 自动监控、慢请求告警")
    print("  ✓ 增强的缓存装饰器 - 函数、响应、方法缓存")
    print()
    print("示例端点：")
    print("  http://localhost:8080/                    - 首页")
    print()
    print("  性能监控：")
    print("  http://localhost:8080/monitor/stats       - 性能统计")
    print("  http://localhost:8080/monitor/slow        - 慢请求列表")
    print("  http://localhost:8080/monitor/recent      - 最近请求")
    print()
    print("  缓存装饰器：")
    print("  http://localhost:8080/cache/function      - 函数缓存")
    print("  http://localhost:8080/cache/response      - 响应缓存")
    print("  http://localhost:8080/cache/method        - 方法缓存")
    print("  http://localhost:8080/cache/stats         - 缓存统计")
    print("  http://localhost:8080/cache/clear         - 清空缓存")
    print()
    print("  性能测试：")
    print("  http://localhost:8080/test/slow?delay=0.5 - 慢请求测试")
    print("  http://localhost:8080/test/fast           - 快速请求测试")
    print()
    print("测试建议：")
    print("  1. 多次访问 /cache/function 观察缓存效果")
    print("  2. 访问 /test/slow?delay=2 触发慢请求告警")
    print("  3. 查看 /monitor/stats 了解性能统计")
    print("  4. 使用 /cache/clear 清空缓存重新测试")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
