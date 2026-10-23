#!/usr/bin/env python
# coding: utf-8
# mypy: ignore-errors
"""
greenlet 服务器基础组件（内部拆分模块）

从 :mod:`litefs.server.greenlet` 拆分而来，承载与 epoll 事件循环耦合的
底层组件，代码自原模块逐字符原样迁移：

- ``SocketIO``：基于 greenlet 切换的非阻塞 socket 原始 IO
- ``Epoll``：epoll 事件循环（含空闲 greenlet 调度）
- ``TCPServer``：经典 TCP 服务器基类
- ``parse_header`` / ``make_headers`` / ``make_environ``：HTTP 报文解析辅助

模块级 ``epoll`` 单例、``mainloop`` 与 ``server_forever`` 亦随迁至此。
以上符号均由 ``litefs.server.greenlet`` 统一再导出，禁止外部直接导入
本模块，不构成公共 API。

类型化治理说明：迁移代码在原模块处于 mypy ``ignore_errors`` 豁免范围，
本模块以文件级指令保持同一治理状态；后续收敛时移除首行指令并加入
pyproject 的 mypy overrides 分阶段治理清单。
"""

import time
from errno import EAGAIN, EMFILE, ENOTCONN, EPIPE, EWOULDBLOCK
from functools import lru_cache, partial
from io import DEFAULT_BUFFER_SIZE, BufferedRWPair, RawIOBase
from traceback import print_exc
from urllib.parse import unquote_plus
from email.message import Message

from typing import Any, Dict, List, Optional, Tuple, cast

try:
    from greenlet import GreenletExit, getcurrent, greenlet  # type: ignore[import-untyped]

    HAS_GREENLET = True
except ImportError:
    HAS_GREENLET = False
    greenlet = None
    getcurrent = None
    GreenletExit = None

try:
    from select import EPOLLERR, EPOLLET, EPOLLHUP, EPOLLIN, EPOLLOUT
    from select import epoll as select_epoll

    HAS_EPOLL = True
except (ImportError, AttributeError):
    HAS_EPOLL = False
    EPOLLIN = EPOLLOUT = EPOLLHUP = EPOLLERR = EPOLLET = 0
    select_epoll = cast(Any, None)

from ..exceptions import HttpError
from ..handlers import server_software

import array
import logging
import socket
import traceback


should_retry_error = (EWOULDBLOCK, EAGAIN)


@lru_cache(maxsize=512)
def parse_header(line: str) -> Tuple[Tuple[str, str], Dict[str, str]]:
    msg = Message()
    msg["content-type"] = line
    return msg.get_params()[0], dict(msg.get_params()[1:])


def make_headers(rw: Any) -> Dict[str, str]:
    headers = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    s = s.decode("utf-8")
    while True:
        if s in ("", "\n", "\r\n"):
            break
        k, v = s.split(":", 1)
        k, v = k.lower().strip(), v.strip()
        headers[k] = v
        s = rw.readline(DEFAULT_BUFFER_SIZE)
        s = s.decode("utf-8")
    return headers


