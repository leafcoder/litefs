#!/usr/bin/env python
# coding: utf-8

"""
插件加载器

从文件系统加载插件
"""

import os
import importlib.util
import sys
from pathlib import Path
from typing import List, Dict, Any

from .base import Plugin


class PluginLoader:
    """
    插件加载器
    
    从指定目录加载插件
    """
    
    def __init__(self, app):
        """
        初始化插件加载器
        
        Args:
            app: Litefs 应用实例
        """
        self.app = app
        self.plugin_dirs: List[str] = []
    
    def add_plugin_dir(self, plugin_dir: str):
        """
        添加插件目录
        
        Args:
            plugin_dir: 插件目录路径
        """
        if plugin_dir not in self.plugin_dirs:
            self.plugin_dirs.append(plugin_dir)
    
    def load_plugins(self) -> Dict[str, Plugin]:
        """
        加载所有插件
        
        Returns:
            插件类字典
        """
        plugins = {}
        
        for plugin_dir in self.plugin_dirs:
            self._load_plugins_from_dir(plugin_dir, plugins)
        
        return plugins
    
    def _load_plugins_from_dir(self, plugin_dir: str, plugins: Dict[str, Plugin]):
        """
        从指定目录加载插件
        
        Args:
            plugin_dir: 插件目录路径
            plugins: 插件类字典
        """
        plugin_path = Path(plugin_dir)
        if not plugin_path.exists():
            return
        
        for item in plugin_path.iterdir():
            if item.is_dir():
                # 检查是否是插件目录（包含 __init__.py 文件）
                init_file = item / "__init__.py"
                if init_file.exists():
                    self._load_plugin_from_dir(item, plugins)
            elif item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                # 直接加载 .py 文件作为插件
                self._load_plugin_from_file(item, plugins)
    
    def _load_plugin_from_dir(self, plugin_dir: Path, plugins: Dict[str, Plugin]):
        """
        从目录加载插件
        
        Args:
            plugin_dir: 插件目录路径
            plugins: 插件类字典
        """
        try:
            # 创建模块名称
            module_name = f"plugin_{plugin_dir.name}"
            
            # 加载模块
            spec = importlib.util.spec_from_file_location(module_name, plugin_dir / "__init__.py")
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # 查找插件类
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                        if hasattr(obj, 'name') and obj.name:
                            plugins[obj.name] = obj
        except Exception as e:
            print(f"加载插件目录 {plugin_dir} 失败: {e}")
    
    def _load_plugin_from_file(self, plugin_file: Path, plugins: Dict[str, Plugin]):
        """
        从文件加载插件
        
        Args:
            plugin_file: 插件文件路径
            plugins: 插件类字典
        """
        try:
            # 创建模块名称
            module_name = f"plugin_{plugin_file.stem}"
            
            # 加载模块
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # 查找插件类
                for name, obj in module.__dict__.items():
                    if isinstance(obj, type) and issubclass(obj, Plugin) and obj != Plugin:
                        if hasattr(obj, 'name') and obj.name:
                            plugins[obj.name] = obj
        except Exception as e:
            print(f"加载插件文件 {plugin_file} 失败: {e}")
