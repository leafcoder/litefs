#!/usr/bin/env python
# coding: utf-8

"""
OpenAPI/Swagger 文档自动生成模块

提供自动从路由生成 OpenAPI 3.0 规范的功能，并集成 Swagger UI 界面。

特性：
- 自动从路由提取 API 信息
- 支持手动添加详细的 API 文档
- OpenAPI 3.0 规范生成
- Swagger UI 界面
- 支持认证配置
- 支持请求/响应模型定义

使用示例：
    from litefs.openapi import OpenAPI
    
    openapi = OpenAPI(app, title='My API', version='1.0.0')
    
    @route('/users')
    @openapi.doc(
        summary='获取用户列表',
        response={'description': '用户列表'}
    )
    def get_users(request):
        return {'users': []}
    
    # 访问文档
    # http://localhost:8080/docs
"""

from .generator import OpenAPIGenerator
from .ui import SwaggerUI

__all__ = ['OpenAPI', 'OpenAPIGenerator', 'SwaggerUI']


class OpenAPI:
    """
    OpenAPI 文档生成器
    
    提供自动从路由生成 OpenAPI 规范的功能。
    """
    
    def __init__(
        self,
        app=None,
        title: str = 'Litefs API',
        version: str = '1.0.0',
        description: str = '',
        docs_url: str = '/docs',
        openapi_url: str = '/openapi.json',
    ):
        """
        初始化 OpenAPI 文档生成器
        
        Args:
            app: Litefs 应用实例
            title: API 标题
            version: API 版本
            description: API 描述
            docs_url: Swagger UI 路径
            openapi_url: OpenAPI JSON 路径
        """
        self.app = app
        self.title = title
        self.version = version
        self.description = description
        self.docs_url = docs_url
        self.openapi_url = openapi_url
        
        self._generator = OpenAPIGenerator(title, version, description)
        self._swagger_ui = SwaggerUI(docs_url, openapi_url)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """
        初始化应用
        
        Args:
            app: Litefs 应用实例
        """
        self.app = app
        
        def openapi_json(request):
            """OpenAPI JSON 规范"""
            spec = self._generator.generate(app.router)
            return spec
        
        def swagger_ui(request):
            """Swagger UI 界面"""
            return self._swagger_ui.render_html(self.openapi_url)
        
        app.add_get(self.openapi_url, openapi_json, name='openapi_json')
        app.add_get(self.docs_url, swagger_ui, name='swagger_ui')
    
    def doc(
        self,
        summary: str = '',
        description: str = '',
        tags: list = None,
        request_body: dict = None,
        response: dict = None,
        parameters: list = None,
        security: list = None,
        deprecated: bool = False,
    ):
        """
        API 文档装饰器
        
        Args:
            summary: API 摘要
            description: API 描述
            tags: 标签列表
            request_body: 请求体定义
            response: 响应定义
            parameters: 参数列表
            security: 安全配置
            deprecated: 是否已废弃
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            doc_info = {
                'summary': summary,
                'description': description,
                'tags': tags or [],
                'request_body': request_body,
                'response': response,
                'parameters': parameters or [],
                'security': security,
                'deprecated': deprecated,
            }
            func._openapi_doc = doc_info
            return func
        return decorator
    
    def add_tag(self, name: str, description: str = ''):
        """
        添加标签
        
        Args:
            name: 标签名称
            description: 标签描述
        """
        self._generator.add_tag(name, description)
    
    def add_security_scheme(self, name: str, scheme: dict):
        """
        添加安全方案
        
        Args:
            name: 安全方案名称
            scheme: 安全方案配置
        """
        self._generator.add_security_scheme(name, scheme)
    
    def add_server(self, url: str, description: str = ''):
        """
        添加服务器
        
        Args:
            url: 服务器 URL
            description: 服务器描述
        """
        self._generator.add_server(url, description)
    
    def schema(self, name: str):
        """
        Schema 装饰器
        
        用于定义请求/响应模型
        
        Args:
            name: Schema 名称
            
        Returns:
            装饰器函数
        """
        def decorator(cls):
            self._generator.add_schema(name, cls)
            return cls
        return decorator
