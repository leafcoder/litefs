#!/usr/bin/env python
# coding: utf-8

"""
OAuth2 提供商

提供主流 OAuth2 提供商的实现，包括 GitHub、Google、微信等。
"""

import base64
import hashlib
import secrets
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class OAuth2UserInfo:
    """OAuth2 用户信息"""
    provider: str
    provider_user_id: str
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'provider': self.provider,
            'provider_user_id': self.provider_user_id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'avatar_url': self.avatar_url,
        }


class OAuth2Provider(ABC):
    """OAuth2 提供商基类"""
    
    name: str = 'base'
    authorize_url: str = ''
    access_token_url: str = ''
    userinfo_url: str = ''
    scope: str = ''
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = '',
        scope: str = None,
        **kwargs
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope or self.scope
        self.extra_params = kwargs
    
    def get_authorize_url(
        self,
        state: str,
        redirect_uri: str = None,
        **kwargs
    ) -> str:
        """
        生成授权 URL
        
        Args:
            state: 状态参数，用于防止 CSRF 攻击
            redirect_uri: 回调地址
            **kwargs: 额外参数
            
        Returns:
            授权 URL
        """
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'response_type': 'code',
            'state': state,
        }
        
        if self.scope:
            params['scope'] = self.scope
        
        params.update(kwargs)
        
        return f"{self.authorize_url}?{urllib.parse.urlencode(params)}"
    
    @abstractmethod
    def get_access_token(
        self,
        code: str,
        redirect_uri: str = None
    ) -> Dict[str, Any]:
        """
        使用授权码获取 Access Token
        
        Args:
            code: 授权码
            redirect_uri: 回调地址
            
        Returns:
            Token 信息
        """
        pass
    
    @abstractmethod
    def get_user_info(self, access_token: str) -> OAuth2UserInfo:
        """
        获取用户信息
        
        Args:
            access_token: Access Token
            
        Returns:
            用户信息
        """
        pass
    
    def _request(
        self,
        url: str,
        method: str = 'GET',
        data: Dict = None,
        headers: Dict = None
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求（同步）

        Args:
            url: 请求 URL
            method: 请求方法
            data: 请求数据
            headers: 请求头

        Returns:
            响应数据
        """
        import json

        try:
            import urllib.request
            import urllib.error

            req_headers = {
                'Accept': 'application/json',
                'User-Agent': 'Litefs-OAuth2/1.0',
            }
            if headers:
                req_headers.update(headers)

            if method == 'GET':
                if data:
                    url = f"{url}?{urllib.parse.urlencode(data)}"
                req = urllib.request.Request(url, headers=req_headers)
            else:
                body = urllib.parse.urlencode(data).encode('utf-8') if data else b''
                req = urllib.request.Request(url, data=body, headers=req_headers, method=method)

            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else ''
            return {'error': f'HTTP {e.code}', 'error_description': error_body}
        except Exception as e:
            return {'error': str(e)}

    async def _async_request(
        self,
        url: str,
        method: str = 'GET',
        data: Dict = None,
        headers: Dict = None
    ) -> Dict[str, Any]:
        """
        发送 HTTP 请求（异步）

        需要 aiohttp 库，如果未安装则回退到同步请求。

        Args:
            url: 请求 URL
            method: 请求方法
            data: 请求数据
            headers: 请求头

        Returns:
            响应数据
        """
        import json
        import logging

        try:
            import aiohttp
        except ImportError:
            logging.getLogger(__name__).warning(
                "aiohttp is not installed, falling back to synchronous OAuth2 request. "
                "Install aiohttp for async support: pip install aiohttp"
            )
            return self._request(url, method=method, data=data, headers=headers)

        req_headers = {
            'Accept': 'application/json',
            'User-Agent': 'Litefs-OAuth2/1.0',
        }
        if headers:
            req_headers.update(headers)

        try:
            async with aiohttp.ClientSession() as session:
                if method == 'GET':
                    if data:
                        url = f"{url}?{urllib.parse.urlencode(data)}"
                    async with session.get(url, headers=req_headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        return await resp.json(content_type=None)
                else:
                    async with session.request(
                        method, url, data=data, headers=req_headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        return await resp.json(content_type=None)
        except Exception as e:
            return {'error': str(e)}
    
    def generate_state(self) -> str:
        """生成随机状态参数"""
        return secrets.token_urlsafe(32)
    
    def generate_pkce_verifier(self) -> str:
        """生成 PKCE code_verifier"""
        return secrets.token_urlsafe(64)
    
    def generate_pkce_challenge(self, verifier: str, method: str = 'S256') -> str:
        """
        生成 PKCE code_challenge
        
        Args:
            verifier: code_verifier
            method: 挑战方法 ('S256' 或 'plain')
            
        Returns:
            code_challenge
        """
        if method == 'S256':
            digest = hashlib.sha256(verifier.encode('utf-8')).digest()
            return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')
        return verifier


class GitHubProvider(OAuth2Provider):
    """GitHub OAuth2 提供商"""
    
    name = 'github'
    authorize_url = 'https://github.com/login/oauth/authorize'
    access_token_url = 'https://github.com/login/oauth/access_token'
    userinfo_url = 'https://api.github.com/user'
    scope = 'user:email'
    
    def get_access_token(
        self,
        code: str,
        redirect_uri: str = None
    ) -> Dict[str, Any]:
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri or self.redirect_uri,
        }
        
        result = self._request(
            self.access_token_url,
            method='POST',
            data=data,
            headers={'Accept': 'application/json'}
        )
        
        if 'error' in result:
            return result
        
        return result
    
    def get_user_info(self, access_token: str) -> OAuth2UserInfo:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json',
        }
        
        user_data = self._request(self.userinfo_url, headers=headers)
        
        if 'error' in user_data:
            return None
        
        emails = self._request(
            'https://api.github.com/user/emails',
            headers=headers
        )
        
        primary_email = None
        if isinstance(emails, list):
            for email_info in emails:
                if email_info.get('primary') and email_info.get('verified'):
                    primary_email = email_info.get('email')
                    break
        
        return OAuth2UserInfo(
            provider=self.name,
            provider_user_id=str(user_data.get('id', '')),
            username=user_data.get('login', ''),
            email=primary_email or user_data.get('email'),
            name=user_data.get('name') or user_data.get('login'),
            avatar_url=user_data.get('avatar_url'),
            raw_data=user_data,
        )


class GoogleProvider(OAuth2Provider):
    """Google OAuth2 提供商"""
    
    name = 'google'
    authorize_url = 'https://accounts.google.com/o/oauth2/v2/auth'
    access_token_url = 'https://oauth2.googleapis.com/token'
    userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    scope = 'openid email profile'
    
    def get_access_token(
        self,
        code: str,
        redirect_uri: str = None
    ) -> Dict[str, Any]:
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'grant_type': 'authorization_code',
        }
        
        result = self._request(
            self.access_token_url,
            method='POST',
            data=data
        )
        
        return result
    
    def get_user_info(self, access_token: str) -> OAuth2UserInfo:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }
        
        user_data = self._request(self.userinfo_url, headers=headers)
        
        if 'error' in user_data:
            return None
        
        return OAuth2UserInfo(
            provider=self.name,
            provider_user_id=str(user_data.get('sub', '')),
            username=user_data.get('email', '').split('@')[0],
            email=user_data.get('email'),
            name=user_data.get('name'),
            avatar_url=user_data.get('picture'),
            raw_data=user_data,
        )


class WeChatProvider(OAuth2Provider):
    """微信 OAuth2 提供商"""
    
    name = 'wechat'
    authorize_url = 'https://open.weixin.qq.com/connect/qrconnect'
    access_token_url = 'https://api.weixin.qq.com/sns/oauth2/access_token'
    userinfo_url = 'https://api.weixin.qq.com/sns/userinfo'
    scope = 'snsapi_login'
    
    def get_authorize_url(
        self,
        state: str,
        redirect_uri: str = None,
        **kwargs
    ) -> str:
        params = {
            'appid': self.client_id,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'response_type': 'code',
            'scope': self.scope,
            'state': state,
        }
        
        return f"{self.authorize_url}?{urllib.parse.urlencode(params)}#wechat_redirect"
    
    def get_access_token(
        self,
        code: str,
        redirect_uri: str = None
    ) -> Dict[str, Any]:
        params = {
            'appid': self.client_id,
            'secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
        }
        
        url = f"{self.access_token_url}?{urllib.parse.urlencode(params)}"
        result = self._request(url)
        
        return result
    
    def get_user_info(self, access_token: str, openid: str = None) -> OAuth2UserInfo:
        if not openid:
            return None
        
        params = {
            'access_token': access_token,
            'openid': openid,
        }
        
        url = f"{self.userinfo_url}?{urllib.parse.urlencode(params)}"
        user_data = self._request(url)
        
        if 'errcode' in user_data:
            return None
        
        return OAuth2UserInfo(
            provider=self.name,
            provider_user_id=str(user_data.get('unionid') or user_data.get('openid', '')),
            username=user_data.get('nickname', ''),
            name=user_data.get('nickname'),
            avatar_url=user_data.get('headimgurl'),
            raw_data=user_data,
        )


class WeComProvider(OAuth2Provider):
    """企业微信 OAuth2 提供商"""
    
    name = 'wecom'
    authorize_url = 'https://open.work.weixin.qq.com/wwopen/sso/qrConnect'
    access_token_url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken'
    userinfo_url = 'https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo'
    scope = 'snsapi_base'
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        agent_id: str = '',
        redirect_uri: str = '',
        **kwargs
    ):
        super().__init__(client_id, client_secret, redirect_uri, **kwargs)
        self.agent_id = agent_id
    
    def get_authorize_url(
        self,
        state: str,
        redirect_uri: str = None,
        **kwargs
    ) -> str:
        params = {
            'appid': self.client_id,
            'agentid': self.agent_id,
            'redirect_uri': redirect_uri or self.redirect_uri,
            'response_type': 'code',
            'scope': self.scope,
            'state': state,
        }
        
        return f"{self.authorize_url}?{urllib.parse.urlencode(params)}"
    
    def get_access_token(
        self,
        code: str,
        redirect_uri: str = None
    ) -> Dict[str, Any]:
        params = {
            'corpid': self.client_id,
            'corpsecret': self.client_secret,
        }
        
        url = f"{self.access_token_url}?{urllib.parse.urlencode(params)}"
        result = self._request(url)
        
        if 'errcode' in result and result['errcode'] != 0:
            return result
        
        return result
    
    def get_user_info(self, access_token: str, code: str = None) -> OAuth2UserInfo:
        if not code:
            return None
        
        params = {
            'access_token': access_token,
            'code': code,
        }
        
        url = f"{self.userinfo_url}?{urllib.parse.urlencode(params)}"
        user_data = self._request(url)
        
        if 'errcode' in user_data and user_data['errcode'] != 0:
            return None
        
        return OAuth2UserInfo(
            provider=self.name,
            provider_user_id=str(user_data.get('UserId', '')),
            username=user_data.get('UserId', ''),
            name=user_data.get('name'),
            raw_data=user_data,
        )


PROVIDERS = {
    'github': GitHubProvider,
    'google': GoogleProvider,
    'wechat': WeChatProvider,
    'wecom': WeComProvider,
}


def get_provider(name: str) -> Optional[type]:
    """获取提供商类"""
    return PROVIDERS.get(name.lower())
