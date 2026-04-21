#!/usr/bin/env python
# coding: utf-8

"""
ASGI 请求处理器

用于在 uvicorn、daphne 等 ASGI 服务器中运行
符合 ASGI 3.0 规范
"""

import asyncio
import io
import json
from hashlib import sha256
from http.cookies import SimpleCookie
from os import urandom
from tempfile import TemporaryFile

from ..exceptions import HttpError
from ..session import Session
from ..utils import gmt_date, log_debug, log_error, render_error
from .base_handler import BaseRequestHandler
from .form_parser import parse_form, parse_header, parse_multipart_asgi
from .response import server_info


class ASGIRequestHandler(BaseRequestHandler):
    """
    ASGI 请求处理器，用于在 uvicorn、daphne 等 ASGI 服务器中运行

    符合 ASGI 3.0 规范，处理 ASGI scope、receive 和 send 并返回标准响应
    """

    def __init__(self, app, scope, receive, send):
        # 构建 environ 字典
        environ = {
            'ASGI_SCOPE': scope,
            'ASGI_RECEIVE': receive,
            'ASGI_SEND': send,
            'REQUEST_METHOD': scope['method'],
            'PATH_INFO': scope['path'],
            'QUERY_STRING': scope.get('query_string', b'').decode('utf-8'),
            'SERVER_NAME': scope['server'][0],
            'SERVER_PORT': str(scope['server'][1]),
            'REMOTE_ADDR': scope['client'][0],
            'REMOTE_PORT': str(scope['client'][1]),
            'SERVER_PROTOCOL': f'HTTP/{scope.get("http_version", "1.1")}',
        }

        # 处理 headers
        headers = scope.get('headers', [])
        for name, value in headers:
            name = name.decode('utf-8').upper().replace('-', '_')
            if name not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                name = f'HTTP_{name}'
            environ[name] = value.decode('utf-8')

        super(ASGIRequestHandler, self).__init__(app, environ)
        self._scope = scope
        self._receive = receive
        self._send = send
        self._headers = []
        self._get = parse_form(self._environ.get("QUERY_STRING", ""))
        self._body = None
        self._post = None
        self._files = None

        # 延迟处理请求体，在需要时异步处理
        self._content_type = self._environ.get("CONTENT_TYPE", "")
        self._content_type_raw = self._content_type
        if self._content_type:
            self._content_type, self._params = parse_header(self._content_type)
        else:
            self._params = {}

        # 延迟加载会话，只在需要时获取
        self._session_id = None
        self._session = None
        self._session_loaded = False
        # 缓存中间件实例，避免重复创建
        self._middlewares = app._get_middleware_instances()

    async def _process_request_body(self):
        """
        异步处理请求体
        """
        if not self._content_type:
            return

        # 检查是否已经处理过请求体
        if self._body is not None or self._post is not None:
            return

        # 异步读取请求体
        body = await self._read_body()

        if not body:
            return

        content_length = len(body)
        max_request_size = getattr(self._app.config, "max_request_size", 10485760)
        if content_length > max_request_size:
            raise HttpError(
                413, f"Request body too large. Maximum size is {max_request_size} bytes"
            )

        if self._content_type_raw == "application/x-www-form-urlencoded":
            post_content = body.decode("utf-8")
            self._post = parse_form(post_content)
        elif self._content_type_raw.startswith("multipart/form-data"):
            boundary = self._params.get("boundary")
            if boundary:
                self._post, self._files = parse_multipart_asgi(
                    body, boundary,
                    getattr(self._app.config, "max_upload_size", 52428800)
                )
        else:
            self._body = body.decode("utf-8")

    async def _read_body(self):
        """
        异步读取请求体
        """
        # 使用字节缓冲区，减少字符串拼接开销
        body_buffer = io.BytesIO()

        while True:
            message = await self._receive()
            if message['type'] == 'http.request':
                body = message.get('body', b'')
                if body:
                    body_buffer.write(body)
                if not message.get('more_body', False):
                    break

        return body_buffer.getvalue()

    def _get_session(self):
        app = self._app
        sessions = app.sessions
        session_name = app.config.session_name

        # 从 headers 中获取 cookie
        cookie_str = ""
        headers = self._scope.get('headers', [])
        for name, value in headers:
            if name.decode('utf-8').lower() == 'cookie':
                cookie_str = value.decode('utf-8')
                break

        # 尝试从 cookie 中获取会话
        if cookie_str:
            cookie = SimpleCookie(cookie_str)
            morsel = cookie.get(session_name)
            if morsel is not None:
                session_id = morsel.value
                # 尝试从会话存储中获取会话
                session = sessions.get(session_id)
                if session is not None:
                    # 设置存储后端实例，确保数据修改时自动保存
                    session.store = sessions
                    return session_id, session

        # 生成新的会话 ID
        session_id = self._new_session_id()
        # 创建 Session 对象时传入存储后端实例
        session = Session(session_id, store=sessions)
        # 只在需要时才保存会话
        self._session_modified = False
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
        cookie_str = ""
        headers = self._scope.get('headers', [])
        for name, value in headers:
            if name.decode('utf-8').lower() == 'cookie':
                cookie_str = value.decode('utf-8')
                break
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

    async def handler(self):
        """
        异步处理请求
        """
        from .response import Response
        from http.client import responses as http_status_codes
        app = self._app

        # 处理请求体
        await self._process_request_body()

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
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

                    # 处理同步和异步处理器
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(self, **params)
                    else:
                        result = handler(self, **params)

                    # 处理 Response 对象
                    if isinstance(result, Response):
                        # 确保会话已加载
                        session_key = None
                        if self._session_loaded:
                            # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                            if self._session_modified:
                                session_key = self._session_id or self.session.id
                                app.sessions.put(session_key, self.session)
                            else:
                                session_key = self._session_id or self.session.id
                        else:
                            # 会话未加载，不需要设置 cookie
                            pass

                        # 设置 session cookie（只有在会话已加载时）
                        if session_key:
                            result.headers.append(("Set-Cookie", self._build_session_cookie_header(session_key)))

                        status_code = result.status_code
                        status_text = http_status_codes.get(status_code, "Unknown")
                        status = "%d %s" % (status_code, status_text)
                        return app.middleware_manager.process_response(
                            self, (status, result.headers, result.content)
                        )

                    if self._headers_responsed:
                        # 确保会话已加载
                        session_key = None
                        if self._session_loaded:
                            # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                            if self._session_modified:
                                session_key = self._session_id or self.session.id
                                app.sessions.put(session_key, self.session)
                            else:
                                session_key = self._session_id or self.session.id

                        # 设置 session cookie（只有在会话已加载时）
                        if session_key:
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

                    # 确保会话已加载
                    session_key = None
                    if self._session_loaded:
                        # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                        if self._session_modified:
                            session_key = self._session_id or self.session.id
                            app.sessions.put(session_key, self.session)
                        else:
                            session_key = self._session_id or self.session.id

                    # 设置 session cookie（只有在会话已加载时）
                    if session_key:
                        self.set_cookie(
                            app.config.session_name, session_key,
                            path="/",
                            secure=app.config.session_secure,
                            httponly=app.config.session_http_only,
                            samesite=app.config.session_same_site
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
    'ASGIRequestHandler',
]
