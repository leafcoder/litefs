#!/usr/bin/env python
# coding: utf-8

"""
OAuth2 认证管理

提供 OAuth2 认证的完整实现，支持多种 OAuth2 提供商。
"""

import time
from typing import Any, Callable, Dict, Optional

from .providers import (
    OAuth2Provider,
    OAuth2UserInfo,
    GitHubProvider,
    GoogleProvider,
    WeChatProvider,
    WeComProvider,
    get_provider,
)


class OAuth2State:
    """OAuth2 状态管理"""
    
    def __init__(self, ttl: int = 600):
        self._states: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl
    
    def create(
        self,
        provider: str,
        redirect_uri: str = None,
        **kwargs
    ) -> str:
        """
        创建状态
        
        Args:
            provider: 提供商名称
            redirect_uri: 回调地址
            **kwargs: 额外数据
            
        Returns:
            状态字符串
        """
        import secrets
        state = secrets.token_urlsafe(32)
        
        self._states[state] = {
            'provider': provider,
            'redirect_uri': redirect_uri,
            'created_at': time.time(),
            **kwargs
        }
        
        return state
    
    def verify(self, state: str) -> Optional[Dict[str, Any]]:
        """
        验证状态
        
        Args:
            state: 状态字符串
            
        Returns:
            状态数据或 None
        """
        data = self._states.pop(state, None)
        
        if not data:
            return None
        
        if time.time() - data['created_at'] > self._ttl:
            return None
        
        return data
    
    def cleanup(self):
        """清理过期状态"""
        now = time.time()
        expired = [
            state for state, data in self._states.items()
            if now - data['created_at'] > self._ttl
        ]
        for state in expired:
            del self._states[state]


