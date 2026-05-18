#!/usr/bin/env python
# coding: utf-8
"""
基于 asyncio 的 HTTP 服务器实现

与 greenlet 版本对比：
- greenlet 版本：使用 epoll + greenlet 实现协程
- asyncio 版本：使用 asyncio 原生事件循环和协程
"""

import asyncio
import socket
import logging
import traceback
from typing import Dict, Any, Optional, Callable, Tuple
from urllib.parse import unquote_plus
from email.message import Message
import time

from ..exceptions import HttpError
from ..handlers import ASGIRequestHandler
from ..utils import log_error


def parse_header(line: str) -> Tuple[Tuple[str, str], Dict[str, str]]:
    """解析 HTTP 头"""
    msg = Message()
    msg["content-type"] = line
    return msg.get_params()[0], dict(msg.get_params()[1:])


class AsyncHTTPRequestHandler:
    """异步 HTTP 请求处理器"""
    
    def __init__(self, app, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, 
                 client_address: Tuple[str, int], server, keep_alive_timeout: float = 5.0):
        self.app = app
        self.reader = reader
        self.writer = writer
        self.client_address = client_address
        self.server = server
        self.keep_alive_timeout = keep_alive_timeout
        self.keep_alive = False
    
    async def handle_request(self):
        """处理请求（支持 keep-alive）"""
        try:
            while True:
                try:
                    # 设置读取超时
                    self.reader._timeout = self.keep_alive_timeout
                    
                    # 构建 ASGI scope
                    scope = await self._build_scope()
                    
                    # 检查是否支持 keep-alive
                    self._check_keep_alive(scope)
                    
                    # 创建 receive 和 send 函数
                    receive = self._create_receive()
                    send = self._create_send()
                    
                    # 使用 ASGIRequestHandler 处理请求
                    handler = ASGIRequestHandler(self.app, scope, receive, send)
                    result = await handler.handler()
                    
                    # 处理返回值 (status, headers, content)
                    if result and isinstance(result, (list, tuple)) and len(result) == 3:
                        status, headers, content = result
                        
                        # 发送响应头
                        status_code = int(status.split()[0])
                        status_text = ' '.join(status.split()[1:])
                        
                        status_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
                        self.writer.write(status_line.encode('utf-8'))
                        
                        # 发送响应头
                        for key, value in headers:
                            header_line = f"{key}: {value}\r\n"
                            self.writer.write(header_line.encode('utf-8'))
                        
                        # 添加 Connection 头
                        if self.keep_alive:
                            self.writer.write(b"Connection: keep-alive\r\n")
                            self.writer.write(f"Keep-Alive: timeout={int(self.keep_alive_timeout)}\r\n".encode('utf-8'))
                        else:
                            self.writer.write(b"Connection: close\r\n")
                        
                        self.writer.write(b"\r\n")
                        
                        # 发送响应体
                        if isinstance(content, str):
                            content = content.encode('utf-8')
                        elif isinstance(content, (list, tuple)):
                            content = b''.join(
                                chunk.encode('utf-8') if isinstance(chunk, str) else chunk
                                for chunk in content
                            )
                        elif isinstance(content, dict):
                            import json
                            content = json.dumps(content).encode('utf-8')
                        elif not isinstance(content, bytes):
                            content = str(content).encode('utf-8')
                        
                        if content:
                            self.writer.write(content)
                        
                        # 确保响应完全发送
                        await self.writer.drain()
                        
                        # 如果不支持 keep-alive，退出循环
                        if not self.keep_alive:
                            break
                        
                except asyncio.TimeoutError:
                    # 超时，关闭连接
                    logging.debug(f"Keep-alive timeout, closing connection")
                    break
                except HttpError as e:
                    await self._send_error(e.status_code, e.message)
                    break
                except Exception as e:
                    logging.error(f"Error handling request: {e}")
                    traceback.print_exc()
                    await self._send_error(500, f"Internal server error: {str(e)}")
                    break
                    
        except Exception as e:
            logging.error(f"Connection error: {e}")
        finally:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
    
    def _check_keep_alive(self, scope: Dict[str, Any]):
        """检查是否支持 keep-alive"""
        # 默认 HTTP/1.1 支持 keep-alive
        http_version = scope.get('http_version', '1.0')
        
        # 检查 Connection 头
        connection_header = None
        for name, value in scope.get('headers', []):
            if name.decode('utf-8').lower() == 'connection':
                connection_header = value.decode('utf-8').lower()
                break
        
        # 判断是否保持连接
        if http_version == '1.1':
            # HTTP/1.1 默认 keep-alive
            self.keep_alive = connection_header != 'close'
        else:
            # HTTP/1.0 默认不 keep-alive
            self.keep_alive = connection_header == 'keep-alive'
    
    async def _build_scope(self) -> Dict[str, Any]:
        """构建 ASGI scope"""
        # 读取请求行
        request_line = await self.reader.readline()
        if not request_line:
            raise HttpError(400, "Empty request line")
        
        request_line = request_line.decode('utf-8').strip()
        parts = request_line.split()
        if len(parts) != 3:
            raise HttpError(400, f"Invalid request line: {request_line}")
        
        method, path, protocol = parts
        
        # 解析路径和查询字符串
        if '?' in path:
            path_info, query_string = path.split('?', 1)
        else:
            path_info, query_string = path, ''
        
        # 读取请求头
        headers = []
        while True:
            line = await self.reader.readline()
            if not line or line == b'\r\n':
                break
            
            line = line.decode('utf-8').strip()
            if ':' in line:
                key, value = line.split(':', 1)
                headers.append([key.strip().encode('utf-8'), value.strip().encode('utf-8')])
        
        # 构建 scope
        scope = {
            'type': 'http',
            'asgi': {'version': '3.0'},
            'http_version': protocol.split('/')[-1],
            'method': method,
            'scheme': 'http',
            'path': path_info,
            'query_string': query_string.encode('utf-8'),
            'root_path': '',
            'headers': headers,
            'server': (self.server.server_name, int(self.server.server_port)),
            'client': self.client_address,
        }
        
        return scope
    
    def _create_receive(self):
        """创建 ASGI receive 函数"""
        async def receive():
            # 读取请求体
            body = await self.reader.read()
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,
            }
        return receive
    
    def _create_send(self):
        """创建 ASGI send 函数"""
        async def send(message):
            if message['type'] == 'http.response.start':
                # 发送响应头
                status_code = message['status']
                status_text = {
                    200: 'OK',
                    404: 'Not Found',
                    500: 'Internal Server Error',
                }.get(status_code, 'Unknown')
                
                status_line = f"HTTP/1.1 {status_code} {status_text}\r\n"
                self.writer.write(status_line.encode('utf-8'))
                
                # 发送响应头
                for name, value in message.get('headers', []):
                    header_line = f"{name.decode('utf-8')}: {value.decode('utf-8')}\r\n"
                    self.writer.write(header_line.encode('utf-8'))
                
                self.writer.write(b"\r\n")
                
            elif message['type'] == 'http.response.body':
                # 发送响应体
                body = message.get('body', b'')
                if body:
                    self.writer.write(body)
                
                await self.writer.drain()
        
        return send
    
    async def _send_response(self, result):
        """发送响应（用于错误处理）"""
        # 这个方法主要用于错误处理，正常情况下由 ASGIRequestHandler 处理
        pass
    
    async def _send_error(self, status_code: int, message: str):
        """发送错误响应"""
        try:
            status_text = {
                400: "Bad Request",
                404: "Not Found",
                500: "Internal Server Error",
            }.get(status_code, "Error")
            
            response = f"HTTP/1.1 {status_code} {status_text}\r\n"
            response += "Content-Type: text/plain; charset=utf-8\r\n"
            response += f"Content-Length: {len(message)}\r\n"
            response += "\r\n"
            response += message
            
            self.writer.write(response.encode('utf-8'))
            await self.writer.drain()
            
        except Exception as e:
            logging.error(f"Error sending error response: {e}")


