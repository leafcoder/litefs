#!/usr/bin/env python
# coding: utf-8

"""
认证中间件

提供 JWT Token 验证和用户身份注入功能。
"""

import functools
from typing import Callable, Optional


class AuthMiddleware:
    """认证中间件"""
    
    def __init__(
        self,
        app=None,
        jwt_manager=None,
        token_location: str = 'header',
        token_name: str = 'Authorization',
        token_prefix: str = 'Bearer',
        exempt_paths: list = None,
    ):
        """
        初始化认证中间件
        
        Args:
            app: Litefs 应用实例（可选）
            jwt_manager: JWT 管理器
            token_location: Token 位置 ('header', 'cookie', 'query')
            token_name: Token 名称
            token_prefix: Token 前缀
            exempt_paths: 豁免路径列表
        """
        self.app = app
        self.jwt_manager = jwt_manager
        self.token_location = token_location
        self.token_name = token_name
        self.token_prefix = token_prefix
        self.exempt_paths = exempt_paths or []
    
    def process_request(self, request):
        """
        处理请求
        
        Args:
            request: 请求对象
            
        Returns:
            None 或响应
        """
        from .models import User
        
        path = getattr(request, 'path', '/')
        
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return None
        
        token = self._extract_token(request)
        
        if not token:
            return None
        
        if not self.jwt_manager:
            return None
        
        payload = self.jwt_manager.decode_token(token)
        
        if not payload:
            return None
        
        user_id = payload.get('sub')
        if not user_id:
            return None
        
        user = User.get_by_id(user_id)
        if user:
            request.user = user
            request.user_id = user_id
        
        return None
    
    def process_response(self, request, response):
        """
        处理响应
        
        Args:
            request: 请求对象
            response: 响应数据
            
        Returns:
            响应数据
        """
        return response
    
    def _extract_token(self, request) -> Optional[str]:
        """
        提取 Token
        
        Args:
            request: 请求对象
            
        Returns:
            Token 或 None
        """
        if self.token_location == 'header':
            environ = getattr(request, '_environ', {})
            header_key = f'HTTP_{self.token_name.upper().replace("-", "_")}'
            auth_header = environ.get(header_key, '')
            if auth_header.startswith(self.token_prefix + ' '):
                return auth_header[len(self.token_prefix) + 1:]
            return auth_header or None
        
        elif self.token_location == 'cookie':
            cookies = getattr(request, 'cookies', {})
            return cookies.get(self.token_name)
        
        elif self.token_location == 'query':
            query = getattr(request, 'query', {})
            return query.get(self.token_name)
        
        return None


def login_required(func: Callable) -> Callable:
    """
    登录验证装饰器
    
    Args:
        func: 处理函数
        
    Returns:
        装饰后的函数
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'user') or request.user is None:
            return {'error': '需要登录'}, 401
        return func(request, *args, **kwargs)
    return wrapper


def role_required(*roles: str) -> Callable:
    """
    角色验证装饰器
    
    Args:
        *roles: 允许的角色列表
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user') or request.user is None:
                return {'error': '需要登录'}, 401
            
            user_roles = getattr(request.user, 'roles', [])
            user_role_names = [r.name if hasattr(r, 'name') else str(r) for r in user_roles]
            
            for role in roles:
                if role in user_role_names:
                    return func(request, *args, **kwargs)
            
            return {'error': '权限不足'}, 403
        return wrapper
    return decorator
