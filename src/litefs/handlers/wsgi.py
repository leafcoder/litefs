#!/usr/bin/env python
# coding: utf-8

"""
WSGI 请求处理器

用于在 gunicorn、uWSGI 等 WSGI 服务器中运行
符合 PEP 3333 规范
"""

from http.cookies import SimpleCookie

from ..exceptions import HttpError
from ..session import Session
from .base import BaseRequestHandler
from .form import parse_form, parse_header, parse_multipart_wsgi


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

    @property
    def cookie(self):
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def handler(self):
        app = self._app

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
            from .response import Response
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

                    return self._process_route_result(result, app)
                except Exception:
                    return self._process_route_error(app)

            # 路由未匹配，返回 404
            return app.middleware_manager.process_response(self, self._response(404))
        except Exception as e:
            middleware_result = app.middleware_manager.process_exception(self, e)
            if middleware_result is not None:
                return middleware_result
            raise


__all__ = [
    'WSGIRequestHandler',
]
