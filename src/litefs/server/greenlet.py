#!/usr/bin/env python
# coding: utf-8

import time
from errno import EAGAIN, EMFILE, ENOTCONN, EPIPE, EWOULDBLOCK  # noqa: F401  # 保持模块符号面
from functools import lru_cache, partial  # noqa: F401  # 保持模块符号面
from io import DEFAULT_BUFFER_SIZE, BufferedRWPair, RawIOBase  # noqa: F401  # 保持模块符号面
from traceback import print_exc  # noqa: F401  # 保持模块符号面
from urllib.parse import unquote_plus  # noqa: F401  # 保持模块符号面
from email.message import Message  # noqa: F401  # 保持模块符号面

from typing import Dict, List, Optional, Any, Tuple  # noqa: F401  # 保持模块符号面

try:
    from greenlet import GreenletExit, getcurrent, greenlet  # noqa: F401  # 保持模块符号面

    HAS_GREENLET = True
except ImportError:
    HAS_GREENLET = False
    greenlet = None
    getcurrent = None
    GreenletExit = None

try:
    from select import EPOLLERR, EPOLLET, EPOLLHUP, EPOLLIN, EPOLLOUT  # noqa: F401
    from select import epoll as select_epoll  # noqa: F401

    HAS_EPOLL = True
except (ImportError, AttributeError):
    HAS_EPOLL = False
    EPOLLIN = EPOLLOUT = EPOLLHUP = EPOLLERR = EPOLLET = 0
    select_epoll = None

from .._json import dump, load
from ..exceptions import HttpError  # noqa: F401  # 对外再导出
from ..handlers import RequestHandler, parse_form, server_software  # noqa: F401  # 对外再导出

import array  # noqa: F401  # 保持模块符号面
import traceback  # noqa: F401  # 保持模块符号面
import logging
import socket
import os
import signal
import select
import tempfile

from .greenlet_server_base import Epoll  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import SocketIO  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import TCPServer  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import mainloop  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import make_environ  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import make_headers  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import parse_header  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import should_retry_error  # noqa: F401  # 内部拆分模块再导出
from .greenlet_server_base import epoll  # noqa: F401  # 内部拆分模块再导出
from . import greenlet_server_base as _greenlet_server_base  # 内部拆分模块句柄


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

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True, processes=4,
                 request_queue_size=None):
        super().__init__(
            server_address, RequestHandlerClass, False,
            request_queue_size=request_queue_size,
        )
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
            with open(pid_file, 'wb') as f:
                dump(pid_data, f)
        except Exception as e:
            logging.warning(f"无法写入 PID 文件: {e}")

    def _read_pid_file(self):
        """读取 PID 文件"""
        pid_file = self._get_pid_file()
        try:
            if os.path.exists(pid_file):
                with open(pid_file, 'rb') as f:
                    return load(f)
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
        # 拆分后 epoll 单例由 greenlet_server_base 持有：worker 重建实例后必须同步，
        # 确保 TCPServer/SocketIO/mainloop 与本方法操作同一 epoll 实例（与拆分前行为一致）
        _greenlet_server_base.epoll = epoll

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


server_forever = _greenlet_server_base.server_forever
