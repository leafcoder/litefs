#!/usr/bin/env python
# coding: utf-8

from errno import EAGAIN, EMFILE, ENOTCONN, EPIPE, EWOULDBLOCK
from functools import lru_cache, partial
from io import DEFAULT_BUFFER_SIZE, BufferedRWPair, RawIOBase
from posixpath import abspath as path_abspath
from posixpath import join as path_join
from time import time
from traceback import print_exc
from urllib.parse import unquote_plus
from email.message import Message

try:
    from greenlet import GreenletExit, getcurrent, greenlet

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
    select_epoll = None

from ..exceptions import HttpError
from ..handlers import RequestHandler, parse_form
from ..utils import log_error

import array
import traceback
import logging
import socket
import sys
import os
import multiprocessing


should_retry_error = (EWOULDBLOCK, EAGAIN)


@lru_cache(maxsize=512)
def parse_header(line):
    msg = Message()
    msg["content-type"] = line
    return msg.get_params()[0], dict(msg.get_params()[1:])


def make_headers(rw):
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


def make_environ(server, rw, client_address):
    environ = dict()
    environ["SERVER_NAME"] = server.server_name
    environ["SERVER_SOFTWARE"] = "litefs/0.4.0"
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

    def __init__(self, server, sock):
        RawIOBase.__init__(self)
        self._fileno = sock.fileno()
        self._sock = sock
        self._server = server

    def fileno(self):
        return self._fileno

    def readable(self):
        return True

    def writable(self):
        return True

    def readinto(self, b):
        real_epoll = epoll._epoll
        fileno = self._fileno
        curr = getcurrent()
        self.read_gr = curr
        if self.write_gr is None:
            real_epoll.register(fileno, EPOLLIN | EPOLLET)
        else:
            real_epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
        data = b""
        try:
            curr.parent.switch()
            data = self._sock.recv(len(b))
        except socket.error as e:
            if e.errno not in should_retry_error:
                raise
        finally:
            self.read_gr = None
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

    def write(self, data):
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

    def close(self):
        if self.closed:
            return
        RawIOBase.close(self)
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            if e.errno != ENOTCONN:
                raise
        self._sock.close()

    read_gr = write_gr = None


