#!/usr/bin/env python
# coding: utf-8

"""
兼容性转发模块

此模块已重命名为 form.py，此文件仅为向后兼容保留。
请使用 from litefs.handlers.form import parse_form, parse_header
"""

from .form import *  # noqa: F401,F403
from .form import (  # noqa: F401
    parse_form,
    parse_header,
    parse_multipart_wsgi,
    parse_multipart_asgi,
    parse_multipart_stream,
)

__all__ = [
    'parse_form',
    'parse_header',
    'parse_multipart_wsgi',
    'parse_multipart_asgi',
    'parse_multipart_stream',
]
