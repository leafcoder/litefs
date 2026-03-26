#!/usr/bin/env python
# coding: utf-8

from typing import List, Optional

from .base import Middleware


class SecurityMiddleware(Middleware):
    """
    安全中间件
    
    添加各种安全相关的 HTTP 响应头，提高应用安全性
    """

    def __init__(
        self,
        app,
        x_frame_options: str = 'DENY',
        x_content_type_options: str = 'nosniff',
        x_xss_protection: str = '1; mode=block',
        strict_transport_security: str = 'max-age=31536000; includeSubDomains',
        content_security_policy: Optional[str] = None,
        referrer_policy: str = 'strict-origin-when-cross-origin',
        permissions_policy: Optional[str] = None,
    ):
        """
        初始化安全中间件
        
        Args:
            app: Litefs 应用实例
            x_frame_options: X-Frame-Options 响应头，防止点击劫持
            x_content_type_options: X-Content-Type-Options 响应头，防止 MIME 类型嗅探
            x_xss_protection: X-XSS-Protection 响应头，启用 XSS 过滤
            strict_transport_security: Strict-Transport-Security 响应头，强制 HTTPS
            content_security_policy: Content-Security-Policy 响应头，定义内容安全策略
            referrer_policy: Referrer-Policy 响应头，控制 Referer 信息
            permissions_policy: Permissions-Policy 响应头，控制浏览器功能
        """
        super(SecurityMiddleware, self).__init__(app)
        self.x_frame_options = x_frame_options
        self.x_content_type_options = x_content_type_options
        self.x_xss_protection = x_xss_protection
        self.strict_transport_security = strict_transport_security
        self.content_security_policy = content_security_policy
        self.referrer_policy = referrer_policy
        self.permissions_policy = permissions_policy

    def process_response(self, request_handler, response):
        """
        处理响应，添加安全响应头
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            添加了安全响应头的响应数据
        """
        if isinstance(response, tuple) and len(response) == 3:
            status, headers, content = response
            headers = list(headers)
        else:
            headers = []
        
        headers.append(('X-Frame-Options', self.x_frame_options))
        headers.append(('X-Content-Type-Options', self.x_content_type_options))
        headers.append(('X-XSS-Protection', self.x_xss_protection))
        headers.append(('Referrer-Policy', self.referrer_policy))
        
        if self.strict_transport_security:
            headers.append(
                ('Strict-Transport-Security', self.strict_transport_security)
            )
        
        if self.content_security_policy:
            headers.append(
                ('Content-Security-Policy', self.content_security_policy)
            )
        
        if self.permissions_policy:
            headers.append(('Permissions-Policy', self.permissions_policy))
        
        if isinstance(response, tuple) and len(response) == 3:
            return status, headers, content
        
        return response


class AuthMiddleware(Middleware):
    """
    认证中间件
    
    基于请求头的简单认证中间件
    """

    def __init__(self, app, auth_header: str = 'Authorization'):
        """
        初始化认证中间件
        
        Args:
            app: Litefs 应用实例
            auth_header: 认证头名称，默认为 'Authorization'
        """
        super(AuthMiddleware, self).__init__(app)
        self.auth_header = auth_header

    def process_request(self, request_handler):
        """
        处理请求，检查认证信息
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            如果认证失败，返回 401 响应
            否则返回 None，继续处理请求
        """
        auth_token = request_handler.environ.get(f'HTTP_{self.auth_header.upper().replace("-", "_")}', '')
        
        if not auth_token:
            return self._create_unauthorized_response('Missing authentication token')
        
        if not self._verify_token(auth_token):
            return self._create_unauthorized_response('Invalid authentication token')
        
        return None

    def _verify_token(self, token: str) -> bool:
        """
        验证令牌
        
        Args:
            token: 认证令牌
            
        Returns:
            如果令牌有效返回 True，否则返回 False
        """
        return True

    def _create_unauthorized_response(self, message: str):
        """
        创建未授权响应
        
        Args:
            message: 错误消息
            
        Returns:
            401 响应
        """
        status = '401 Unauthorized'
        headers = [
            ('Content-Type', 'application/json; charset=utf-8'),
            ('WWW-Authenticate', 'Bearer realm="Litefs"'),
        ]
        content = f'{{"error": "{message}"}}'.encode('utf-8')
        
        return status, headers, content