def make_environ(server: Any, rw: Any, client_address: Tuple[str, int]) -> Dict[str, Any]:
    environ = dict()
    environ["SERVER_NAME"] = server.server_name
    environ["SERVER_SOFTWARE"] = server_software
    environ["SERVER_PORT"] = server.server_port
    environ["REMOTE_ADDR"] = client_address[0]
    environ["REMOTE_HOST"] = client_address[0]
    environ["REMOTE_PORT"] = client_address[1]

    s = rw.readline(DEFAULT_BUFFER_SIZE)
    s = s.decode("utf-8")
    if not s:
        raise HttpError("invalid http headers")
    request_method, path_info, protocol = s.strip().split()
    if "?" in path_info:
        path_info, query_string = path_info.split("?", 1)
    else:
        path_info, query_string = path_info, ""
    path_info = unquote_plus(path_info)
    base_uri, script_name = path_info.split("/", 1)
    if "" == script_name:
        script_name = "index.html"
    environ["REQUEST_METHOD"] = request_method.upper()
    environ["QUERY_STRING"] = unquote_plus(query_string)
    environ["SERVER_PROTOCOL"] = protocol
    environ["SCRIPT_NAME"] = script_name
    environ["PATH_INFO"] = path_info
    headers = make_headers(rw)
    length = headers.get("content-length")
    content_type = headers.get("content-type")
    if content_type:
        environ["CONTENT_TYPE"] = content_type
    else:
        environ["CONTENT_TYPE"] = content_type = "text/plain; charset=utf-8"
    if length:
        environ["CONTENT_LENGTH"] = length = int(length)
        if hasattr(server, 'max_request_size') and length > server.max_request_size:
            raise HttpError(413, "Request Entity Too Large")
    _, params = parse_header(content_type)
    charset = params.get("charset")
    environ["CHARSET"] = charset
    for k, v in headers.items():
        k = k.replace("-", "_").upper()
        if k in environ:
            continue
        k = f"HTTP_{k}"
        environ[k] = v
    return environ


class SocketIO(RawIOBase):

    def __init__(self, server: Any, sock: socket.socket) -> None:
        RawIOBase.__init__(self)
        self._fileno = sock.fileno()
        self._sock = sock
        self._server = server

    def fileno(self) -> int:
        return self._fileno

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def readinto(self, b: Any) -> int:
        real_epoll = epoll._epoll
        fileno = self._fileno
        curr = getcurrent()
        self.read_gr = curr
        if self.write_gr is None:
            real_epoll.register(fileno, EPOLLIN | EPOLLET)
        else:
            real_epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
        # 登记空闲读超时截止时间，超过后由 Epoll._check_read_deadlines 断连
        idle_timeout = getattr(self._server, 'idle_read_timeout', None)
        if idle_timeout and idle_timeout > 0:
            epoll._read_deadlines[fileno] = time.time() + idle_timeout
        data = b""
        try:
            curr.parent.switch()
            data = self._sock.recv(len(b))
        except socket.error as e:
            if e.errno not in should_retry_error:
                raise
        finally:
            self.read_gr = None
            epoll._read_deadlines.pop(fileno, None)
            if self.write_gr is None:
                real_epoll.unregister(fileno)
            else:
                real_epoll.modify(fileno, EPOLLOUT | EPOLLET)
        n = len(data)
        try:
            b[:n] = data
        except TypeError as err:
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array(b"b", data)
        return n

    def write(self, data: bytes) -> int:
        real_epoll = epoll._epoll
        fileno = self._fileno
        curr = getcurrent()
        self.write_gr = curr
        if self.read_gr is None:
            real_epoll.register(fileno, EPOLLOUT | EPOLLET)
        else:
            real_epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
        try:
            curr.parent.switch()
            return self._sock.send(data)
        except socket.error as e:
            if e.errno not in should_retry_error:
                raise
        finally:
            self.write_gr = None
            if self.read_gr is None:
                real_epoll.unregister(fileno)
            else:
                real_epoll.modify(fileno, EPOLLIN | EPOLLET)

    def close(self) -> None:
        if self.closed:
            return
        RawIOBase.close(self)
        try:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except socket.error as e:
                if e.errno != ENOTCONN:
                    raise
        finally:
            try:
                self._sock.close()
            except Exception:
                pass

    read_gr: Optional[Any] = None
    write_gr: Optional[Any] = None


