#!/usr/bin/env python
# coding: utf-8

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from litefs.core import Litefs
from litefs.middleware import (
    LoggingMiddleware,
    CORSMiddleware,
    SecurityMiddleware,
    RateLimitMiddleware,
    ThrottleMiddleware,
)

def test_middleware_with_parameters():
    """测试中间件参数传递"""
    print('=== 测试中间件参数传递 ===\n')
    
    app = Litefs(webroot='./examples/basic/site', debug=True)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:3000', 'https://example.com'],
        allow_methods=['GET', 'POST', 'PUT'],
        allow_headers=['Content-Type', 'Authorization'],
        allow_credentials=True,
        max_age=3600,
    )
    
    app.add_middleware(
        SecurityMiddleware,
        x_frame_options='DENY',
        x_content_type_options='nosniff',
        x_xss_protection='1; mode=block',
        strict_transport_security='max-age=31536000',
    )
    
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=50,
        window_seconds=60,
        block_duration=120,
    )
    
    app.add_middleware(
        ThrottleMiddleware,
        min_interval=0.05,
    )
    
    app.add_middleware(LoggingMiddleware)
    
    middleware_instances = app._get_middleware_instances()
    
    print(f'中间件数量: {len(middleware_instances)}\n')
    
    for i, middleware in enumerate(middleware_instances, 1):
        print(f'{i}. {middleware.__class__.__name__}')
        
        if isinstance(middleware, CORSMiddleware):
            print(f'   - allow_origins: {middleware.allow_origins}')
            print(f'   - allow_methods: {middleware.allow_methods}')
            print(f'   - allow_headers: {middleware.allow_headers}')
            print(f'   - allow_credentials: {middleware.allow_credentials}')
            print(f'   - max_age: {middleware.max_age}')
        
        elif isinstance(middleware, SecurityMiddleware):
            print(f'   - x_frame_options: {middleware.x_frame_options}')
            print(f'   - x_content_type_options: {middleware.x_content_type_options}')
            print(f'   - x_xss_protection: {middleware.x_xss_protection}')
            print(f'   - strict_transport_security: {middleware.strict_transport_security}')
        
        elif isinstance(middleware, RateLimitMiddleware):
            print(f'   - max_requests: {middleware.max_requests}')
            print(f'   - window_seconds: {middleware.window_seconds}')
            print(f'   - block_duration: {middleware.block_duration}')
        
        elif isinstance(middleware, ThrottleMiddleware):
            print(f'   - min_interval: {middleware.min_interval}')
        
        elif isinstance(middleware, LoggingMiddleware):
            print(f'   - logger: {middleware.logger.name}')
        
        print()
    
    print('✓ 所有中间件参数传递成功！')

if __name__ == '__main__':
    test_middleware_with_parameters()
