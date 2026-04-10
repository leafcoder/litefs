#!/usr/bin/env python
# coding: utf-8

"""
版本信息管理

统一管理项目的版本号，避免在多个文件中重复定义
"""

__version__ = "0.5.0"
__version_info__ = (0, 5, 0)
__license__ = "MIT"
__author__ = "Leafcoder"
__email__ = "leafcoder@gmail.com"


def get_version():
    """获取版本字符串"""
    return __version__


def get_version_info():
    """获取版本信息元组"""
    return __version_info__


def get_version_tuple():
    """获取版本元组 (major, minor, micro)"""
    return __version_info__


def get_major_version():
    """获取主版本号"""
    return __version_info__[0]


def get_minor_version():
    """获取次版本号"""
    return __version_info__[1]


def get_micro_version():
    """获取微版本号"""
    return __version_info__[2]


def format_version(major, minor, micro):
    """格式化版本号为字符串"""
    return f"{major}.{minor}.{micro}"


__all__ = [
    "__version__",
    "__version_info__",
    "__license__",
    "__author__",
    "__email__",
    "get_version",
    "get_version_info",
    "get_version_tuple",
    "get_major_version",
    "get_minor_version",
    "get_micro_version",
    "format_version",
]
