#!/usr/bin/env python
# coding: utf-8

"""
兼容性转发模块

此模块已重命名为 socket.py，此文件仅为向后兼容保留。
请使用 from litefs.handlers.socket import SocketRequestHandler
"""

from .socket import *  # noqa: F401,F403
from .socket import (  # noqa: F401
    SocketRequestHandler,
    RequestHandler,
    is_bytes,
    imap,
    EOFS,
    POSTS_HEADER_NAME,
    FILES_HEADER_NAME,
    should_retry_error,
    double_slash_sub,
    startswith_dot_sub,
    suffixes,
)

__all__ = [
    'SocketRequestHandler',
    'RequestHandler',
    'is_bytes',
    'imap',
]
