#!/usr/bin/env python
# coding: utf-8

"""
WebSocket 服务器模块

提供 WebSocket 服务器实现。
"""

import socket
import threading
import re
import time
from typing import Callable, Dict, Optional, Any
from urllib.parse import urlparse

from .protocol import Frame, Opcode, CloseCode, compute_accept_key
from .connection import WebSocketConnection, ConnectionManager


class WebSocketServer:
    """
    WebSocket 服务器
    
    独立运行，支持与 HTTP 服务器共存。
    """
    
    def __init__(
        self,
        host: str = '0.0.0.0',
        port: int = 8765,
        path: str = '/ws',
        auth_required: bool = False,
        auth_handler: Callable = None,
        ping_interval: int = 30,
        ping_timeout: int = 60,
    ):
        self.host = host
        self.port = port
        self.path = path
        self.auth_required = auth_required
        self.auth_handler = auth_handler
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        self._manager = ConnectionManager()
        self._handlers: Dict[str, Callable] = {}
        self._server_socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def handler(self, path: str = None):
        """
        装饰器：注册 WebSocket 处理函数
        
        Args:
            path: WebSocket 路径
        """
        def decorator(func: Callable):
            route_path = path or self.path
            self._handlers[route_path] = func
            return func
        return decorator
    
    def broadcast(self, data: Any):
        """广播消息给所有连接"""
        self._manager.broadcast(data)
    
    def broadcast_to_room(self, room: str, data: Any):
        """广播消息到房间"""
        self._manager.broadcast_to_room(room, data)
    
    def start(self, blocking: bool = True):
        """
        启动服务器
        
        Args:
            blocking: 是否阻塞运行
        """
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(128)
        self._running = True
        
        if blocking:
            self._run()
        else:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
    
    def stop(self):
        """停止服务器"""
        self._running = False
        
        for conn in self._manager.get_all_connections():
            try:
                conn.close()
            except Exception:
                pass
        
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
    
    def _run(self):
        """服务器主循环"""
        while self._running:
            try:
                self._server_socket.settimeout(1.0)
                client_socket, address = self._server_socket.accept()
                
                thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                thread.start()
            except socket.timeout:
                continue
            except Exception:
                if self._running:
                    continue
                break
    
    def _handle_client(self, client_socket: socket.socket, address: tuple):
        """处理客户端连接"""
        connection = None
        
        try:
            request = self._read_http_request(client_socket)
            if not request:
                client_socket.close()
                return
            
            path, headers = request
            
            if not self._validate_handshake(headers):
                self._send_bad_request(client_socket)
                client_socket.close()
                return
            
            self._send_handshake_response(client_socket, headers)
            
            client_socket.settimeout(None)
            client_socket.setblocking(True)
            
            parsed = urlparse(path)
            ws_path = parsed.path
            query_string = parsed.query
            
            connection = WebSocketConnection(
                socket=client_socket,
                address=address,
                path=ws_path,
                query_string=query_string,
                headers=headers,
            )
            
            if self.auth_required and self.auth_handler:
                if not self.auth_handler(connection):
                    connection.close(code=CloseCode.UNAUTHORIZED, reason='Unauthorized')
                    return
            
            self._manager.add(connection)
            
            handler = self._find_handler(ws_path)
            if handler:
                try:
                    handler(connection)
                except Exception:
                    pass
            
            self._manager.remove(connection)
            
        except Exception:
            pass
        finally:
            try:
                client_socket.close()
            except Exception:
                pass
    
    def _read_http_request(self, client_socket: socket.socket) -> Optional[tuple]:
        """读取 HTTP 请求"""
        client_socket.settimeout(5.0)
        
        buffer = b''
        while b'\r\n\r\n' not in buffer:
            try:
                chunk = client_socket.recv(1024)
                if not chunk:
                    return None
                buffer += chunk
            except Exception:
                return None
        
        request_text = buffer.decode('utf-8', errors='replace')
        lines = request_text.split('\r\n')
        
        if not lines:
            return None
        
        request_line = lines[0]
        match = re.match(r'GET\s+(\S+)\s+HTTP/1\.1', request_line)
        if not match:
            return None
        
        path = match.group(1)
        
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip().lower()] = value.strip()
        
        return path, headers
    
    def _validate_handshake(self, headers: dict) -> bool:
        """验证握手请求"""
        if headers.get('upgrade', '').lower() != 'websocket':
            return False
        
        if 'upgrade' not in headers.get('connection', '').lower():
            return False
        
        if 'sec-websocket-key' not in headers:
            return False
        
        return True
    
    def _send_handshake_response(self, client_socket: socket.socket, headers: dict):
        """发送握手响应"""
        key = headers['sec-websocket-key']
        accept_key = compute_accept_key(key)
        
        response = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: websocket\r\n'
            'Connection: Upgrade\r\n'
            f'Sec-WebSocket-Accept: {accept_key}\r\n'
            '\r\n'
        )
        
        client_socket.sendall(response.encode('utf-8'))
    
    def _send_bad_request(self, client_socket: socket.socket):
        """发送错误响应"""
        response = 'HTTP/1.1 400 Bad Request\r\n\r\n'
        client_socket.sendall(response.encode('utf-8'))
    
    def _find_handler(self, path: str) -> Optional[Callable]:
        """查找路径对应的处理函数"""
        if path in self._handlers:
            return self._handlers[path]
        
        for pattern, handler in self._handlers.items():
            if self._match_path(pattern, path):
                return handler
        
        return None
    
    def _match_path(self, pattern: str, path: str) -> bool:
        """匹配路径"""
        if pattern == path:
            return True
        
        regex = re.sub(r'\{(\w+)\}', r'[^/]+', pattern)
        return bool(re.fullmatch(regex, path))


