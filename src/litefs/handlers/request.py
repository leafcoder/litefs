#!/usr/bin/env python
# coding: utf-8

"""
LiteFS 请求处理模块（兼容性转发）

此模块已拆分为独立子模块，所有导入转发到新模块。
请直接从 litefs.handlers 导入所需的类和函数。

.. deprecated::
    此模块仅为向后兼容保留，新代码请使用 litefs.handlers 直接导入。
"""

# 从新模块转发所有导入
from .base import BaseRequestHandler
from .wsgi import WSGIRequestHandler
from .asgi import ASGIRequestHandler
from .socket import (
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
from .response import (
    Response,
    DEFAULT_STATUS_MESSAGE,
    default_content_type,
    json_content_type,
    server_info,
    http_status_codes,
)
from .form import (
    parse_header,
    parse_form,
    parse_multipart_wsgi,
    parse_multipart_asgi,
    parse_multipart_stream,
    _form_cache,
    form_dict_match,
)

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
