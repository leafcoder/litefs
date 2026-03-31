#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import sys
from datetime import datetime
from posixpath import abspath as path_abspath

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
from .server import (
    DEFAULT_BUFFER_SIZE,
    BufferedRWPair,
    HTTPServer,
    SocketIO,
    mainloop,
)
from .utils import log_error, make_logger

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
    config.webroot = path_abspath(config.webroot)
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
        self.files = CacheManager.get_file_cache(
            clean_period=getattr(config, 'file_cache_clean_period', 60),
            expiration_time=getattr(config, 'file_cache_expiration_time', 3600),
        )

        self.middleware_manager = MiddlewareManager()
        self._middleware_instances = []
        error_pages_dir = getattr(config, "error_pages_dir", None)
        self.error_page_renderer = ErrorPageRenderer(error_pages_dir)

    def wsgi(self):
        """
        返回符合 PEP 3333 规范的 WSGI application callable

        用法:
            import litefs
            app = litefs.Litefs(webroot='./site')
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

    def handler(self, request, environ, server):
        raw = SocketIO(server, request)
        rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
        request_handler = RequestHandler(self, rw, environ, request)
        result = request_handler.handler()
        return request_handler.finish(result)

    def run(self, poll_interval=0.2):
        observer = Observer()
        event_handler = FileEventHandler(self)
        observer.schedule(event_handler, self.config.webroot, recursive=True)
        observer.start()
        self.server = HTTPServer((self.host, self.port), self.handler)
        self.server.max_request_size = self.config.max_request_size
        try:
            self.server.start()
            mainloop(poll_interval=poll_interval)
        except KeyboardInterrupt:
            pass
        except Exception:
            log_error(self.logger)
        finally:
            observer.stop()
            observer.join()
            self.server.server_close()


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
        "--webroot",
        dest="webroot",
        required=False,
        default="./site",
        help="use WEBROOT as root directory",
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
        "--not-found",
        dest="not_found",
        required=False,
        default="not_found",
        help="use NOT_FOUND as 404 page",
    )
    parser.add_argument(
        "--default-page",
        dest="default_page",
        required=False,
        default="index",
        help="use DEFAULT_PAGE as web default page",
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
    litefs = (
        Litefs(**kwargs)
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
    )
    litefs.run(poll_interval=0.1)


if "__main__" == __name__:
    test_server()
