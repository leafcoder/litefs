#!/usr/bin/env python
# coding: utf-8

"""
增强的日志中间件

提供请求追踪、结构化日志、性能监控等功能
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from functools import wraps

from .base import Middleware


class EnhancedLoggingMiddleware(Middleware):
    """
    增强的日志中间件
    
    功能特性：
    - 请求追踪：为每个请求生成唯一 ID
    - 结构化日志：支持 JSON 格式输出
    - 性能监控：记录详细的性能指标
    - 敏感信息过滤：自动过滤敏感参数
    - 智能日志级别：根据响应状态码自动调整
    """
    
    # 敏感参数名称列表
    SENSITIVE_PARAMS = [
        'password', 'passwd', 'pwd',
        'token', 'access_token', 'refresh_token',
        'secret', 'api_key', 'apikey',
        'credit_card', 'card_number',
        'ssn', 'social_security_number'
    ]
    
    def __init__(
        self, 
        app, 
        logger: Optional[logging.Logger] = None,
        structured: bool = False,
        sensitive_params: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_length: int = 1000
    ):
        """
        初始化增强的日志中间件
        
        Args:
            app: Litefs 应用实例
            logger: 日志记录器，如果为 None 则使用应用的日志记录器
            structured: 是否使用结构化日志（JSON 格式）
            sensitive_params: 自定义敏感参数列表
            exclude_paths: 不记录日志的路径列表（支持通配符）
            log_request_body: 是否记录请求体
            log_response_body: 是否记录响应体
            max_body_length: 记录的最大请求/响应体长度
        """
        super(EnhancedLoggingMiddleware, self).__init__(app)
        
        if logger is None:
            self.logger = getattr(app, "logger", logging.getLogger(__name__))
        else:
            self.logger = logger
        
        self.structured = structured
        self.sensitive_params = self.SENSITIVE_PARAMS + (sensitive_params or [])
        self.exclude_paths = exclude_paths or []
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_length = max_body_length
    
    def _should_skip_logging(self, path: str) -> bool:
        """
        检查是否应该跳过日志记录
        
        Args:
            path: 请求路径
            
        Returns:
            是否跳过
        """
        import fnmatch
        
        for pattern in self.exclude_paths:
            if fnmatch.fnmatch(path, pattern):
                return True
        
        return False
    
    def _generate_request_id(self) -> str:
        """
        生成请求 ID
        
        Returns:
            请求 ID 字符串
        """
        return str(uuid.uuid4())
    
    def _filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤敏感数据
        
        Args:
            data: 原始数据字典
            
        Returns:
            过滤后的数据字典
        """
        if not isinstance(data, dict):
            return data
        
        filtered = {}
        for key, value in data.items():
            if key.lower() in [param.lower() for param in self.sensitive_params]:
                filtered[key] = '***FILTERED***'
            elif isinstance(value, dict):
                filtered[key] = self._filter_sensitive_data(value)
            else:
                filtered[key] = value
        
        return filtered
    
    def _truncate_body(self, body: Any, max_length: int = None) -> str:
        """
        截断请求/响应体
        
        Args:
            body: 请求/响应体
            max_length: 最大长度
            
        Returns:
            截断后的字符串
        """
        if max_length is None:
            max_length = self.max_body_length
        
        if body is None:
            return ''
        
        if isinstance(body, bytes):
            try:
                body = body.decode('utf-8')
            except UnicodeDecodeError:
                return f'<binary data: {len(body)} bytes>'
        
        body_str = str(body)
        
        if len(body_str) > max_length:
            return body_str[:max_length] + '... (truncated)'
        
        return body_str
    
    def _get_log_level(self, status_code: int) -> int:
        """
        根据状态码获取日志级别
        
        Args:
            status_code: HTTP 状态码
            
        Returns:
            日志级别
        """
        if status_code >= 500:
            return logging.ERROR
        elif status_code >= 400:
            return logging.WARNING
        else:
            return logging.INFO
    
    def _format_log_message(self, data: Dict[str, Any], level: int) -> str:
        """
        格式化日志消息
        
        Args:
            data: 日志数据
            level: 日志级别
            
        Returns:
            格式化后的日志消息
        """
        if self.structured:
            return json.dumps(data, ensure_ascii=False, default=str)
        else:
            # 传统格式
            request_id = data.get('request_id', '-')
            method = data.get('method', 'GET')
            path = data.get('path', '/')
            status_code = data.get('status_code', 200)
            duration = data.get('duration', 0)
            remote_addr = data.get('remote_addr', '-')
            
            if 'error' in data:
                return f"[{request_id}] {remote_addr} - {method} {path} - {status_code} - {duration:.3f}s - ERROR: {data['error']}"
            else:
                return f"[{request_id}] {remote_addr} - {method} {path} - {status_code} - {duration:.3f}s"
    
    def process_request(self, request_handler):
        """
        处理请求，记录请求开始信息
        
        Args:
            request_handler: 请求处理器实例
        """
        # 检查是否跳过日志记录
        path = request_handler.environ.get("PATH_INFO", "/")
        if self._should_skip_logging(path):
            return None
        
        # 生成请求 ID
        request_id = self._generate_request_id()
        request_handler.request_id = request_id
        request_handler._start_time = time.time()
        
        # 收集请求信息
        request_data = {
            'request_id': request_id,
            'timestamp': datetime.now().isoformat(),
            'method': request_handler.environ.get("REQUEST_METHOD", "GET"),
            'path': path,
            'query_string': request_handler.environ.get("QUERY_STRING", ""),
            'remote_addr': request_handler.environ.get("REMOTE_ADDR", "-"),
            'user_agent': request_handler.environ.get("HTTP_USER_AGENT", "-"),
            'referer': request_handler.environ.get("HTTP_REFERER", "-"),
            'content_type': request_handler.environ.get("CONTENT_TYPE", ""),
            'content_length': request_handler.environ.get("CONTENT_LENGTH", "0"),
            'server_protocol': request_handler.environ.get("SERVER_PROTOCOL", "HTTP/1.1"),
            'pid': os.getpid()
        }
        
        # 记录请求参数（GET 和 POST）
        if hasattr(request_handler, 'get') and request_handler.get:
            request_data['get_params'] = self._filter_sensitive_data(dict(request_handler.get))
        
        if hasattr(request_handler, 'post') and request_handler.post:
            request_data['post_params'] = self._filter_sensitive_data(dict(request_handler.post))
        
        # 记录请求体
        if self.log_request_body and hasattr(request_handler, 'body') and request_handler.body:
            request_data['request_body'] = self._truncate_body(request_handler.body)
        
        # 记录请求开始
        log_message = self._format_log_message(request_data, logging.INFO)
        self.logger.info(f"Request started: {log_message}")
        
        # 保存请求数据，供后续使用
        request_handler._log_data = request_data
        
        return None
    
    def process_response(self, request_handler, response):
        """
        处理响应，记录请求处理结果
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            响应数据
        """
        # 检查是否跳过日志记录
        path = request_handler.environ.get("PATH_INFO", "/")
        if self._should_skip_logging(path):
            return response
        
        # 计算请求处理时间
        duration = 0
        if hasattr(request_handler, '_start_time'):
            duration = time.time() - request_handler._start_time
        
        # 解析响应状态码
        status_code = 200
        if isinstance(response, tuple) and len(response) == 3:
            status, headers, content = response
            status_code = int(status.split()[0]) if isinstance(status, str) else status
        elif isinstance(response, dict):
            status_code = response.get('status_code', 200)
        
        # 构建响应数据
        response_data = {
            'request_id': getattr(request_handler, 'request_id', '-'),
            'timestamp': datetime.now().isoformat(),
            'method': request_handler.environ.get("REQUEST_METHOD", "GET"),
            'path': path,
            'status_code': status_code,
            'duration': round(duration, 3),
            'remote_addr': request_handler.environ.get("REMOTE_ADDR", "-"),
            'pid': os.getpid()
        }
        
        # 记录响应体
        if self.log_response_body and isinstance(response, tuple) and len(response) == 3:
            _, _, content = response
            response_data['response_body'] = self._truncate_body(content)
        
        # 根据状态码确定日志级别
        log_level = self._get_log_level(status_code)
        
        # 记录响应
        log_message = self._format_log_message(response_data, log_level)
        self.logger.log(log_level, f"Request completed: {log_message}")
        
        # 添加性能响应头
        if isinstance(response, tuple) and len(response) == 3:
            status, headers, content = response
            headers = list(headers)
            headers.append(('X-Request-ID', str(response_data['request_id'])))
            headers.append(('X-Response-Time', f'{duration:.3f}s'))
            return status, headers, content
        
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
        # 计算请求处理时间
        duration = 0
        if hasattr(request_handler, '_start_time'):
            duration = time.time() - request_handler._start_time
        
        # 构建错误数据
        error_data = {
            'request_id': getattr(request_handler, 'request_id', '-'),
            'timestamp': datetime.now().isoformat(),
            'method': request_handler.environ.get("REQUEST_METHOD", "GET"),
            'path': request_handler.environ.get("PATH_INFO", "/"),
            'status_code': 500,
            'duration': round(duration, 3),
            'remote_addr': request_handler.environ.get("REMOTE_ADDR", "-"),
            'pid': os.getpid(),
            'error': str(exception),
            'error_type': type(exception).__name__
        }
        
        # 记录异常
        log_message = self._format_log_message(error_data, logging.ERROR)
        self.logger.error(f"Request failed: {log_message}", exc_info=True)
        
        return None


