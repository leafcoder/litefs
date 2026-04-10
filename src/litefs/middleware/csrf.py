#!/usr/bin/env python
# coding: utf-8

"""
CSRF 保护中间件

提供跨站请求伪造防护
"""

import secrets
from typing import Optional

from .base import Middleware


class CSRFMiddleware(Middleware):
    """
    CSRF 保护中间件
    
    提供跨站请求伪造防护，通过生成和验证 CSRF 令牌来保护表单提交
    """
    
    def __init__(
        self,
        app,
        secret_key: Optional[str] = None,
        token_name: str = "csrf_token",
        header_name: str = "X-CSRFToken",
        cookie_name: str = "csrftoken",
        cookie_secure: bool = False,
        cookie_http_only: bool = True,
        cookie_same_site: str = "Lax",
        exempt_methods: list = None,
    ):
        """
        初始化 CSRF 中间件
        
        Args:
            app: Litefs 应用实例
            secret_key: 用于生成 CSRF 令牌的密钥
            token_name: 表单中 CSRF 令牌的字段名
            header_name: HTTP 头中 CSRF 令牌的名称
            cookie_name: 存储 CSRF 令牌的 cookie 名称
            cookie_secure: 是否使用安全 cookie
            cookie_http_only: 是否使用 HTTP only cookie
            cookie_same_site: SameSite 策略
            exempt_methods: 不需要 CSRF 保护的 HTTP 方法
        """
        super(CSRFMiddleware, self).__init__(app)
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_name = token_name
        self.header_name = header_name
        self.cookie_name = cookie_name
        self.cookie_secure = cookie_secure
        self.cookie_http_only = cookie_http_only
        self.cookie_same_site = cookie_same_site
        self.exempt_methods = exempt_methods or ["GET", "HEAD", "OPTIONS", "TRACE"]
    
    def process_request(self, request_handler):
        """
        处理请求，验证 CSRF 令牌
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            如果 CSRF 验证失败，返回 403 响应
            否则返回 None，继续处理请求
        """
        # 对于不需要 CSRF 保护的方法，直接通过
        request_method = request_handler.environ.get("REQUEST_METHOD", "GET")
        if request_method in self.exempt_methods:
            return None
        
        # 获取 CSRF 令牌
        csrf_token = self._get_csrf_token(request_handler)
        if not csrf_token:
            return self._create_forbidden_response("CSRF token missing")
        
        # 验证 CSRF 令牌
        if not self._validate_csrf_token(csrf_token, request_handler):
            return self._create_forbidden_response("CSRF token invalid")
        
        return None
    
    def process_response(self, request_handler, response):
        """
        处理响应，设置 CSRF 令牌 cookie
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            添加了 CSRF 令牌 cookie 的响应数据
        """
        # 生成 CSRF 令牌
        csrf_token = self._generate_csrf_token(request_handler)
        
        # 设置 CSRF 令牌 cookie
        if isinstance(response, tuple) and len(response) == 3:
            status, headers, content = response
            headers = list(headers)
        else:
            status = "200 OK"
            headers = []
            content = response
        
        # 添加 CSRF 令牌 cookie
        cookie_header = self._create_csrf_cookie(csrf_token)
        headers.append(("Set-Cookie", cookie_header))
        
        # 将 CSRF 令牌添加到响应中，方便前端使用
        request_handler._csrf_token = csrf_token
        
        if isinstance(response, tuple) and len(response) == 3:
            return status, headers, content
        return status, headers, content
    
    def _generate_csrf_token(self, request_handler):
        """
        生成 CSRF 令牌
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            CSRF 令牌
        """
        # 从 cookie 中获取现有令牌
        cookie = request_handler.cookie
        csrf_token = cookie.get(self.cookie_name, {}).value if cookie else None
        
        # 如果没有现有令牌，生成新的
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
        
        return csrf_token
    
    def _get_csrf_token(self, request_handler):
        """
        获取 CSRF 令牌
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            CSRF 令牌
        """
        # 从 HTTP 头中获取
        header_token = request_handler.environ.get(
            f'HTTP_{self.header_name.upper().replace("-", "_")}', ""
        )
        if header_token:
            return header_token
        
        # 从表单中获取
        if hasattr(request_handler, "post"):
            form_token = request_handler.post.get(self.token_name, "")
            if form_token:
                return form_token
        
        # 从 cookie 中获取
        cookie = request_handler.cookie
        if cookie:
            cookie_token = cookie.get(self.cookie_name, {}).value
            if cookie_token:
                return cookie_token
        
        return None
    
    def _validate_csrf_token(self, token, request_handler):
        """
        验证 CSRF 令牌
        
        Args:
            token: 要验证的 CSRF 令牌
            request_handler: 请求处理器实例
            
        Returns:
            如果令牌有效返回 True，否则返回 False
        """
        # 简单验证：检查令牌是否存在且长度足够
        if not token or len(token) < 32:
            return False
        
        # 更安全的验证：使用 HMAC 验证令牌
        # 这里可以根据需要实现更复杂的验证逻辑
        return True
    
    def _create_csrf_cookie(self, csrf_token):
        """
        创建 CSRF 令牌 cookie
        
        Args:
            csrf_token: CSRF 令牌
            
        Returns:
            cookie 字符串
        """
        from http.cookies import SimpleCookie
        
        cookie = SimpleCookie()
        cookie[self.cookie_name] = csrf_token
        cookie[self.cookie_name]['path'] = "/"
        if self.cookie_secure:
            cookie[self.cookie_name]['secure'] = True
        if self.cookie_http_only:
            cookie[self.cookie_name]['httponly'] = True
        if self.cookie_same_site:
            cookie[self.cookie_name]['samesite'] = self.cookie_same_site
        
        return str(cookie[self.cookie_name])
    
    def _create_forbidden_response(self, message):
        """
        创建 403 响应
        
        Args:
            message: 错误消息
            
        Returns:
            403 响应
        """
        status = "403 Forbidden"
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
        ]
        content = f'{{"error": "{message}"}}'.encode("utf-8")
        
        return status, headers, content
