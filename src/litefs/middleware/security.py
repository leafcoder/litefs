#!/usr/bin/env python
# coding: utf-8

import json
from typing import Callable, List, Optional

from .base import Middleware


class SecurityMiddleware(Middleware):
    """
    安全中间件

    添加各种安全相关的 HTTP 响应头，提高应用安全性
    """

    def __init__(
        self,
        app,
        x_frame_options: str = "DENY",
        x_content_type_options: str = "nosniff",
        x_xss_protection: str = "1; mode=block",
        strict_transport_security: str = "max-age=31536000; includeSubDomains",
        content_security_policy: Optional[str] = None,
        referrer_policy: str = "strict-origin-when-cross-origin",
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

        headers.append(("X-Frame-Options", self.x_frame_options))
        headers.append(("X-Content-Type-Options", self.x_content_type_options))
        headers.append(("X-XSS-Protection", self.x_xss_protection))
        headers.append(("Referrer-Policy", self.referrer_policy))

        if self.strict_transport_security:
            headers.append(("Strict-Transport-Security", self.strict_transport_security))

        if self.content_security_policy:
            headers.append(("Content-Security-Policy", self.content_security_policy))

        if self.permissions_policy:
            headers.append(("Permissions-Policy", self.permissions_policy))

        if isinstance(response, tuple) and len(response) == 3:
            return status, headers, content

        return response


class AuthMiddleware(Middleware):
    """
    认证中间件

    基于 Bearer Token 的认证中间件，支持自定义验证函数和 JWT 集成
    """

    def __init__(
        self,
        app,
        auth_header: str = "Authorization",
        token_verifier: Optional[Callable[[str], bool]] = None,
        jwt_manager=None,
    ):
        """
        初始化认证中间件

        Args:
            app: Litefs 应用实例
            auth_header: 认证头名称，默认为 'Authorization'
            token_verifier: 自定义令牌验证函数，接收 token 字符串，返回 bool。
                            如果未提供，将尝试使用 jwt_manager 或拒绝所有请求。
            jwt_manager: JWT 管理器实例（litefs.auth.jwt.JWTManager），
                         如果提供且未指定 token_verifier，将用于验证 JWT token
        """
        super(AuthMiddleware, self).__init__(app)
        self.auth_header = auth_header
        self.token_verifier = token_verifier
        self.jwt_manager = jwt_manager

    def process_request(self, request_handler):
        """
        处理请求，检查认证信息

        Args:
            request_handler: 请求处理器实例

        Returns:
            如果认证失败，返回 401 响应
            否则返回 None，继续处理请求
        """
        auth_token = request_handler.environ.get(
            f'HTTP_{self.auth_header.upper().replace("-", "_")}', ""
        )

        if not auth_token:
            return self._create_unauthorized_response("Missing authentication token")

        # 提取 Bearer token
        token = self._extract_bearer_token(auth_token)
        if token is None:
            return self._create_unauthorized_response(
                "Invalid authorization header format. Expected: Bearer <token>"
            )

        if not self._verify_token(token):
            return self._create_unauthorized_response("Invalid authentication token")

        return None

    def _extract_bearer_token(self, auth_token: str) -> Optional[str]:
        """
        从 Authorization 头中提取 Bearer Token

        Args:
            auth_token: Authorization 头的值

        Returns:
            Bearer token 字符串，格式不正确时返回 None
        """
        parts = auth_token.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        # 也允许直接传入 token（兼容不带 Bearer 前缀的情况）
        if len(parts) == 1 and auth_token.strip():
            return auth_token.strip()
        return None

    def _verify_token(self, token: str) -> bool:
        """
        验证令牌

        验证优先级:
        1. 自定义 token_verifier 函数
        2. jwt_manager 实例
        3. 默认拒绝所有请求（安全默认值）

        Args:
            token: 认证令牌

        Returns:
            如果令牌有效返回 True，否则返回 False
        """
        # 优先使用自定义验证函数
        if self.token_verifier is not None:
            try:
                return bool(self.token_verifier(token))
            except Exception:
                return False

        # 使用 JWT 管理器验证
        if self.jwt_manager is not None:
            try:
                payload = self.jwt_manager.decode(token)
                return payload is not None
            except Exception:
                return False

        # 安全默认值：如果没有配置验证器，拒绝所有请求
        # 使用方必须显式提供 token_verifier 或 jwt_manager
        return False

    def _create_unauthorized_response(self, message: str):
        """
        创建未授权响应

        Args:
            message: 错误消息

        Returns:
            401 响应
        """
        status = "401 Unauthorized"
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("WWW-Authenticate", 'Bearer realm="Litefs"'),
        ]
        content = json.dumps({"error": message}).encode("utf-8")

        return status, headers, content
