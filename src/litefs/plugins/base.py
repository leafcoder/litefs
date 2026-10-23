#!/usr/bin/env python
# coding: utf-8

"""
插件基类和管理器

定义插件的基本接口和管理功能
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)


def _parse_version(version: str) -> Tuple[int, ...]:
    """将 '0.13.0' 形式的版本字符串解析为可比较的整数元组

    非数字段按 0 处理，保证比较不抛异常。
    """
    parts = []
    for part in str(version).split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class Plugin(ABC):
    """
    插件基类

    所有插件必须继承此类并实现必要的方法
    """

    # 插件名称
    name: str = ""
    # 插件版本
    version: str = "0.1.0"
    # 插件描述
    description: str = ""
    # 插件作者
    author: str = ""
    # 插件依赖
    dependencies: List[str] = []
    # 插件配置选项
    config_options: Dict[str, Any] = {}
    # 要求的最低框架版本声明（如 '0.13.0'，空串表示不检查）
    required_litefs_version: str = ""

    def __init__(self, app):
        """
        初始化插件

        Args:
            app: Litefs 应用实例
        """
        self.app = app
        self.config = app.config

    @abstractmethod
    def initialize(self):
        """
        初始化插件

        插件加载时调用
        """
        pass

    def shutdown(self):
        """
        关闭插件

        应用关闭时调用
        """
        pass

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取插件配置

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        plugin_config = self.config.get(f'plugin_{self.name}', {})
        return plugin_config.get(key, default)

    def set_config(self, key: str, value: Any):
        """
        设置插件配置

        Args:
            key: 配置键
            value: 配置值
        """
        plugin_config = self.config.get(f'plugin_{self.name}', {})
        plugin_config[key] = value
        self.config.set(f'plugin_{self.name}', plugin_config)


class PluginManager:
    """
    插件管理器

    负责插件的注册、加载和管理
    """

    def __init__(self, app):
        """
        初始化插件管理器

        Args:
            app: Litefs 应用实例
        """
        self.app = app
        self.plugins: Dict[str, Plugin] = {}
        self.loaded_plugins: List[Plugin] = []
        # 加载失败的插件清单（插件名 → 失败原因）
        self.failed_plugins: Dict[str, str] = {}

    def register(self, plugin_class):
        """
        注册插件

        Args:
            plugin_class: 插件类
        """
        if not issubclass(plugin_class, Plugin):
            raise TypeError("插件必须继承 Plugin 基类")

        plugin_name = plugin_class.name
        if not plugin_name:
            raise ValueError("插件必须设置 name 属性")

        self.plugins[plugin_name] = plugin_class

    def load_all(self):
        """
        加载所有注册的插件

        单个插件失败（含依赖缺失等异常）只记录日志与失败清单，
        不中断其余插件的加载（异常隔离）。
        """
        for plugin_name in list(self.plugins):
            try:
                self.load(plugin_name)
            except Exception as e:
                reason = "插件 %s 加载失败: %s" % (plugin_name, e)
                logger.error(reason)
                self.failed_plugins[plugin_name] = str(e)

    def load(self, plugin_name: str) -> bool:
        """
        加载指定插件

        实例化与 initialize 阶段的异常不向外抛出，而是记录到
        日志器与 ``failed_plugins`` 失败清单（异常隔离）；注册级
        错误（插件未注册、依赖未注册）仍抛 ``ValueError``。

        Args:
            plugin_name: 插件名称

        Returns:
            bool: 是否加载成功
        """
        if plugin_name not in self.plugins:
            raise ValueError(f"插件 {plugin_name} 未注册")

        plugin_class = self.plugins[plugin_name]

        # 版本兼容声明检查（未声明 required_litefs_version 时跳过）
        required = getattr(plugin_class, 'required_litefs_version', '') or ''
        if required:
            from .._version import get_version
            current = get_version()
            if _parse_version(required) > _parse_version(current):
                reason = (
                    "插件 %s 要求 litefs >= %s，当前版本 %s，拒绝加载"
                    % (plugin_name, required, current)
                )
                logger.warning(reason)
                self.failed_plugins[plugin_name] = reason
                return False

        # 检查依赖（未注册属于注册级错误，保留抛出语义）
        for dependency in plugin_class.dependencies:
            if dependency not in self.plugins:
                raise ValueError(
                    f"插件 {plugin_name} 依赖 {dependency}，但该插件未注册"
                )
            if not any(p.name == dependency for p in self.loaded_plugins):
                if not self.load(dependency):
                    reason = (
                        "插件 %s 依赖 %s 加载失败" % (plugin_name, dependency)
                    )
                    logger.error(reason)
                    self.failed_plugins[plugin_name] = reason
                    return False

        # 实例化与初始化失败仅记录，不向外抛出（异常隔离）
        try:
            plugin = plugin_class(self.app)
            plugin.initialize()
        except Exception as e:
            reason = "插件 %s 加载失败: %s" % (plugin_name, e)
            logger.error(reason)
            self.failed_plugins[plugin_name] = str(e)
            return False

        # 添加到已加载插件列表
        self.loaded_plugins.append(plugin)
        return True

    def unload(self, plugin_name: str):
        """
        卸载指定插件

        Args:
            plugin_name: 插件名称
        """
        for plugin in self.loaded_plugins:
            if plugin.name == plugin_name:
                plugin.shutdown()
                self.loaded_plugins.remove(plugin)
                break

    def unload_all(self):
        """
        卸载所有插件
        """
        for plugin in reversed(self.loaded_plugins):
            plugin.shutdown()
        self.loaded_plugins.clear()

    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """
        获取指定插件实例

        Args:
            plugin_name: 插件名称

        Returns:
            插件实例或 None
        """
        for plugin in self.loaded_plugins:
            if plugin.name == plugin_name:
                return plugin
        return None

    def get_all_plugins(self) -> List[Plugin]:
        """
        获取所有已加载的插件

        Returns:
            插件实例列表
        """
        return self.loaded_plugins

    def has_plugin(self, plugin_name: str) -> bool:
        """
        检查插件是否已加载

        Args:
            plugin_name: 插件名称

        Returns:
            是否已加载
        """
        return any(plugin.name == plugin_name for plugin in self.loaded_plugins)
