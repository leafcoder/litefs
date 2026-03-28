#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.middleware import (
    CORSMiddleware,
    LoggingMiddleware,
    SecurityMiddleware,
    HealthCheck,
)


def check_database():
    """检查数据库连接"""
    return True


def check_cache():
    """检查缓存服务"""
    return True


def check_disk_space():
    """检查磁盘空间"""
    import shutil
    total, used, free = shutil.disk_usage('.')
    return free > 1024 * 1024 * 1024


def check_external_api():
    """检查外部 API"""
    return True


def check_migrations():
    """检查数据库迁移"""
    return True


def main():
    """启动服务器"""
    app = Litefs(webroot='./examples/01-quickstart/site', debug=True)
    
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(CORSMiddleware)
    app.add_middleware(HealthCheck, path='/health', ready_path='/health/ready')
    
    app.add_health_check('database', check_database)
    app.add_health_check('cache', check_cache)
    app.add_health_check('disk_space', check_disk_space)
    app.add_health_check('external_api', check_external_api)
    
    app.add_ready_check('migrations', check_migrations)
    
    print("Starting Litefs server with health checks...")
    print("Health check endpoint: http://localhost:9090/health")
    print("Ready check endpoint: http://localhost:9090/health/ready")
    
    app.run()


if __name__ == '__main__':
    main()