class Epoll(object):

    def __init__(self) -> None:
        self._epoll = select_epoll()
        self._servers: Dict[int, socket.socket] = {}
        self._greenlets: Dict[int, Any] = {}
        self._idles: List[Tuple[float, Any]] = []
        # 连接读等待的空闲超时截止时间：fileno -> 绝对时间戳
        self._read_deadlines: Dict[int, float] = {}

    def register(self, server_socket: socket.socket) -> None:
        servers = self._servers
        fileno = server_socket.fileno()
        servers[fileno] = server_socket
        self._epoll.register(fileno, EPOLLIN | EPOLLET)

    def unregister(self, server_socket: socket.socket) -> None:
        servers = self._servers
        fileno = server_socket.fileno()
        if fileno in servers:
            self._epoll.unregister(fileno)
            del servers[fileno]

    def close(self) -> None:
        for fileno, server_socket in self._servers.items():
            self._epoll.unregister(fileno)
            server_socket.server_close()
        self._epoll.close()

    def _check_read_deadlines(self) -> None:
        """检查空闲读超时

        对超过 idle_read_timeout 仍无数据到达的连接，向其 greenlet 注入
        socket.timeout 使请求处理流程退出并关闭连接（慢速连接攻击防护）。
        """
        deadlines = self._read_deadlines
        if not deadlines:
            return
        now_ts = time.time()
        expired = [fileno for fileno, ts in deadlines.items() if ts <= now_ts]
        for fileno in expired:
            deadlines.pop(fileno, None)
            gr = self._greenlets.pop(fileno, None)
            if gr is not None:
                try:
                    gr.throw(socket.timeout('idle read timeout'))
                except Exception:
                    pass

    def poll(self, poll_interval: float = 0.2) -> None:
        servers = self._servers
        greenlets = self._greenlets
        _poll = self._epoll.poll
        idles = self._idles
        while True:
            events = _poll(poll_interval)
            for fileno, event in events:
                if fileno in servers:
                    server = servers[fileno]
                    try:
                        server.handle_request()
                    except KeyboardInterrupt:
                        break
                    except socket.error as e:
                        if e.errno == EMFILE:
                            raise
                        print_exc()
                    except Exception:
                        print_exc()
                elif fileno in greenlets:
                    # 只处理还在 greenlets 字典中的连接
                    if (event & EPOLLIN) or (event & EPOLLOUT):
                        try:
                            greenlets[fileno].switch()
                        except KeyboardInterrupt:
                            break
                        except Exception:
                            # greenlet 执行出错，清理连接
                            gr = greenlets.pop(fileno, None)
                            if gr is not None:
                                gr.throw()
                            print_exc()
                    elif event & (EPOLLHUP | EPOLLERR):
                        try:
                            # 发送异常给 greenlet，让它退出
                            greenlets[fileno].throw()
                        except KeyboardInterrupt:
                            break
                        except Exception:
                            pass
                        finally:
                            # 清理 greenlet
                            gr = greenlets.pop(fileno, None)
                            if gr is not None:
                                gr.throw()
                self._check_read_deadlines()
            while len(idles):
                now_ts = time.time()
                ts, gr = idles.pop(0)
                if ts > now_ts:
                    idles.append((ts, gr))
                    idles.sort()
                    break
                else:
                    gr.switch()


