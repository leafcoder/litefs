#!/usr/bin/env python
# coding: utf-8

"""
认证授权模块

提供完整的用户认证和授权解决方案：
- JWT Token 认证
- OAuth2 社交登录
- 用户注册/登录
- 密码加密
- 权限控制
- Token 刷新
- 认证中间件

使用示例：
    from litefs.auth import Auth, login_required, role_required
    
    auth = Auth(app, secret_key='your-secret-key')
    
    @route('/protected')
    @login_required
    def protected(request):
        return {'user': request.user.username}
    
    @route('/admin')
    @role_required('admin')
    def admin_only(request):
        return {'message': 'Admin access'}

OAuth2 示例：
    from litefs.auth import OAuth2
    
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
        return {'user': user_info.to_dict()}
"""

from .jwt import JWTManager, create_token, decode_token
from .password import hash_password, verify_password
from .middleware import AuthMiddleware, login_required, role_required
from .decorators import permission_required, current_user
from .models import User, Role, Permission, init_default_roles_and_permissions
from .oauth2 import OAuth2, OAuth2State, create_oauth2_blueprint
from .providers import (
    OAuth2Provider,
    OAuth2UserInfo,
    GitHubProvider,
    GoogleProvider,
    WeChatProvider,
    WeComProvider,
    get_provider,
)

__all__ = [
    'Auth',
    'JWTManager',
    'create_token',
    'decode_token',
    'hash_password',
    'verify_password',
    'AuthMiddleware',
    'login_required',
    'role_required',
    'permission_required',
    'current_user',
    'User',
    'Role',
    'Permission',
    'init_default_roles_and_permissions',
    'OAuth2',
    'OAuth2State',
    'OAuth2Provider',
    'OAuth2UserInfo',
    'GitHubProvider',
    'GoogleProvider',
    'WeChatProvider',
    'WeComProvider',
    'get_provider',
    'create_oauth2_blueprint',
]


class Auth:
    """
    认证授权管理器
    
    提供完整的用户认证和授权功能。
    """
    
    def __init__(
        self,
        app=None,
        secret_key: str = None,
        algorithm: str = 'HS256',
        access_token_expires: int = 3600,
        refresh_token_expires: int = 604800,
        token_location: str = 'header',
        token_name: str = 'Authorization',
        token_prefix: str = 'Bearer',
    ):
        """
        初始化认证管理器
        
        Args:
            app: Litefs 应用实例
            secret_key: JWT 密钥
            algorithm: JWT 算法
            access_token_expires: Access Token 过期时间（秒）
            refresh_token_expires: Refresh Token 过期时间（秒）
            token_location: Token 位置 ('header', 'cookie', 'query')
            token_name: Token 名称
            token_prefix: Token 前缀
        """
        self.secret_key = secret_key or 'change-me-in-production'
        self.algorithm = algorithm
        self.access_token_expires = access_token_expires
        self.refresh_token_expires = refresh_token_expires
        self.token_location = token_location
        self.token_name = token_name
        self.token_prefix = token_prefix
        
        self._jwt = JWTManager(
            secret_key=self.secret_key,
            algorithm=self.algorithm,
            access_token_expires=self.access_token_expires,
            refresh_token_expires=self.refresh_token_expires,
        )
        
        self._middleware = AuthMiddleware(
            jwt_manager=self._jwt,
            token_location=token_location,
            token_name=token_name,
            token_prefix=token_prefix,
        )
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """
        初始化应用
        
        Args:
            app: Litefs 应用实例
        """
        app.add_middleware(self._middleware.__class__, jwt_manager=self._jwt)
        
        app.add_post('/auth/login', self.login_handler, name='auth_login')
        app.add_post('/auth/register', self.register_handler, name='auth_register')
        app.add_post('/auth/refresh', self.refresh_handler, name='auth_refresh')
        app.add_post('/auth/logout', self.logout_handler, name='auth_logout')
    
    def login_handler(self, request):
        """登录处理"""
        data = request.json or {}
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {'error': '用户名和密码不能为空'}, 400
        
        user = User.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            return {'error': '用户名或密码错误'}, 401
        
        access_token = self._jwt.create_access_token({'sub': user.id, 'username': user.username})
        refresh_token = self._jwt.create_refresh_token({'sub': user.id})
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.access_token_expires,
        }
    
    def register_handler(self, request):
        """注册处理"""
        data = request.json or {}
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        
        if not username or not password:
            return {'error': '用户名和密码不能为空'}, 400
        
        if User.get_by_username(username):
            return {'error': '用户名已存在'}, 400
        
        password_hash = hash_password(password)
        user = User.create(
            username=username,
            password_hash=password_hash,
            email=email,
        )
        
        return {'message': '注册成功', 'user_id': user.id}, 201
    
    def refresh_handler(self, request):
        """Token 刷新处理"""
        data = request.json or {}
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return {'error': 'Refresh Token 不能为空'}, 400
        
        payload = self._jwt.decode_token(refresh_token)
        if not payload or payload.get('type') != 'refresh':
            return {'error': '无效的 Refresh Token'}, 401
        
        user_id = payload.get('sub')
        user = User.get_by_id(user_id)
        if not user:
            return {'error': '用户不存在'}, 401
        
        access_token = self._jwt.create_access_token({'sub': user.id, 'username': user.username})
        
        return {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': self.access_token_expires,
        }
    
    def logout_handler(self, request):
        """登出处理"""
        return {'message': '登出成功'}
    
    def create_user(self, username: str, password: str, **kwargs):
        """
        创建用户
        
        Args:
            username: 用户名
            password: 密码
            **kwargs: 其他属性
            
        Returns:
            User 实例
        """
        password_hash = hash_password(password)
        return User.create(username=username, password_hash=password_hash, **kwargs)
    
    def authenticate(self, username: str, password: str):
        """
        验证用户
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            User 实例或 None
        """
        user = User.get_by_username(username)
        if user and verify_password(password, user.password_hash):
            return user
        return None
