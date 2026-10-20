#!/usr/bin/env python
# coding: utf-8

"""
Litefs 应用核心

`Litefs` 类通过 Mixin 组合各能力模块：

- RoutingMixin     路由注册与 WebSocket 入口（app/routing_mixin.py）
- ProtocolMixin    WSGI / ASGI 协议适配与错误处理（app/protocol_mixin.py）
- ExtensionMixin   中间件、插件、健康检查与数据库扩展（app/extension_mixin.py）
- ServerMixin      服务器启动、关闭与热重载（app/server_mixin.py）

本文件仅保留应用装配逻辑（构造函数）与向后兼容的符号再导出，
对外接口（``from litefs.core import Litefs, make_config, ...``）保持不变。
"""

import logging
from typing import Any, Optional, Union

from .cache import CacheBackend, CacheManager
from .database import DatabaseManager
from .error_pages import ErrorPageRenderer
from .middleware import MiddlewareManager
from .routing import Router
from .server import HTTPServer, ProcessHTTPServer
from .utils import make_logger

from .plugins import PluginLoader, PluginManager

from .app.helpers import (  # noqa: F401  向后兼容再导出
    _guess_content_type,
    _parse_result_tuple,
    _serialize_content,
    init_session_manager,
    is_port_available,
    make_config,
    make_server,
)
from .app.routing_mixin import RoutingMixin
from .app.protocol_mixin import ProtocolMixin
from .app.extension_mixin import ExtensionMixin
from .app.server_mixin import ServerMixin
from .app.server_cli import _cmd_args, test_server  # noqa: F401  向后兼容再导出


class Litefs(RoutingMixin, ProtocolMixin, ExtensionMixin, ServerMixin):
    """Litefs Web 应用

    组合路由、协议适配、扩展能力与服务器生命周期，
    构造函数负责装配配置、日志、会话、缓存、中间件、
    路由、数据库与插件系统。
    """

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
        self.sessions = init_session_manager(config)
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


if "__main__" == __name__:
    test_server()
