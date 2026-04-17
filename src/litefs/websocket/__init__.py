#!/usr/bin/env python
# coding: utf-8

"""
WebSocket 模块

提供 WebSocket 支持，包括：
- WebSocket 服务器
- 连接管理
- 房间/频道管理
- 认证集成

使用示例：
    from litefs import Litefs
    
    app = Litefs()
    
    @app.websocket('/ws')
    def ws_handler(ws):
        ws.send('欢迎连接!')
        for message in ws:
            ws.broadcast(message)
"""

from .server import WebSocket, WebSocketServer
from .connection import WebSocketConnection, ConnectionManager
from .protocol import Opcode, CloseCode, Frame

__all__ = [
    'WebSocket',
    'WebSocketServer',
    'WebSocketConnection',
    'ConnectionManager',
    'Opcode',
    'CloseCode',
    'Frame',
]
