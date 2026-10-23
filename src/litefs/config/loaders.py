#!/usr/bin/env python
# coding: utf-8

"""
配置文件加载 Mixin

内部拆分模块：由 litefs.config.core 装配进 Config，不构成公共 API。
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from .._json import load


class ConfigLoadersMixin:
    """多格式配置文件加载能力

    依赖宿主 ``Config`` 装配的实例属性与类常量，
    以下声明仅供类型检查使用，运行时无开销。
    """

    _config: Dict[str, Any]
    DEFAULT_CONFIG: Dict[str, Any]
    ENV_PREFIX: str

    if TYPE_CHECKING:
        # 跨 Mixin 方法：由 Config 核心提供
        def _update_config(self, config_data: Dict[str, Any]) -> None: ...

    def _load_yaml_config(self, config_path: Path):
        """加载 YAML 配置文件"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if config_data:
                    self._update_config(config_data)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")

    def _load_json_config(self, config_path: Path):
        """加载 JSON 配置文件"""
        with open(config_path, 'rb') as f:
            config_data = load(f)
            if config_data:
                self._update_config(config_data)

    def _load_toml_config(self, config_path: Path):
        """加载 TOML 配置文件"""
        try:
            import tomli
            with open(config_path, 'rb') as f:
                config_data = tomli.load(f)
                if config_data:
                    self._update_config(config_data)
        except ImportError:
            try:
                import tomllib
                with open(config_path, 'rb') as f:
                    config_data = tomllib.load(f)
                    if config_data:
                        self._update_config(config_data)
            except ImportError:
                raise ImportError("需要安装 tomli (Python < 3.11): pip install tomli")

    def _load_env_vars(self):
        """加载环境变量"""
        for key, default_value in self.DEFAULT_CONFIG.items():
            env_key = f"{self.ENV_PREFIX}{key.upper()}"
            env_value = os.getenv(env_key)

            if env_value is not None:
                self._config[key] = self._parse_env_value(env_value, default_value)

        # 处理 memcache_servers 配置，确保它是一个列表
        if isinstance(self._config.get('memcache_servers'), str):
            self._config['memcache_servers'] = [
                s.strip() for s in self._config['memcache_servers'].split(',')
            ]

    def _parse_env_value(self, value: str, default_value: Any) -> Any:
        """
        解析环境变量值

        Args:
            value: 环境变量值
            default_value: 默认值，用于推断类型

        Returns:
            解析后的值
        """
        if isinstance(default_value, bool):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default_value, int):
            return int(value)
        elif isinstance(default_value, float):
            return float(value)
        elif isinstance(default_value, list):
            return [v.strip() for v in value.split(',')]
        else:
            return value
