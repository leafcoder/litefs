#!/usr/bin/env python
# coding: utf-8

"""
原生 Socket 请求处理器响应方法 Mixin（内部拆分模块）

从 :mod:`litefs.handlers.socket` 拆分而来，仅承载
``SocketRequestHandler`` 的响应头与响应内容构造方法
（``_add_header`` / ``_add_response_headers`` / ``set_cookie`` /
``redirect`` / ``_cast``）。
由 ``litefs.handlers.socket`` 统一再导出，禁止外部直接导入本模块。
"""

import itertools
from http.cookies import SimpleCookie
from typing import TYPE_CHECKING, Any

from .._json import dumps


class SocketResponseMixin:
    """响应方法 Mixin

    依赖宿主 ``SocketRequestHandler`` 装配的属性与方法，
    以下声明仅供类型检查使用，运行时零开销。
    """

    if TYPE_CHECKING:
        _response_headers: Any
        _cookies: Any
        _headers_responsed: Any
        _environ: Any
        _status_code: Any
        start_response: Any

    def _add_header(self, key, value):
        # 添加到 _response_headers 字典中
        response_headers = self._response_headers
        response_headers[key] = value

    def _add_response_headers(self, headers):
        for header, value in headers:
            self._response_headers[header] = value

    def set_cookie(self, name, value, **options):
        if self._cookies is None:
            self._cookies = {}
        cookie = SimpleCookie()
        cookie[name] = value
        for key, val in options.items():
            # 将下划线参数转换为连字符形式（如 max_age -> max-age）
            cookie_key = key.replace('_', '-')
            cookie[name][cookie_key] = val
        self._cookies[name] = cookie

    def redirect(self, url=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        url = "/" if url is None else url
        response_headers = self._response_headers
        response_headers["Content-Type"] = "text/html;charset=utf-8"
        host = self._environ.get("HTTP_HOST")
        if not host:
            server_name = self._environ.get("SERVER_NAME", "localhost")
            server_port = self._environ.get("SERVER_PORT", "80")
            if server_port not in ("80", "443"):
                host = "%s:%s" % (server_name, server_port)
            else:
                host = server_name
        scheme = (
            "https"
            if self._environ.get("HTTPS") == "on" or self._environ.get("SERVER_PORT") == "443"
            else "http"
        )
        response_headers["Location"] = "%s://%s%s" % (scheme, host, url)
        status_code = 302
        status_text = "Found"
        content = "%d %s" % (status_code, status_text)
        headers = response_headers.items()
        self.start_response(status_code, headers=headers)
        return content

    def _cast(self, s=None):
        # is_bytes / imap 定义于宿主模块 litefs.handlers.socket，
        # 延迟导入以避免 socket 与本模块之间的模块级循环导入
        from .socket import imap, is_bytes
        response_headers = self._response_headers

        if not s:
            if "Content-Length" not in response_headers:
                response_headers["Content-Length"] = 0
            return []

        # 对于 3xx 重定向响应，设置 Content-Type 为 text/html; charset=utf-8
        if 300 <= self._status_code < 400:
            response_headers["Content-Type"] = "text/html; charset=utf-8"
            # 直接返回空字符串，不需要转换为 JSON 格式
            return [b""]

        content_type = response_headers.get("Content-Type", "")
        is_json_response = "application/json" in content_type

        # 先处理 dict 类型（dict 是 Iterable 但需要特殊处理）
        if isinstance(s, dict):
            if is_json_response:
                try:
                    s = dumps(s)
                except (TypeError, ValueError) as e:
                    raise TypeError("Response data cannot be JSON serialized: %s" % e)
            else:
                s = str(s)

        # 先检查是否是可迭代对象（但不是字符串、字节、元组、列表或字典）
        from collections.abc import Iterable
        if (
            not isinstance(s, (str, bytes, tuple, list, dict, type(None)))
            and isinstance(s, Iterable)
        ):
            try:
                iter_s = iter(s)
                first = next(iter_s)
                while not first:
                    first = next(iter_s)
            except StopIteration:
                return self._cast()
            if is_bytes(first):
                new_iter_s = itertools.chain([first], iter_s)
            elif isinstance(first, str):

                def encoder(item):
                    """将元素编码为 UTF-8 字节串"""
                    return str(item).encode("utf-8")

                new_iter_s = itertools.chain([first], iter_s)
                new_iter_s = imap(encoder, new_iter_s)
            else:
                raise TypeError("response type is not allowd: %s" % type(first))
            return new_iter_s

        if isinstance(s, (tuple, list)):
            if is_json_response:
                s = dumps(s)
            else:
                if len(s) > 0 and (isinstance(s[0], str) or is_bytes(s[0])):
                    first_type = type(s[0])
                    if isinstance(first_type, type) and issubclass(first_type, str):
                        s = [item if isinstance(item, str) else str(item) for item in s]
                        join_chr = s[0][:0]
                        s = join_chr.join(s)
                    else:
                        s = [item if is_bytes(item) else str(item).encode("utf-8") for item in s]
                        join_chr = s[0][:0]
                        s = join_chr.join(s)
                else:
                    s = [str(item) for item in s]
                    s = "".join(s)
        elif not (isinstance(s, str) or is_bytes(s)):
            if is_json_response:
                try:
                    s = dumps(s)
                except (TypeError, ValueError) as e:
                    raise TypeError("Response data cannot be JSON serialized: %s" % e)
            else:
                s = str(s)

        if isinstance(s, str):
            s = s.encode("utf-8")
        if is_bytes(s):
            if "Content-Length" not in response_headers:
                response_headers["Content-Length"] = len(s)
            return [s]
        return []
