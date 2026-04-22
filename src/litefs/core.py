#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import sys
import socket
import time
from datetime import datetime
from posixpath import abspath as path_abspath
from typing import Dict, List, Optional, Callable, Any, Union, Iterable, Type, TypeVar, Tuple, cast

from watchdog.observers import Observer

from .cache import (
    CacheBackend,
    CacheFactory,
    CacheManager,
    FileEventHandler,
    MemoryCache,
    TreeCache,
)
from .config import Config, load_config
from .database import DatabaseManager
from .error_pages import ErrorPageRenderer
from .handlers import RequestHandler, WSGIRequestHandler, ASGIRequestHandler
from .middleware import MiddlewareManager
from .routing import Router
from .server import (
    DEFAULT_BUFFER_SIZE,
    BufferedRWPair,
    HTTPServer,
    ProcessHTTPServer,
    SocketIO,
    mainloop,
)
from .utils import log_error, log_info, make_logger

from ._version import __version__
from .plugins import PluginManager, PluginLoader


def _guess_content_type(content) -> str:
    """根据内容类型猜测 Content-Type"""
    if isinstance(content, (dict, list, tuple)):
        return "application/json; charset=utf-8"
    if isinstance(content, str) and content.startswith('<'):
        return "text/html; charset=utf-8"
    if isinstance(content, bytes):
        return "application/octet-stream"
    return "text/html; charset=utf-8"


def _serialize_content(content, is_json: bool = False):
    """
    将响应内容序列化为 bytes 列表

    统一 WSGI/ASGI 的内容序列化逻辑，消除重复代码。

    Args:
        content: 响应内容（任意类型）
        is_json: Content-Type 是否包含 application/json

    Returns:
        list[bytes]: 序列化后的字节列表
    """
    import json
    from collections.abc import Iterable

    if isinstance(content, (dict,)):
        return [json.dumps(content, ensure_ascii=False).encode("utf-8")]

    if isinstance(content, (list, tuple)):
        if is_json:
            return [json.dumps(content, ensure_ascii=False, default=str).encode("utf-8")]
        result = []
        for item in content:
            if isinstance(item, str):
                result.append(item.encode("utf-8"))
            elif isinstance(item, bytes):
                result.append(item)
            else:
                result.append(str(item).encode("utf-8"))
        return result

    if isinstance(content, str):
        if is_json:
            return [json.dumps(content, ensure_ascii=False).encode("utf-8")]
        return [content.encode("utf-8")]

    if isinstance(content, bytes):
        return [content]

    if content is None:
        return [b""]

    # 可迭代对象（生成器等）
    if isinstance(content, Iterable):
        def _gen():
            for item in content:
                if isinstance(item, str):
                    yield item.encode("utf-8")
                elif isinstance(item, bytes):
                    yield item
                else:
                    yield str(item).encode("utf-8")
        return list(_gen())

    return [str(content).encode("utf-8")]


def _parse_result_tuple(result):
    """
    解析处理函数返回的结果元组

    Args:
        result: 处理函数的返回值

    Returns:
        (status, headers, content) 三元组
    """
    if (
        isinstance(result, (list, tuple))
        and len(result) == 3
        and isinstance(result[0], str)
        and isinstance(result[1], list)
    ):
        return result[0], result[1], result[2]
    content = result
    content_type = _guess_content_type(content)
    return "200 OK", [("Content-Type", content_type)], content


def make_config(**kwargs: Dict[str, Any]) -> Config:
    """
    创建配置对象

    支持多种配置来源：
    1. 默认配置
    2. 配置文件（通过 config_file 参数）
    3. 环境变量（LITEFS_*）
    4. 代码中的配置（kwargs）

    Args:
        **kwargs: 配置项

    Returns:
        Config 对象
    """
    config_file = kwargs.pop('config_file', None)
    config = load_config(config_file=config_file, **kwargs)
    return config


def make_server(host: str, port: int, request_size: int = -1) -> socket.socket:
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    if -1 == request_size:
        request_size = 1024
    sock.listen(request_size)
    sock.setblocking(False)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock

