#!/usr/bin/env python
# coding: utf-8

import asyncio
import inspect
from typing import Any, Callable, Optional


class Middleware:
    """
    中间件基类

    所有中间件都应该继承此类并实现 process_request 和/或 process_response 方法。
    
    支持同步和异步两种模式：
    - 同步模式：实现 process_request / process_response / process_exception
    - 异步模式：实现 async_process_request / async_process_response / async_process_exception
    
    异步方法优先级高于同步方法。在 ASGI 路径中，如果中间件实现了异步方法，
    将使用异步调用；否则回退到同步调用（通过 run_in_executor 避免阻塞事件循环）。
    """

    def __init__(self, app):
        """
        初始化中间件

        Args:
            app: Litefs 应用实例
        """
        self.app = app

    def process_request(self, request_handler):
        """
        处理请求，在请求到达业务逻辑之前执行（同步版本）

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应，中断后续处理
        """
        pass

    async def async_process_request(self, request_handler):
        """
        处理请求，在请求到达业务逻辑之前执行（异步版本）

        默认实现调用同步版本的 process_request。
        子类可以覆盖此方法来实现真正的异步逻辑。

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应，中断后续处理
        """
        return self.process_request(request_handler)

    def process_response(self, request_handler, response):
        """
        处理响应，在响应返回给客户端之前执行（同步版本）

        Args:
            request_handler: 请求处理器实例
            response: 响应数据

        Returns:
            修改后的响应数据
        """
        return response

    async def async_process_response(self, request_handler, response):
        """
        处理响应，在响应返回给客户端之前执行（异步版本）

        默认实现调用同步版本的 process_response。
        子类可以覆盖此方法来实现真正的异步逻辑。

        Args:
            request_handler: 请求处理器实例
            response: 响应数据

        Returns:
            修改后的响应数据
        """
        return self.process_response(request_handler, response)

    def process_exception(self, request_handler, exception):
        """
        处理异常（同步版本）

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
            其他值: 返回该值作为响应，不抛出异常
        """
        return None

    async def async_process_exception(self, request_handler, exception):
        """
        处理异常（异步版本）

        默认实现调用同步版本的 process_exception。
        子类可以覆盖此方法来实现真正的异步逻辑。

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
            其他值: 返回该值作为响应，不抛出异常
        """
        return self.process_exception(request_handler, exception)

    def _has_async_override(self, method_name: str) -> bool:
        """
        检查中间件是否覆盖了异步方法（而非仅使用默认的同步回退）

        Args:
            method_name: 异步方法名（如 'async_process_request'）

        Returns:
            如果子类自己实现了该异步方法，返回 True
        """
        method = getattr(self, method_name, None)
        if method is None:
            return False
        # 检查方法是否在当前类中定义（而非仅继承自基类）
        for cls in type(self).__mro__:
            if method_name in cls.__dict__:
                return cls is not Middleware
        return False


class MiddlewareManager:
    """
    中间件管理器

    负责管理所有中间件的注册、加载和执行。
    同时支持同步（WSGI）和异步（ASGI）调用路径。
    """

    def __init__(self):
        self._middlewares = []

    def add(self, middleware_class, **kwargs):
        """
        添加中间件

        Args:
            middleware_class: 中间件类
            **kwargs: 传递给中间件构造函数的参数

        Returns:
            self: 支持链式调用
        """
        self._middlewares.append((middleware_class, kwargs))
        return self

    def remove(self, middleware_class):
        """
        移除中间件

        Args:
            middleware_class: 中间件类
        """
        self._middlewares = [
            (cls, kwargs) for cls, kwargs in self._middlewares if cls != middleware_class
        ]

    def clear(self):
        """
        清空所有中间件
        """
        self._middlewares.clear()

    def get_middleware_instances(self, app):
        """
        获取所有中间件实例

        Args:
            app: Litefs 应用实例

        Returns:
            中间件实例列表
        """
        instances = []
        for middleware_class, kwargs in self._middlewares:
            instances.append(middleware_class(app, **kwargs))
        return instances

    # ==================== 同步调用路径（WSGI/Socket） ====================

    def process_request(self, request_handler):
        """
        按顺序执行所有中间件的 process_request 方法（同步）

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应
        """
        for middleware in request_handler._middlewares:
            result = middleware.process_request(request_handler)
            if result is not None:
                return result
        return None

    def process_response(self, request_handler, response):
        """
        按逆序执行所有中间件的 process_response 方法（同步）

        Args:
            request_handler: 请求处理器实例
            response: 响应数据

        Returns:
            处理后的响应数据
        """
        for middleware in reversed(request_handler._middlewares):
            response = middleware.process_response(request_handler, response)
        return response

    def process_exception(self, request_handler, exception):
        """
        按顺序执行所有中间件的 process_exception 方法（同步）

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
            其他值: 返回该值作为响应
        """
        for middleware in request_handler._middlewares:
            result = middleware.process_exception(request_handler, exception)
            if result is not None:
                return result
        return None

    # ==================== 异步调用路径（ASGI） ====================

    async def async_process_request(self, request_handler):
        """
        按顺序执行所有中间件的请求处理（异步）

        对于实现了 async_process_request 的中间件，使用 await 调用；
        对于仅有同步 process_request 的中间件，使用 run_in_executor
        避免阻塞事件循环。

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应
        """
        loop = asyncio.get_event_loop()
        for middleware in request_handler._middlewares:
            if middleware._has_async_override('async_process_request'):
                result = await middleware.async_process_request(request_handler)
            else:
                # 同步中间件放到线程池中执行，避免阻塞事件循环
                result = await loop.run_in_executor(
                    None, middleware.process_request, request_handler
                )
            if result is not None:
                return result
        return None

    async def async_process_response(self, request_handler, response):
        """
        按逆序执行所有中间件的响应处理（异步）

        Args:
            request_handler: 请求处理器实例
            response: 响应数据

        Returns:
            处理后的响应数据
        """
        loop = asyncio.get_event_loop()
        for middleware in reversed(request_handler._middlewares):
            if middleware._has_async_override('async_process_response'):
                response = await middleware.async_process_response(request_handler, response)
            else:
                response = await loop.run_in_executor(
                    None, middleware.process_response, request_handler, response
                )
        return response

    async def async_process_exception(self, request_handler, exception):
        """
        按顺序执行所有中间件的异常处理（异步）

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
            其他值: 返回该值作为响应
        """
        loop = asyncio.get_event_loop()
        for middleware in request_handler._middlewares:
            if middleware._has_async_override('async_process_exception'):
                result = await middleware.async_process_exception(request_handler, exception)
            else:
                result = await loop.run_in_executor(
                    None, middleware.process_exception, request_handler, exception
                )
            if result is not None:
                return result
        return None
