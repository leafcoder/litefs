#!/usr/bin/env python
# coding: utf-8

"""
ASGI 请求处理器

用于在 uvicorn、daphne 等 ASGI 服务器中运行
符合 ASGI 3.0 规范
"""

import asyncio
import io
from http.cookies import SimpleCookie

from ..exceptions import HttpError
from ..session import Session
from .base import BaseRequestHandler
from .form import parse_form, parse_header, parse_multipart_asgi


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

    async def handler(self):
        """
        异步处理请求
        """
        app = self._app

        # 处理请求体
        await self._process_request_body()

        middleware_result = await app.middleware_manager.async_process_request(self)
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

                    return await self._async_process_route_result(result, app)
                except Exception:
                    return await self._async_process_route_error(app)

            # 路由未匹配，返回 404
            return await app.middleware_manager.async_process_response(
                self, self._response(404)
            )
        except Exception as e:
            middleware_result = await app.middleware_manager.async_process_exception(self, e)
            if middleware_result is not None:
                return middleware_result
            raise

    async def _async_process_route_result(self, result, app):
        """
        异步处理路由处理器的返回结果
        """
        from .response import Response
        from http.client import responses as http_status_codes

        if isinstance(result, Response):
            return await self._async_handle_response_object(result, app, http_status_codes)

        if self._headers_responsed:
            return await self._async_handle_headers_responsed(result, app, http_status_codes)

        return await self._async_handle_normal_result(result, app, http_status_codes)

    async def _async_handle_response_object(self, result, app, http_status_codes):
        """异步处理 Response 对象类型的返回值"""
        session_key = self._session_id or self.session.id
        if self._session_modified:
            app.sessions.put(session_key, self.session)

        result.headers.append(("Set-Cookie", self._build_session_cookie_header(session_key)))

        status_code = result.status_code
        status_text = http_status_codes.get(status_code, "Unknown")
        status = "%d %s" % (status_code, status_text)
        return await app.middleware_manager.async_process_response(
            self, (status, result.headers, result.content)
        )

    async def _async_handle_headers_responsed(self, result, app, http_status_codes):
        """异步处理已经调用过 start_response 的情况"""
        session_key = self._session_id or self.session.id
        app.sessions.put(session_key, self.session)

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

        from .response import server_info
        response_headers = [("Server", server_info)]
        response_headers.extend(self._headers)

        return await app.middleware_manager.async_process_response(
            self, (status, response_headers, result)
        )

    async def _async_handle_normal_result(self, result, app, http_status_codes):
        """异步处理普通返回值"""
        return await app.middleware_manager.async_process_response(
            self, self._response(self._status_code, content=result)
        )

    async def _async_process_route_error(self, app):
        """异步处理路由执行过程中的异常"""
        from ..utils import log_error, render_error
        log_error(app.logger)
        if app.config.debug:
            content = render_error()
            return await app.middleware_manager.async_process_response(
                self, self._response(500, content=content)
            )
        return await app.middleware_manager.async_process_response(self, self._response(500))


__all__ = [
    'ASGIRequestHandler',
]
