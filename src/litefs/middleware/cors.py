#!/usr/bin/env python
# coding: utf-8

from typing import List, Optional

from .base import Middleware


class CORSMiddleware(Middleware):
    """
    CORS 中间件
    
    处理跨域资源共享（CORS）请求，支持配置允许的来源、方法、头部等
    """

    def __init__(
        self,
        app,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        expose_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        max_age: int = 86400,
    ):
        """
        初始化 CORS 中间件
        
        Args:
            app: Litefs 应用实例
            allow_origins: 允许的来源列表，如 ['http://localhost:3000', 'https://example.com']
                          如果为 None，则允许所有来源（不推荐生产环境使用）
            allow_methods: 允许的 HTTP 方法列表，如 ['GET', 'POST', 'PUT', 'DELETE']
            allow_headers: 允许的请求头列表，如 ['Content-Type', 'Authorization']
            expose_headers: 允许暴露给客户端的响应头列表
            allow_credentials: 是否允许携带凭证（cookies、authorization headers）
            max_age: 预检请求的缓存时间（秒）
        """
        super(CORSMiddleware, self).__init__(app)
        self.allow_origins = allow_origins or ['*']
        self.allow_methods = allow_methods or [
            'GET',
            'POST',
            'PUT',
            'DELETE',
            'OPTIONS',
            'PATCH',
        ]
        self.allow_headers = allow_headers or [
            'Content-Type',
            'Authorization',
            'X-Requested-With',
        ]
        self.expose_headers = expose_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def process_request(self, request_handler):
        """
        处理请求，检查是否为预检请求
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            如果是预检请求，返回预检响应
            否则返回 None，继续处理请求
        """
        method = request_handler.environ.get('REQUEST_METHOD', 'GET')
        
        if method == 'OPTIONS':
            return self._create_preflight_response(request_handler)
        
        return None

    def process_response(self, request_handler, response):
        """
        处理响应，添加 CORS 响应头
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            添加了 CORS 响应头的响应数据
        """
        origin = request_handler.environ.get('HTTP_ORIGIN', '')
        
        if self._is_origin_allowed(origin):
            if isinstance(response, tuple) and len(response) == 3:
                status, headers, content = response
                headers = list(headers)
            else:
                headers = []
            
            if '*' in self.allow_origins:
                headers.append(('Access-Control-Allow-Origin', '*'))
            else:
                headers.append(('Access-Control-Allow-Origin', origin))
            
            if self.allow_credentials:
                headers.append(('Access-Control-Allow-Credentials', 'true'))
            
            if self.expose_headers:
                headers.append(
                    ('Access-Control-Expose-Headers', ', '.join(self.expose_headers))
                )
            
            if isinstance(response, tuple) and len(response) == 3:
                return status, headers, content
        
        return response

    def _is_origin_allowed(self, origin: str) -> bool:
        """
        检查来源是否被允许
        
        Args:
            origin: 请求来源
            
        Returns:
            如果来源被允许返回 True，否则返回 False
        """
        if not origin:
            return False
        
        if '*' in self.allow_origins:
            return True
        
        return origin in self.allow_origins

    def _create_preflight_response(self, request_handler):
        """
        创建预检请求响应
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            预检请求响应
        """
        origin = request_handler.environ.get('HTTP_ORIGIN', '')
        request_method = request_handler.environ.get(
            'HTTP_ACCESS_CONTROL_REQUEST_METHOD', ''
        )
        request_headers = request_handler.environ.get(
            'HTTP_ACCESS_CONTROL_REQUEST_HEADERS', ''
        )
        
        headers = []
        
        if self._is_origin_allowed(origin):
            if '*' in self.allow_origins:
                headers.append(('Access-Control-Allow-Origin', '*'))
            else:
                headers.append(('Access-Control-Allow-Origin', origin))
            
            if self.allow_credentials:
                headers.append(('Access-Control-Allow-Credentials', 'true'))
            
            headers.append(
                ('Access-Control-Allow-Methods', ', '.join(self.allow_methods))
            )
            
            if request_headers:
                headers.append(('Access-Control-Allow-Headers', request_headers))
            elif self.allow_headers:
                headers.append(
                    ('Access-Control-Allow-Headers', ', '.join(self.allow_headers))
                )
            
            headers.append(('Access-Control-Max-Age', str(self.max_age)))
        
        status = '200 OK'
        content = b''
        
        return status, headers, content