class AsyncHTTPServer:
    """基于 asyncio 的 HTTP 服务器"""
    
    def __init__(self, app, host: str = '0.0.0.0', port: int = 8080, 
                 processes: int = 1, keep_alive_timeout: float = 5.0, **kwargs):
        self.app = app
        self.host = host
        self.port = port
        self.processes = processes
        self.keep_alive_timeout = keep_alive_timeout
        self.server_name = host
        self.server_port = str(port)
        
        self._server = None
        self._loop = None
    
    async def handle_client(self, reader: asyncio.StreamReader, 
                           writer: asyncio.StreamWriter):
        """处理客户端连接"""
        peername = writer.get_extra_info('peername')
        client_address = peername if peername else ('unknown', 0)
        
        handler = AsyncHTTPRequestHandler(
            self.app, reader, writer, client_address, self, self.keep_alive_timeout
        )
        
        await handler.handle_request()
    
    async def start(self):
        """启动服务器"""
        self._server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port,
            reuse_address=True,
        )
        
        addrs = ', '.join(str(sock.getsockname()) for sock in self._server.sockets)
        logging.info(f"Serving on {addrs}")
        
        async with self._server:
            await self._server.serve_forever()
    
    def run(self):
        """运行服务器"""
        logging.info(f"Starting asyncio HTTP server on {self.host}:{self.port}")
        logging.info(f"Processes: {self.processes}")
        
        # 注意：asyncio 版本不支持多进程，但可以通过启动多个进程来实现
        # 这里我们只启动单个进程
        if self.processes > 1:
            logging.warning(
                f"AsyncIO server doesn't support multi-process in single instance. "
                f"Starting 1 process instead of {self.processes}. "
                f"Use multiple server instances or a process manager for scaling."
            )
        
        try:
            asyncio.run(self.start())
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
        except Exception as e:
            logging.error(f"Server error: {e}")
            traceback.print_exc()


def run_asyncio(app, host: str = '0.0.0.0', port: int = 8080, 
                       processes: int = 1, keep_alive_timeout: float = 5.0, **kwargs):
    """运行基于 asyncio 的 HTTP 服务器
    
    Args:
        app: Litefs 应用实例
        host: 监听地址
        port: 监听端口
        processes: 进程数（asyncio 版本不支持多进程）
        keep_alive_timeout: Keep-Alive 超时时间（秒）
        **kwargs: 其他参数
    """
    server = AsyncHTTPServer(app, host, port, processes, keep_alive_timeout, **kwargs)
    server.run()
