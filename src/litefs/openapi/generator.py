#!/usr/bin/env python
# coding: utf-8

"""
OpenAPI 规范生成器
"""

import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Type


class OpenAPIGenerator:
    """OpenAPI 3.0 规范生成器"""
    
    def __init__(
        self,
        title: str = 'Litefs API',
        version: str = '1.0.0',
        description: str = '',
    ):
        """
        初始化生成器
        
        Args:
            title: API 标题
            version: API 版本
            description: API 描述
        """
        self.title = title
        self.version = version
        self.description = description
        
        self._tags: List[Dict] = []
        self._servers: List[Dict] = []
        self._security_schemes: Dict[str, Dict] = {}
        self._schemas: Dict[str, Dict] = {}
    
    def add_tag(self, name: str, description: str = ''):
        """添加标签"""
        self._tags.append({'name': name, 'description': description})
    
    def add_server(self, url: str, description: str = ''):
        """添加服务器"""
        self._servers.append({'url': url, 'description': description})
    
    def add_security_scheme(self, name: str, scheme: dict):
        """添加安全方案"""
        self._security_schemes[name] = scheme
    
    def add_schema(self, name: str, schema_class: Type):
        """添加 Schema"""
        properties = {}
        required = []
        
        if hasattr(schema_class, '__annotations__'):
            for field_name, field_type in schema_class.__annotations__.items():
                properties[field_name] = self._get_type_schema(field_type)
                
                default = getattr(schema_class, field_name, inspect.Parameter.empty)
                if default is inspect.Parameter.empty:
                    required.append(field_name)
        
        self._schemas[name] = {
            'type': 'object',
            'properties': properties,
        }
        
        if required:
            self._schemas[name]['required'] = required
    
    def _get_type_schema(self, python_type: Type) -> Dict:
        """将 Python 类型转换为 OpenAPI Schema"""
        type_map = {
            str: {'type': 'string'},
            int: {'type': 'integer'},
            float: {'type': 'number'},
            bool: {'type': 'boolean'},
            list: {'type': 'array', 'items': {'type': 'string'}},
            dict: {'type': 'object'},
        }
        
        if python_type in type_map:
            return type_map[python_type]
        
        origin = getattr(python_type, '__origin__', None)
        if origin is list:
            args = getattr(python_type, '__args__', (str,))
            return {
                'type': 'array',
                'items': self._get_type_schema(args[0]) if args else {'type': 'string'}
            }
        elif origin is dict:
            return {'type': 'object'}
        
        return {'type': 'string'}
    
    def generate(self, router) -> Dict[str, Any]:
        """
        生成 OpenAPI 规范
        
        Args:
            router: 路由器实例
            
        Returns:
            OpenAPI 规范字典
        """
        spec = {
            'openapi': '3.0.0',
            'info': {
                'title': self.title,
                'version': self.version,
                'description': self.description,
            },
            'paths': {},
        }
        
        if self._servers:
            spec['servers'] = self._servers
        
        if self._tags:
            spec['tags'] = self._tags
        
        if self._security_schemes:
            spec['components'] = {
                'securitySchemes': self._security_schemes,
                'schemas': self._schemas,
            }
        elif self._schemas:
            spec['components'] = {'schemas': self._schemas}
        
        for route in router.routes:
            path_item = self._generate_path_item(route)
            if path_item:
                path = route.path
                
                for param_name in route.param_names:
                    path = path.replace(f'{{{param_name}}}', f'{{{param_name}}}')
                
                if path not in spec['paths']:
                    spec['paths'][path] = {}
                
                for method in route.methods:
                    method_lower = method.lower()
                    spec['paths'][path][method_lower] = path_item.get(method_lower, {})
        
        return spec
    
    def _generate_path_item(self, route) -> Dict[str, Any]:
        """
        生成路径项
        
        Args:
            route: 路由对象
            
        Returns:
            路径项字典
        """
        handler = route.handler
        doc_info = getattr(handler, '_openapi_doc', {})
        
        result = {}
        
        for method in route.methods:
            method_lower = method.lower()
            
            operation = {
                'summary': doc_info.get('summary', handler.__name__),
                'description': doc_info.get('description', ''),
                'operationId': f'{method_lower}_{route.name or handler.__name__}',
                'responses': {
                    '200': doc_info.get('response', {
                        'description': '成功响应',
                        'content': {
                            'application/json': {
                                'schema': {'type': 'object'}
                            }
                        }
                    })
                },
            }
            
            tags = doc_info.get('tags', [])
            if tags:
                operation['tags'] = tags
            
            parameters = self._extract_parameters(route, doc_info)
            if parameters:
                operation['parameters'] = parameters
            
            request_body = doc_info.get('request_body')
            if request_body:
                operation['requestBody'] = request_body
            
            security = doc_info.get('security')
            if security:
                operation['security'] = security
            
            if doc_info.get('deprecated', False):
                operation['deprecated'] = True
            
            result[method_lower] = operation
        
        return result
    
    def _extract_parameters(self, route, doc_info: Dict) -> List[Dict]:
        """
        提取参数
        
        Args:
            route: 路由对象
            doc_info: 文档信息
            
        Returns:
            参数列表
        """
        parameters = []
        
        for param_name in route.param_names:
            parameters.append({
                'name': param_name,
                'in': 'path',
                'required': True,
                'schema': {'type': 'string'},
                'description': f'{param_name} 参数',
            })
        
        doc_params = doc_info.get('parameters', [])
        for param in doc_params:
            parameters.append(param)
        
        return parameters
