#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import sys
import socket
import time
from datetime import datetime
from posixpath import abspath as path_abspath
from typing import Optional

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
from .error_pages import ErrorPageRenderer
from .handlers import RequestHandler, WSGIRequestHandler
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


def make_config(**kwargs):
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


def make_server(host, port, request_size=-1):
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

def is_port_available(host, port):
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

    def __init__(self, **kwargs):
        self.config = config = make_config(**kwargs)
        level = logging.DEBUG if config.debug else logging.INFO
        self.logger = make_logger(__name__, log=config.log, level=level)
        
        # 禁止 watchdog 的 DEBUG 日志输出
        watchdog_logger = logging.getLogger('watchdog')
        watchdog_logger.setLevel(logging.INFO)
        watchdog_observers_logger = logging.getLogger('watchdog.observers')
        watchdog_observers_logger.setLevel(logging.INFO)
        
        self.host = config.host
        self.port = config.port
        self.server = None

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
        error_pages_dir = getattr(config, "error_pages_dir", None)
        self.error_page_renderer = ErrorPageRenderer(error_pages_dir)
        
        # 初始化路由管理器
        self.router = Router()

    def wsgi(self):
        """
        返回符合 PEP 3333 规范的 WSGI application callable

        用法:
            import litefs
            app = litefs.Litefs()
            application = app.wsgi()

        在 gunicorn 中使用:
            gunicorn -w 4 -b :8000 wsgi_example:application

        在 uWSGI 中使用:
            uwsgi --http :8000 --wsgi-file wsgi_example.py
        """

        def application(environ, start_response):
            """
            WSGI application callable

            Args:
                environ: WSGI 环境变量字典
                start_response: 开始响应的 callable

            Returns:
                可迭代的 bytes
            """
            try:
                request_handler = WSGIRequestHandler(self, environ)

                middleware_result = self.middleware_manager.process_request(request_handler)
                if middleware_result is not None:
                    if isinstance(middleware_result, (list, tuple)) and len(middleware_result) == 3:
                        status, headers, content = middleware_result
                        start_response(status, headers)
                    else:
                        content = middleware_result
                        status, headers = "200 OK", [("Content-Type", "text/plain; charset=utf-8")]
                        start_response(status, headers)

                    if isinstance(content, (str, bytes, dict, list, tuple, type(None))):
                        if isinstance(content, str):
                            return [content.encode("utf-8")]
                        elif isinstance(content, bytes):
                            return [content]
                        elif isinstance(content, dict):
                            import json

                            content = json.dumps(content, ensure_ascii=False)
                            return [content.encode("utf-8")]
                        elif isinstance(content, (list, tuple)):
                            import json

                            content = json.dumps(content, ensure_ascii=False, default=str)
                            return [content.encode("utf-8")]
                        else:
                            return [b""]
                    else:
                        return [str(content).encode("utf-8")]

                handler_result = request_handler.handler()

                if (
                    isinstance(handler_result, (list, tuple))
                    and len(handler_result) == 3
                    and isinstance(handler_result[0], str)
                    and isinstance(handler_result[1], list)
                ):
                    status, headers, content = handler_result
                    start_response(status, headers)
                else:
                    content = handler_result
                    status, headers = "200 OK", [("Content-Type", "text/plain; charset=utf-8")]
                    start_response(status, headers)

                headers_dict = dict(headers)
                content_type = headers_dict.get("Content-Type", "")
                is_json = "application/json" in content_type

                from collections.abc import Iterable

                if not isinstance(
                    content, (str, bytes, dict, list, tuple, type(None))
                ) and isinstance(content, Iterable):

                    def content_generator():
                        for item in content:
                            if isinstance(item, str):
                                yield item.encode("utf-8")
                            elif isinstance(item, bytes):
                                yield item
                            else:
                                yield str(item).encode("utf-8")

                    return content_generator()
                elif isinstance(content, dict):
                    import json

                    content = json.dumps(content, ensure_ascii=False)
                    return [content.encode("utf-8")]
                elif isinstance(content, (list, tuple)):
                    if is_json:
                        import json

                        content = json.dumps(content, ensure_ascii=False, default=str)
                        return [content.encode("utf-8")]
                    else:
                        result = []
                        for item in content:
                            if isinstance(item, str):
                                result.append(item.encode("utf-8"))
                            elif isinstance(item, bytes):
                                result.append(item)
                            else:
                                result.append(str(item).encode("utf-8"))
                        return result
                elif isinstance(content, str):
                    if is_json:
                        import json

                        content = json.dumps(content, ensure_ascii=False)
                        return [content.encode("utf-8")]
                    return [content.encode("utf-8")]
                elif isinstance(content, bytes):
                    return [content]
                else:
                    return [str(content).encode("utf-8")]
            except Exception as e:
                middleware_result = self.middleware_manager.process_exception(request_handler, e)
                if middleware_result is not None:
                    if isinstance(middleware_result, (list, tuple)) and len(middleware_result) == 3:
                        status, headers, content = middleware_result
                        start_response(status, headers)
                    else:
                        content = middleware_result
                        status, headers = "200 OK", [("Content-Type", "text/plain; charset=utf-8")]
                        start_response(status, headers)

                    if isinstance(content, str):
                        return [content.encode("utf-8")]
                    elif isinstance(content, bytes):
                        return [content]
                    else:
                        return [str(content).encode("utf-8")]

                from .exceptions import HttpError

                if isinstance(e, HttpError):
                    status_code = e.args[0] if len(e.args) > 0 else 500
                    message = e.args[1] if len(e.args) > 1 else str(e)
                    status = f"{status_code} {message}"
                    headers = [("Content-Type", "text/plain; charset=utf-8")]
                    start_response(status, headers)
                    return [message.encode("utf-8")]
                else:
                    log_error(self.logger, str(e))
                    status = "500 Internal Server Error"
                    headers = [("Content-Type", "text/plain; charset=utf-8")]
                    start_response(status, headers)
                    return [b"500 Internal Server Error"]

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
            if callable(obj) and hasattr(obj, '_routes'):
                for route_info in obj._routes:
                    self.add_route(
                        path=route_info['path'],
                        methods=route_info['methods'],
                        handler=obj,
                        name=route_info['name']
                    )
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

    def run(self, poll_interval=0.2, processes=1, no_reload=False):
        import os
        import sys
        import subprocess
        import time
        import signal
        from pathlib import Path
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
        
        # 获取启动脚本路径
        main_file = getattr(sys.modules['__main__'], '__file__', None)
        if main_file:
            main_file = os.path.abspath(main_file)
        
        # 检查是否是子进程
        is_child_process = os.environ.get('LITEFS_CHILD_PROCESS', '0') == '1'
        
        print(f"[DEBUG] run() called: is_child_process={is_child_process}, no_reload={no_reload}")
        
        # 如果禁用热重载或已经是子进程，直接运行服务器
        if no_reload or is_child_process:
            # 子进程：实际运行服务器
            # 设置环境变量
            os.environ['LITEFS_CHILD_PROCESS'] = '1'
            
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
            except Exception as e:
                log_error(self.logger, "Server error: %s" % str(e))
            finally:
                # 关闭服务器
                if hasattr(self, 'server') and self.server:
                    try:
                        # 先关闭所有工作进程
                        if hasattr(self.server, 'shutdown'):
                            self.server.shutdown()
                            # 给工作进程足够的时间关闭
                            time.sleep(1)
                        # 再关闭服务器套接字
                        self.server.server_close()
                    except Exception:
                        pass
        else:
            # 父进程，启动子进程监控
            print("[DEBUG] Parent process: Starting")
            
            # 启动子进程循环
            while True:
                print("[DEBUG] Parent process: Starting child process")
                
                # 启动子进程
                try:
                    # 准备环境变量
                    env = os.environ.copy()
                    env['LITEFS_CHILD_PROCESS'] = '1'
                    
                    # 启动子进程
                    child_proc = subprocess.Popen(
                        [sys.executable] + sys.argv,
                        env=env,
                        close_fds=True
                    )
                    
                    print(f"[DEBUG] Parent process: Child process started (PID: {child_proc.pid})")
                    
                    # 简单的文件监控（暂时跳过 watchdog 避免复杂问题）
                    if main_file:
                        project_dir = os.path.dirname(main_file)
                        print(f"[DEBUG] Parent process: Monitoring directory: {project_dir}")
                        
                        # 监控文件变化
                        file_mod_times = {}
                        for root, dirs, files in os.walk(project_dir):
                            for file in files:
                                if file.endswith('.py'):
                                    file_path = os.path.join(root, file)
                                    file_mod_times[file_path] = os.path.getmtime(file_path)
                        
                        # 等待子进程或文件变化
                        while child_proc.poll() is None:
                            # 检查文件变化
                            should_restart = False
                            for root, dirs, files in os.walk(project_dir):
                                for file in files:
                                    if file.endswith('.py'):
                                        file_path = os.path.join(root, file)
                                        if file_path in file_mod_times:
                                            current_mtime = os.path.getmtime(file_path)
                                            if current_mtime != file_mod_times[file_path]:
                                                print(f"[DEBUG] Parent process: File changed: {file_path}")
                                                should_restart = True
                                                break
                                if should_restart:
                                    break
                            
                            if should_restart:
                                print("[DEBUG] Parent process: Stopping child process")
                                child_proc.terminate()
                                try:
                                    child_proc.wait(timeout=3)
                                except subprocess.TimeoutExpired:
                                    print("[DEBUG] Parent process: Killing child process")
                                    child_proc.kill()
                                    child_proc.wait()
                                break
                            
                            time.sleep(1)
                    else:
                        # 没有主文件，直接等待子进程退出
                        child_proc.wait()
                    
                    # 子进程已退出
                    exit_code = child_proc.returncode
                    print(f"[DEBUG] Parent process: Child process exited with code: {exit_code}")
                    
                    # 如果是文件变化导致的重启，继续循环
                    if 'should_restart' in locals() and should_restart:
                        print("[DEBUG] Parent process: Restarting...")
                        # 等待一段时间，确保所有旧的工作进程都已经完全关闭
                        # 检查端口是否已经释放
                        print(f"[DEBUG] Parent process: Checking if port {self.port} is available...")
                        start_time = time.time()
                        while time.time() - start_time < 30:  # 最多等待 30 秒
                            if is_port_available(self.host, self.port):
                                print(f"[DEBUG] Parent process: Port {self.port} is available!")
                                break
                            print(f"[DEBUG] Parent process: Port {self.port} is still in use, waiting...")
                            time.sleep(1)
                        else:
                            print(f"[DEBUG] Parent process: Port {self.port} is still in use after 30 seconds, trying anyway...")
                        continue
                    else:
                        break
                        
                except Exception as e:
                    print(f"[DEBUG] Parent process: Error: {e}")
                    time.sleep(1)


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
    )

    args = _cmd_args(sys.argv)
    kwargs = vars(args)
    processes = kwargs.pop('processes', 1)
    litefs = (
        Litefs(**kwargs)
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
    )
    litefs.run(poll_interval=0.1, processes=processes)


if "__main__" == __name__:
    test_server()
