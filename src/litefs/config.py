#!/usr/bin/env python
# coding: utf-8

import os
import sys
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class Config:
    """
    配置管理类

    支持多种配置来源：
    1. 默认配置
    2. 配置文件（YAML、JSON、TOML）
    3. 环境变量
    4. 命令行参数
    5. 代码中的配置

    配置优先级（从高到低）：
    代码配置 > 环境变量 > 配置文件 > 默认值
    """

    DEFAULT_CONFIG = {
        'host': 'localhost',
        'port': 9090,
        'webroot': './site',
        'debug': False,
        'not_found': 'not_found',
        'default_page': 'index,index.html',
        'log': './default.log',
        'listen': 1024,
        'max_request_size': 10485760,
        'max_upload_size': 52428800,
        'config_file': None,
    }

    ENV_PREFIX = 'LITEFS_'

    def __init__(self, config_file: Optional[str] = None, **kwargs):
        """
        初始化配置

        Args:
            config_file: 配置文件路径
            **kwargs: 其他配置项
        """
        self._config: Dict[str, Any] = {}
        self._load_default_config()
        
        if config_file:
            self._load_config_file(config_file)
        elif kwargs.get('config_file'):
            self._load_config_file(kwargs['config_file'])
        
        self._load_env_vars()
        self._update_config(kwargs)
    
    def _load_default_config(self):
        """加载默认配置"""
        self._config.update(self.DEFAULT_CONFIG.copy())
    
    def _load_config_file(self, config_file: str):
        """
        加载配置文件

        支持的格式：YAML、JSON、TOML

        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        file_ext = config_path.suffix.lower()
        
        if file_ext in ['.yaml', '.yml']:
            self._load_yaml_config(config_path)
        elif file_ext == '.json':
            self._load_json_config(config_path)
        elif file_ext in ['.toml', '.ini']:
            self._load_toml_config(config_path)
        else:
            raise ValueError(f"不支持的配置文件格式: {file_ext}")
    
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
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
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
        else:
            return value
    
    def _update_config(self, config_data: Dict[str, Any]):
        """
        更新配置

        Args:
            config_data: 配置数据
        """
        for key, value in config_data.items():
            if key in self.DEFAULT_CONFIG:
                self._config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置项

        Args:
            key: 配置键
            value: 配置值
        """
        if key in self.DEFAULT_CONFIG:
            self._config[key] = value
        else:
            raise ValueError(f"未知的配置项: {key}")
    
    def update(self, **kwargs):
        """
        批量更新配置

        Args:
            **kwargs: 配置项
        """
        for key, value in kwargs.items():
            self.set(key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            配置字典
        """
        return self._config.copy()
    
    def __getattr__(self, name: str) -> Any:
        """通过属性访问配置"""
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any):
        """通过属性设置配置"""
        if name.startswith('_') or name == 'ENV_PREFIX':
            super().__setattr__(name, value)
        elif name in self.DEFAULT_CONFIG:
            self._config[name] = value
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"Config({self._config})"
    
    def __contains__(self, key: str) -> bool:
        """检查配置项是否存在"""
        return key in self._config
    
    def keys(self) -> List[str]:
        """获取所有配置键"""
        return list(self._config.keys())
    
    def values(self) -> List[Any]:
        """获取所有配置值"""
        return list(self._config.values())
    
    def items(self) -> List[tuple]:
        """获取所有配置项"""
        return list(self._config.items())


def load_config(
    config_file: Optional[str] = None,
    env_prefix: Optional[str] = None,
    **kwargs
) -> Config:
    """
    加载配置

    Args:
        config_file: 配置文件路径
        env_prefix: 环境变量前缀（默认为 LITEFS_）
        **kwargs: 其他配置项

    Returns:
        Config 对象
    """
    config = Config(config_file=config_file, **kwargs)
    
    if env_prefix:
        config.ENV_PREFIX = env_prefix
        config._load_env_vars()
    
    return config


def merge_configs(*configs: Union[Config, Dict[str, Any]]) -> Config:
    """
    合并多个配置

    Args:
        *configs: 配置对象或字典

    Returns:
        合并后的 Config 对象
    """
    merged_config = Config.__new__(Config)
    merged_config._config = {}
    merged_config._config.update(merged_config.DEFAULT_CONFIG.copy())
    
    for config in configs:
        if isinstance(config, Config):
            merged_config._config.update(config.to_dict())
        elif isinstance(config, dict):
            merged_config._config.update(config)
    
    return merged_config
