#!/usr/bin/env python
# coding: utf-8

"""
兼容性转发模块

此模块已重命名为 base.py，此文件仅为向后兼容保留。
请使用 from litefs.handlers.base import BaseRequestHandler
"""

from .base import *  # noqa: F401,F403
from .base import BaseRequestHandler  # noqa: F401

__all__ = ['BaseRequestHandler']