class TCPServer(object):
    """Classic Python TCPServer"""

    allow_reuse_address = True
    request_queue_size = 4194304
    # 最大并发连接数（None 表示不限制），达到上限后新连接被快速拒绝；
    # 可由应用配置 max_connections 覆盖
    max_connections = None
    # 空闲读超时（秒）：连接阻塞等待读数据超过该时长将被断开，
    # 设为 0 或 None 可禁用；可由应用配置 idle_read_timeout 覆盖
    idle_read_timeout = 30.0
    address_family, socket_type = socket.AF_INET, socket.SOCK_STREAM

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Any,
        bind_and_activate: bool = True
    ) -> None:
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.socket = socket.socket(self.address_family, self.socket_type)
        self._started = False
        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
            except Exception:
                self.server_close()
                raise

    def server_bind(self) -> None:
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # 启用 SO_REUSEPORT，允许多个进程绑定到同一个端口
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except (AttributeError, OSError):
            # 某些系统可能不支持 SO_REUSEPORT
            pass
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logging.info("bind %s:%s", *self.server_address)
        self.socket.bind(self.server_address)
        self.socket.setblocking(0)

    def server_activate(self) -> None:
        self.socket.listen(self.request_queue_size)

    def server_close(self) -> None:
        self.socket.close()

    def fileno(self) -> int:
        return self.socket.fileno()

    def get_request(self) -> Tuple[socket.socket, Tuple[str, int]]:
        return self.socket.accept()

    def handle_request(self) -> None:
        self._handle_request_noblock()

    def _handle_request_noblock(self) -> None:
        while True:
            try:
                request, client_address = self.get_request()
            except socket.error as e:
                errno = e.args[0]
                if EAGAIN == errno or EWOULDBLOCK == errno:
                    return
                raise
            if self.verify_request(request, client_address):
                try:
                    self.process_request(request, client_address)
                except Exception:
                    self.handle_error(request, client_address)
                    self.shutdown_request(request)
            else:
                self.shutdown_request(request)

    def handle_timeout(self) -> None:
        pass

    def verify_request(self, request: socket.socket, client_address: Tuple[str, int]) -> bool:
        if self.max_connections is not None and epoll is not None:
            # 连接数达到上限：快速拒绝（shutdown_request 立即关闭连接），
            # 不为其创建 greenlet 与 epoll 注册项
            if len(epoll._greenlets) >= self.max_connections:
                return False
        return True

    def process_request(self, request: socket.socket, client_address: Tuple[str, int]) -> None:
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def finish_request(self, request: socket.socket, client_address: Tuple[str, int]) -> None:
        request.setblocking(0)
        fileno = request.fileno()
        epoll._greenlets[fileno] = curr = greenlet(
            partial(self._finish_request, request, client_address)
        )
        curr.switch()

    def _finish_request(self, request: socket.socket, client_address: Tuple[str, int]) -> None:
        raw = SocketIO(self, request)
        try:
            rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
            environ = make_environ(self, rw, client_address)
            self.RequestHandlerClass(request, rw, environ, self)
            self.shutdown_request(request)
        except socket.error as e:
            if e.errno == EPIPE:
                raise GreenletExit
            raise
        except HttpError as e:
            # Send HTTP error response
            try:
                status_code = e.status_code
                message = e.message
                response = f"HTTP/1.1 {status_code} {message}\r\n"
                response += "Content-Type: text/html; charset=utf-8\r\n"
                response += "Content-Length: %d\r\n" % len(message)
                response += "\r\n"
                response += message
                # Write the response
                rw.write(response.encode('utf-8'))
                # Flush the buffer to ensure the response is sent
                if hasattr(rw, 'flush'):
                    rw.flush()
            finally:
                self.shutdown_request(request)
        finally:
            # 确保在所有情况下都清理 greenlet 和关闭连接
            try:
                try:
                    if raw.read_gr is not None:
                        raw.read_gr.throw()
                    if raw.write_gr is not None:
                        raw.write_gr.throw()
                finally:
                    fileno = raw.fileno()
                    gr = epoll._greenlets.pop(fileno, None)
                    if gr is not None:
                        gr.throw()
            finally:
                # 确保连接被关闭
                if not raw.closed:
                    try:
                        raw.close()
                    except Exception:
                        pass

    def shutdown_request(self, request: socket.socket) -> None:
        try:
            request.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        self.close_request(request)

    def close_request(self, request: socket.socket) -> None:
        request.close()

    def handle_error(self, request: socket.socket, client_address: Tuple[str, int]) -> None:
        traceback.print_exc()

    def server_forever(self, poll_interval: float = 0.1) -> None:
        if not self._started:
            epoll.register(self)
        mainloop(poll_interval=poll_interval)

    def start(self) -> None:
        if not self._started:
            epoll.register(self)
            self._started = True

    def shutdown(self) -> None:
        if self._started:
            epoll.unregister(self)
            self._started = False


def mainloop(poll_interval: float = 0.1) -> None:
    try:
        epoll.poll(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass


server_forever = mainloop

epoll: Any = Epoll() if HAS_EPOLL else None
