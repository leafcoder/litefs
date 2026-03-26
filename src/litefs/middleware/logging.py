#!/usr/bin/env python
# coding: utf-8

import logging
import time
from typing import Optional

from .base import Middleware


class LoggingMiddleware(Middleware):
    """
    日志中间件
    
    记录所有请求和响应的详细信息，包括请求时间、响应时间、状态码等
    """

    def __init__(self, app, logger: Optional[logging.Logger] = None):
        """
        初始化日志中间件
        
        Args:
            app: Litefs 应用实例
            logger: 日志记录器，如果为 None 则使用默认日志记录器
        """
        super(LoggingMiddleware, self).__init__(app)
        self.logger = logger or logging.getLogger(__name__)

    def process_request(self, request_handler):
        """
        处理请求，记录请求开始时间
        
        Args:
            request_handler: 请求处理器实例
        """
        request_handler._start_time = time.time()
        self.logger.info(
            '%s - %s %s %s - Started',
            request_handler.environ.get('REMOTE_ADDR', '-'),
            request_handler.environ.get('REQUEST_METHOD', 'GET'),
            request_handler.environ.get('PATH_INFO', '/'),
            request_handler.environ.get('SERVER_PROTOCOL', 'HTTP/1.1')
        )

    def process_response(self, request_handler, response):
        """
        处理响应，记录请求处理时间
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            响应数据
        """
        if hasattr(request_handler, '_start_time'):
            duration = time.time() - request_handler._start_time
            
            if isinstance(response, tuple) and len(response) == 3:
                status, headers, content = response
                status_code = status.split()[0] if isinstance(status, str) else status
            else:
                status_code = 200
            
            self.logger.info(
                '%s - %s %s %s - %s - %.3fs',
                request_handler.environ.get('REMOTE_ADDR', '-'),
                request_handler.environ.get('REQUEST_METHOD', 'GET'),
                request_handler.environ.get('PATH_INFO', '/'),
                request_handler.environ.get('SERVER_PROTOCOL', 'HTTP/1.1'),
                status_code,
                duration
            )
        
        return response

    def process_exception(self, request_handler, exception):
        """
        处理异常，记录异常信息
        
        Args:
            request_handler: 请求处理器实例
            exception: 异常对象
            
        Returns:
            None: 继续抛出异常
        """
        self.logger.error(
            '%s - %s %s %s - Exception: %s',
            request_handler.environ.get('REMOTE_ADDR', '-'),
            request_handler.environ.get('REQUEST_METHOD', 'GET'),
            request_handler.environ.get('PATH_INFO', '/'),
            request_handler.environ.get('SERVER_PROTOCOL', 'HTTP/1.1'),
            str(exception),
            exc_info=True
        )
        return None
