#!/usr/bin/env python
# coding: utf-8

import os
import re
from mimetypes import guess_type
from typing import Any, Callable, Dict, List, Optional, Pattern, Tuple, Union

from ..security import secure_path_join
from .radix_tree import RadixTree


class Route:
    """
    路由类，表示一个路由规则
    """
    
    def __init__(self, path: str, methods: List[str], handler: Callable, name: Optional[str] = None):
        """
        初始化路由
        
        Args:
            path: 路由路径，支持参数和正则表达式
            methods: HTTP 方法列表
            handler: 处理函数
            name: 路由名称，用于反向解析
        """
        self.path = path
        self.methods = [method.upper() for method in methods]
        self.handler = handler
        self.name = name
        self.pattern, self.param_names = self._compile_path(path)
    
    def _compile_path(self, path: str) -> Tuple[Pattern, List[str]]:
        """
        编译路径为正则表达式
        
        Args:
            path: 路由路径
            
        Returns:
            编译后的正则表达式和参数名称列表
        """
        param_names = []
        pattern = path
        
        # 处理路径参数，如 /user/{id} 或 /static/{file_path:path}
        param_pattern = re.compile(r'\{(\w+)(?::(\w+))?\}')
        matches = param_pattern.findall(pattern)
        
        for param_name, param_type in matches:
            param_names.append(param_name)
            if param_type == 'path':
                # 匹配多个路径段（含斜杠）
                pattern = pattern.replace(f'{{{param_name}:path}}', f'(?P<{param_name}>.+)')
            else:
                # 匹配单个路径段（不含斜杠）
                pattern = pattern.replace(f'{{{param_name}}}', f'(?P<{param_name}>[^/]+)')
        
        # 确保路径完全匹配
        pattern = f'^{pattern}$'
        return re.compile(pattern), param_names
    
    def match(self, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        匹配路径和方法
        
        Args:
            path: 请求路径
            method: HTTP 方法
            
        Returns:
            匹配成功返回参数字典，失败返回 None
        """
        if method.upper() not in self.methods:
            return None
        
        match = self.pattern.match(path)
        if match:
            return match.groupdict()
        
        return None


class Router:
    """
    路由管理器
    """
    
    def __init__(self):
        """
        初始化路由管理器
        """
        from .radix_tree import RadixTree
        
        self.routes: List[Route] = []
        self.named_routes: Dict[str, Route] = {}
        self._route_tree = RadixTree()
        self._tree_dirty = True
    
    def add_route(self, path: str, methods: List[str], handler: Callable, name: Optional[str] = None):
        """
        添加路由
        
        Args:
            path: 路由路径
            methods: HTTP 方法列表
            handler: 处理函数
            name: 路由名称
        """
        route = Route(path, methods, handler, name)
        self.routes.append(route)
        
        if name:
            self.named_routes[name] = route
        
        # 标记路由树需要重建
        self._tree_dirty = True
    
    def add_get(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 GET 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['GET'], handler, name)
    
    def add_post(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 POST 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['POST'], handler, name)
    
    def add_put(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 PUT 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['PUT'], handler, name)
    
    def add_delete(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 DELETE 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['DELETE'], handler, name)
    
    def add_patch(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 PATCH 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['PATCH'], handler, name)
    
    def add_options(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 OPTIONS 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['OPTIONS'], handler, name)
    
    def add_head(self, path: str, handler: Callable, name: Optional[str] = None):
        """
        添加 HEAD 方法路由
        
        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        self.add_route(path, ['HEAD'], handler, name)
    
    def add_static(self, prefix: str, directory: str, name: Optional[str] = None):
        """
        添加静态文件路由
        
        Args:
            prefix: URL 前缀，如 '/static'
            directory: 静态文件目录路径
            name: 路由名称
        """
        self.static_prefix = prefix
        self.static_directory = directory
        
        def static_handler(handler_self, file_path: str = ''):
            """
            静态文件处理函数
            
            Args:
                handler_self: 请求处理器实例
                file_path: 文件路径（相对于静态目录）
            """
            # 使用安全的路径拼接
            full_path = secure_path_join(directory, file_path.lstrip('/'))
            
            # 检查路径是否安全
            if full_path is None:
                handler_self.start_response(403, [('Content-Type', 'text/plain; charset=utf-8')])
                return 'Forbidden'
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                handler_self.start_response(404, [('Content-Type', 'text/plain; charset=utf-8')])
                return 'Not Found'
            
            # 检查是否为文件
            if not os.path.isfile(full_path):
                handler_self.start_response(403, [('Content-Type', 'text/plain; charset=utf-8')])
                return 'Forbidden'
            
            # 获取文件内容
            try:
                with open(full_path, 'rb') as f:
                    content = f.read()
                
                # 获取 MIME 类型
                mime_type, encoding = guess_type(full_path)
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                # 设置响应头
                handler_self.start_response(200, [
                    ('Content-Type', f'{mime_type}; charset=utf-8'),
                    ('Content-Length', str(len(content)))
                ])
                
                return content
            except Exception as e:
                handler_self.start_response(500, [('Content-Type', 'text/plain; charset=utf-8')])
                return f'Internal Server Error: {str(e)}'
        
        # 添加路由，支持路径参数
        self.add_route(f'{prefix}/{{file_path:path}}', ['GET', 'HEAD'], static_handler, name)
    
    def match(self, path: str, method: str) -> Optional[Tuple[Callable, Dict[str, Any]]]:
        """
        匹配路由
        
        Args:
            path: 请求路径
            method: HTTP 方法
            
        Returns:
            匹配成功返回 (handler, params)，失败返回 None
        """
        # 如果路由树过期，重新构建
        if self._tree_dirty:
            self._build_route_tree()
        
        # 尝试直接匹配（快速路径）
        result = self._route_tree.find(path, method)
        if result is not None:
            route, params = result
            return route.handler, params
        
        # 尝试不带末尾斜杠的匹配
        if path != '/' and path.endswith('/'):
            result = self._route_tree.find(path[:-1], method)
            if result is not None:
                route, params = result
                return route.handler, params
        
        # 尝试带末尾斜杠的匹配
        elif path != '/' and not path.endswith('/'):
            result = self._route_tree.find(path + '/', method)
            if result is not None:
                route, params = result
                return route.handler, params
        
        return None
    
    def _build_route_tree(self):
        """
        构建路由树
        
        将所有路由插入到 Radix Tree 中
        """
        self._route_tree = RadixTree()
        
        for route in self.routes:
            self._route_tree.insert(route.path, route)
            
            if route.name:
                self.named_routes[route.name] = route
                self._route_tree.add_named_route(route.name, route)
        
        self._tree_dirty = False
    
    def url_for(self, name: str, **kwargs) -> str:
        """
        根据路由名称生成 URL
        
        Args:
            name: 路由名称
            **kwargs: 路由参数
            
        Returns:
            生成的 URL
        """
        route = self.named_routes.get(name)
        if not route:
            raise ValueError(f"Route with name '{name}' not found")
        
        url = route.path
        for param_name, value in kwargs.items():
            url = url.replace(f'{{{param_name}}}', str(value))
        
        return url


def route(path: str, methods: List[str] = None, name: Optional[str] = None):
    """
    路由装饰器
    
    Args:
        path: 路由路径
        methods: HTTP 方法列表，默认 ['GET']
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    if methods is None:
        methods = ['GET']
    
    def decorator(handler: Callable) -> Callable:
        # 存储路由信息到处理函数
        if not hasattr(handler, '_routes'):
            handler._routes = []
        
        handler._routes.append({
            'path': path,
            'methods': methods,
            'name': name
        })
        
        return handler
    
    return decorator


def get(path: str, name: Optional[str] = None):
    """
    GET 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['GET'], name)


def post(path: str, name: Optional[str] = None):
    """
    POST 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['POST'], name)


def put(path: str, name: Optional[str] = None):
    """
    PUT 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['PUT'], name)


def delete(path: str, name: Optional[str] = None):
    """
    DELETE 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['DELETE'], name)


def patch(path: str, name: Optional[str] = None):
    """
    PATCH 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['PATCH'], name)


def options(path: str, name: Optional[str] = None):
    """
    OPTIONS 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['OPTIONS'], name)


def head(path: str, name: Optional[str] = None):
    """
    HEAD 方法路由装饰器
    
    Args:
        path: 路由路径
        name: 路由名称
        
    Returns:
        装饰器函数
    """
    return route(path, ['HEAD'], name)
