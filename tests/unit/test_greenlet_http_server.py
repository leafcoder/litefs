#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Greenlet HTTP 服务器测试

覆盖 :mod:`litefs.server.greenlet` 中的 ``HTTPServer``、``WSGIServer`` 与
``ProcessHTTPServer``（PID 文件管理、信号处理、Master-Worker 生命周期）。
涉及 fork / 信号的部分均以 Mock 隔离，不在测试进程内真正 fork。
"""

import os
import signal
import subprocess
import sys
import time
from unittest.mock import Mock, patch

import pytest

from litefs.server import greenlet_server_base as gsb
from litefs.server.greenlet import (
    HTTPServer,
    ProcessHTTPServer,
    WSGIServer,
)


@pytest.fixture
def restore_signals():
    """保存并恢复 SIGINT/SIGTERM/SIGCHLD 处理器，避免污染测试进程"""
    saved = {
        sig: signal.getsignal(sig)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGCHLD)
    }
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


def _make_process_server(**kwargs):
    """构造未绑定的 ProcessHTTPServer（bind_and_activate=False）"""
    return ProcessHTTPServer(("127.0.0.1", 0), Mock, **kwargs)


class TestHTTPServer:
    """HTTPServer 绑定行为测试"""

    def test_server_bind_sets_name_and_port(self):
        """测试 server_bind 设置 server_name 与 server_port"""
        srv = HTTPServer(("127.0.0.1", 0), Mock)
        try:
            port = srv.socket.getsockname()[1]
            assert srv.server_port == port
            assert srv.server_name  # getfqdn 返回非空
        finally:
            srv.server_close()

    def test_class_attributes(self):
        """测试类级默认属性"""
        assert HTTPServer.allow_reuse_address == 1
        assert HTTPServer.max_request_size == 10485760


class TestWSGIServer:
    """WSGIServer environ 与 app 管理测试"""

    def test_server_bind_setup_environ(self):
        """测试 server_bind 时构建 base_environ"""
        srv = WSGIServer(("127.0.0.1", 0), Mock)
        try:
            env = srv.base_environ
            assert env["SERVER_NAME"] == srv.server_name
            assert env["SERVER_PORT"] == str(srv.server_port)
            assert env["REMOTE_HOST"] == ""
            assert env["CONTENT_LENGTH"] == -1
            assert env["SCRIPT_NAME"] == ""
        finally:
            srv.server_close()

    def test_get_set_app(self):
        """测试 get_app/set_app 存取应用对象"""
        srv = WSGIServer(("127.0.0.1", 0), Mock)
        try:
            assert srv.get_app() is None
            app = Mock()
            srv.set_app(app)
            assert srv.get_app() is app
        finally:
            srv.server_close()


class TestProcessHTTPServerPidFile:
    """PID 文件读写与残留进程清理测试"""

    def test_init_defaults(self):
        """测试初始化默认状态"""
        srv = _make_process_server()
        assert srv.processes == 4
        assert srv.workers == []
        assert srv._shutdown_requested is False
        assert srv._master_pid == os.getpid()
        assert srv._worker_pids == []
        srv.server_close()

    def test_init_custom_processes(self):
        """测试自定义进程数"""
        srv = _make_process_server(processes=2)
        assert srv.processes == 2
        srv.server_close()

    def test_pid_file_roundtrip(self):
        """测试 PID 文件写入、读取与删除"""
        srv = _make_process_server()
        try:
            srv._worker_pids = [111, 222]
            srv._write_pid_file()

            pid_file = srv._get_pid_file()
            assert os.path.exists(pid_file)
            assert "127.0.0.1_0" in pid_file

            data = srv._read_pid_file()
            assert data["master_pid"] == os.getpid()
            assert data["worker_pids"] == [111, 222]

            srv._remove_pid_file()
            assert not os.path.exists(pid_file)
            assert srv._read_pid_file() is None
        finally:
            srv._remove_pid_file()
            srv.server_close()

    def test_read_pid_file_corrupt(self):
        """测试损坏的 PID 文件返回 None"""
        srv = _make_process_server()
        try:
            pid_file = srv._get_pid_file()
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, "wb") as f:
                f.write(b"\x00\x01not-json")

            assert srv._read_pid_file() is None
        finally:
            srv._remove_pid_file()
            srv.server_close()

    def test_is_process_alive(self):
        """测试进程存活检测：自身存活、已退出进程不存活"""
        srv = _make_process_server()
        try:
            assert srv._is_process_alive(os.getpid()) is True

            proc = subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(0.01)"]
            )
            proc.wait()
            assert srv._is_process_alive(proc.pid) is False
        finally:
            srv.server_close()

    def test_kill_stale_processes_no_file(self):
        """测试无 PID 文件时直接返回"""
        srv = _make_process_server()
        try:
            srv._remove_pid_file()
            srv._kill_stale_processes()  # 快速返回，不抛异常
        finally:
            srv.server_close()

    def test_kill_stale_processes_terminates(self):
        """测试残留进程被 SIGTERM 清理且 PID 文件被删除"""
        srv = _make_process_server()
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            # 等待子进程稳定存活
            time.sleep(0.2)
            srv._worker_pids = []
            srv._write_pid_file()
            # 覆写 master_pid 为真实残留子进程
            pid_file = srv._get_pid_file()
            from litefs._json import dump

            with open(pid_file, "wb") as f:
                dump(
                    {
                        "master_pid": proc.pid,
                        "worker_pids": [],
                        "port": 0,
                        "host": "127.0.0.1",
                        "starttime": time.time(),
                    },
                    f,
                )

            srv._kill_stale_processes()

            assert proc.poll() is not None  # 子进程已退出
            assert not os.path.exists(pid_file)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            srv._remove_pid_file()
            srv.server_close()

    def test_kill_stale_processes_dead_pids(self):
        """测试 PID 文件中全部为已退出进程时仅删除文件"""
        srv = _make_process_server()
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        try:
            from litefs._json import dump

            pid_file = srv._get_pid_file()
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, "wb") as f:
                dump(
                    {
                        "master_pid": dead.pid,
                        "worker_pids": [dead.pid],
                        "port": 0,
                        "host": "127.0.0.1",
                        "starttime": time.time(),
                    },
                    f,
                )

            srv._kill_stale_processes()

            assert not os.path.exists(pid_file)
        finally:
            srv._remove_pid_file()
            srv.server_close()


@pytest.mark.usefixtures("restore_signals")
class TestProcessHTTPServerSignals:
    """信号处理器安装测试"""

    def test_setup_signal_handlers(self):
        """测试信号处理器写入管道触发关闭标记"""
        srv = _make_process_server()
        pipe_r, pipe_w = os.pipe()
        srv._signal_pipe_w = pipe_w
        try:
            srv._setup_signal_handlers()

            term_handler = signal.getsignal(signal.SIGTERM)
            assert term_handler is not None
            assert signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN

            # 直接触发处理器，验证向管道写入标记
            term_handler(signal.SIGTERM, None)
            assert os.read(pipe_r, 1) == b"1"
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
            srv.server_close()


class TestProcessHTTPServerMasterLoop:
    """Master 循环与 Worker 管理测试"""

    def test_master_loop_exits_on_signal(self):
        """测试信号管道可读时退出主循环"""
        srv = _make_process_server()
        pipe_r, pipe_w = os.pipe()
        srv._signal_pipe_r = pipe_r
        try:
            with patch(
                "litefs.server.greenlet.select.select",
                side_effect=[([], [], []), ([pipe_r], [], [])],
            ):
                srv._master_loop(0.01)

            assert srv._shutdown_requested is True
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
            srv.server_close()

    def test_master_loop_keyboard_interrupt(self):
        """测试 select 抛出 KeyboardInterrupt 时优雅退出"""
        srv = _make_process_server()
        pipe_r, pipe_w = os.pipe()
        srv._signal_pipe_r = pipe_r
        try:
            with patch(
                "litefs.server.greenlet.select.select",
                side_effect=KeyboardInterrupt,
            ):
                srv._master_loop(0.01)

            assert srv._shutdown_requested is True
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
            srv.server_close()

    def test_master_loop_generic_error_continues(self):
        """测试 select 普通异常被记录后继续循环"""
        srv = _make_process_server()
        pipe_r, pipe_w = os.pipe()
        srv._signal_pipe_r = pipe_r
        try:
            with patch(
                "litefs.server.greenlet.select.select",
                side_effect=[RuntimeError("boom"), KeyboardInterrupt],
            ):
                srv._master_loop(0.01)

            assert srv._shutdown_requested is True
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
            srv.server_close()

    def test_check_workers_restarts_dead(self):
        """测试意外退出的 Worker 被重启并更新 PID 文件"""
        srv = _make_process_server()
        try:
            srv._worker_pids = [123]
            srv._is_process_alive = Mock(return_value=True)
            srv._is_process_alive.return_value = True
            with patch("os.fork", return_value=60000) as m_fork:
                # 使第一个 pid 检测为已退出
                srv._is_process_alive = Mock(side_effect=[False, True])
                srv._check_workers()

            m_fork.assert_called_once()
            assert srv._worker_pids == [60000]
        finally:
            srv._remove_pid_file()
            srv.server_close()

    def test_check_workers_all_alive_noop(self):
        """测试全部 Worker 存活时不做任何操作"""
        srv = _make_process_server()
        try:
            srv._worker_pids = [123]
            srv._is_process_alive = Mock(return_value=True)
            with patch("os.fork") as m_fork:
                srv._check_workers()

            m_fork.assert_not_called()
            assert srv._worker_pids == [123]
        finally:
            srv.server_close()

    def test_shutdown_workers_empty_noop(self):
        """测试无 Worker 时关闭为无操作"""
        srv = _make_process_server()
        try:
            srv._shutdown_workers()
            assert srv._worker_pids == []
        finally:
            srv.server_close()

    def test_shutdown_workers_all_dead(self):
        """测试 Worker 全部退出时快速完成关闭"""
        srv = _make_process_server()
        try:
            srv._worker_pids = [111, 222]
            srv._is_process_alive = Mock(return_value=False)

            srv._shutdown_workers()

            assert srv._worker_pids == []
        finally:
            srv.server_close()

    def test_shutdown_workers_sigkill_fallback(self):
        """测试 SIGTERM 超时后对存活 Worker 发送 SIGKILL"""
        srv = _make_process_server()
        try:
            srv._worker_pids = [111]
            srv._is_process_alive = Mock(return_value=True)
            fake_time = Mock()
            fake_time.time.side_effect = [0.0, 0.0, 10.0]  # start / 首轮 / 超时
            fake_time.sleep = Mock()

            with patch("os.kill") as m_kill, patch(
                "litefs.server.greenlet.time", fake_time
            ):
                srv._shutdown_workers()

            kill_signals = [call.args[1] for call in m_kill.call_args_list]
            assert signal.SIGTERM in kill_signals
            assert signal.SIGKILL in kill_signals
            assert srv._worker_pids == []
        finally:
            srv.server_close()

    def test_server_forever_lifecycle(self):
        """测试 server_forever：fork Worker → 写 PID 文件 → 信号退出 → 清理"""
        srv = _make_process_server()
        pipe_r, pipe_w = os.pipe()
        try:
            with patch("os.fork", return_value=54321), patch.object(
                srv, "_is_process_alive", return_value=True
            ), patch.object(srv, "_kill_stale_processes") as m_kill_stale, patch.object(
                srv, "_shutdown_workers"
            ) as m_shutdown_workers, patch.object(
                srv, "_setup_signal_handlers"
            ), patch(
                "litefs.server.greenlet.select.select",
                side_effect=[([], [], []), ([pipe_r], [], [])],
            ):
                srv._signal_pipe_r = pipe_r
                srv.server_forever(poll_interval=0.01)

            m_kill_stale.assert_called_once()
            m_shutdown_workers.assert_called_once()
            assert srv._worker_pids == [54321] * srv.processes
            assert srv._shutdown_requested is True
            assert not os.path.exists(srv._get_pid_file())  # finally 中已清理
        finally:
            os.close(pipe_r)
            os.close(pipe_w)
            srv._remove_pid_file()
            srv.server_close()


class TestProcessHTTPServerWorker:
    """工作进程主循环测试（进程内直接调用，信号与 epoll 隔离）"""

    @pytest.fixture(autouse=True)
    def restore_epoll_singleton(self):
        """_run_worker 会重建模块级 epoll 单例，测试后恢复"""
        self._orig_epoll = gsb.epoll
        yield
        import litefs.server.greenlet as gl

        gl.epoll = self._orig_epoll
        gsb.epoll = self._orig_epoll

    def test_run_worker_epoll_branch(self):
        """测试 epoll 分支：重建单例并同步到拆分模块"""
        import litefs.server.greenlet as gl

        srv = _make_process_server()
        try:
            with patch("signal.signal"), patch.object(
                gsb.Epoll, "poll", side_effect=KeyboardInterrupt
            ):
                srv._run_worker(0, 0.01)

            # 单例已重建且双向同步
            assert gl.epoll is not self._orig_epoll
            assert gsb.epoll is gl.epoll
            assert srv._started is True
        finally:
            srv.server_close()

    def test_run_worker_epoll_generic_error(self):
        """测试 epoll 分支普通异常被记录后退出"""
        srv = _make_process_server()
        try:
            with patch("signal.signal"), patch.object(
                gsb.Epoll, "poll", side_effect=RuntimeError("boom")
            ):
                srv._run_worker(0, 0.01)  # 异常被捕获记录，不向外抛
        finally:
            srv.server_close()

    def test_run_worker_no_epoll_branch(self):
        """测试无 epoll 环境降级为 handle_request 轮询"""
        import litefs.server.greenlet as gl

        srv = _make_process_server()
        srv.handle_request = Mock(side_effect=KeyboardInterrupt)
        try:
            with patch("signal.signal"), patch.object(
                gl, "HAS_EPOLL", False
            ):
                srv._run_worker(1, 0.01)

            srv.handle_request.assert_called_once()
            assert gl.epoll is None
        finally:
            srv.server_close()


def test_module_server_forever_alias():
    """测试 greenlet.server_forever 为拆分模块别名"""
    from litefs.server import greenlet_server_base
    from litefs.server import greenlet

    assert greenlet.server_forever is greenlet_server_base.server_forever