class WebSocket:
    """
    WebSocket 集成类
    
    与 Litefs 应用集成。
    """
    
    def __init__(
        self,
        app=None,
        path: str = '/ws',
        host: str = None,
        port: int = None,
        auth_required: bool = False,
        auth_handler: Callable = None,
    ):
        self.path = path
        self.auth_required = auth_required
        self.auth_handler = auth_handler
        
        self._server: Optional[WebSocketServer] = None
        self._handlers: Dict[str, Callable] = {}
        
        if app:
            self.init_app(app, host, port)
    
    def init_app(self, app, host: str = None, port: int = None):
        """
        初始化应用
        
        Args:
            app: Litefs 应用实例
            host: WebSocket 服务器主机
            port: WebSocket 服务器端口
        """
        self._app = app
        self._ws_host = host or getattr(app.config, 'host', '0.0.0.0')
        self._ws_port = port or (getattr(app.config, 'port', 8080) + 1)
        
        app._websocket = self
    
    def start(self):
        """启动 WebSocket 服务器"""
        self._server = WebSocketServer(
            host=self._ws_host,
            port=self._ws_port,
            auth_required=self.auth_required,
            auth_handler=self.auth_handler,
        )
        
        for path, handler in self._handlers.items():
            self._server._handlers[path] = handler
        
        self._server.start(blocking=False)
    
    def stop(self):
        """停止 WebSocket 服务器"""
        if self._server:
            self._server.stop()
    
    def handler(self, path: str = None):
        """
        装饰器：注册 WebSocket 处理函数
        
        Args:
            path: WebSocket 路径
        """
        def decorator(func: Callable):
            route_path = path or self.path
            self._handlers[route_path] = func
            return func
        return decorator
    
    def broadcast(self, data: Any):
        """广播消息给所有连接"""
        if self._server:
            self._server.broadcast(data)
    
    def broadcast_to_room(self, room: str, data: Any):
        """广播消息到房间"""
        if self._server:
            self._server.broadcast_to_room(room, data)
    
    @property
    def manager(self) -> ConnectionManager:
        """获取连接管理器"""
        if self._server:
            return self._server._manager
        return None
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        if self._server:
            return self._server._manager.connection_count
        return 0
