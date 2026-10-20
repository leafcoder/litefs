#!/usr/bin/env python
# coding: utf-8

"""
路由注册 Mixin

提供装饰器风格与方法链风格的路由注册、静态文件路由、
WebSocket 入口、模块路由批量注册与 URL 反向解析。
"""

import importlib
from typing import TYPE_CHECKING, Callable, Optional

from ..routing import Router

if TYPE_CHECKING:
    from ..websocket import WebSocket


class RoutingMixin:
    """路由注册与 URL 生成能力

    依赖宿主 ``Litefs`` 装配时提供的属性，
    以下声明仅供类型检查使用，运行时无开销。
    """

    #: 由 Litefs.__init__ 装配的宿主属性
    router: Router
    port: int
    _websocket_instance: Optional["WebSocket"]

    def add_route(self, path, methods=None, handler=None, name=None):
        """
        添加路由

        Args:
            path: 路由路径
            methods: HTTP 方法列表，默认 ['GET']
            handler: 处理函数
            name: 路由名称
        """
        if methods is None:
            methods = ['GET']

        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_route(path, methods, func, name)
                return func
            return decorator
        else:
            self.router.add_route(path, methods, handler, name)
            return self

    def add_get(self, path, handler=None, name=None):
        """
        添加 GET 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_get(path, func, name)
                return func
            return decorator
        else:
            self.router.add_get(path, handler, name)
            return self

    def add_post(self, path, handler=None, name=None):
        """
        添加 POST 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_post(path, func, name)
                return func
            return decorator
        else:
            self.router.add_post(path, handler, name)
            return self

    def add_put(self, path, handler=None, name=None):
        """
        添加 PUT 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_put(path, func, name)
                return func
            return decorator
        else:
            self.router.add_put(path, handler, name)
            return self

    def add_delete(self, path, handler=None, name=None):
        """
        添加 DELETE 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_delete(path, func, name)
                return func
            return decorator
        else:
            self.router.add_delete(path, handler, name)
            return self

    def add_patch(self, path, handler=None, name=None):
        """
        添加 PATCH 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_patch(path, func, name)
                return func
            return decorator
        else:
            self.router.add_patch(path, handler, name)
            return self

    def add_options(self, path, handler=None, name=None):
        """
        添加 OPTIONS 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_options(path, func, name)
                return func
            return decorator
        else:
            self.router.add_options(path, handler, name)
            return self

    def add_head(self, path, handler=None, name=None):
        """
        添加 HEAD 方法路由

        Args:
            path: 路由路径
            handler: 处理函数
            name: 路由名称
        """
        # 支持装饰器风格调用
        if handler is None:
            def decorator(func):
                self.router.add_head(path, func, name)
                return func
            return decorator
        else:
            self.router.add_head(path, handler, name)
            return self

    def add_static(self, prefix: str, directory: str,
                   name: Optional[str] = None):
        """
        添加静态文件路由

        Args:
            prefix: URL 前缀，如 '/static'
            directory: 静态文件目录路径
            name: 路由名称
        """
        self.router.add_static(prefix, directory, name)
        return self

    def websocket(self, path: str = '/ws', auth_required: bool = False,
                  auth_handler: Optional[Callable] = None,
                  port: Optional[int] = None):
        """
        WebSocket 路由装饰器

        Args:
            path: WebSocket 路径
            auth_required: 是否需要认证
            auth_handler: 认证处理函数
            port: WebSocket 服务器端口（默认 HTTP 端口 + 1）

        Returns:
            装饰器函数

        使用示例:
            @app.websocket('/ws')
            def ws_handler(ws):
                ws.send('欢迎连接!')
                for message in ws:
                    ws.broadcast(message)
        """
        from ..websocket import WebSocket

        ws = getattr(self, '_websocket_instance', None)
        if ws is None:
            ws_port = port or (self.port + 1)
            ws = WebSocket(
                app=self,
                path=path,
                port=ws_port,
                auth_required=auth_required,
                auth_handler=auth_handler,
            )
            self._websocket_instance = ws

        return ws.handler(path)

    def get_websocket(self) -> Optional['WebSocket']:
        """
        获取 WebSocket 实例

        Returns:
            WebSocket 实例或 None
        """
        return getattr(self, '_websocket_instance', None)

    def register_routes(self, module):
        """
        注册模块中的路由

        Args:
            module: 包含路由装饰器的模块对象或模块名称
        """
        # 如果是模块名称字符串，导入模块
        if isinstance(module, str):
            module = importlib.import_module(module)

        for name in dir(module):
            obj = getattr(module, name)
            # 确保对象是可调用的，并且有 _routes 属性
            if callable(obj) and hasattr(obj, '_routes'):
                try:
                    # 尝试遍历 _routes
                    for route_info in obj._routes:
                        self.add_route(
                            path=route_info['path'],
                            methods=route_info['methods'],
                            handler=obj,
                            name=route_info['name']
                        )
                except TypeError:
                    # 如果 _routes 不是可迭代的，跳过
                    pass
        return self

    def url_for(self, name, **kwargs):
        """
        根据路由名称生成 URL

        Args:
            name: 路由名称
            **kwargs: 路由参数

        Returns:
            生成的 URL
        """
        return self.router.url_for(name, **kwargs)
