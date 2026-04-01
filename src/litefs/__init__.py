#!/usr/bin/env python
# coding: utf-8

from ._version import (
    __version__,
    __version_info__,
    __license__,
    __author__,
    __email__,
)

__doc__ = """\
Build a web server framework using Python. Litefs was developed to imple\
ment a server framework that can quickly, securely, and flexibly build Web \
projects. Litefs is a high-performance HTTP server. Litefs has the characte\
ristics of high stability, rich functions, and low system consumption.

Author: leafcoder
Email: leafcoder@gmail.com

Copyright (c) 2020, Leafcoder.
License: MIT (see LICENSE for details)
"""

from .cache import (
    CacheBackend,
    CacheFactory,
    CacheManager,
    FileEventHandler,
    LiteFile,
    MemoryCache,
    RedisCache,
    TreeCache,
    get_global_cache,
)
from .cli import main as cli_main
from .config import Config, load_config, merge_configs
from .core import Litefs, _cmd_args, make_config, make_server, test_server
from .error_pages import ErrorPageRenderer
from .exceptions import HttpError
from .handlers import RequestHandler, WSGIRequestHandler, EnhancedRequestHandler, parse_form
from .middleware import MiddlewareManager

from .server import HTTPServer, TCPServer, WSGIServer, mainloop, make_environ, make_headers
from .session import Session
from .utils import gmt_date, log_debug, log_error, log_info, make_logger, render_error
from .validators import (
    ValidationError,
    Validator,
    RequiredValidator,
    TypeValidator,
    StringValidator,
    NumberValidator,
    EmailValidator,
    URLValidator,
    ChoiceValidator,
    RegexValidator,
    FormValidator,
    required,
    string_type,
    number_type,
    email,
    url,
    choice,
    regex,
)

__all__ = [
    "Litefs",
    "Config",
    "load_config",
    "merge_configs",
    "make_config",
    "make_server",
    "test_server",
    "_cmd_args",
    "cli_main",
    "TreeCache",
    "MemoryCache",
    "RedisCache",
    "CacheBackend",
    "CacheFactory",
    "CacheManager",
    "get_global_cache",
    "LiteFile",
    "FileEventHandler",
    "Session",
    "RequestHandler",
    "WSGIRequestHandler",
    "parse_form",
    "new_module",
    "HTTPServer",
    "WSGIServer",
    "TCPServer",
    "make_environ",
    "make_headers",
    "mainloop",
    "HttpError",
    "make_logger",
    "log_error",
    "log_info",
    "log_debug",
    "render_error",
    "gmt_date",
    "__version__",
    "__version_info__",
    "__license__",
    "__author__",
    "__email__",
    "ErrorPageRenderer",
    "EnhancedRequestHandler",
    "ValidationError",
    "Validator",
    "RequiredValidator",
    "TypeValidator",
    "StringValidator",
    "NumberValidator",
    "EmailValidator",
    "URLValidator",
    "ChoiceValidator",
    "RegexValidator",
    "FormValidator",
    "required",
    "string_type",
    "number_type",
    "email",
    "url",
    "choice",
    "regex",
]
