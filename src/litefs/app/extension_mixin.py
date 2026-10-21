#!/usr/bin/env python
# coding: utf-8

"""
应用扩展能力 Mixin

提供中间件管理、健康检查、插件注册加载与数据库访问等扩展方法。
"""

import os
import warnings
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from ..config import Config
    from ..database import DatabaseManager
    from ..middleware import MiddlewareManager
    from ..plugins import PluginLoader, PluginManager


class ExtensionMixin:
    """中间件、健康检查、插件与数据库扩展能力

    依赖宿主 ``Litefs`` 装配时提供的属性，
    以下声明仅供类型检查使用，运行时无开销。
    """

    #: 由 Litefs.__init__ 装配的宿主属性
    middleware_manager: "MiddlewareManager"
    _middleware_instances: Optional[List[Any]]
    db_manager: "DatabaseManager"
    config: "Config"
    plugin_manager: "PluginManager"
    plugin_loader: "PluginLoader"

    def _init_debug_middleware(self):
        """初始化调试中间件"""
        if os.environ.get('LITEFS_DEBUG', '0') == '1':
            from ..debug.middleware import DebugMiddleware
            self.add_middleware(DebugMiddleware)

    def _init_prometheus_middleware(self):
        """按配置启用 Prometheus 监控中间件

        仅当 ``prometheus_enabled`` 为真时启用，此时会在应用构造阶段
        校验 prometheus-client 是否可用，缺失时立即抛出带安装指引的异常，
        避免延迟到首个请求才失败。
        """
        if not getattr(self.config, 'prometheus_enabled', False):
            return

        from ..metrics import load_prometheus_client

        # 提前校验可选依赖，保证启动期失败而非请求期失败
        load_prometheus_client()

        from ..middleware import PrometheusMiddleware

        self.add_middleware(
            PrometheusMiddleware,
            path=getattr(self.config, 'prometheus_path', '/metrics'),
            namespace=getattr(self.config, 'prometheus_namespace', 'litefs'),
        )

    def _init_i18n_middleware(self):
        """按配置启用国际化中间件

        仅当 ``i18n_enabled`` 为真时启用，自动挂载
        :class:`~litefs.i18n.middleware.LocaleMiddleware`，
        受支持语言、默认语言、翻译目录等均从配置读取。
        """
        if not getattr(self.config, 'i18n_enabled', False):
            return

        from ..middleware import LocaleMiddleware

        self.add_middleware(
            LocaleMiddleware,
            supported_locales=getattr(self.config, 'i18n_supported_locales', None),
            default_locale=getattr(self.config, 'i18n_default_locale', 'en'),
            locale_dir=getattr(self.config, 'i18n_locale_dir', 'locales'),
            cookie_name=getattr(self.config, 'i18n_cookie_name', 'locale'),
            param_name=getattr(self.config, 'i18n_param_name', 'locale'),
        )

    def send_mail(self, message: Any, asynchronous: bool = False) -> Any:
        """
        发送邮件

        Args:
            message: :class:`~litefs.mail.Message` 邮件消息
            asynchronous: 是否通过 Celery 异步发送

        Returns:
            :class:`~litefs.mail.MailSendResult` 发送结果
        """
        from ..mail import get_mail_config, send_mail, send_mail_async

        config = get_mail_config(self)
        if asynchronous:
            return send_mail_async(message, config)
        return send_mail(message, config)

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

    def _get_middleware_instances(self):
        """
        获取中间件实例（缓存）

        Returns:
            中间件实例列表
        """
        if self._middleware_instances is None:
            instances = self.middleware_manager.get_middleware_instances(self)
            self._middleware_instances = instances
        return self._middleware_instances

    def add_health_check(self, name: str, check_func):
        """
        添加健康检查

        Args:
            name: 检查名称
            check_func: 检查函数，返回 True 表示健康，False 表示不健康
        """
        from ..middleware import HealthCheck

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
        from ..middleware import HealthCheck

        for middleware in self._get_middleware_instances():
            if isinstance(middleware, HealthCheck):
                middleware.add_ready_check(name, check_func)
                break

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
        warnings.warn(
            'session() method is deprecated, use db_session() instead',
            DeprecationWarning,
        )
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
        for _plugin_name, plugin_class in plugins.items():
            self.plugin_manager.register(plugin_class)

        # 加载所有注册的插件
        self.plugin_manager.load_all()
        return self

    def get_plugin(self, plugin_name: str) -> Optional[Any]:
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
        return bool(self.plugin_manager.has_plugin(plugin_name))

    def get_all_plugins(self):
        """
        获取所有已加载的插件

        Returns:
            插件实例列表
        """
        return self.plugin_manager.get_all_plugins()
