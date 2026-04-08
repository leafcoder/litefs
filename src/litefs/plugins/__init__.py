#!/usr/bin/env python
# coding: utf-8

"""
插件系统

提供插件接口定义、加载机制和管理功能
"""

from .base import Plugin, PluginManager
from .loader import PluginLoader

__all__ = ['Plugin', 'PluginManager', 'PluginLoader']
