#!/usr/bin/env python
# coding: utf-8

"""
配置管理

支持多种配置来源和分层管理
"""

from .core import Config, load_config, merge_configs

__all__ = ["Config", "load_config", "merge_configs"]
