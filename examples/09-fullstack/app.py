#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
完整的 Litefs Web 应用示例

这个示例展示了如何使用 Litefs 构建一个完整的 Web 应用，包括：
- 路由处理
- 表单处理
- 会话管理
- 缓存使用
- 中间件集成
- 模板渲染
- 静态文件服务
- 健康检查
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import litefs
from litefs import Litefs
from litefs.middleware import (
    LoggingMiddleware,
    SecurityMiddleware,
    CORSMiddleware,
    RateLimitMiddleware,
    HealthCheck
)
from litefs.cache import MemoryCache


class FullStackApp:
    """完整的 Litefs Web 应用类"""
    
    def __init__(self):
        """初始化应用"""
        # 初始化 Litefs 应用
        self.app = Litefs(
            host='0.0.0.0',
            port=8080,
            webroot=os.path.join(os.path.dirname(__file__), 'site'),
            debug=True,
            log=os.path.join(os.path.dirname(__file__), 'app.log'),
            max_request_size=20971520,  # 20MB
            max_upload_size=52428800     # 50MB
        )
        
        # 初始化缓存
        self.cache = MemoryCache(max_size=10000)
        
        # 配置中间件
        self._configure_middleware()
        
        # 配置健康检查
        self._configure_health_checks()
        
    def _configure_middleware(self):
        """配置中间件"""
        # 链式添加中间件
        self.app.add_middleware(LoggingMiddleware)
        self.app.add_middleware(SecurityMiddleware)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=['http://localhost:3000', 'https://example.com'],
            allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
            allow_headers=['Content-Type', 'Authorization'],
            allow_credentials=True,
            max_age=86400
        )
        self.app.add_middleware(
            RateLimitMiddleware,
            max_requests=100,
            window_seconds=60,
            block_duration=120
        )
    
    def _configure_health_checks(self):
        """配置健康检查"""
        # 添加健康检查
        def check_app_health():
            """检查应用健康状态"""
            return True
        
        def check_cache_health():
            """检查缓存健康状态"""
            try:
                self.cache.put('health_check', 'ok')
                value = self.cache.get('health_check')
                return value == 'ok'
            except Exception:
                return False
        
        self.app.add_health_check('app', check_app_health)
        self.app.add_health_check('cache', check_cache_health)
        
        # 添加就绪检查
        def check_app_ready():
            """检查应用是否就绪"""
            return True
        
        self.app.add_ready_check('app', check_app_ready)
    
    def run(self):
        """运行应用"""
        print("=" * 80)
        print("Full Stack Litefs Application")
        print("=" * 80)
        print(f"Version: {litefs.__version__}")
        print(f"Host: {self.app.config.host}")
        print(f"Port: {self.app.config.port}")
        print(f"Webroot: {self.app.config.webroot}")
        print(f"Debug: {self.app.config.debug}")
        print(f"Log: {self.app.config.log}")
        print("=" * 80)
        print("Available endpoints:")
        print("  http://localhost:8080/ - Home page")
        print("  http://localhost:8080/about - About page")
        print("  http://localhost:8080/contact - Contact form")
        print("  http://localhost:8080/dashboard - User dashboard")
        print("  http://localhost:8080/health - Health check")
        print("  http://localhost:8080/health/ready - Readiness check")
        print("=" * 80)
        
        # 运行应用
        self.app.run()
    
    def get_wsgi_application(self):
        """获取 WSGI 应用"""
        return self.app.wsgi()


if __name__ == '__main__':
    # 创建并运行应用
    app = FullStackApp()
    app.run()
