#!/usr/bin/env python
# coding: utf-8

"""
调试中间件

拦截请求和响应，收集调试信息。
"""

import time
from typing import Optional

from litefs.middleware.base import Middleware

from . import DebugToolbar, RequestDebug, get_current_debug, is_debug_enabled


class DebugMiddleware(Middleware):
    """
    调试中间件
    
    在请求处理过程中收集调试信息。
    """
    
    def __init__(self, app=None):
        super().__init__(app)
        self.enabled = is_debug_enabled()
    
    def process_request(self, request_handler):
        """
        处理请求
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            None
        """
        if not self.enabled:
            return None
        
        environ = getattr(request_handler, 'environ', {})
        method = environ.get('REQUEST_METHOD', 'GET')
        path = environ.get('PATH_INFO', '/')
        query_string = environ.get('QUERY_STRING', '')
        
        debug = DebugToolbar.start_request(
            method=method,
            path=path,
            query_string=query_string,
        )
        
        debug.headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').title()
                debug.headers[header_name] = value
        
        request_handler._debug = debug
        
        return None
    
    def process_response(self, request_handler, response):
        """
        处理响应
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            响应数据
        """
        if not self.enabled:
            return response
        
        debug = getattr(request_handler, '_debug', None)
        if not debug:
            return response
        
        if isinstance(response, tuple) and len(response) >= 3:
            status_line, headers, body = response[0], response[1], response[2]
            
            if status_line:
                parts = status_line.split(' ', 1)
                if parts[0].isdigit():
                    debug.response_status = int(parts[0])
            
            if headers:
                for key, value in headers:
                    debug.response_headers[key] = value
            
            if body:
                if isinstance(body, str):
                    debug.response_size = len(body.encode('utf-8'))
                elif isinstance(body, bytes):
                    debug.response_size = len(body)
        else:
            if hasattr(request_handler, '_status_code'):
                debug.response_status = request_handler._status_code
            
            if hasattr(request_handler, '_response_headers'):
                for key, value in request_handler._response_headers.items():
                    debug.response_headers[key] = value
            
            if response:
                if isinstance(response, str):
                    debug.response_size = len(response.encode('utf-8'))
                elif isinstance(response, bytes):
                    debug.response_size = len(response)
                elif isinstance(response, (dict, list, tuple)):
                    import json
                    debug.response_size = len(json.dumps(response, ensure_ascii=False).encode('utf-8'))
        
        debug.handler_time = (time.time() - debug.start_time) * 1000 - debug.routing_time - debug.db_time
        
        DebugToolbar.end_request(debug)
        
        return response
    
    def process_exception(self, request_handler, exception):
        """
        处理异常
        
        Args:
            request_handler: 请求处理器实例
            exception: 异常对象
            
        Returns:
            None
        """
        if not self.enabled:
            return None
        
        debug = getattr(request_handler, '_debug', None)
        if debug:
            debug.add_error(exception, context='Request handler')
        
        return None


def track_sql(sql: str, params: tuple = ()):
    """
    追踪 SQL 查询
    
    Args:
        sql: SQL 语句
        params: 参数
        
    Returns:
        上下文管理器
    """
    class SQLTracker:
        def __init__(self, sql, params):
            self.sql = sql
            self.params = params
            self.start_time = 0
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            duration = (time.time() - self.start_time) * 1000
            debug = get_current_debug()
            if debug:
                debug.add_sql_query(self.sql, self.params, duration)
    
    return SQLTracker(sql, params)


def track_performance(name: str):
    """
    追踪性能
    
    Args:
        name: 性能指标名称
        
    Returns:
        上下文管理器
    """
    class PerformanceTracker:
        def __init__(self, name):
            self.name = name
            self.start_time = 0
        
        def __enter__(self):
            self.start_time = time.time()
            return self
        
        def __exit__(self, *args):
            duration = (time.time() - self.start_time) * 1000
            debug = get_current_debug()
            if debug:
                if self.name == 'routing':
                    debug.routing_time += duration
                elif self.name == 'template':
                    debug.template_time += duration
    
    return PerformanceTracker(name)