def log_performance(func):
    """
    性能日志装饰器
    
    用于记录函数执行时间
    
    Args:
        func: 被装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            logging.info(
                f"Performance: {func.__name__} executed in {duration:.3f}s"
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            logging.error(
                f"Performance: {func.__name__} failed after {duration:.3f}s - {str(e)}",
                exc_info=True
            )
            raise
    
    return wrapper


def log_async_performance(func):
    """
    异步性能日志装饰器
    
    用于记录异步函数执行时间
    
    Args:
        func: 被装饰的异步函数
        
    Returns:
        装饰后的异步函数
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            duration = time.time() - start_time
            logging.info(
                f"Performance: {func.__name__} executed in {duration:.3f}s"
            )
            
            return result
        
        except Exception as e:
            duration = time.time() - start_time
            logging.error(
                f"Performance: {func.__name__} failed after {duration:.3f}s - {str(e)}",
                exc_info=True
            )
            raise
    
    return wrapper


class RequestContextLogger:
    """
    请求上下文日志记录器
    
    提供在请求上下文中记录日志的便捷方法
    """
    
    def __init__(self, request_handler):
        """
        初始化请求上下文日志记录器
        
        Args:
            request_handler: 请求处理器实例
        """
        self.request_handler = request_handler
        self.request_id = getattr(request_handler, 'request_id', '-')
    
    def info(self, message: str, **kwargs):
        """
        记录 INFO 级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文数据
        """
        extra_data = {'request_id': self.request_id, **kwargs}
        logging.info(f"[{self.request_id}] {message}", extra=extra_data)
    
    def warning(self, message: str, **kwargs):
        """
        记录 WARNING 级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文数据
        """
        extra_data = {'request_id': self.request_id, **kwargs}
        logging.warning(f"[{self.request_id}] {message}", extra=extra_data)
    
    def error(self, message: str, **kwargs):
        """
        记录 ERROR 级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文数据
        """
        extra_data = {'request_id': self.request_id, **kwargs}
        logging.error(f"[{self.request_id}] {message}", extra=extra_data, exc_info=True)
    
    def debug(self, message: str, **kwargs):
        """
        记录 DEBUG 级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文数据
        """
        extra_data = {'request_id': self.request_id, **kwargs}
        logging.debug(f"[{self.request_id}] {message}", extra=extra_data)