class OAuth2:
    """
    OAuth2 认证管理器
    
    提供完整的 OAuth2 认证流程管理。
    
    使用示例:
        oauth = OAuth2(app)
        
        oauth.register(
            name='github',
            client_id='your-client-id',
            client_secret='your-client-secret',
            redirect_uri='http://localhost:8080/auth/github/callback'
        )
        
        @route('/login/github')
        def github_login(request):
            return oauth.authorize_redirect(request, 'github')
        
        @route('/auth/github/callback')
        def github_callback(request):
            user_info = oauth.authorize_user(request, 'github')
            if user_info:
                return {'user': user_info.to_dict()}
            return {'error': '认证失败'}
    """
    
    def __init__(
        self,
        app=None,
        state_ttl: int = 600,
        user_mapper: Callable[[OAuth2UserInfo], Any] = None,
    ):
        """
        初始化 OAuth2 管理器
        
        Args:
            app: Litefs 应用实例
            state_ttl: 状态有效期（秒）
            user_mapper: 用户映射函数
        """
        self._providers: Dict[str, OAuth2Provider] = {}
        self._state = OAuth2State(ttl=state_ttl)
        self._user_mapper = user_mapper
        self._app = app
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """
        初始化应用
        
        Args:
            app: Litefs 应用实例
        """
        self._app = app
    
    def register(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str = '',
        scope: str = None,
        provider_class: type = None,
        **kwargs
    ):
        """
        注册 OAuth2 提供商
        
        Args:
            name: 提供商名称
            client_id: 客户端 ID
            client_secret: 客户端密钥
            redirect_uri: 回调地址
            scope: 权限范围
            provider_class: 提供商类
            **kwargs: 额外参数
        """
        if provider_class:
            provider_cls = provider_class
        else:
            provider_cls = get_provider(name)
        
        if not provider_cls:
            raise ValueError(f"Unknown provider: {name}")
        
        provider = provider_cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            **kwargs
        )
        
        self._providers[name] = provider
    
    def get_provider(self, name: str) -> Optional[OAuth2Provider]:
        """
        获取提供商
        
        Args:
            name: 提供商名称
            
        Returns:
            OAuth2Provider 实例
        """
        return self._providers.get(name)
    
    def authorize_redirect(
        self,
        request,
        provider_name: str,
        callback_url: str = None,
        **kwargs
    ):
        """
        生成授权重定向响应
        
        Args:
            request: 请求对象
            provider_name: 提供商名称
            callback_url: 回调地址
            **kwargs: 额外参数
            
        Returns:
            重定向响应
        """
        from litefs.handlers import Response
        
        provider = self._providers.get(provider_name)
        if not provider:
            return Response.json({'error': f'Unknown provider: {provider_name}'}, status_code=400)
        
        redirect_uri = callback_url or provider.redirect_uri
        
        state = self._state.create(
            provider=provider_name,
            redirect_uri=redirect_uri,
            **kwargs
        )
        
        authorize_url = provider.get_authorize_url(
            state=state,
            redirect_uri=redirect_uri
        )
        
        return Response.redirect(authorize_url)
    
    def authorize_user(
        self,
        request,
        provider_name: str = None,
        **kwargs
    ) -> Optional[OAuth2UserInfo]:
        """
        完成授权并获取用户信息
        
        Args:
            request: 请求对象
            provider_name: 提供商名称（可选，从状态中获取）
            **kwargs: 额外参数
            
        Returns:
            用户信息或 None
        """
        code = self._get_code(request)
        state = self._get_state(request)
        
        if not code:
            return None
        
        state_data = self._state.verify(state)
        if not state_data:
            return None
        
        provider_name = provider_name or state_data.get('provider')
        provider = self._providers.get(provider_name)
        
        if not provider:
            return None
        
        token_data = provider.get_access_token(
            code=code,
            redirect_uri=state_data.get('redirect_uri')
        )
        
        if 'error' in token_data:
            return None
        
        access_token = token_data.get('access_token')
        if not access_token:
            return None
        
        if provider_name == 'wechat':
            openid = token_data.get('openid')
            user_info = provider.get_user_info(access_token, openid=openid)
        elif provider_name == 'wecom':
            user_info = provider.get_user_info(access_token, code=code)
        else:
            user_info = provider.get_user_info(access_token)
        
        if user_info and self._user_mapper:
            return self._user_mapper(user_info)
        
        return user_info
    
    def _get_code(self, request) -> Optional[str]:
        """从请求中获取授权码"""
        if hasattr(request, 'query'):
            return request.query.get('code')
        
        if hasattr(request, 'query_string'):
            from urllib.parse import parse_qs
            params = parse_qs(request.query_string)
            codes = params.get('code', [])
            return codes[0] if codes else None
        
        return None
    
    def _get_state(self, request) -> Optional[str]:
        """从请求中获取状态"""
        if hasattr(request, 'query'):
            return request.query.get('state')
        
        if hasattr(request, 'query_string'):
            from urllib.parse import parse_qs
            params = parse_qs(request.query_string)
            states = params.get('state', [])
            return states[0] if states else None
        
        return None
    
    def get_authorize_url(
        self,
        provider_name: str,
        callback_url: str = None,
        state: str = None,
    ) -> str:
        """
        获取授权 URL
        
        Args:
            provider_name: 提供商名称
            callback_url: 回调地址
            state: 状态参数
            
        Returns:
            授权 URL
        """
        provider = self._providers.get(provider_name)
        if not provider:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        redirect_uri = callback_url or provider.redirect_uri
        
        if not state:
            state = self._state.create(
                provider=provider_name,
                redirect_uri=redirect_uri
            )
        
        return provider.get_authorize_url(
            state=state,
            redirect_uri=redirect_uri
        )
    
    def set_user_mapper(self, mapper: Callable[[OAuth2UserInfo], Any]):
        """
        设置用户映射函数
        
        Args:
            mapper: 映射函数，接收 OAuth2UserInfo 返回用户对象
        """
        self._user_mapper = mapper


def create_oauth2_blueprint(oauth: OAuth2, prefix: str = '/auth'):
    """
    创建 OAuth2 蓝图
    
    Args:
        oauth: OAuth2 管理器
        prefix: URL 前缀
        
    Returns:
        路由列表
    """
    from litefs.routing import get
    
    routes = []
    
    for name, provider in oauth._providers.items():
        def make_login_handler(provider_name):
            def login_handler(request):
                return oauth.authorize_redirect(request, provider_name)
            return login_handler
        
        def make_callback_handler(provider_name):
            def callback_handler(request):
                user_info = oauth.authorize_user(request, provider_name)
                if user_info:
                    return {'success': True, 'user': user_info.to_dict()}
                return {'success': False, 'error': '认证失败'}
            return callback_handler
        
        login_route = get(f'{prefix}/{name}')(make_login_handler(name))
        callback_route = get(f'{prefix}/{name}/callback')(make_callback_handler(name))
        
        routes.extend([login_route, callback_route])
    
    return routes
