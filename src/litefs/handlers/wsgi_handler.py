#!/usr/bin/env python
# coding: utf-8

"""
WSGI 请求处理器

用于在 gunicorn、uWSGI 等 WSGI 服务器中运行
符合 PEP 3333 规范
"""

import json
from hashlib import sha256
from http.cookies import SimpleCookie
from os import urandom
from tempfile import TemporaryFile
from urllib.parse import unquote_plus

from ..exceptions import HttpError
from ..session import Session
from ..utils import gmt_date, log_debug, log_error, render_error
from .base_handler import BaseRequestHandler
from .form_parser import parse_form, parse_header, parse_multipart_wsgi


class WSGIRequestHandler(BaseRequestHandler):
    """
    WSGI 请求处理器，用于在 gunicorn、uWSGI 等 WSGI 服务器中运行

    符合 PEP 3333 规范，处理 WSGI environ 并返回标准响应
    """

    def __init__(self, app, environ):
        super(WSGIRequestHandler, self).__init__(app, environ)
        self._environ = self._normalize_environ(environ)
        self._headers = []
        self._get = parse_form(self._environ.get("QUERY_STRING", ""))

        content_type = self._environ.get("CONTENT_TYPE", "")
        if content_type:
            content_type_raw = content_type
            content_type, params = parse_header(content_type)
            content_length_str = self._environ.get("CONTENT_LENGTH") or "0"
            content_length = int(content_length_str) if content_length_str.strip() else 0

            if content_length > 0:
                max_request_size = getattr(app.config, "max_request_size", 10485760)
                if content_length > max_request_size:
                    raise HttpError(
                        413, f"Request body too large. Maximum size is {max_request_size} bytes"
                    )

            if content_type_raw == "application/x-www-form-urlencoded":
                if content_length > 0:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        post_content = wsgi_input.read(content_length)
                        post_content = post_content.decode("utf-8")
                        self._post = parse_form(post_content)
            elif content_type_raw.startswith("multipart/form-data"):
                boundary = params.get("boundary")
                if boundary:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        content_length_str = self._environ.get("CONTENT_LENGTH") or "0"
                        content_length = (
                            int(content_length_str) if content_length_str.strip() else 0
                        )
                        if content_length > 0:
                            self._post, self._files = parse_multipart_wsgi(
                                wsgi_input, boundary, content_length,
                                getattr(app.config, "max_upload_size", 52428800)
                            )
            else:
                if content_length > 0:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        self._body = wsgi_input.read(content_length)
                        self._body = self._body.decode("utf-8")

        self._session_id, self._session = self._get_session()
        self._middlewares = app._get_middleware_instances()

    def _normalize_environ(self, environ):
        normalized = dict(environ)

        if "PATH_INFO" not in normalized:
            normalized["PATH_INFO"] = "/"

        if "REQUEST_METHOD" not in normalized:
            normalized["REQUEST_METHOD"] = "GET"

        if "QUERY_STRING" not in normalized:
            normalized["QUERY_STRING"] = ""

        if "CONTENT_LENGTH" not in normalized:
            normalized["CONTENT_LENGTH"] = "0"
        else:
            content_length = normalized.get("CONTENT_LENGTH", "0")
            if content_length == "" or content_length is None:
                normalized["CONTENT_LENGTH"] = "0"

        if "CONTENT_TYPE" not in normalized:
            normalized["CONTENT_TYPE"] = ""

        if "HTTP_HOST" not in normalized:
            host = normalized.get("SERVER_NAME", "localhost")
            port = normalized.get("SERVER_PORT", "80")
            if port != "80":
                normalized["HTTP_HOST"] = "%s:%s" % (host, port)
            else:
                normalized["HTTP_HOST"] = host

        return normalized

    def _get_session(self):
        app = self._app
        sessions = app.sessions
        session_name = app.config.session_name
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie(cookie_str)
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

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

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
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

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

    @property
    def cookie(self):
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

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

    def handler(self):
        from .response import Response
        from http.client import responses as http_status_codes
        app = self._app

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
            if isinstance(middleware_result, Response):
                return self.handle_response(middleware_result)
            return middleware_result

        try:
            environ = self._environ
            path_info = environ.get("PATH_INFO", "/")
            request_method = environ.get("REQUEST_METHOD", "GET")

            # 尝试使用路由系统处理请求
            route_match = app.router.match(path_info, request_method)
            if route_match:
                handler, params = route_match
                try:
                    # 将路由参数添加到请求对象
                    setattr(self, 'route_params', params)
                    setattr(self, 'path_params', params)
                    result = handler(self, **params)

                    # 处理 Response 对象
                    if isinstance(result, Response):
                        # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                        app = self._app
                        session_key = self._session_id or self.session.id
                        if self._session_modified:
                            app.sessions.put(session_key, self.session)

                        # 设置 session cookie（每次都设置，确保 cookie 不会丢失）
                        result.headers.append(("Set-Cookie", self._build_session_cookie_header(session_key)))

                        status_code = result.status_code
                        status_text = http_status_codes.get(status_code, "Unknown")
                        status = "%d %s" % (status_code, status_text)
                        return app.middleware_manager.process_response(
                            self, (status, result.headers, result.content)
                        )

                    if self._headers_responsed:
                        # 保存 Session 数据到 Session 存储
                        app = self._app
                        session_key = self._session_id or self.session.id
                        app.sessions.put(session_key, self.session)

                        # 设置 session cookie（每次都设置，确保 cookie 不会丢失）
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

                        response_headers = [("Server", "litefs/0.8.0")]
                        response_headers.extend(self._headers)

                        return app.middleware_manager.process_response(
                            self, (status, response_headers, result)
                        )
                    return app.middleware_manager.process_response(
                        self, self._response(self._status_code, content=result)
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


__all__ = [
    'WSGIRequestHandler',
]
