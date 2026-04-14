#!/usr/bin/env python
# coding: utf-8

from typing import Dict, List, Optional, Callable, Any, Union, Tuple, Awaitable

from ..exceptions import HttpError
from ..handlers import ASGIRequestHandler


class ASGIServer:
    """ASGI 服务器基类"""

    application = None

    def __init__(self, application: Optional[Callable] = None) -> None:
        if application:
            self.application = application

    def get_app(self) -> Callable:
        return self.application

    def set_app(self, application: Callable) -> None:
        self.application = application


async def asgi_application(scope: Dict[str, Any], receive: Callable[[], Awaitable[Dict[str, Any]]], send: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
    """
    ASGI 应用函数，符合 ASGI 3.0 规范

    Args:
        scope: 包含请求信息的字典
        receive: 接收消息的异步函数
        send: 发送消息的异步函数
    """
    # 只处理 HTTP 请求
    if scope['type'] != 'http':
        return

    # 构建 ASGI 环境
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

    # 调用 ASGIRequestHandler
    try:
        # 这里需要从应用实例获取 Litefs 实例
        # 实际使用时，这个函数会被 Litefs.asgi() 方法包装
        pass
    except HttpError as e:
        # 处理 HTTP 错误
        await send({
            'type': 'http.response.start',
            'status': e.status_code,
            'headers': [
                (b'content-type', b'text/plain; charset=utf-8'),
                (b'content-length', str(len(e.message)).encode('utf-8')),
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': e.message.encode('utf-8'),
        })
    except Exception as e:
        # 处理其他错误
        status = 500
        message = 'Internal Server Error'
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': [
                (b'content-type', b'text/plain; charset=utf-8'),
                (b'content-length', str(len(message)).encode('utf-8')),
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': message.encode('utf-8'),
        })
