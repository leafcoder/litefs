#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs
from litefs.middleware import (
    LoggingMiddleware,
    CORSMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
)


def basic_middleware_example():
    """
    基础中间件使用示例
    """
    print('=== 基础中间件使用示例 ===')
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    
    print('已添加日志中间件和安全中间件')
    print('中间件列表:', [m.__name__ for m in app.middleware_manager._middlewares])


def cors_middleware_example():
    """
    CORS 中间件使用示例
    """
    print('\n=== CORS 中间件使用示例 ===')
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000', 'https://example.com'],
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['Content-Type', 'Authorization'],
        allow_credentials=True,
        max_age=86400,
    )
    
    middleware_instances = app._get_middleware_instances()
    cors_middleware = middleware_instances[0]
    
    print('已添加 CORS 中间件')
    print('允许的来源:', cors_middleware.allow_origins)
    print('允许的方法:', cors_middleware.allow_methods)


def rate_limit_middleware_example():
    """
    限流中间件使用示例
    """
    print('\n=== 限流中间件使用示例 ===')
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=10,
        window_seconds=60,
        block_duration=120,
    )
    
    middleware_instances = app._get_middleware_instances()
    rate_limit_middleware = middleware_instances[0]
    
    print('已添加限流中间件')
    print('最大请求数:', rate_limit_middleware.max_requests)
    print('时间窗口:', rate_limit_middleware.window_seconds, '秒')
    print('封禁时长:', rate_limit_middleware.block_duration, '秒')


def custom_middleware_example():
    """
    自定义中间件使用示例
    """
    print('\n=== 自定义中间件使用示例 ===')
    
    from litefs.middleware import Middleware
    
    class CustomTimingMiddleware(Middleware):
        """
        自定义计时中间件
        """
        
        def process_request(self, request_handler):
            import time
            request_handler._custom_start_time = time.time()
        
        def process_response(self, request_handler, response):
            if hasattr(request_handler, '_custom_start_time'):
                duration = time.time() - request_handler._custom_start_time
                print(f'请求处理耗时: {duration:.3f}秒')
            return response
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(CustomTimingMiddleware)
    
    print('已添加自定义计时中间件')


def chain_middleware_example():
    """
    链式添加中间件示例
    """
    print('\n=== 链式添加中间件示例 ===')
    
    app = (
        Litefs(webroot='./examples/basic/site')
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
        .add_middleware(RateLimitMiddleware)
    )
    
    print('已使用链式调用添加多个中间件')
    print('中间件数量:', len(app.middleware_manager._middlewares))


def remove_middleware_example():
    """
    移除中间件示例
    """
    print('\n=== 移除中间件示例 ===')
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    
    print('添加中间件后的数量:', len(app.middleware_manager._middlewares))
    
    app.remove_middleware(LoggingMiddleware)
    
    print('移除日志中间件后的数量:', len(app.middleware_manager._middlewares))


def clear_middleware_example():
    """
    清空中间件示例
    """
    print('\n=== 清空中间件示例 ===')
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(CORSMiddleware)
    
    print('添加中间件后的数量:', len(app.middleware_manager._middlewares))
    
    app.clear_middleware()
    
    print('清空中间件后的数量:', len(app.middleware_manager._middlewares))


def wsgi_middleware_example():
    """
    WSGI 模式下使用中间件示例
    """
    print('\n=== WSGI 模式下使用中间件示例 ===')
    
    app = Litefs(webroot='./examples/basic/site')
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(CORSMiddleware)
    
    application = app.wsgi()
    
    print('已创建 WSGI 应用，中间件已集成')
    print('可以在 gunicorn 或 uWSGI 中使用此应用')
    print('示例命令:')
    print('  gunicorn -w 4 -b :8000 wsgi_middleware_example:application')
    print('  uwsgi --http :8000 --wsgi-file wsgi_middleware_example.py')


if __name__ == '__main__':
    basic_middleware_example()
    cors_middleware_example()
    rate_limit_middleware_example()
    custom_middleware_example()
    chain_middleware_example()
    remove_middleware_example()
    clear_middleware_example()
    wsgi_middleware_example()
    
    print('\n=== 所有示例运行完成 ===')
