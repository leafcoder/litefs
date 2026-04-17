#!/usr/bin/env python
# coding: utf-8

"""
WebSocket 连接管理模块

管理单个 WebSocket 连接的生命周期。
"""

import json
import socket
import time
from typing import Any, Dict, List, Optional, Set, Callable, Iterator
from urllib.parse import parse_qs

from .protocol import Frame, Opcode, CloseCode, parse_close_payload, build_close_payload


class WebSocketConnection:
    """
    WebSocket 连接封装
    
    提供简化的消息收发接口。
    """
    
    def __init__(
        self,
        socket,
        address: tuple,
        path: str,
        query_string: str = '',
        headers: dict = None,
    ):
        self.socket = socket
        self.address = address
        self.path = path
        self.query_string = query_string
        self.headers = headers or {}
        
        self._query_params = None
        self._rooms: Set[str] = set()
        self._closed = False
        self._user = None
        self._last_ping = time.time()
        self._buffer = b''
        
        self._manager: Optional['ConnectionManager'] = None
    
    @property
    def query_params(self) -> Dict[str, List[str]]:
        """获取查询参数"""
        if self._query_params is None:
            self._query_params = parse_qs(self.query_string)
        return self._query_params
    
    @property
    def user(self):
        """获取用户对象"""
        return self._user
    
    @user.setter
    def user(self, value):
        """设置用户对象"""
        self._user = value
    
    @property
    def rooms(self) -> Set[str]:
        """获取所属房间列表"""
        return self._rooms.copy()
    
    @property
    def is_closed(self) -> bool:
        """连接是否已关闭"""
        return self._closed
    
    def send(self, data: Any) -> bool:
        """
        发送消息
        
        Args:
            data: 消息数据（自动 JSON 序列化 dict/list）
            
        Returns:
            是否发送成功
        """
        if self._closed:
            return False
        
        try:
            if isinstance(data, (dict, list)):
                payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
                opcode = Opcode.TEXT
            elif isinstance(data, str):
                payload = data.encode('utf-8')
                opcode = Opcode.TEXT
            elif isinstance(data, bytes):
                payload = data
                opcode = Opcode.BINARY
            else:
                payload = str(data).encode('utf-8')
                opcode = Opcode.TEXT
            
            frame = Frame(opcode=opcode, payload=payload)
            self.socket.sendall(frame.build())
            return True
        except Exception:
            self._closed = True
            return False
    
    def send_bytes(self, data: bytes) -> bool:
        """发送二进制消息"""
        if self._closed:
            return False
        
        try:
            frame = Frame(opcode=Opcode.BINARY, payload=data)
            self.socket.sendall(frame.build())
            return True
        except Exception:
            self._closed = True
            return False
    
    def ping(self) -> bool:
        """发送 Ping 帧"""
        if self._closed:
            return False
        
        try:
            frame = Frame(opcode=Opcode.PING, payload=b'')
            self.socket.sendall(frame.build())
            self._last_ping = time.time()
            return True
        except Exception:
            self._closed = True
            return False
    
    def close(self, code: int = CloseCode.NORMAL, reason: str = '') -> bool:
        """
        关闭连接
        
        Args:
            code: 关闭状态码
            reason: 关闭原因
            
        Returns:
            是否发送成功
        """
        if self._closed:
            return False
        
        try:
            payload = build_close_payload(code, reason)
            frame = Frame(opcode=Opcode.CLOSE, payload=payload)
            self.socket.sendall(frame.build())
            self._closed = True
            
            if self._manager:
                self._manager.remove(self)
            
            self.socket.close()
            return True
        except Exception:
            self._closed = True
            return False
    
    def join(self, room: str):
        """加入房间"""
        self._rooms.add(room)
        if self._manager:
            self._manager._join_room(self, room)
    
    def leave(self, room: str):
        """离开房间"""
        self._rooms.discard(room)
        if self._manager:
            self._manager._leave_room(self, room)
    
    def broadcast(self, data: Any, exclude_self: bool = True):
        """
        广播消息给所有连接
        
        Args:
            data: 消息数据
            exclude_self: 是否排除自己
        """
        if self._manager:
            self._manager.broadcast(data, exclude=[self] if exclude_self else None)
    
    def to_room(self, room: str, data: Any, exclude_self: bool = True):
        """
        发送消息到房间
        
        Args:
            room: 房间名
            data: 消息数据
            exclude_self: 是否排除自己
        """
        if self._manager:
            self._manager.broadcast_to_room(
                room, data, 
                exclude=[self] if exclude_self else None
            )
    
    def receive(self, timeout: float = None) -> Optional[Any]:
        """
        接收一条消息
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            消息数据（JSON 自动解析）或 None
        """
        if self._closed:
            return None
        
        try:
            if timeout:
                self.socket.settimeout(timeout)
            
            while True:
                frame = self._read_frame()
                if frame is None:
                    return None
                
                if frame.opcode == Opcode.TEXT:
                    try:
                        return json.loads(frame.payload.decode('utf-8'))
                    except json.JSONDecodeError:
                        return frame.payload.decode('utf-8')
                elif frame.opcode == Opcode.BINARY:
                    return frame.payload
                elif frame.opcode == Opcode.PING:
                    pong = Frame(opcode=Opcode.PONG, payload=frame.payload)
                    self.socket.sendall(pong.build())
                elif frame.opcode == Opcode.CLOSE:
                    self.close()
                    return None
        except Exception:
            self._closed = True
            return None
    
    def _read_frame(self) -> Optional[Frame]:
        """读取一个完整帧"""
        while True:
            frame, consumed = Frame.parse(self._buffer)
            if frame:
                self._buffer = self._buffer[consumed:]
                return frame
            
            try:
                chunk = self.socket.recv(4096)
                if not chunk:
                    self._closed = True
                    return None
                self._buffer += chunk
            except socket.timeout:
                continue
            except Exception as e:
                self._closed = True
                return None
    
    def __iter__(self) -> Iterator[Any]:
        """消息迭代器"""
        while not self._closed:
            message = self.receive()
            if message is None:
                break
            yield message
    
    def __repr__(self):
        return f"<WebSocketConnection {self.address} path={self.path}>"


