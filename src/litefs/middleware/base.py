#!/usr/bin/env python
# coding: utf-8

from typing import Callable, Any, Optional


class Middleware:
    """
    中间件基类
    
    所有中间件都应该继承此类并实现 process_request 和/或 process_response 方法
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
        处理请求，在请求到达业务逻辑之前执行
        
        Args:
            request_handler: 请求处理器实例
            
        Returns:
            None: 继续处理请求
            其他值: 直接返回该值作为响应，中断后续处理
        """
        pass

    def process_response(self, request_handler, response):
        """
        处理响应，在响应返回给客户端之前执行
        
        Args:
            request_handler: 请求处理器实例
            response: 响应数据
            
        Returns:
            修改后的响应数据
        """
        return response

    def process_exception(self, request_handler, exception):
        """
        处理异常
        
        Args:
            request_handler: 请求处理器实例
            exception: 异常对象
            
        Returns:
            None: 继续抛出异常
            其他值: 返回该值作为响应，不抛出异常
        """
        return None


class MiddlewareManager:
    """
    中间件管理器
    
    负责管理所有中间件的注册、加载和执行
    """

    def __init__(self):
        self._middlewares = []

    def add(self, middleware_class):
        """
        添加中间件
        
        Args:
            middleware_class: 中间件类
            
        Returns:
            self: 支持链式调用
        """
        self._middlewares.append(middleware_class)
        return self

    def remove(self, middleware_class):
        """
        移除中间件
        
        Args:
            middleware_class: 中间件类
        """
        if middleware_class in self._middlewares:
            self._middlewares.remove(middleware_class)

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
        return [middleware_class(app) for middleware_class in self._middlewares]

    def process_request(self, request_handler):
        """
        按顺序执行所有中间件的 process_request 方法
        
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
        按逆序执行所有中间件的 process_response 方法
        
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
        按顺序执行所有中间件的 process_exception 方法
        
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
