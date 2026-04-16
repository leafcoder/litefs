#!/usr/bin/env python
# coding: utf-8

import json
import time
import sys
import os
from typing import Any, Dict, List, Optional, Callable

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from middleware.base import Middleware
from exceptions import HttpError


class HealthCheck(Middleware):
    """
    健康检查中间件

    提供 /health 和 /health/ready 端点用于健康检查
    """

    def __init__(self, app, path: str = '/health', ready_path: str = '/health/ready'):
        """
        初始化健康检查中间件

        Args:
            app: Litefs 应用实例
            path: 健康检查端点路径，默认为 /health
            ready_path: 就绪检查端点路径，默认为 /health/ready
        """
        super().__init__(app)
        self.path = path
        self.ready_path = ready_path
        self._checks: Dict[str, Callable] = {}
        self._ready_checks: Dict[str, Callable] = {}

    def add_check(self, name: str, check_func: Callable[[], bool]):
        """
        添加健康检查

        Args:
            name: 检查名称
            check_func: 检查函数，返回 True 表示健康，False 表示不健康
        """
        self._checks[name] = check_func

    def add_ready_check(self, name: str, check_func: Callable[[], bool]):
        """
        添加就绪检查

        Args:
            name: 检查名称
            check_func: 检查函数，返回 True 表示就绪，False 表示未就绪
        """
        self._ready_checks[name] = check_func

    def process_request(self, request_handler):
        """
        处理请求，检查是否为健康检查端点

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应
        """
        path = request_handler._environ.get('PATH_INFO', '')
        method = request_handler._environ.get('REQUEST_METHOD', 'GET')

        if method == 'GET':
            if path == self.path:
                return self._handle_health_check(request_handler)
            elif path == self.ready_path:
                return self._handle_ready_check(request_handler)

        return None

    def _handle_health_check(self, request_handler):
        """
        处理健康检查请求

        Args:
            request_handler: 请求处理器实例

        Returns:
            健康检查响应
        """
        from ..handlers.request import Response
        
        status_code = 200
        checks = {}

        for name, check_func in self._checks.items():
            try:
                is_healthy = check_func()
                checks[name] = {
                    'status': 'pass' if is_healthy else 'fail',
                    'timestamp': time.time()
                }
                if not is_healthy:
                    status_code = 503
            except Exception as e:
                checks[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                }
                status_code = 503

        response_data = {
            'status': 'healthy' if status_code == 200 else 'unhealthy',
            'timestamp': time.time(),
            'checks': checks
        }

        return Response.json(response_data, status_code=status_code)

    def _handle_ready_check(self, request_handler):
        """
        处理就绪检查请求

        Args:
            request_handler: 请求处理器实例

        Returns:
            就绪检查响应
        """
        from ..handlers.request import Response
        
        status_code = 200
        checks = {}

        for name, check_func in self._ready_checks.items():
            try:
                is_ready = check_func()
                checks[name] = {
                    'status': 'pass' if is_ready else 'fail',
                    'timestamp': time.time()
                }
                if not is_ready:
                    status_code = 503
            except Exception as e:
                checks[name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': time.time()
                }
                status_code = 503

        response_data = {
            'status': 'ready' if status_code == 200 else 'not_ready',
            'timestamp': time.time(),
            'checks': checks
        }

        return Response.json(response_data, status_code=status_code)
