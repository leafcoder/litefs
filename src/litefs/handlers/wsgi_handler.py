#!/usr/bin/env python
# coding: utf-8

"""
兼容性转发模块

此模块已重命名为 wsgi.py，此文件仅为向后兼容保留。
请使用 from litefs.handlers.wsgi import WSGIRequestHandler
"""

from .wsgi import *  # noqa: F401,F403
from .wsgi import WSGIRequestHandler  # noqa: F401

__all__ = ['WSGIRequestHandler']