def is_port_available(host: str, port: int) -> bool:
    """
    检查端口是否可用
    
    Args:
        host: 主机地址
        port: 端口号
        
    Returns:
        bool: 端口是否可用
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


class Litefs(object):

    def __init__(self, **kwargs: Any) -> None:
        self.config = config = make_config(**kwargs)
        level = logging.DEBUG if config.debug else logging.INFO
        self.logger = make_logger(__name__, log=config.log, level=level)
        
        # 禁止 watchdog 的 DEBUG 日志输出
        watchdog_logger = logging.getLogger('watchdog')
        watchdog_logger.setLevel(logging.INFO)
        watchdog_observers_logger = logging.getLogger('watchdog.observers')
        watchdog_observers_logger.setLevel(logging.INFO)
        
        self.host: str = config.host
        self.port: int = config.port
        self.server: Optional[Union[HTTPServer, ProcessHTTPServer]] = None

        # 使用全局 Session 管理器，确保 Session 对象常驻内存
        # 不会因为 Litefs 实例的创建和销毁而丢失数据
        from litefs.session.manager import SessionManager
        from litefs.session.factory import SessionBackend
        # 获取 session 相关配置
        session_backend = getattr(config, 'session_backend', SessionBackend.MEMORY)
        session_config = {}
        if session_backend == SessionBackend.REDIS:
            session_config = {
                "host": getattr(config, "redis_host", "localhost"),
                "port": getattr(config, "redis_port", 6379),
                "db": getattr(config, "redis_db", 0),
                "password": getattr(config, "redis_password", None),
                "key_prefix": getattr(config, "redis_session_key_prefix", "litefs:session:"),
                "expiration_time": getattr(config, "session_expiration_time", 3600),
            }
        elif session_backend == SessionBackend.DATABASE:
            session_config = {
                "db_path": getattr(config, "database_path", ":memory:"),
                "table_name": getattr(config, "database_session_table", "sessions"),
                "expiration_time": getattr(config, "session_expiration_time", 3600),
            }
        elif session_backend == SessionBackend.MEMCACHE:
            session_config = {
                "servers": getattr(config, "memcache_servers", ["localhost:11211"]),
                "key_prefix": getattr(config, "memcache_session_key_prefix", "litefs:session:"),
                "expiration_time": getattr(config, "session_expiration_time", 3600),
            }
        elif session_backend == SessionBackend.MEMORY:
            session_config = {
                "max_size": getattr(config, "session_max_size", 1000000),
            }
        # 使用 SessionManager 管理 Session 实例
        self.sessions = SessionManager.get_session_cache(
            backend=session_backend,
            cache_key='default',
            **session_config
        )
        self.caches = CacheManager.get_cache(
            backend=getattr(config, 'cache_backend', CacheBackend.TREE),
            cache_key='app_cache',
            max_size=getattr(config, 'cache_max_size', 10000),
            clean_period=getattr(config, 'cache_clean_period', 60),
            expiration_time=getattr(config, 'cache_expiration_time', 3600),
        )


        self.middleware_manager = MiddlewareManager()
        self._middleware_instances = []
        
        self._init_debug_middleware()
        
        error_pages_dir = getattr(config, "error_pages_dir", None)
        self.error_page_renderer = ErrorPageRenderer(error_pages_dir)
        
        # 初始化路由管理器
        self.router = Router()

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.get_database(self.config)
        
        # 初始化插件系统
        self.plugin_manager = PluginManager(self)
        self.plugin_loader = PluginLoader(self)
        
        # 添加默认插件目录
        self.plugin_loader.add_plugin_dir('./plugins')
        self.plugin_loader.add_plugin_dir('./litefs/plugins')

    def _init_debug_middleware(self):
        """初始化调试中间件"""
        import os
        if os.environ.get('LITEFS_DEBUG', '0') == '1':
            from .debug.middleware import DebugMiddleware
            self.add_middleware(DebugMiddleware)

    def database(self, name: str = 'default') -> Any:
        """
        获取数据库实例

        Args:
            name: 数据库名称

        Returns:
            数据库实例
        """
        return self.db_manager.get_database(self.config, name)

    def db_session(self, name: str = 'default') -> Any:
        """
        获取数据库会话

        Args:
            name: 数据库名称

        Returns:
            数据库会话实例
        """
        return self.db_manager.get_session(name)

    def session(self, name: str = 'default') -> Any:
        """
        获取数据库会话（别名，已废弃，建议使用 db_session）

        Args:
            name: 数据库名称

        Returns:
            数据库会话实例
        """
        import warnings
        warnings.warn('session() method is deprecated, use db_session() instead', DeprecationWarning)
        return self.db_session(name)

    def create_all_tables(self, name: str = 'default'):
        """
        创建所有数据表

        Args:
            name: 数据库名称
        """
        self.db_manager.create_all(name)

    def drop_all_tables(self, name: str = 'default'):
        """
        删除所有数据表

        Args:
            name: 数据库名称
        """
        self.db_manager.drop_all(name)

    def _handle_error_parts(self, request_handler, error):
        """Process an exception and return normalized error parts.

        Tries middleware exception handler first, then HttpError, then generic 500.

        Returns:
            tuple: (status_line, headers, content) from _parse_result_tuple if middleware handled it
                   (first element is a string — the WSGI status line).
            tuple: (status_code, content_type, status_text, body_text) if no middleware handled it
                   (first element is an int — the HTTP status code).
        """
        if request_handler is not None:
            middleware_result = self.middleware_manager.process_exception(request_handler, error)
            if middleware_result is not None:
                return _parse_result_tuple(middleware_result)

        from .exceptions import HttpError

        if isinstance(error, HttpError):
            return (error.status_code, "text/html; charset=utf-8", error.message, error.message)
        else:
            log_error(self.logger, str(error))
            return (500, "text/html; charset=utf-8", "500 Internal Server Error", "Internal Server Error")

    def wsgi(self):
        """
        返回符合 PEP 3333 规范的 WSGI application callable

        用法:
            from litefs.core import Litefs
            app = Litefs()
            application = app.wsgi()

        在 gunicorn 中使用:
            gunicorn -w 4 -b :8000 wsgi_example:application

        在 uWSGI 中使用:
            uwsgi --http :8000 --wsgi-file wsgi_example.py
        """

        def application(environ, start_response):
            try:
                request_handler = WSGIRequestHandler(self, environ)

                # 中间件请求处理
                middleware_result = self.middleware_manager.process_request(request_handler)
                if middleware_result is not None:
                    status, headers, content = _parse_result_tuple(middleware_result)
                    start_response(status, headers)
                    return _serialize_content(content, "application/json" in dict(headers).get("Content-Type", ""))

                # 业务处理
                handler_result = request_handler.handler()
                status, headers, content = _parse_result_tuple(handler_result)
                start_response(status, headers)
                is_json = "application/json" in dict(headers).get("Content-Type", "")
                return _serialize_content(content, is_json)

            except Exception as e:
                result = self._handle_error_parts(request_handler, e)
                if len(result) == 3 and isinstance(result[0], str):
                    # Middleware handled it — result is (status_line, headers, content)
                    status, headers, content = result
                    start_response(status, headers)
                    return _serialize_content(content, "application/json" in dict(headers).get("Content-Type", ""))

                # Error parts — result is (status_code, content_type, status_text, body_text)
                status_code, content_type, status_text, body_text = result
                status = f"{status_code} {status_text}"
                headers = [("Content-Type", content_type)]
                start_response(status, headers)
                return [body_text.encode("utf-8")]

        return application

    def asgi(self):
        """
        返回符合 ASGI 3.0 规范的 ASGI application callable

        用法:
            from litefs.core import Litefs
            app = Litefs()
            application = app.asgi()

        在 uvicorn 中使用:
            uvicorn asgi_example:application

        在 daphne 中使用:
            daphne asgi_example:application
        """

        async def _send_asgi_response(send, status, headers, content):
            """发送 ASGI 响应"""
            status_code = int(status.split()[0])
            asgi_headers = []
            for k, v in headers:
                if k.lower() != 'content-length':
                    asgi_headers.append((k.encode('utf-8'), v.encode('utf-8')))

            content_bytes_list = _serialize_content(content, "application/json" in dict(headers).get("Content-Type", ""))
            body = b''.join(content_bytes_list)

            await send({
                'type': 'http.response.start',
                'status': status_code,
                'headers': asgi_headers,
            })
            await send({
                'type': 'http.response.body',
                'body': body,
            })

        async def application(scope, receive, send):
            # 只处理 HTTP 请求
            if scope['type'] != 'http':
                return

            request_handler = None
            try:
                request_handler = ASGIRequestHandler(self, scope, receive, send)

                # 中间件请求处理
                middleware_result = self.middleware_manager.process_request(request_handler)
                if middleware_result is not None:
                    status, headers, content = _parse_result_tuple(middleware_result)
                    await _send_asgi_response(send, status, headers, content)
                    return

                # 业务处理
                handler_result = await request_handler.handler()
                status, headers, content = _parse_result_tuple(handler_result)
                await _send_asgi_response(send, status, headers, content)

            except Exception as e:
                result = self._handle_error_parts(request_handler, e)
                if len(result) == 3 and isinstance(result[0], str):
                    # Middleware handled it — result is (status_line, headers, content)
                    status, headers, content = result
                    await _send_asgi_response(send, status, headers, content)
                    return

                # Error parts — result is (status_code, content_type, status_text, body_text)
                status_code, content_type, status_text, body_text = result
                await send({
                    'type': 'http.response.start',
                    'status': status_code,
                    'headers': [
                        (b'content-type', content_type.encode('utf-8')),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': body_text.encode('utf-8'),
                })

        return application

    def add_middleware(self, middleware_class, **kwargs):
        """
        添加中间件

        Args:
            middleware_class: 中间件类
            **kwargs: 传递给中间件构造函数的参数

        Returns:
            self: 支持链式调用
        """
        self.middleware_manager.add(middleware_class, **kwargs)
        self._middleware_instances = None
        return self

    def remove_middleware(self, middleware_class):
        """
        移除中间件

        Args:
            middleware_class: 中间件类
        """
        self.middleware_manager.remove(middleware_class)
        self._middleware_instances = None

    def clear_middleware(self):
        """
        清空所有中间件
        """
        self.middleware_manager.clear()
        self._middleware_instances = None
    
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
    
    def add_static(self, prefix: str, directory: str, name: Optional[str] = None):
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
                  auth_handler: Callable = None, port: int = None):
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
        from .websocket import WebSocket
        
        if not hasattr(self, '_websocket_instance'):
            ws_port = port or (self.port + 1)
            self._websocket_instance = WebSocket(
                app=self,
                path=path,
                port=ws_port,
                auth_required=auth_required,
                auth_handler=auth_handler,
            )
        
        return self._websocket_instance.handler(path)
    
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
        import importlib

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
    
    def register_plugin(self, plugin_class):
        """
        注册插件
        
        Args:
            plugin_class: 插件类
        """
        self.plugin_manager.register(plugin_class)
        return self
    
    def load_plugins(self):
        """
        加载所有插件
        """
        # 从文件系统加载插件
        plugins = self.plugin_loader.load_plugins()
        for plugin_name, plugin_class in plugins.items():
            self.plugin_manager.register(plugin_class)
        
        # 加载所有注册的插件
        self.plugin_manager.load_all()
        return self
    
    def get_plugin(self, plugin_name: str):
        """
        获取插件实例
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件实例或 None
        """
        return self.plugin_manager.get_plugin(plugin_name)
    
    def has_plugin(self, plugin_name: str) -> bool:
        """
        检查插件是否已加载
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否已加载
        """
        return self.plugin_manager.has_plugin(plugin_name)
    
    def get_all_plugins(self):
        """
        获取所有已加载的插件
        
        Returns:
            插件实例列表
        """
        return self.plugin_manager.get_all_plugins()

    def add_health_check(self, name: str, check_func):
        """
        添加健康检查

        Args:
            name: 检查名称
            check_func: 检查函数，返回 True 表示健康，False 表示不健康
        """
        from .middleware import HealthCheck
        
        for middleware in self._get_middleware_instances():
            if isinstance(middleware, HealthCheck):
                middleware.add_check(name, check_func)
                break

    def add_ready_check(self, name: str, check_func):
        """
        添加就绪检查

        Args:
            name: 检查名称
            check_func: 检查函数，返回 True 表示就绪，False 表示未就绪
        """
        from .middleware import HealthCheck
        
        for middleware in self._get_middleware_instances():
            if isinstance(middleware, HealthCheck):
                middleware.add_ready_check(name, check_func)
                break

    def _get_middleware_instances(self):
        """
        获取中间件实例（缓存）

        Returns:
            中间件实例列表
        """
        if self._middleware_instances is None:
            self._middleware_instances = self.middleware_manager.get_middleware_instances(self)
        return self._middleware_instances

    def handler(self, request, rw, environ, server):
        request_handler = RequestHandler(self, rw, environ, request)
        result = request_handler.handler()
        return request_handler.finish(result)

    def run(self, poll_interval=0.2, processes=1, reload=False):
        import os
        import sys
        import signal

        main_file = getattr(sys.modules['__main__'], '__file__', None)
        if main_file:
            main_file = os.path.abspath(main_file)

        is_child_process = os.environ.get('LITEFS_CHILD_PROCESS', '0') == '1'

        if not reload or is_child_process:
            self._run_server(poll_interval, processes)
        else:
            self._run_with_reload(main_file)

    def _run_server(self, poll_interval, processes):
        """启动服务器（无热重载）"""
        import sys
        import signal

        def signal_handler(signum, frame):
            if hasattr(self, 'server') and self.server:
                try:
                    if hasattr(self.server, 'shutdown'):
                        self.server.shutdown()
                except Exception as e:
                    log_error(self.logger, "Error shutting down server in signal handler: %s" % str(e))
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.load_plugins()

        ws_instance = self.get_websocket()
        if ws_instance:
            ws_instance.start()
            log_info(self.logger, "WebSocket server started on port %d" % (self.port + 1))

        log_info(self.logger, "Starting server on %s:%d (processes=%d)" % (self.host, self.port, processes))

        try:
            if processes > 1:
                self.server = ProcessHTTPServer((self.host, self.port), self.handler, processes=processes)
                self.server.max_request_size = self.config.max_request_size
                self.server.server_forever(poll_interval=poll_interval)
            else:
                self.server = HTTPServer((self.host, self.port), self.handler)
                self.server.max_request_size = self.config.max_request_size
                self.server.start()
                mainloop(poll_interval=poll_interval)
        except KeyboardInterrupt:
            log_info(self.logger, "Server stopped by user")
        except SystemExit:
            log_info(self.logger, "Server stopped by signal")
        except Exception as e:
            log_error(self.logger, "Server error: %s" % str(e))
        finally:
            self._cleanup_server()

    def _cleanup_server(self):
        """清理服务器资源"""
        ws_instance = self.get_websocket()
        if ws_instance:
            try:
                ws_instance.stop()
            except Exception as e:
                log_error(self.logger, "Error stopping WebSocket: %s" % str(e))
        if hasattr(self, 'server') and self.server:
            try:
                if hasattr(self.server, 'shutdown'):
                    self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                log_error(self.logger, "Error closing server: %s" % str(e))
        try:
            from .database import DatabaseManager
            DatabaseManager.close_all()
        except Exception as e:
            log_error(self.logger, "Error closing database connections: %s" % str(e))

    def _scan_file_modtimes(self, watch_dirs):
        """扫描所有 Python 文件的修改时间"""
        import os

        mod_times = {}
        for watch_dir in watch_dirs:
            if not os.path.exists(watch_dir):
                continue
            for root, dirs, files in os.walk(watch_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            mod_times[file_path] = os.path.getmtime(file_path)
                        except OSError:
                            pass
        return mod_times

    def _check_file_changes(self, watch_dirs, file_mod_times):
        """检查文件是否有变化"""
        current_mod_times = self._scan_file_modtimes(watch_dirs)

        for file_path, mtime in current_mod_times.items():
            if file_path not in file_mod_times:
                return True
            if mtime != file_mod_times[file_path]:
                return True

        for file_path in file_mod_times:
            if file_path not in current_mod_times:
                return True

        return False

    def _run_with_reload(self, main_file):
        """启动带热重载的服务器"""
        import os
        import sys
        import signal
        import subprocess
        import time

        child_proc = None

        def parent_signal_handler(signum, frame):
            if child_proc and child_proc.poll() is None:
                try:
                    child_proc.terminate()
                    child_proc.wait(timeout=5)
                except Exception as e:
                    log_error(self.logger, "Error terminating child process: %s" % str(e))
                    try:
                        child_proc.kill()
                        child_proc.wait()
                    except Exception as e2:
                        log_error(self.logger, "Error killing child process: %s" % str(e2))
            sys.exit(0)

        signal.signal(signal.SIGINT, parent_signal_handler)
        signal.signal(signal.SIGTERM, parent_signal_handler)

        log_info(self.logger, "Starting server with hot reload on %s:%d" % (self.host, self.port))

        if main_file:
            project_dir = os.path.dirname(main_file)
            watch_dirs = [project_dir]

            src_dir = os.path.join(os.path.dirname(project_dir), 'src')
            if os.path.exists(src_dir):
                watch_dirs.append(src_dir)
        else:
            watch_dirs = []

        file_mod_times = self._scan_file_modtimes(watch_dirs)

        while True:
            try:
                env = os.environ.copy()
                env['LITEFS_CHILD_PROCESS'] = '1'

                child_proc = subprocess.Popen(
                    [sys.executable] + sys.argv,
                    env=env,
                    close_fds=True
                )

                while child_proc.poll() is None:
                    time.sleep(1)

                    if self._check_file_changes(watch_dirs, file_mod_times):
                        log_info(self.logger, "File changed, restarting server...")
                        file_mod_times = self._scan_file_modtimes(watch_dirs)

                        try:
                            child_proc.terminate()
                            child_proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child_proc.kill()
                            child_proc.wait()
                        except Exception as e:
                            log_error(self.logger, "Error terminating child process on file change: %s" % str(e))
                        break

                exit_code = child_proc.returncode

                if exit_code == 0 or exit_code is None:
                    continue

                if exit_code not in (0, -2, -15):
                    log_error(self.logger, "Server exited with code %d" % exit_code)

                break

            except Exception as e:
                log_error(self.logger, "Error starting server: %s" % str(e))
                time.sleep(1)
            finally:
                if child_proc and child_proc.poll() is None:
                    try:
                        child_proc.terminate()
                        child_proc.wait(timeout=5)
                    except Exception as e:
                        log_error(self.logger, "Error terminating child process: %s" % str(e))
                        try:
                            child_proc.kill()
                            child_proc.wait()
                        except Exception as e2:
                            log_error(self.logger, "Error killing child process: %s" % str(e2))


def _cmd_args(args):
    title = args[0] if args else "litefs"
    parser = argparse.ArgumentParser(title, description=__doc__)
    parser.add_argument(
        "-H", "--host", dest="host", required=False, default="localhost", help="bind server to HOST"
    )
    parser.add_argument(
        "-P",
        "--port",
        action="store",
        dest="port",
        type=int,
        required=False,
        default=9090,
        help="bind server to PORT",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        required=False,
        default=False,
        help="start server in debug mode",
    )

    parser.add_argument(
        "--log", dest="log", required=False, default="./default.log", help="save log to LOG"
    )
    parser.add_argument(
        "--listen", dest="listen", type=int, required=False, default=1024, help="server LISTEN"
    )
    parser.add_argument(
        "--max-request-size",
        dest="max_request_size",
        required=False,
        type=int,
        default=10485760,
        help="maximum request body size in bytes (default: 10MB)",
    )
    parser.add_argument(
        "--max-upload-size",
        dest="max_upload_size",
        required=False,
        type=int,
        default=52428800,
        help="maximum file upload size in bytes (default: 50MB)",
    )
    parser.add_argument(
        "--config",
        dest="config_file",
        required=False,
        default=None,
        help="path to configuration file (YAML, JSON, or TOML)",
    )
    parser.add_argument(
        "--processes",
        dest="processes",
        type=int,
        required=False,
        default=1,
        help="number of worker processes (default: 1)",
    )
    args = parser.parse_args(args and args[1:])
    return args


def test_server():
    from litefs.middleware import (
        CORSMiddleware,
        LoggingMiddleware,
        SecurityMiddleware,
        CSRFMiddleware,
    )

    args = _cmd_args(sys.argv)
    kwargs = vars(args)
    processes = kwargs.pop('processes', 1)
    litefs = (
        Litefs(**kwargs)
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
        .add_middleware(CSRFMiddleware)
    )
    litefs.run(poll_interval=0.1, processes=processes)


if "__main__" == __name__:
    test_server()
