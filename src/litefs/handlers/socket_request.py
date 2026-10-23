#!/usr/bin/env python
# coding: utf-8

"""
原生 Socket 请求处理器请求属性 Mixin（内部拆分模块）

从 :mod:`litefs.handlers.socket` 拆分而来，仅承载
``SocketRequestHandler`` 的请求只读属性（property）集合。
由 ``litefs.handlers.socket`` 统一再导出，禁止外部直接导入本模块。
"""

from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Any

from .._json import loads
from .form import parse_header


class SocketRequestPropertiesMixin:
    """请求属性 Mixin

    依赖宿主 ``SocketRequestHandler`` 装配的属性，
    以下声明仅供类型检查使用，运行时零开销。
    """

    if TYPE_CHECKING:
        _app: Any
        _environ: Any
        _body: Any
        _files: Any
        _get: Any
        _post: Any
        _session_id: Any
        _session: Any

    @property
    def config(self):
        return self._app.config

    @property
    def files(self):
        return self._files or {}

    @property
    def body(self):
        return self._body

    @property
    def json(self):
        body = self._body
        if not self._body:
            return {}
        content_type = self.content_type
        content_type, _ = parse_header(content_type)
        content_type = content_type.lower()
        if content_type not in ("application/json", "application/json-rpc"):
            return {}
        return loads(body)

    @property
    def environ(self):
        return self._environ

    @property
    def params(self):
        return self._get

    @property
    def data(self):
        return self._post

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def request_method(self):
        return self.environ["REQUEST_METHOD"]

    method = request_method

    @property
    def server_protocol(self):
        return self.environ["SERVER_PROTOCOL"]

    @property
    def content_type(self):
        return self.environ.get("CONTENT_TYPE")

    @property
    def charset(self, default="UTF-8"):
        _, params = parse_header(self.content_type)
        return params.get("charset", default)

    @property
    def content_length(self):
        return int(self.environ.get("CONTENT_LENGTH") or -1)

    @property
    def path_info(self):
        return self.environ["PATH_INFO"]

    @property
    def query_string(self):
        return self.environ["QUERY_STRING"]

    @property
    def request_uri(self):
        environ = self.environ
        path_info = environ["PATH_INFO"]
        query_string = environ["QUERY_STRING"]
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self.environ.get("HTTP_REFERER")

    @property
    def cookie(self):
        cookie_str = self.environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie
