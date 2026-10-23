#!/usr/bin/env python
# coding: utf-8

"""
请求处理器请求属性 Mixin（内部拆分模块）

从 :mod:`litefs.handlers.base` 拆分而来，仅承载
``BaseRequestHandler`` 的请求只读属性（property）集合。
由 ``litefs.handlers.base`` 统一再导出，禁止外部直接导入本模块，
不构成公共 API。
"""

from typing import TYPE_CHECKING, Any

from .._json import loads
from .form import parse_header


class RequestPropertiesMixin:
    """请求只读属性 Mixin

    依赖宿主 ``BaseRequestHandler`` 装配的属性，
    以下声明仅供类型检查使用，运行时零开销。
    """

    if TYPE_CHECKING:
        _app: Any
        _environ: Any
        _session_id: Any
        _session: Any
        _get: Any
        _post: Any
        _body: Any
        _files: Any
        _request_headers: Any

    # ==================== 请求属性（共享） ====================

    @property
    def config(self):
        return self._app.config

    @property
    def app(self):
        """
        获取应用实例

        Returns:
            应用实例
        """
        return self._app

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def get(self):
        return self._get

    @property
    def post(self):
        return self._post

    @property
    def body(self):
        return self._body

    @property
    def files(self):
        return self._files or {}

    @property
    def form(self):
        """
        表单数据，与 post 属性相同

        Returns:
            表单数据字典
        """
        return self._post

    @property
    def json(self):
        body = self._body
        if not body:
            return {}
        content_type = self._environ.get("CONTENT_TYPE", "")
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
    def request_method(self):
        return self._environ.get("REQUEST_METHOD", "GET")

    method = request_method

    @property
    def server_protocol(self):
        return self._environ.get("SERVER_PROTOCOL", "HTTP/1.1")

    @property
    def content_type(self):
        return self._environ.get("CONTENT_TYPE")

    @property
    def charset(self):
        content_type = self.content_type
        if content_type:
            _, params = parse_header(content_type)
            return params.get("charset", "UTF-8")
        return "UTF-8"

    @property
    def content_length(self):
        return int(self._environ.get("CONTENT_LENGTH", 0) or 0)

    @property
    def path_info(self):
        return self._environ.get("PATH_INFO", "/")

    @property
    def query_string(self):
        return self._environ.get("QUERY_STRING", "")

    @property
    def request_uri(self):
        path_info = self.path_info
        query_string = self.query_string
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self._environ.get("HTTP_REFERER")

    @staticmethod
    def _build_request_headers(environ):
        """
        从 environ 字典中提取所有 HTTP 请求头并缓存

        Args:
            environ: WSGI/ASGI environ 字典

        Returns:
            包含所有请求头的字典
        """
        headers = {}
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                headers[header_name] = value
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                header_name = key.replace('_', '-').lower()
                headers[header_name] = value
        return headers

    @property
    def headers(self):
        """
        获取所有请求头（已缓存，O(1) 访问）

        Returns:
            包含所有请求头的字典
        """
        return self._request_headers
