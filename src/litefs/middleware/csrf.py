#!/usr/bin/env python
# coding: utf-8

"""
CSRF 保护中间件

提供跨站请求伪造防护
"""

import hashlib
import hmac
import json
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
        
        # 对于 API 路由，跳过 CSRF 保护
        path = request_handler.environ.get("PATH_INFO", "/")
        if path.startswith("/api/"):
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
            # 使用 request_handler 的状态码，而不是硬编码 200
            from litefs.handlers import http_status_codes
            status_code = getattr(request_handler, '_status_code', 200)
            status_text = http_status_codes.get(status_code, "OK")
            status = f"{status_code} {status_text}"
            headers = []
            content = response
        
        # 添加 CSRF 令牌 cookie
        cookie_header = self._create_csrf_cookie(csrf_token)
        headers.append(("Set-Cookie", cookie_header))
        
        # 将 CSRF 令牌添加到响应中，方便前端使用
        request_handler._csrf_token = csrf_token
        
        return status, headers, content
    
    def _generate_csrf_token(self, request_handler):
        """
        生成 CSRF 令牌（HMAC-SHA256 签名方式）
        
        令牌格式: <随机nonce>.<HMAC签名>
        签名内容: nonce + session_id，绑定到当前会话
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            CSRF 令牌
        """
        # 从 cookie 中获取现有令牌，验证其是否仍有效
        cookie = request_handler.cookie
        if cookie:
            cookie_item = cookie.get(self.cookie_name)
            if cookie_item:
                existing_token = cookie_item.value
                if self._validate_csrf_token(existing_token, request_handler):
                    return existing_token
        
        # 生成新的 HMAC-SHA256 签名令牌
        nonce = secrets.token_urlsafe(32)
        session_id = self._get_session_id(request_handler)
        signature = self._sign_token(nonce, session_id)
        csrf_token = f"{nonce}.{signature}"
        
        return csrf_token

    def _sign_token(self, nonce: str, session_id: str) -> str:
        """
        使用 HMAC-SHA256 对 nonce 和 session_id 进行签名
        
        Args:
            nonce: 随机字符串
            session_id: 会话 ID
            
        Returns:
            签名的十六进制字符串
        """
        message = f"{nonce}:{session_id}".encode("utf-8")
        key = self.secret_key.encode("utf-8")
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    def _get_session_id(self, request_handler) -> str:
        """
        获取当前请求的 session_id，用于绑定 CSRF 令牌到会话
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            session_id 字符串，如果没有会话则返回空字符串
        """
        session_id = getattr(request_handler, 'session_id', None)
        if session_id:
            return str(session_id)
        # 尝试从 session 属性获取
        session = getattr(request_handler, 'session', None)
        if session and hasattr(session, 'id'):
            return str(session.id)
        return ""
    
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
            cookie_item = cookie.get(self.cookie_name)
            if cookie_item:
                cookie_token = cookie_item.value
                if cookie_token:
                    return cookie_token
        
        return None
    
    def _validate_csrf_token(self, token, request_handler):
        """
        验证 CSRF 令牌（HMAC-SHA256 签名验证）
        
        验证流程:
        1. 检查令牌格式（必须包含 nonce.signature）
        2. 使用 secret_key 和当前 session_id 重新计算签名
        3. 使用恒定时间比较防止时序攻击
        
        Args:
            token: 要验证的 CSRF 令牌
            request_handler: 请求处理器实例
            
        Returns:
            如果令牌有效返回 True，否则返回 False
        """
        if not token or len(token) < 64:
            return False
        
        # 解析令牌格式: nonce.signature
        parts = token.rsplit(".", 1)
        if len(parts) != 2:
            return False
        
        nonce, signature = parts
        if not nonce or not signature:
            return False
        
        # 使用当前 session_id 重新计算签名
        session_id = self._get_session_id(request_handler)
        expected_signature = self._sign_token(nonce, session_id)
        
        # 使用恒定时间比较，防止时序攻击
        return hmac.compare_digest(signature, expected_signature)
    
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
        content = json.dumps({"error": message}).encode("utf-8")

        return status, headers, content
