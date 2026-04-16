#!/usr/bin/env python
# coding: utf-8

"""
增强日志中间件示例

本示例展示如何使用 EnhancedLoggingMiddleware 提供的高级日志功能：
- 请求追踪（Request ID）
- 结构化日志输出
- 性能监控
- 敏感信息过滤
- 智能日志级别
"""

import logging
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, post
from litefs.middleware import EnhancedLoggingMiddleware, log_performance


def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger('enhanced-logging-example')


app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

logger = setup_logging()

app.add_middleware(EnhancedLoggingMiddleware, 
    logger=logger,
    structured=False,
    log_request_body=True,
    log_response_body=False,
    exclude_paths=['/health', '/static/*'],
    sensitive_params=['password', 'token', 'secret']
)


@route('/', name='index')
def index(request):
    """
    首页 - 演示基本日志功能
    """
    logger.info("访问首页")
    
    return {
        'message': '欢迎使用增强日志中间件示例',
        'features': [
            '请求追踪（Request ID）',
            '结构化日志输出',
            '性能监控',
            '敏感信息过滤',
            '智能日志级别'
        ],
        'endpoints': {
            '/': '首页',
            '/login': '登录示例（演示敏感信息过滤）',
            '/slow': '慢请求示例（演示性能监控）',
            '/error': '错误示例（演示错误日志）',
            '/health': '健康检查（不记录日志）',
            '/structured': '结构化日志示例'
        }
    }


@post('/login', name='login')
def login(request):
    """
    登录示例 - 演示敏感信息过滤
    
    注意：password 参数会被自动过滤为 ***FILTERED***
    """
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    logger.info(f"用户登录尝试: {username}")
    
    if username == 'admin' and password == 'secret':
        logger.info(f"用户登录成功: {username}")
        return {
            'status': 'success',
            'message': '登录成功',
            'user': username
        }
    else:
        logger.warning(f"用户登录失败: {username}")
        return {
            'status': 'error',
            'message': '用户名或密码错误'
        }, 401


@route('/slow', name='slow_request')
@log_performance
def slow_request(request):
    """
    慢请求示例 - 演示性能监控
    
    使用 @log_performance 装饰器记录函数执行时间
    """
    logger.info("开始处理慢请求")
    
    time.sleep(2)
    
    logger.info("慢请求处理完成")
    
    return {
        'message': '这是一个慢请求',
        'duration': '2秒'
    }


@route('/error', name='error_example')
def error_example(request):
    """
    错误示例 - 演示错误日志
    
    这个端点会抛出异常，触发错误日志记录
    """
    logger.info("即将抛出异常")
    
    raise ValueError("这是一个测试异常")


@route('/health', name='health_check')
def health_check(request):
    """
    健康检查 - 不记录日志
    
    这个端点被配置在 exclude_paths 中，不会记录日志
    """
    return {
        'status': 'healthy',
        'timestamp': time.time()
    }


@route('/structured', name='structured_logging')
def structured_logging(request):
    """
    结构化日志示例
    
    演示如何使用结构化日志输出（JSON 格式）
    """
    app_with_structured = Litefs(
        host='0.0.0.0',
        port=8081,
        debug=True
    )
    
    structured_logger = logging.getLogger('structured-logging')
    structured_logger.setLevel(logging.INFO)
    
    app_with_structured.add_middleware(EnhancedLoggingMiddleware,
        logger=structured_logger,
        structured=True,
        log_request_body=True,
        log_response_body=False
    )
    
    return {
        'message': '结构化日志示例',
        'note': '要查看结构化日志输出，请访问 http://localhost:8081',
        'format': 'JSON 格式的日志输出，便于日志分析和处理'
    }


@route('/context', name='context_logging')
def context_logging(request):
    """
    上下文日志示例
    
    演示如何使用 RequestContextLogger 记录带请求 ID 的日志
    """
    from litefs.middleware import RequestContextLogger
    
    ctx_logger = RequestContextLogger(request)
    
    ctx_logger.info("这是上下文日志消息")
    ctx_logger.debug("调试信息")
    ctx_logger.warning("警告信息")
    
    return {
        'message': '上下文日志示例',
        'request_id': request.request_id,
        'note': '查看日志输出，所有消息都包含相同的 request_id'
    }


@route('/params', name='params_example')
def params_example(request):
    """
    参数日志示例
    
    演示如何记录 GET 和 POST 参数
    """
    get_params = request.GET or {}
    post_params = request.POST or {}
    
    logger.info(f"GET 参数: {dict(get_params)}")
    logger.info(f"POST 参数: {dict(post_params)}")
    
    return {
        'message': '参数日志示例',
        'get_params': dict(get_params),
        'post_params': dict(post_params),
        'note': '访问此端点时添加查询参数，例如: /params?name=test&value=123'
    }


if __name__ == '__main__':
    print("=" * 60)
    print("增强日志中间件示例")
    print("=" * 60)
    print()
    print("功能特性：")
    print("  ✓ 请求追踪 - 每个请求都有唯一的 Request ID")
    print("  ✓ 结构化日志 - 支持 JSON 格式输出")
    print("  ✓ 性能监控 - 记录请求处理时间")
    print("  ✓ 敏感信息过滤 - 自动过滤密码等敏感参数")
    print("  ✓ 智能日志级别 - 根据状态码自动调整日志级别")
    print()
    print("示例端点：")
    print("  http://localhost:8080/              - 首页")
    print("  http://localhost:8080/login         - 登录示例（POST）")
    print("  http://localhost:8080/slow          - 慢请求示例")
    print("  http://localhost:8080/error         - 错误示例")
    print("  http://localhost:8080/health        - 健康检查（不记录日志）")
    print("  http://localhost:8080/structured    - 结构化日志示例")
    print("  http://localhost:8080/context       - 上下文日志示例")
    print("  http://localhost:8080/params        - 参数日志示例")
    print()
    print("测试命令：")
    print("  curl http://localhost:8080/")
    print("  curl -X POST -d 'username=admin&password=secret' http://localhost:8080/login")
    print("  curl http://localhost:8080/slow")
    print("  curl http://localhost:8080/error")
    print("  curl 'http://localhost:8080/params?name=test&value=123'")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
