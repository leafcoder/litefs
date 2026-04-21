#!/usr/bin/env python
# coding: utf-8

"""
请求处理器基类

提供所有请求处理器共用的基础功能
"""

import json
from hashlib import sha256
from http.cookies import SimpleCookie
from http.client import responses as http_status_codes
from os import urandom

from .response import (
    DEFAULT_STATUS_MESSAGE,
    default_content_type,
    json_content_type,
    server_info,
)
from .form import parse_form, parse_header


class BaseRequestHandler:
    """
    请求处理器基类，提供通用的请求处理功能

    所有 WSGI/ASGI/Socket 请求处理器共享的属性和方法集中在此，
    减少子类间的代码重复。
    """

    def __init__(self, app, environ):
        self._app = app
        self._environ = environ
        self._headers_responsed = False
        self._status_code = 200
        self._get = {}
        self._post = {}
        self._body = ""
        self._files = {}
        self._session_id = None
        self._session = None
        self._session_modified = False
        self._session_loaded = False
        self._template_lookup = None
        # 初始化 _headers 属性，用于存储响应头
        self._headers = []

    # ==================== 模板渲染 ====================

    def render_template(self, template_name, **kwargs):
        """
        渲染模板

        Args:
            template_name: 模板文件名
            **kwargs: 模板变量

        Returns:
            渲染后的 HTML 字符串
        """
        import os

        # 延迟初始化模板查找器
        if self._template_lookup is None:
            # 获取模板目录路径
            template_dir = getattr(self._app.config, 'template_dir', 'templates')
            if not os.path.isabs(template_dir):
                # 如果是相对路径，相对于当前工作目录
                template_dir = os.path.join(os.getcwd(), template_dir)

            # 创建模板查找器
            # 在开发模式下禁用缓存，确保模板修改后立即生效
            debug_mode = getattr(self._app, 'debug', False) if self._app else False
            from mako.lookup import TemplateLookup
            self._template_lookup = TemplateLookup(
                directories=[template_dir],
                input_encoding='utf-8',
                encoding_errors='replace',
                cache_enabled=not debug_mode
            )

        try:
            # 获取模板
            template = self._template_lookup.get_template(template_name)
            # 渲染模板
            content = template.render(**kwargs)

            # 直接返回渲染后的内容，不设置 Content-Type
            # Content-Type 会在 _response 方法中设置
            return content
        except Exception as e:
            # 模板渲染失败，返回错误信息
            import traceback
            error_detail = traceback.format_exc()
            error_content = f"<h1>Template Error</h1><p>Failed to render template '{template_name}': {str(e)}</p><pre>{error_detail}</pre>"

            # 直接返回错误内容，不设置 Content-Type
            # Content-Type 会在 _response 方法中设置
            return error_content

    # ==================== 会话管理 ====================

    def _new_session_id(self):
        """生成新的会话 ID（SHA256 随机值，确保唯一）"""
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    def _build_session_cookie_header(self, session_key):
        """
        构建会话 Cookie 头部

        Args:
            session_key: 会话 ID

        Returns:
            Set-Cookie 头部值
        """
        app = self._app
        session_name = app.config.session_name
        session_secure = app.config.session_secure
        session_http_only = app.config.session_http_only
        session_same_site = app.config.session_same_site
        cookie_header = SimpleCookie()
        cookie_header[session_name] = session_key
        cookie_header[session_name]['path'] = "/"
        if session_secure:
            cookie_header[session_name]['secure'] = True
        if session_http_only:
            cookie_header[session_name]['httponly'] = True
        if session_same_site:
            cookie_header[session_name]['samesite'] = session_same_site
        return str(cookie_header[session_name])

    def _save_session_to_store(self):
        """
        保存会话到存储并返回 session_key。

        Returns:
            session_key 如果会话已加载且有 ID，否则 None
        """
        app = self._app
        session_key = None

        if self._session_loaded:
            session_key = self._session_id or self.session.id
            if self._session_modified:
                app.sessions.put(session_key, self.session)

        return session_key

    # ==================== 响应构建 ====================

    def start_response(self, status_code=200, headers=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        self._status_code = int(status_code)
        if headers is not None:
            for header in headers:
                if not isinstance(header, (list, tuple)):
                    header = header.encode("utf-8")
                    k, v = header.split(":")
                    k, v = k.strip(), v.strip()
                else:
                    k, v = header
                self._add_header(k, v)
        self._headers_responsed = True

    def _add_header(self, key, value):
        self._headers.append((key, value))

    def _add_response_headers(self, headers):
        headers.extend(self._headers)

    def set_cookie(self, key, value, **kwargs):
        cookie = SimpleCookie()
        cookie[key] = value
        for k, v in kwargs.items():
            if not v:
                continue
            cookie[key][k] = v
        self._headers.append(("Set-Cookie", str(cookie[key])))

    def _redirect(self, url):
        url = "/" if url is None else url
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Location", url)]
        status_code = 302
        status_text = "Found"
        content = "%d %s" % (status_code, status_text)
        return self._response(status_code, headers=headers, content=content)

    def _build_response_headers(self, status_code, extra_headers=None, content=None):
        """
        构建响应头列表

        Args:
            status_code: HTTP 状态码
            extra_headers: 额外的响应头
            content: 响应内容

        Returns:
            响应头列表
        """
        # 创建响应头列表
        response_headers = []
        response_headers.append(("Server", server_info))
        response_headers.append(("X-Content-Type-Options", "nosniff"))
        response_headers.append(("X-Frame-Options", "SAMEORIGIN"))
        response_headers.append(("X-XSS-Protection", "1; mode=block"))

        # 添加 self._headers 中的内容
        if hasattr(self, '_headers'):
            response_headers.extend(self._headers)

        # 添加传入的 headers 参数
        if extra_headers:
            response_headers.extend(extra_headers)

        # 检查是否已经有 Content-Type 响应头
        has_content_type = any(h[0].lower() == 'content-type' for h in response_headers)

        # 如果没有 Content-Type 响应头，根据状态码和内容类型设置默认的 Content-Type
        if not has_content_type:
            if status_code >= 400:
                response_headers.append(("Content-Type", "text/html; charset=utf-8"))
            else:
                from collections.abc import Iterable

                # dict、list、tuple 类型设置为 application/json
                if isinstance(content, (dict, list, tuple)):
                    response_headers.append(("Content-Type", json_content_type))
                # HTML 字符串设置为 text/html
                elif isinstance(content, str) and content.lstrip().startswith('<'):
                    response_headers.append(("Content-Type", "text/html; charset=utf-8"))
                # 字节类型设置为 application/octet-stream
                elif isinstance(content, bytes):
                    response_headers.append(("Content-Type", "application/octet-stream"))
                # 其他可迭代对象设置为 text/plain
                elif not isinstance(content, (str, bytes, type(None))) and isinstance(content, Iterable):
                    response_headers.append(("Content-Type", "text/plain; charset=utf-8"))
                # 其他类型使用默认的 text/html
                else:
                    response_headers.append(("Content-Type", default_content_type))

        # 检查是否已经有 Content-Length 或 Transfer-Encoding 头
        has_content_length = any(h[0].lower() == 'content-length' for h in response_headers)
        has_transfer_encoding = any(h[0].lower() == 'transfer-encoding' for h in response_headers)

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
                response_headers.append(("Content-Length", str(content_length)))
            elif not isinstance(content, (dict, list, tuple, type(None))) and isinstance(content, Iterable):
                # 对于生成器等可迭代对象，使用 Transfer-Encoding: chunked
                response_headers.append(("Transfer-Encoding", "chunked"))

        return response_headers

    def _prepare_response(self, status_code, extra_headers=None, content=None):
        """
        准备响应的内部方法，处理会话和设置响应头

        Args:
            status_code: HTTP 状态码
            extra_headers: 额外的响应头
            content: 响应内容

        Returns:
            (status, response_headers, content): 状态行、响应头和内容
        """
        status_code = int(status_code)
        status_text = http_status_codes.get(status_code, "Unknown")
        status = "%d %s" % (status_code, status_text)

        # 构建响应头
        response_headers = self._build_response_headers(status_code, extra_headers, content)

        # 处理会话
        self._process_session_response(response_headers)

        # 标记响应头已发送
        self._headers_responsed = True

        # 如果 content 为 None，设置默认的错误信息
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                "code": status_code,
                "message": status_text,
                "explain": status_text,
            }

        return status, response_headers, content

    def _process_session_response(self, response_headers):
        """
        处理会话相关的响应

        Args:
            response_headers: 响应头列表
        """
        session_key = self._save_session_to_store()

        # 设置 session cookie（只有在会话已加载时）
        if session_key:
            session_name = self._app.config.session_name
            session_secure = self._app.config.session_secure
            session_http_only = self._app.config.session_http_only
            session_same_site = self._app.config.session_same_site
            cookie_header = SimpleCookie()
            cookie_header[session_name] = session_key
            cookie_header[session_name]['path'] = "/"
            if session_secure:
                cookie_header[session_name]['secure'] = True
            if session_http_only:
                cookie_header[session_name]['httponly'] = True
            if session_same_site:
                cookie_header[session_name]['samesite'] = session_same_site
            response_headers.append(("Set-Cookie", str(cookie_header[session_name])))

    def _response(self, status_code, headers=None, content=None):
        """
        生成响应的兼容方法

        Args:
            status_code: HTTP 状态码
            headers: 响应头
            content: 响应内容

        Returns:
            (status, response_headers, content)
        """
        return self._prepare_response(status_code, headers, content)

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
        return json.loads(body)

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
    def charset(self, default="UTF-8"):
        content_type = self.content_type
        if content_type:
            _, params = parse_header(content_type)
            return params.get("charset", default)
        return default

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

    @property
    def headers(self):
        """
        获取所有请求头

        Returns:
            包含所有请求头的字典
        """
        headers = {}
        for key, value in self._environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                headers[header_name] = value
            elif key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                header_name = key.replace('_', '-').lower()
                headers[header_name] = value
        return headers

    def handle_response(self, result):
        """
        处理响应结果，支持 Response 对象
        """
        from .response import Response
        if isinstance(result, Response):
            self._status_code = result.status_code
            for header, value in result.headers:
                self._add_header(header, value)
            return result.content
        return result

    def _process_route_result(self, result, app):
        """
        处理路由处理器的返回结果，统一处理 Response 对象、
        已发送头部的响应、和普通返回值。

        Args:
            result: 路由处理器的返回值
            app: 应用实例

        Returns:
            经过 middleware 处理的响应元组
        """
        from .response import Response
        from http.client import responses as http_status_codes

        # 处理 Response 对象
        if isinstance(result, Response):
            return self._handle_response_object(result, app, http_status_codes)

        if self._headers_responsed:
            return self._handle_headers_responsed(result, app, http_status_codes)

        return self._handle_normal_result(result, app, http_status_codes)

    def _handle_response_object(self, result, app, http_status_codes):
        """处理 Response 对象类型的返回值"""
        # 保存会话
        session_key = self._session_id or self.session.id
        if self._session_modified:
            app.sessions.put(session_key, self.session)

        # 设置 session cookie
        result.headers.append(("Set-Cookie", self._build_session_cookie_header(session_key)))

        status_code = result.status_code
        status_text = http_status_codes.get(status_code, "Unknown")
        status = "%d %s" % (status_code, status_text)
        return app.middleware_manager.process_response(
            self, (status, result.headers, result.content)
        )

    def _handle_headers_responsed(self, result, app, http_status_codes):
        """处理已经调用过 start_response 的情况"""
        # 保存会话
        session_key = self._session_id or self.session.id
        app.sessions.put(session_key, self.session)

        # 设置 session cookie
        self.set_cookie(
            app.config.session_name, session_key,
            path="/",
            secure=app.config.session_secure,
            httponly=app.config.session_http_only,
            samesite=app.config.session_same_site
        )

        status_code = int(self._status_code)
        status_text = http_status_codes.get(status_code, "Unknown")
        status = "%d %s" % (status_code, status_text)

        response_headers = [("Server", server_info)]
        response_headers.extend(self._headers)

        return app.middleware_manager.process_response(
            self, (status, response_headers, result)
        )

    def _handle_normal_result(self, result, app, http_status_codes):
        """处理普通返回值"""
        return app.middleware_manager.process_response(
            self, self._response(self._status_code, content=result)
        )

    def _process_route_error(self, app):
        """处理路由执行过程中的异常"""
        from ..utils import log_error, render_error
        log_error(app.logger)
        if app.config.debug:
            content = render_error()
            return app.middleware_manager.process_response(
                self, self._response(500, content=content)
            )
        return app.middleware_manager.process_response(self, self._response(500))


__all__ = [
    'BaseRequestHandler',
]