class Epoll(object):

    def __init__(self):
        self._epoll = select_epoll()
        self._servers = {}
        self._greenlets = {}
        self._idles = []

    def register(self, server_socket):
        servers = self._servers
        fileno = server_socket.fileno()
        servers[fileno] = server_socket
        self._epoll.register(fileno, EPOLLIN | EPOLLET)

    def unregister(self, server_socket):
        servers = self._servers
        fileno = server_socket.fileno()
        if fileno in servers:
            self._epoll.unregister(fileno)
            del servers[fileno]

    def close(self):
        for fileno, server_socket in self._servers.items():
            self._epoll.unregister(fileno)
            server_socket.server_close()
        self._epoll.close()

    def poll(self, poll_interval=0.2):
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
                elif (event & EPOLLIN) or (event & EPOLLOUT):
                    try:
                        greenlets[fileno].switch()
                    except KeyboardInterrupt:
                        break
                    except Exception:
                        print_exc()
                elif event & (EPOLLHUP | EPOLLERR):
                    try:
                        greenlets[fileno].throw()
                    except KeyboardInterrupt:
                        break
                    except Exception:
                        print_exc()
            while len(idles):
                now_ts = time()
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
    address_family, socket_type = socket.AF_INET, socket.SOCK_STREAM

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
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

    def server_bind(self):
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

    def server_activate(self):
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        self.socket.close()

    def fileno(self):
        return self.socket.fileno()

    def get_request(self):
        return self.socket.accept()

    def handle_request(self):
        self._handle_request_noblock()

    def _handle_request_noblock(self):
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

    def handle_timeout(self):
        pass

    def verify_request(self, request, client_address):
        return True

    def process_request(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def finish_request(self, request, client_address):
        request.setblocking(0)
        fileno = request.fileno()
        epoll._greenlets[fileno] = curr = greenlet(
            partial(self._finish_request, request, client_address)
        )
        curr.switch()

    def _finish_request(self, request, client_address):
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
                # Give some time for the response to be sent
                import time
                time.sleep(0.1)
            except Exception:
                pass
            finally:
                self.shutdown_request(request)
        except Exception as e:
            raise
        finally:
            try:
                if raw.read_gr is not None:
                    raw.read_gr.throw()
                if raw.write_gr is not None:
                    raw.write_gr.throw()
            finally:
                fileno = raw.fileno()
                epoll._greenlets.pop(fileno, None)
            if not raw.closed:
                try:
                    raw.close()
                except Exception:
                    pass

    def shutdown_request(self, request):
        try:
            request.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        self.close_request(request)

    def close_request(self, request):
        request.close()

    def handle_error(self, request, client_address):
        traceback.print_exc()

    def server_forever(self, poll_interval=0.1):
        if not self._started:
            epoll.register(self)
        mainloop(poll_interval=poll_interval)

    def start(self):
        if not self._started:
            epoll.register(self)
            self._started = True

    def shutdown(self):
        if self._started:
            epoll.unregister(self)
            self._started = False


class HTTPServer(TCPServer):

    allow_reuse_address = 1
    max_request_size = 10485760

    def server_bind(self):
        TCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port


class ProcessHTTPServer(HTTPServer):
    """多进程 HTTP 服务器"""

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, processes=4):
        """
        初始化多进程 HTTP 服务器
        
        Args:
            server_address: 服务器地址
            RequestHandlerClass: 请求处理器类
            bind_and_activate: 是否绑定和激活
            processes: 进程数，默认为 4
        """
        # 延迟绑定端口，避免热重载时端口被占用
        super().__init__(server_address, RequestHandlerClass, False)
        self.processes = processes
        self.workers = []

    def server_forever(self, poll_interval=0.1):
        """启动多进程服务器"""
        # 绑定和激活服务器
        self.server_bind()
        self.server_activate()
        
        # 启动多个进程
        for i in range(self.processes):
            worker = multiprocessing.Process(target=self._run_worker, args=(i, poll_interval))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
            logging.info(f"启动工作进程 {i}")
        
        # 等待所有进程结束
        try:
            for worker in self.workers:
                worker.join()
        except KeyboardInterrupt:
            logging.info("接收到中断信号，停止服务器")
            self.shutdown()

    def _run_worker(self, worker_id, poll_interval):
        """运行工作进程"""
        logging.info(f"工作进程 {worker_id} 启动，PID: {os.getpid()}")
        try:
            # 每个进程创建自己的 epoll 实例
            global epoll
            epoll = Epoll() if HAS_EPOLL else None
            
            # 运行主循环
            if HAS_EPOLL:
                # 注册服务器套接字到 epoll
                if not hasattr(self, '_started') or not self._started:
                    epoll.register(self)
                    self._started = True
                
                # 运行 epoll 循环
                while True:
                    epoll.poll(poll_interval=poll_interval)
            else:
                # 运行传统循环
                while True:
                    self.handle_request()
        except Exception as e:
            logging.error(f"工作进程 {worker_id} 出错: {e}")
            import traceback
            traceback.print_exc()

    def shutdown(self):
        """关闭服务器"""
        for worker in self.workers:
            if worker.is_alive():
                worker.terminate()
                # 等待工作进程完全关闭
                worker.join(timeout=5)
        logging.info("服务器已关闭")


class WSGIServer(HTTPServer):

    application = None

    def server_bind(self):
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        env = {}
        env["SERVER_NAME"] = self.server_name
        env["SERVER_PORT"] = str(self.server_port)
        env["REMOTE_HOST"] = ""
        env["CONTENT_LENGTH"] = -1
        env["SCRIPT_NAME"] = ""
        self.base_environ = env

    def get_app(self):
        return self.application

    def set_app(self, application):
        self.application = application


def mainloop(poll_interval=0.1):
    try:
        epoll.poll(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass


server_forever = mainloop

epoll = Epoll() if HAS_EPOLL else None
