#!/usr/bin/env python
# coding: utf-8

"""
OpenAPI 规范生成器
"""

import inspect
from typing import Any, Dict, List, Optional, Tuple, Type

# 推断为 JSON requestBody 的保留参数名
_BODY_PARAM_NAMES = ('data', 'body', 'payload')


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

        # 基于 handler 签名的渐进式推断（query 参数与 requestBody）
        sig_params = self._infer_signature_parameters(route, doc_info)

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

            parameters = self._extract_parameters(route, doc_info, sig_params[0])
            if parameters:
                operation['parameters'] = parameters

            request_body = doc_info.get('request_body')
            if not request_body:
                request_body = sig_params[1]
            if request_body:
                operation['requestBody'] = request_body

            security = doc_info.get('security')
            if security:
                operation['security'] = security

            if doc_info.get('deprecated', False):
                operation['deprecated'] = True

            result[method_lower] = operation

        return result

    def _get_handler_annotations(self, handler) -> Dict[str, Any]:
        """
        提取 handler 签名中的参数注解

        Args:
            handler: 处理函数

        Returns:
            参数名到注解的映射（无法内省时返回空字典）
        """
        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            return {}
        return {
            name: param.annotation
            for name, param in signature.parameters.items()
            if param.annotation is not inspect.Parameter.empty
        }

    def _infer_signature_parameters(
        self, route, doc_info: Dict,
    ) -> Tuple[List[Dict], Optional[Dict]]:
        """
        基于 handler 签名渐进式推断 query 参数与 requestBody

        框架约定 handler 首参数为 request 对象（方法绑定后 self 已被
        排除），其余签名参数按以下规则推断：

        - 路径参数与显式 ``@openapi.doc`` 参数跳过（文档优先，不重复）
        - ``data`` / ``body`` / ``payload`` 保留名参数推断为 JSON requestBody
        - 其余参数推断为 query 参数（有默认值非必填，无默认值必填）

        Args:
            route: 路由对象
            doc_info: 显式文档信息

        Returns:
            (query 参数列表, requestBody 字典或 None)
        """
        handler = route.handler
        try:
            signature = inspect.signature(handler)
        except (TypeError, ValueError):
            return [], None

        params = list(signature.parameters.values())
        # 框架约定：首参数为 request 对象
        candidates = params[1:] if params else []

        known_names = set(route.param_names)
        for param in doc_info.get('parameters', []):
            known_names.add(param.get('name'))

        query_params: List[Dict] = []
        request_body: Optional[Dict] = None

        for param in candidates:
            if param.kind in (inspect.Parameter.VAR_POSITIONAL,
                              inspect.Parameter.VAR_KEYWORD):
                continue
            if param.name in known_names:
                continue

            annotation = param.annotation
            annotated = annotation is not inspect.Parameter.empty

            # 保留名参数推断为 JSON requestBody
            if param.name in _BODY_PARAM_NAMES:
                if request_body is None:
                    schema = (
                        self._get_type_schema(annotation)
                        if annotated else {'type': 'object'}
                    )
                    request_body = {
                        'required': param.default is inspect.Parameter.empty,
                        'content': {'application/json': {'schema': schema}},
                    }
                continue

            schema = self._get_type_schema(annotation) if annotated \
                else {'type': 'string'}
            query_params.append({
                'name': param.name,
                'in': 'query',
                'required': param.default is inspect.Parameter.empty,
                'schema': schema,
                'description': f'{param.name} 参数',
            })

        return query_params, request_body

    def _extract_parameters(
        self,
        route,
        doc_info: Dict,
        sig_query_params: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        提取参数

        路径参数类型优先取 handler 签名注解（缺省为 string），
        显式文档参数次之，签名推断的 query 参数兜底。

        Args:
            route: 路由对象
            doc_info: 文档信息
            sig_query_params: 签名推断的 query 参数列表

        Returns:
            参数列表
        """
        parameters = []

        annotations = self._get_handler_annotations(route.handler)
        for param_name in route.param_names:
            annotation = annotations.get(param_name, inspect.Parameter.empty)
            if annotation is not inspect.Parameter.empty:
                schema = self._get_type_schema(annotation)
            else:
                schema = {'type': 'string'}
            parameters.append({
                'name': param_name,
                'in': 'path',
                'required': True,
                'schema': schema,
                'description': f'{param_name} 参数',
            })

        doc_params = doc_info.get('parameters', [])
        for param in doc_params:
            parameters.append(param)

        if sig_query_params:
            parameters.extend(sig_query_params)

        return parameters
