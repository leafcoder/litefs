#!/usr/bin/env python
# coding: utf-8

"""
WSGI / ASGI 协议适配 Mixin

提供 PEP 3333 与 ASGI 3.0 应用入口，以及统一的错误处理流程。
"""

from typing import Any, Tuple

from ..handlers import ASGIRequestHandler, RequestHandler, WSGIRequestHandler
from ..utils import log_error

from .helpers import _parse_result_tuple, _serialize_content


class ProtocolMixin:
    """WSGI / ASGI 协议适配与错误处理能力"""

    def _build_error_parts(self, error) -> Tuple[int, str, str, str]:
        """Build error parts from exception when no middleware handled it.

        Args:
            error: The exception that occurred.

        Returns:
            tuple: (status_code, content_type, status_text, body_text)
        """
        from ..exceptions import HttpError

        if isinstance(error, HttpError):
            return (
                error.status_code,
                "text/html; charset=utf-8",
                error.message,
                error.message,
            )
        else:
            log_error(self.logger, str(error))
            return (
                500,
                "text/html; charset=utf-8",
                "500 Internal Server Error",
                "Internal Server Error",
            )

    def _handle_error_parts(self, request_handler, error):
        """Process an exception and return normalized error parts.

        Tries middleware exception handler first, then falls back to common logic.

        Returns:
            tuple: (status_line, headers, content) from _parse_result_tuple if middleware handled it
                   (first element is a string — the WSGI status line).
            tuple: (status_code, content_type, status_text, body_text) if no middleware handled it
                   (first element is an int — the HTTP status code).
        """
        if request_handler is not None:
            middleware_result = self.middleware_manager.process_exception(
                request_handler, error
            )
            if middleware_result is not None:
                return _parse_result_tuple(middleware_result)

        return self._build_error_parts(error)

    async def _async_handle_error_parts(self, request_handler, error):
        """Async version of _handle_error_parts for ASGI path.

        Tries async middleware exception handler first, then falls back to common logic.

        Returns:
            Same format as _handle_error_parts.
        """
        if request_handler is not None:
            middleware_result = await self.middleware_manager.async_process_exception(
                request_handler, error
            )
            if middleware_result is not None:
                return _parse_result_tuple(middleware_result)

        return self._build_error_parts(error)

    def wsgi(self):
        """
        返回符合 PEP 3333 规范的 WSGI application callable

        用法:
            from litefs.core import Litefs
            app = Litefs()
            application = app.wsgi()

        在 gunicorn 中使用:
            gunicorn -w 4 -b :8000 wsgi_example:application

        在 uWSGI 中使用:
            uwsgi --http :8000 --wsgi-file wsgi_example.py
        """

        def application(environ, start_response):
            try:
                request_handler = WSGIRequestHandler(self, environ)

                # 中间件请求处理
                middleware_result = self.middleware_manager.process_request(
                    request_handler
                )
                if middleware_result is not None:
                    status, headers, content = _parse_result_tuple(
                        middleware_result
                    )
                    start_response(status, headers)
                    is_json = "application/json" in dict(headers).get(
                        "Content-Type", ""
                    )
                    return _serialize_content(content, is_json)

                # 业务处理
                handler_result = request_handler.handler()
                status, headers, content = _parse_result_tuple(handler_result)
                start_response(status, headers)
                is_json = "application/json" in dict(headers).get(
                    "Content-Type", ""
                )
                return _serialize_content(content, is_json)

            except Exception as e:
                result = self._handle_error_parts(request_handler, e)
                if len(result) == 3 and isinstance(result[0], str):
                    # Middleware handled it — (status_line, headers, content)
                    status, headers, content = result
                    start_response(status, headers)
                    is_json = "application/json" in dict(headers).get(
                        "Content-Type", ""
                    )
                    return _serialize_content(content, is_json)

                # Error parts — (status_code, content_type, status_text, body)
                status_code, content_type, status_text, body_text = result
                status = f"{status_code} {status_text}"
                headers = [("Content-Type", content_type)]
                start_response(status, headers)
                return [body_text.encode("utf-8")]

        return application

    def asgi(self):
        """
        返回符合 ASGI 3.0 规范的 ASGI application callable

        用法:
            from litefs.core import Litefs
            app = Litefs()
            application = app.asgi()

        在 uvicorn 中使用:
            uvicorn asgi_example:application

        在 daphne 中使用:
            daphne asgi_example:application
        """

        async def _send_asgi_response(send, status, headers, content):
            """发送 ASGI 响应"""
            status_code = int(status.split()[0])
            asgi_headers = []
            for k, v in headers:
                if k.lower() != 'content-length':
                    asgi_headers.append(
                        (k.encode('utf-8'), v.encode('utf-8'))
                    )

            is_json = "application/json" in dict(headers).get(
                "Content-Type", ""
            )
            content_bytes_list = _serialize_content(content, is_json)
            body = b''.join(content_bytes_list)

            await send({
                'type': 'http.response.start',
                'status': status_code,
                'headers': asgi_headers,
            })
            await send({
                'type': 'http.response.body',
                'body': body,
            })

        async def application(scope, receive, send):
            # 只处理 HTTP 请求
            if scope['type'] != 'http':
                return

            request_handler = None
            try:
                request_handler = ASGIRequestHandler(self, scope, receive, send)

                # 中间件请求处理
                middleware_result = (
                    await self.middleware_manager.async_process_request(
                        request_handler
                    )
                )
                if middleware_result is not None:
                    status, headers, content = _parse_result_tuple(
                        middleware_result
                    )
                    await _send_asgi_response(send, status, headers, content)
                    return

                # 业务处理
                handler_result = await request_handler.handler()
                status, headers, content = _parse_result_tuple(handler_result)
                await _send_asgi_response(send, status, headers, content)

            except Exception as e:
                result = await self._async_handle_error_parts(
                    request_handler, e
                )
                if len(result) == 3 and isinstance(result[0], str):
                    # Middleware handled it — (status_line, headers, content)
                    status, headers, content = result
                    await _send_asgi_response(send, status, headers, content)
                    return

                # Error parts — (status_code, content_type, status_text, body)
                status_code, content_type, _status_text, body_text = result
                await send({
                    'type': 'http.response.start',
                    'status': status_code,
                    'headers': [
                        (b'content-type', content_type.encode('utf-8')),
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': body_text.encode('utf-8'),
                })

        return application

    def handler(self, request, rw, environ, server) -> Any:
        """处理单次原生 HTTP 请求（服务器回调入口）"""
        request_handler = RequestHandler(self, rw, environ, request)
        result = request_handler.handler()
        return request_handler.finish(result)
