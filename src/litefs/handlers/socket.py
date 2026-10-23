#!/usr/bin/env python
# coding: utf-8

"""
原生 Socket 请求处理器

用于 litefs 内置 HTTP 服务器
直接操作 socket 进行请求处理
"""

import re
from errno import EAGAIN, EWOULDBLOCK
from http.cookies import SimpleCookie
from io import DEFAULT_BUFFER_SIZE, StringIO
from urllib.parse import unquote_plus

from .._json import dumps_str
from ..exceptions import HttpError
from ..session import Session
from ..utils import log_error, render_error
from .base import BaseRequestHandler
from .form import (
    parse_form,
    parse_header,
    parse_multipart_asgi,
    parse_multipart_stream,
    read_chunked_body,
)
from .response import (  # noqa: F401  # server_info/server_software 为对外再导出
    DEFAULT_STATUS_MESSAGE,
    default_content_type,
    json_content_type,
    server_info,
    server_software,
)
from .socket_request import SocketRequestPropertiesMixin
from .socket_response import SocketResponseMixin


def is_bytes(s):
    """检查对象是否为字节类型"""
    return isinstance(s, bytes)


def imap(func, iterable):
    """延迟版本的 map"""
    return map(func, iterable)


class SocketRequestHandler(SocketResponseMixin, SocketRequestPropertiesMixin, BaseRequestHandler):
    """
    原生 Socket 请求处理器

    用于 litefs 内置 HTTP 服务器，直接操作 socket 进行请求处理
    """

    default_headers = {
        "Content-Type": default_content_type,
        "Server": server_software,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block"
    }

    def __init__(self, app, rw, environ, request):
        super(SocketRequestHandler, self).__init__(app, environ)
        self._request = request
        self._rw = rw
        self._buffers = StringIO()
        self._response_headers = {}
        self._headers = []  # 显式初始化 _headers 属性，确保它存在
        self._cookies = None
        self._get = parse_form(environ["QUERY_STRING"])
        content_type = environ.get("CONTENT_TYPE", "")
        self.content_type_raw = content_type_raw = content_type
        content_type, content_type_params = parse_header(content_type)
        self._post = {}
        self._body = ""
        self._files = {}
        # 读取请求体并设置到 POST_CONTENT
        if content_type:
            content_length_value = environ.get("CONTENT_LENGTH") or 0
            content_length = int(content_length_value) if content_length_value else 0

            if content_length > 0:
                max_request_size = getattr(app.config, "max_request_size", 10485760)
                if content_length > max_request_size:
                    raise HttpError(
                        413, f"Request body too large. Maximum size is {max_request_size} bytes"
                    )

            # chunked 传输编码（无 Content-Length）：解码请求体（修复 D11）
            chunked_body = None
            transfer_encoding = ""
            for te_key in ("HTTP_TRANSFER_ENCODING", "TRANSFER_ENCODING"):
                if environ.get(te_key):
                    transfer_encoding = str(environ[te_key]).lower()
                    break
            if "chunked" in transfer_encoding:
                max_request_size = getattr(app.config, "max_request_size", 10485760)
                chunked_body = read_chunked_body(rw.readline, rw.read, max_request_size)
                environ["CONTENT_LENGTH"] = str(len(chunked_body))
                content_length = len(chunked_body)

            if content_length:
                if content_type_raw == "application/x-www-form-urlencoded":
                    post_content = (
                        chunked_body if chunked_body is not None
                        else rw.read(int(content_length))
                    )
                    self._post = parse_form(post_content)
                    self._body = post_content
                elif content_type_raw.startswith("multipart/form-data"):
                    boundary = content_type_params.get("boundary", None)
                    if chunked_body is not None:
                        self._post, self._files = parse_multipart_asgi(
                            chunked_body, boundary,
                            getattr(app.config, "max_upload_size", 52428800),
                        )
                    else:
                        self._post, self._files = self._parse_multipart(rw, boundary)
                else:
                    post_content = (
                        chunked_body if chunked_body is not None
                        else rw.read(int(content_length))
                    )
                    environ["POST_CONTENT"] \
                        = unquote_plus(post_content.decode("utf-8"))
                    self._body = post_content
        self._session_id, self._session = self._get_session(environ)
        self._middlewares = app._get_middleware_instances()

    def _parse_multipart(self, rw, boundary):
        """
        解析 multipart 表单数据（流式版本）

        Args:
            rw: 读写流对象
            boundary: multipart boundary

        Returns:
            (posts, files): 表单字段字典和上传文件字典
        """
        return parse_multipart_stream(
            rw, boundary,
            getattr(self._app.config, "max_upload_size", 52428800),
            DEFAULT_BUFFER_SIZE
        )

    def _get_session(self, environ):
        app = self._app
        sessions = app.sessions
        session_name = app.config.session_name
        cookie = environ.get("HTTP_COOKIE")
        cookie = SimpleCookie(cookie)
        morsel = cookie.get(session_name)
        if morsel is not None:
            session_id = morsel.value
            session = sessions.get(session_id)
            if session is not None:
                # 设置存储后端实例，确保数据修改时自动保存
                session.store = sessions
                return session_id, session

        session_id = self._new_session_id()
        # 创建 Session 对象时传入存储后端实例
        session = Session(session_id, store=sessions)
        sessions.put(session_id, session)
        return None, session

    def handle_response(self, result):
        """
        处理响应结果，支持 Response 对象
        """
        from .response import Response
        if isinstance(result, Response):
            self._status_code = result.status_code
            for header, value in result.headers:
                self._add_header(header, value)
            content = result.content
            if isinstance(content, dict):
                return dumps_str(content)
            return content
        return result

    def _build_response_headers(self, status_code, extra_headers=None, content=None):
        """
        重写基类方法，为 socket handler 添加特定的响应头处理

        Args:
            status_code: HTTP 状态码
            extra_headers: 额外的响应头
            content: 响应内容

        Returns:
            响应头字典
        """
        # 添加 self._response_headers 中的响应头
        existing_header_names = [h[0].lower() for h in (extra_headers or [])]
        for header, value in self._response_headers.items():
            if header.lower() not in existing_header_names:
                # 转换为元组格式
                if extra_headers is None:
                    extra_headers = []
                if not any(h[0].lower() == header.lower() for h in extra_headers):
                    extra_headers.append((header, value))

        # 添加标准头部
        standard_headers = [
            ("Server", server_software),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "SAMEORIGIN"),
            ("X-XSS-Protection", "1; mode=block")
        ]

        # 检查并添加标准头部，避免重复
        if extra_headers is None:
            extra_headers = []
        existing_header_names = [h[0].lower() for h in extra_headers]
        for header in standard_headers:
            if header[0].lower() not in existing_header_names:
                extra_headers.append(header)

        # 检查是否已经有 Content-Type 响应头
        has_content_type = any(h[0].lower() == 'content-type' for h in extra_headers)

        if status_code >= 400:
            if not has_content_type:
                extra_headers = [("Content-Type", "text/html; charset=utf-8")] + list(extra_headers)
        elif not has_content_type:
            from collections.abc import Iterable

            if isinstance(content, (dict, list, tuple)):
                # dict、list、tuple 返回 JSON
                extra_headers = [("Content-Type", json_content_type)] + list(extra_headers)
            elif isinstance(content, str) and content.lstrip().startswith('<'):
                # HTML 内容
                extra_headers = [("Content-Type", "text/html; charset=utf-8")] + list(extra_headers)
            elif isinstance(content, bytes):
                # 字节内容，默认为二进制流
                extra_headers = [("Content-Type", "application/octet-stream")] + list(extra_headers)
            elif (
                not isinstance(content, (str, bytes, type(None)))
                and isinstance(content, Iterable)
            ):
                # 其他可迭代对象
                extra_headers = [
                    ("Content-Type", "text/plain; charset=utf-8")
                ] + list(extra_headers)
            else:
                # 其他类型默认为 text/html
                extra_headers = [("Content-Type", default_content_type)] + list(extra_headers)

        # 转换为字典返回
        headers_dict = {}
        for header, value in extra_headers:
            headers_dict[header] = value

        return headers_dict

    def _response(self, status_code, headers=None, content=None):
        """
        生成响应的兼容方法

        Args:
            status_code: HTTP 状态码
            headers: 响应头
            content: 响应内容

        Returns:
            content
        """
        from http.client import responses as http_status_codes

        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        status_code = int(status_code)
        status_text = http_status_codes.get(status_code, "Unknown")

        if headers is None:
            headers = []

        # 添加 self._response_headers 中的响应头
        existing_header_names = [h[0].lower() for h in headers]
        for header, value in self._response_headers.items():
            if header.lower() not in existing_header_names:
                headers.append((header, value))

        # 添加标准头部
        standard_headers = [
            ("Server", server_software),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "SAMEORIGIN"),
            ("X-XSS-Protection", "1; mode=block")
        ]

        # 检查并添加标准头部，避免重复
        existing_header_names = [h[0].lower() for h in headers]
        for header in standard_headers:
            if header[0].lower() not in existing_header_names:
                headers.append(header)

        # 检查是否已经有 Content-Type 响应头
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)

        if status_code >= 400:
            if not has_content_type:
                headers = [("Content-Type", "text/html; charset=utf-8")] + list(headers)
        elif not has_content_type:
            from collections.abc import Iterable

            if isinstance(content, (dict, list, tuple)):
                # dict、list、tuple 返回 JSON
                headers = [("Content-Type", json_content_type)] + list(headers)
            elif isinstance(content, str) and content.lstrip().startswith('<'):
                # HTML 内容
                headers = [("Content-Type", "text/html; charset=utf-8")] + list(headers)
            elif isinstance(content, bytes):
                # 字节内容，默认为二进制流
                headers = [("Content-Type", "application/octet-stream")] + list(headers)
            elif (
                not isinstance(content, (str, bytes, type(None)))
                and isinstance(content, Iterable)
            ):
                # 其他可迭代对象
                headers = [("Content-Type", "text/plain; charset=utf-8")] + list(headers)
            else:
                # 其他类型默认为 text/html
                headers = [("Content-Type", default_content_type)] + list(headers)

        # 设置 session cookie
        if self.session_id is None:
            self.set_cookie(
                self._app.config.session_name,
                self.session.id,
                path="/",
                secure=self._app.config.session_secure,
                httponly=self._app.config.session_http_only,
                samesite=self._app.config.session_same_site
            )

        # 保存 Session 数据到 Session 存储
        self._app.sessions.put(self.session.id, self.session)

        # 检查是否已经有 Content-Length 或 Transfer-Encoding 头
        has_content_length = any(h[0].lower() == 'content-length' for h in headers)
        has_transfer_encoding = any(h[0].lower() == 'transfer-encoding' for h in headers)

        # 处理不同类型的 content
        from collections.abc import Iterable
        if not has_content_length and not has_transfer_encoding:
            if isinstance(content, (str, bytes)):
                # 对于字符串或字节，计算长度并添加 Content-Length 头
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                    content_length = len(content_bytes)
                else:
                    content_length = len(content)
                headers.append(("Content-Length", str(content_length)))
            elif (
                not isinstance(content, (dict, list, tuple, type(None)))
                and isinstance(content, Iterable)
            ):
                # 对于生成器等可迭代对象，使用 Transfer-Encoding: chunked
                headers.append(("Transfer-Encoding", "chunked"))

        self.start_response(status_code, headers=headers)
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                "code": status_code,
                "message": status_text,
                "explain": status_text,
            }
        return content

    def finish(self, content):
        """
        完成响应并写入 socket
        """
        try:
            rw = self._rw

            if (
                isinstance(content, (list, tuple))
                and len(content) == 3
                and isinstance(content[0], str)
                and isinstance(content[1], list)
            ):
                status_line, response_headers, response_content = content
                status_code = int(status_line.split()[0])
                status_text = "Unknown"

                from http.client import responses as http_status_codes
                status_text = http_status_codes.get(status_code, "Unknown")

                for header_name, header_value in response_headers:
                    if header_name.lower() == 'set-cookie':
                        if self._cookies is None:
                            self._cookies = {}
                        cookie = SimpleCookie()
                        cookie.load(header_value)
                        for key, morsel in cookie.items():
                            self._cookies[key] = morsel
                    else:
                        self._response_headers[header_name] = header_value

                content = response_content
            else:
                status_code = self._status_code
                from http.client import responses as http_status_codes
                status_text = http_status_codes.get(status_code, "Unknown")

            line = "HTTP/1.1 %d %s\r\n" % (status_code, status_text)
            line = line.encode("utf-8")
            rw.write(line)
            headers = self._response_headers.copy()

            # 添加标准头部（如果不存在）
            standard_headers = {
                "Server": server_software,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "SAMEORIGIN",
                "X-XSS-Protection": "1; mode=block"
            }

            for header, value in standard_headers.items():
                if header not in headers:
                    headers[header] = value

            # 如果没有 Content-Type 头部，根据内容类型设置
            if "Content-Type" not in headers:
                # 对于 3xx 重定向响应，设置 Content-Type 为 text/html; charset=utf-8
                if 300 <= status_code < 400:
                    content_type_value = "text/html; charset=utf-8"
                elif isinstance(content, (dict, list, tuple)):
                    # dict、list、tuple 返回 JSON
                    content_type_value = json_content_type
                elif isinstance(content, str) and content.lstrip().startswith('<'):
                    # HTML 内容
                    content_type_value = "text/html; charset=utf-8"
                elif isinstance(content, bytes):
                    # 字节内容，默认为二进制流
                    content_type_value = "application/octet-stream"
                else:
                    # 其他类型默认为 text/html
                    content_type_value = default_content_type
                headers["Content-Type"] = content_type_value
                self._response_headers["Content-Type"] = content_type_value

            # 检查是否已经有 Content-Length 或 Transfer-Encoding 头
            has_content_length = "Content-Length" in headers
            has_transfer_encoding = "Transfer-Encoding" in headers

            # 处理不同类型的 content
            from collections.abc import Iterable
            if not has_content_length and not has_transfer_encoding:
                if isinstance(content, (str, bytes)):
                    # 对于字符串或字节，计算长度并添加 Content-Length 头
                    if isinstance(content, str):
                        content_bytes = content.encode('utf-8')
                        content_length = len(content_bytes)
                    else:
                        content_length = len(content)
                    headers["Content-Length"] = str(content_length)
                elif (
                    not isinstance(content, (dict, list, tuple, type(None)))
                    and isinstance(content, Iterable)
                ):
                    # 对于生成器等可迭代对象，使用 Transfer-Encoding: chunked
                    headers["Transfer-Encoding"] = "chunked"

            # 写入头部
            for header, value in headers.items():
                line = "%s: %s\r\n" % (header, value)
                line = line.encode("utf-8")
                rw.write(line)
            if self._cookies:
                for c in self._cookies.values():
                    # 直接使用 cookie 的输出，它已经包含了完整的 Set-Cookie 头部
                    line = str(c) + "\r\n"
                    line = line.encode("utf-8")
                    rw.write(line)
            rw.write("\r\n".encode("utf-8"))
            # 对于 3xx 重定向响应，直接返回空字符串，不需要转换为 JSON 格式
            if 300 <= status_code < 400:
                rw.write(b"")
            else:
                # 检查是否使用 chunked 编码
                if (
                    has_transfer_encoding
                    and headers.get("Transfer-Encoding", "").lower() == "chunked"
                ):
                    # 使用 chunked 编码格式写入数据
                    for chunk in self._cast(content):
                        # 计算 chunk 长度并转换为十六进制
                        chunk_length = len(chunk)
                        # 写入 chunk 长度（十六进制）+ 回车换行
                        rw.write(f"{chunk_length:x}\r\n".encode("utf-8"))
                        # 写入 chunk 数据
                        rw.write(chunk)
                        # 写入回车换行
                        rw.write(b"\r\n")
                    # 写入结束 chunk
                    rw.write(b"0\r\n\r\n")
                else:
                    # 普通方式写入数据
                    for _ in self._cast(content):
                        rw.write(_)
            rw.close()
        except Exception:
            if not self._headers_responsed:
                try:
                    log_error(self._app.logger)
                    rw = self._rw
                    status_code = 500
                    status_text = "Unknown"
                    from http.client import responses as http_status_codes
                    status_text = http_status_codes.get(status_code, "Unknown")
                    line = "HTTP/1.1 %d %s\r\n" % (status_code, status_text)
                    line = line.encode("utf-8")
                    rw.write(line)
                    rw.write("Content-Type: text/html; charset=utf-8\r\n".encode("utf-8"))
                    rw.write(f"Server: {server_software}\r\n".encode("utf-8"))
                    rw.write("X-Content-Type-Options: nosniff\r\n".encode("utf-8"))
                    rw.write("X-Frame-Options: SAMEORIGIN\r\n".encode("utf-8"))
                    rw.write("X-XSS-Protection: 1; mode=block\r\n".encode("utf-8"))
                    rw.write("\r\n".encode("utf-8"))
                    if self._app.config.debug:
                        error_content = render_error()
                        if isinstance(error_content, str):
                            error_content = error_content.encode("utf-8")
                        rw.write(error_content)
                    else:
                        rw.write(b"500 Internal Server Error")
                    rw.close()
                except Exception:
                    pass
            else:
                try:
                    log_error(self._app.logger)
                except Exception:
                    pass
            raise

    def __del__(self):
        files = self._environ.get("FILES")
        if not files:
            return
        for fp in files.values():
            fp.close()

    def handler(self):
        """
        处理请求的主方法
        """
        app = self._app

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
            content = self.handle_response(middleware_result)
            return app.middleware_manager.process_response(self, content)

        try:
            environ = self.environ
            path_info = environ["PATH_INFO"]
            request_method = environ["REQUEST_METHOD"]

            # 尝试使用路由系统处理请求
            route_match = app.router.match_with_route(path_info, request_method)
            if route_match:
                route, params = route_match
                handler = route.handler
                try:
                    # 将路由参数添加到请求对象
                    setattr(self, 'route_path', route.path)
                    setattr(self, 'route_params', params)
                    setattr(self, 'path_params', params)
                    result = handler(self, **params)

                    # 处理 Response 对象
                    content = self.handle_response(result)

                    if self._headers_responsed:
                        return app.middleware_manager.process_response(self, content)
                    return app.middleware_manager.process_response(
                        self, self._response(self._status_code, content=content)
                    )
                except Exception:
                    log_error(app.logger)
                    if app.config.debug:
                        content = render_error()
                        return app.middleware_manager.process_response(
                            self, self._response(500, content=content)
                        )
                    return app.middleware_manager.process_response(self, self._response(500))

            # 路由未匹配，返回 404
            return app.middleware_manager.process_response(self, self._response(404))
        except Exception as e:
            middleware_result = app.middleware_manager.process_exception(self, e)
            if middleware_result is not None:
                return middleware_result
            raise


# 向后兼容别名
RequestHandler = SocketRequestHandler

# 导出常量以保持向后兼容
EOFS = ("", "\n", "\r\n")
POSTS_HEADER_NAME = "litefs.posts"
FILES_HEADER_NAME = "litefs.files"
should_retry_error = (EWOULDBLOCK, EAGAIN)
double_slash_sub = re.compile(r"\/{2,}").sub
startswith_dot_sub = re.compile(r"\/\.+").sub
suffixes = (".py", ".pyc", ".pyo", ".so")

__all__ = [
    'SocketRequestHandler',
    'RequestHandler',
    'is_bytes',
    'imap',
    'EOFS',
    'POSTS_HEADER_NAME',
    'FILES_HEADER_NAME',
    'should_retry_error',
    'double_slash_sub',
    'startswith_dot_sub',
    'suffixes',
]
