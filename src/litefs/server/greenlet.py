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

from typing import Dict, List, Optional, Callable, Any, Union, Tuple, cast

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
import time
import signal
import select
import tempfile
import json


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
    environ["SERVER_SOFTWARE"] = "litefs/0.5.0"
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
            except:
                pass

    read_gr: Optional[Any] = None
    write_gr: Optional[Any] = None


class Epoll(object):

    def __init__(self) -> None:
        self._epoll = select_epoll()
        self._servers: Dict[int, socket.socket] = {}
        self._greenlets: Dict[int, Any] = {}
        self._idles: List[Tuple[float, Any]] = []

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

    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass: Any, bind_and_activate: bool = True) -> None:
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
            except Exception:
                pass
            finally:
                self.shutdown_request(request)
        except Exception as e:
            raise
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


class HTTPServer(TCPServer):

    allow_reuse_address = 1
    max_request_size = 10485760

    def server_bind(self):
        TCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port


class ProcessHTTPServer(HTTPServer):
    """多进程 HTTP 服务器（改进版）
    
    改进点：
    1. 使用 PID 文件管理进程，避免残留
    2. Master-Worker 架构，Master 负责管理 Worker
    3. 优雅关闭，先停止接收新连接，等待现有请求完成
    4. 信号管道通信，确保信号可靠传递
    """

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, processes=4):
        super().__init__(server_address, RequestHandlerClass, False)
        self.processes = processes
        self.workers = []
        self._shutdown_requested = False
        self._master_pid = os.getpid()
        self._worker_pids = []
        self._signal_pipe_r = None
        self._signal_pipe_w = None
        self._listen_sock = None

    def _get_pid_file(self):
        """获取 PID 文件路径"""
        host, port = self.server_address
        pid_dir = os.path.join(tempfile.gettempdir(), 'litefs')
        os.makedirs(pid_dir, exist_ok=True)
        return os.path.join(pid_dir, f'litefs_{host}_{port}.pid')

    def _write_pid_file(self):
        """写入 PID 文件"""
        pid_file = self._get_pid_file()
        pid_data = {
            'master_pid': os.getpid(),
            'worker_pids': self._worker_pids,
            'port': self.server_address[1],
            'host': self.server_address[0],
            'starttime': time.time()
        }
        try:
            with open(pid_file, 'w') as f:
                json.dump(pid_data, f)
        except Exception as e:
            logging.warning(f"无法写入 PID 文件: {e}")

    def _read_pid_file(self):
        """读取 PID 文件"""
        pid_file = self._get_pid_file()
        try:
            if os.path.exists(pid_file):
                with open(pid_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _remove_pid_file(self):
        """删除 PID 文件"""
        pid_file = self._get_pid_file()
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception:
            pass

    def _is_process_alive(self, pid):
        """检查进程是否存活"""
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _kill_stale_processes(self):
        """清理残留进程"""
        pid_data = self._read_pid_file()
        if not pid_data:
            return
        
        master_pid = pid_data.get('master_pid')
        worker_pids = pid_data.get('worker_pids', [])
        
        all_pids = [master_pid] + worker_pids
        all_pids = [p for p in all_pids if p and p != os.getpid()]
        
        for pid in all_pids:
            if self._is_process_alive(pid):
                logging.info(f"清理残留进程: PID {pid}")
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(0.1)
                    if self._is_process_alive(pid):
                        os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        
        self._remove_pid_file()
        time.sleep(0.5)

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        def handle_signal(signum, frame):
            if self._signal_pipe_w is not None:
                try:
                    os.write(self._signal_pipe_w, b'1')
                except OSError:
                    pass
        
        signal.signal(signal.SIGTERM, handle_signal)
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGCHLD, signal.SIG_IGN)

    def server_forever(self, poll_interval=0.1):
        """启动多进程服务器"""
        self._kill_stale_processes()
        
        self._signal_pipe_r, self._signal_pipe_w = os.pipe()
        
        self.server_bind()
        self.server_activate()
        self._listen_sock = self.socket
        
        self._setup_signal_handlers()
        
        for i in range(self.processes):
            worker_pid = os.fork()
            if worker_pid == 0:
                self._run_worker(i, poll_interval)
                os._exit(0)
            else:
                self._worker_pids.append(worker_pid)
                logging.info(f"启动工作进程 {i}, PID: {worker_pid}")
        
        self._write_pid_file()
        
        try:
            self._master_loop(poll_interval)
        except Exception as e:
            logging.error(f"Master 进程错误: {e}")
        finally:
            self._shutdown_workers()
            self._remove_pid_file()

    def _master_loop(self, poll_interval):
        """Master 进程主循环"""
        while not self._shutdown_requested:
            try:
                rlist, _, _ = select.select([self._signal_pipe_r], [], [], poll_interval)
                if rlist:
                    self._shutdown_requested = True
                    break
                
                self._check_workers()
            except KeyboardInterrupt:
                self._shutdown_requested = True
                break
            except Exception as e:
                logging.error(f"Master 循环错误: {e}")

    def _check_workers(self):
        """检查工作进程状态，自动重启意外退出的进程"""
        for i, pid in enumerate(self._worker_pids):
            if pid and not self._is_process_alive(pid):
                logging.warning(f"工作进程 {i} (PID: {pid}) 意外退出，正在重启...")
                new_pid = os.fork()
                if new_pid == 0:
                    self._run_worker(i, 0.1)
                    os._exit(0)
                else:
                    self._worker_pids[i] = new_pid
                    self._write_pid_file()
                    logging.info(f"重启工作进程 {i}, 新 PID: {new_pid}")

    def _run_worker(self, worker_id, poll_interval):
        """运行工作进程"""
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        
        logging.info(f"工作进程 {worker_id} 启动，PID: {os.getpid()}")
        
        global epoll
        epoll = Epoll() if HAS_EPOLL else None
        
        if HAS_EPOLL:
            epoll.register(self)
            self._started = True
            
            try:
                while not self._shutdown_requested:
                    epoll.poll(poll_interval=poll_interval)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                logging.error(f"工作进程 {worker_id} 错误: {e}")
            finally:
                try:
                    epoll.unregister(self)
                except Exception:
                    pass
        else:
            try:
                while not self._shutdown_requested:
                    self.handle_request()
            except KeyboardInterrupt:
                pass

    def _shutdown_workers(self):
        """关闭所有工作进程"""
        if not self._worker_pids:
            return
        
        logging.info("正在关闭工作进程...")
        
        for pid in self._worker_pids:
            if pid and self._is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
        
        timeout = 5
        start_time = time.time()
        while time.time() - start_time < timeout:
            all_dead = True
            for pid in self._worker_pids:
                if pid and self._is_process_alive(pid):
                    all_dead = False
                    break
            if all_dead:
                break
            time.sleep(0.1)
        
        for pid in self._worker_pids:
            if pid and self._is_process_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        
        self._worker_pids = []
        logging.info("所有工作进程已关闭")

    def shutdown(self):
        """关闭服务器"""
        self._shutdown_requested = True
        
        if os.getpid() == self._master_pid:
            self._shutdown_workers()
            self._remove_pid_file()
        
        try:
            self.server_close()
        except Exception:
            pass
        
        if self._signal_pipe_r is not None:
            try:
                os.close(self._signal_pipe_r)
            except OSError:
                pass
        if self._signal_pipe_w is not None:
            try:
                os.close(self._signal_pipe_w)
            except OSError:
                pass


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


def mainloop(poll_interval: float = 0.1) -> None:
    try:
        epoll.poll(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass


server_forever = mainloop

epoll = Epoll() if HAS_EPOLL else None