class ConnectionManager:
    """
    连接管理器
    
    管理所有 WebSocket 连接和房间。
    """
    
    def __init__(self):
        self._connections: Set[WebSocketConnection] = set()
        self._rooms: Dict[str, Set[WebSocketConnection]] = {}
    
    def add(self, connection: WebSocketConnection):
        """添加连接"""
        connection._manager = self
        self._connections.add(connection)
    
    def remove(self, connection: WebSocketConnection):
        """移除连接"""
        self._connections.discard(connection)
        for room in list(connection._rooms):
            self._leave_room(connection, room)
    
    def _join_room(self, connection: WebSocketConnection, room: str):
        """加入房间"""
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(connection)
    
    def _leave_room(self, connection: WebSocketConnection, room: str):
        """离开房间"""
        if room in self._rooms:
            self._rooms[room].discard(connection)
            if not self._rooms[room]:
                del self._rooms[room]
    
    def broadcast(self, data: Any, exclude: List[WebSocketConnection] = None):
        """
        广播消息给所有连接
        
        Args:
            data: 消息数据
            exclude: 排除的连接列表
        """
        exclude_set = set(exclude) if exclude else set()
        for conn in self._connections:
            if conn not in exclude_set:
                conn.send(data)
    
    def broadcast_to_room(self, room: str, data: Any, exclude: List[WebSocketConnection] = None):
        """
        广播消息到房间
        
        Args:
            room: 房间名
            data: 消息数据
            exclude: 排除的连接列表
        """
        if room not in self._rooms:
            return
        
        exclude_set = set(exclude) if exclude else set()
        for conn in self._rooms[room]:
            if conn not in exclude_set:
                conn.send(data)
    
    def get_room_connections(self, room: str) -> Set[WebSocketConnection]:
        """获取房间内所有连接"""
        return self._rooms.get(room, set()).copy()
    
    def get_all_connections(self) -> Set[WebSocketConnection]:
        """获取所有连接"""
        return self._connections.copy()
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)
    
    @property
    def room_count(self) -> int:
        """当前房间数"""
        return len(self._rooms)
