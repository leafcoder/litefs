#!/usr/bin/env python
# coding: utf-8
"""
LiteFS 请求处理模块

此模块重新导出所有请求处理相关的类和函数，
以保持向后兼容性。
"""

# 从各拆分模块导入
from .response import (
    Response,
    DEFAULT_STATUS_MESSAGE,
    default_content_type,
    json_content_type,
)

from .form_parser import (
    parse_header,
    parse_form,
    parse_multipart_wsgi,
    parse_multipart_asgi,
    parse_multipart_stream,
    _form_cache,
    form_dict_match,
)

from .base_handler import BaseRequestHandler
from .wsgi_handler import WSGIRequestHandler
from .asgi_handler import ASGIRequestHandler
from .socket_handler import (
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

from http.client import responses as http_status_codes
from .._version import __version__

server_info = f"litefs/{__version__} python/{__import__('sys').version.split()[0]}"


__all__ = [
    # 请求处理器
    "RequestHandler",
    "WSGIRequestHandler",
    "ASGIRequestHandler",
    "BaseRequestHandler",
    "SocketRequestHandler",

    # 响应
    "Response",

    # 工具函数
    "parse_form",
    "parse_header",
    "parse_multipart_wsgi",
    "parse_multipart_asgi",
    "parse_multipart_stream",
    "is_bytes",
    "imap",
    "form_dict_match",

    # 常量
    "DEFAULT_STATUS_MESSAGE",
    "default_content_type",
    "json_content_type",
    "server_info",
    "http_status_codes",
    "EOFS",
    "POSTS_HEADER_NAME",
    "FILES_HEADER_NAME",
    "should_retry_error",
    "double_slash_sub",
    "startswith_dot_sub",
    "suffixes",

    # 内部使用
    "_form_cache",
]
