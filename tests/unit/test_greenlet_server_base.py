#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
greenlet 服务器基础组件测试

覆盖 :mod:`litefs.server.greenlet_server_base` 中的 ``SocketIO``、
``Epoll``、``TCPServer``、``mainloop`` 及 ``make_environ`` 边界分支。
所有用例仅使用本地 socketpair / 回环地址与 Mock，不依赖外部服务。
"""

import errno
import socket
import time
from io import BytesIO
from unittest.mock import Mock, patch

import pytest

try:
    from greenlet import greenlet, getcurrent

    HAS_GREENLET = True
except ImportError:
    HAS_GREENLET = False

try:
    from select import EPOLLIN, EPOLLOUT, EPOLLHUP, EPOLLERR, EPOLLET

    HAS_EPOLL = True
except (ImportError, AttributeError):
    HAS_EPOLL = False

requires_greenlet = pytest.mark.skipif(not HAS_GREENLET, reason="greenlet 未安装")
requires_epoll = pytest.mark.skipif(
    not HAS_GREENLET or not HAS_EPOLL, reason="greenlet/epoll 不可用"
)


@requires_greenlet
class TestSocketIO:
    """SocketIO 基于 greenlet 切换的 IO 行为测试"""

    def _make_pair(self):
        """创建非阻塞 socketpair 并返回 (读端 SocketIO, 对端 socket)"""
        from litefs.server import greenlet_server_base as gsb

        a, b = socket.socketpair()
        a.setblocking(False)
        return gsb.SocketIO(None, a), b, a

    def test_fileno_and_flags(self):
        """测试 fileno 与 readable/writable 标志"""
        io, _b, a = self._make_pair()
        try:
            assert io.fileno() == a.fileno()
            assert io.readable() is True
            assert io.writable() is True
        finally:
            io.close()

    @requires_epoll
    def test_readinto_switch_and_recv(self):
        """测试 readinto 注册 EPOLLIN 后挂起、父 greenlet 恢复后收到数据"""
        io, b, _a = self._make_pair()
        buf = bytearray(64)
        result = []

        def run():
            result.append(io.readinto(buf))

        child = greenlet(run)
        child.switch()
        # readinto 应已挂起并登记当前 greenlet
        assert io.read_gr is child
        assert io.write_gr is None

        b.sendall(b"hello")
        child.switch()

        assert result == [5]
        assert bytes(buf[:5]) == b"hello"
        assert io.read_gr is None

    @requires_epoll
    def test_write_switch_and_send(self):
        """测试 write 注册 EPOLLOUT 后挂起、父 greenlet 恢复后完成发送"""
        io, b, _a = self._make_pair()
        result = []

        def run():
            result.append(io.write(b"payload"))

        child = greenlet(run)
        child.switch()
        assert io.write_gr is child

        child.switch()

        assert result == [7]
        assert b.recv(64) == b"payload"
        assert io.write_gr is None

    @requires_epoll
    def test_readinto_modify_when_write_pending(self):
        """测试 readinto 在 write_gr 已登记时走 modify 分支"""
        from litefs.server import greenlet_server_base as gsb

        io, b, a = self._make_pair()
        buf = bytearray(64)

        def run():
            io.write_gr = getcurrent()
            io.readinto(buf)

        # 预注册 fd，使 readinto 的 modify 分支可执行
        gsb.epoll._epoll.register(a.fileno(), EPOLLOUT | EPOLLET)
        try:
            child = greenlet(run)
            child.switch()
            b.sendall(b"ok")
            child.switch()

            assert bytes(buf[:2]) == b"ok"
            assert io.read_gr is None
            assert io.write_gr == child  # write_gr 并未被 readinto 清理
        finally:
            try:
                gsb.epoll._epoll.unregister(a.fileno())
            except OSError:
                pass
            io.close()
            b.close()

    @requires_epoll
    def test_write_modify_when_read_pending(self):
        """测试 write 在 read_gr 已登记时走 modify 分支"""
        from litefs.server import greenlet_server_base as gsb

        io, b, a = self._make_pair()
        result = []

        def run():
            io.read_gr = getcurrent()
            result.append(io.write(b"xy"))

        # 预注册 fd，使 write 的 modify 分支可执行
        gsb.epoll._epoll.register(a.fileno(), EPOLLIN | EPOLLET)
        try:
            child = greenlet(run)
            child.switch()
            child.switch()

            assert result == [2]
            assert b.recv(64) == b"xy"
            assert io.read_gr == child  # read_gr 并未被 write 清理
        finally:
            try:
                gsb.epoll._epoll.unregister(a.fileno())
            except OSError:
                pass
            io.close()
            b.close()

    @requires_epoll
    def test_readinto_socket_error_non_retryable(self):
        """测试 readinto 遇到非可重试 errno 时向上抛出"""
        from litefs.server import greenlet_server_base as gsb

        a, b = socket.socketpair()
        a.setblocking(False)
        # Mock 传输层但使用真实 fd，保证 epoll 注册合法
        sock = Mock()
        sock.fileno.return_value = a.fileno()
        sock.recv.side_effect = socket.error(errno.ECONNRESET, "reset")
        io = gsb.SocketIO(None, sock)

        child = greenlet(lambda: io.readinto(bytearray(16)))
        try:
            with pytest.raises(socket.error):
                child.switch()
                child.switch()
        finally:
            io.close()
            a.close()
            b.close()

    def test_close(self):
        """测试 close 关闭底层连接且幂等"""
        io, _b, a = self._make_pair()
        io.close()
        assert io.closed is True
        assert a.fileno() == -1
        io.close()  # 幂等，不抛异常

    def test_close_enotconn_swallowed(self):
        """测试 shutdown 报 ENOTCONN 时被吞掉且仍执行 close"""
        from litefs.server import greenlet_server_base as gsb

        sock = Mock()
        sock.fileno.return_value = 1
        sock.shutdown.side_effect = socket.error(errno.ENOTCONN, "not connected")
        io = gsb.SocketIO(None, sock)

        io.close()

        assert io.closed is True
        sock.close.assert_called_once()

    def test_close_other_errno_raised(self):
        """测试 shutdown 报其他 errno 时向上抛出"""
        from litefs.server import greenlet_server_base as gsb

        sock = Mock()
        sock.fileno.return_value = 1
        sock.shutdown.side_effect = socket.error(errno.EACCES, "denied")
        io = gsb.SocketIO(None, sock)

        with pytest.raises(socket.error):
            io.close()

    def test_close_with_close_failure_swallowed(self):
        """测试底层 close 抛异常时被吞掉"""
        from litefs.server import greenlet_server_base as gsb

        sock = Mock()
        sock.fileno.return_value = 1
        sock.shutdown.side_effect = socket.error(errno.ENOTCONN, "not connected")
        sock.close.side_effect = RuntimeError("boom")
        io = gsb.SocketIO(None, sock)

        io.close()
        assert io.closed is True


@requires_epoll
class TestEpoll:
    """Epoll 事件循环分发测试（_epoll 以 Mock 注入事件）"""

    def _make_epoll(self):
        from litefs.server import greenlet_server_base as gsb

        ep = gsb.Epoll()
        ep._epoll = Mock()
        return ep

    def test_register_unregister(self):
        """测试注册与注销服务器 socket"""
        ep = self._make_epoll()
        sock = socket.socket()
        try:
            sock.bind(("127.0.0.1", 0))
            fileno = sock.fileno()

            ep.register(sock)
            assert ep._servers[fileno] is sock

            ep.unregister(sock)
            assert fileno not in ep._servers
            ep.unregister(sock)  # 重复注销为无操作
        finally:
            sock.close()

    def test_close(self):
        """测试 close 注销全部服务器 socket 并关闭 epoll"""
        ep = self._make_epoll()
        server = Mock()
        server.fileno.return_value = 42
        ep._servers[42] = server

        ep.close()

        server.server_close.assert_called_once()
        ep._epoll.close.assert_called_once()

    def test_poll_dispatch_server_event(self):
        """测试 poll 分发服务器事件到 handle_request"""
        ep = self._make_epoll()
        server = Mock()
        server.fileno.return_value = 10
        ep._servers[10] = server
        ep._epoll.poll.side_effect = [[(10, EPOLLIN)], KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        server.handle_request.assert_called_once()

    def test_poll_server_emfile_raises(self):
        """测试 handle_request 报 EMFILE 时向上抛出"""
        from errno import EMFILE

        ep = self._make_epoll()
        server = Mock()
        server.fileno.return_value = 10
        server.handle_request.side_effect = socket.error(EMFILE, "too many")
        ep._servers[10] = server
        ep._epoll.poll.side_effect = [[(10, EPOLLIN)], KeyboardInterrupt]

        with pytest.raises(socket.error):
            ep.poll(0.01)

    def test_poll_server_generic_error_continues(self):
        """测试 handle_request 报普通异常时打印并继续循环"""
        ep = self._make_epoll()
        server = Mock()
        server.fileno.return_value = 10
        server.handle_request.side_effect = RuntimeError("boom")
        ep._servers[10] = server
        ep._epoll.poll.side_effect = [
            [(10, EPOLLIN)],
            [(10, EPOLLIN)],
            KeyboardInterrupt,
        ]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        assert server.handle_request.call_count == 2

    def test_poll_dispatch_greenlet_ready(self):
        """测试 poll 就绪事件切换回连接 greenlet"""
        ep = self._make_epoll()
        gr = Mock()
        ep._greenlets[20] = gr
        ep._epoll.poll.side_effect = [[(20, EPOLLIN | EPOLLOUT)], KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        gr.switch.assert_called_once()
        assert 20 in ep._greenlets

    def test_poll_greenlet_switch_error_cleanup(self):
        """测试连接 greenlet 切换出错时清理并 throw"""
        ep = self._make_epoll()
        gr = Mock()
        gr.switch.side_effect = RuntimeError("dead")
        ep._greenlets[20] = gr
        ep._epoll.poll.side_effect = [[(20, EPOLLIN)], KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        assert 20 not in ep._greenlets
        gr.throw.assert_called()

    def test_poll_greenlet_hup_throws(self):
        """测试 HUP/ERR 事件向 greenlet throw 并清理"""
        ep = self._make_epoll()
        gr = Mock()
        ep._greenlets[30] = gr
        ep._epoll.poll.side_effect = [[(30, EPOLLHUP | EPOLLERR)], KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        assert 30 not in ep._greenlets
        gr.throw.assert_called()

    def test_poll_idle_due_switch(self):
        """测试到期 idle greenlet 被切换"""
        ep = self._make_epoll()
        gr = Mock()
        ep._idles.append((time.time() - 1, gr))
        ep._epoll.poll.side_effect = [[], KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        gr.switch.assert_called_once()
        assert len(ep._idles) == 0

    def test_poll_idle_future_rescheduled(self):
        """测试未到期 idle greenlet 重新入队等待"""
        ep = self._make_epoll()
        gr = Mock()
        ep._idles.append((time.time() + 10, gr))
        ep._epoll.poll.side_effect = [[], KeyboardInterrupt]

        with pytest.raises(KeyboardInterrupt):
            ep.poll(0.01)

        gr.switch.assert_not_called()
        assert len(ep._idles) == 1


@requires_greenlet
class TestTCPServer:
    """TCPServer 生命周期与请求分发测试"""

    def test_lifecycle_and_fileno(self):
        """测试绑定、激活、fileno 与关闭"""
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        try:
            assert srv.fileno() == srv.socket.fileno()
            assert srv._started is False
        finally:
            srv.server_close()

    def test_init_bind_failure_closes_socket(self):
        """测试绑定失败时关闭 socket 并向上抛出"""
        from litefs.server import greenlet_server_base as gsb

        with patch(
            "socket.socket.bind", side_effect=OSError(errno.EADDRINUSE, "in use")
        ):
            with pytest.raises(OSError):
                gsb.TCPServer(("127.0.0.1", 0), Mock)

    def test_handle_request_no_pending(self):
        """测试无待处理连接时静默返回（EAGAIN）"""
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        try:
            srv.socket.setblocking(0)
            srv._handle_request_noblock()  # 不应抛出
        finally:
            srv.server_close()

    def _make_dispatch_server(self, **overrides):
        """构造可注入 process_request/shutdown_request 的服务器"""
        from litefs.server import greenlet_server_base as gsb

        class DispatchServer(gsb.TCPServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.process_request = Mock(**overrides.get("process", {}))
                self.shutdown_request = Mock()
                self.verify = Mock(return_value=True)

            def verify_request(self, request, client_address):
                return self.verify(request, client_address)

        return DispatchServer

    def test_handle_request_dispatches_process(self):
        """测试有待处理连接时进入 process_request"""
        server_cls = self._make_dispatch_server()
        srv = server_cls(("127.0.0.1", 0), Mock)
        try:
            srv.socket.setblocking(0)
            cli = socket.socket()
            cli.connect(srv.socket.getsockname())
            try:
                srv._handle_request_noblock()
            finally:
                cli.close()

            assert srv.process_request.call_count == 1
            srv.shutdown_request.assert_not_called()
        finally:
            srv.server_close()

    def test_handle_request_verify_rejects(self):
        """测试 verify_request 拒绝时直接关闭请求"""
        server_cls = self._make_dispatch_server()
        srv = server_cls(("127.0.0.1", 0), Mock)
        try:
            srv.socket.setblocking(0)
            cli = socket.socket()
            cli.connect(srv.socket.getsockname())
            try:
                srv.verify.return_value = False
                srv._handle_request_noblock()
            finally:
                cli.close()

            srv.process_request.assert_not_called()
            assert srv.shutdown_request.call_count == 1
        finally:
            srv.server_close()

    def test_handle_request_process_error(self):
        """测试 process_request 抛异常时记录错误并关闭请求"""
        server_cls = self._make_dispatch_server()
        srv = server_cls(("127.0.0.1", 0), Mock)
        try:
            srv.socket.setblocking(0)
            srv.process_request.side_effect = RuntimeError("boom")
            cli = socket.socket()
            cli.connect(srv.socket.getsockname())
            try:
                srv._handle_request_noblock()
            finally:
                cli.close()

            srv.shutdown_request.assert_called_once()
        finally:
            srv.server_close()

    def test_process_request_base_error_path(self):
        """测试基类 process_request 捕获 finish_request 异常"""
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        try:
            srv.finish_request = Mock(side_effect=RuntimeError("boom"))
            srv.handle_error = Mock()
            srv.shutdown_request = Mock()

            srv.process_request(Mock(), ("127.0.0.1", 1))

            srv.handle_error.assert_called_once()
            srv.shutdown_request.assert_called_once()
        finally:
            srv.server_close()

    def test_handle_error_and_close_request(self):
        """测试 handle_error 与 close_request 基础行为"""
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        try:
            request = Mock()
            srv.handle_error(request, ("127.0.0.1", 1))  # 仅打印，不抛出
            srv.close_request(request)
            request.close.assert_called_once()
            srv.handle_timeout()  # 空实现
        finally:
            srv.server_close()

    def test_start_shutdown(self):
        """测试 start/shutdown 切换注册状态（epoll Mock 注入）"""
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        try:
            with patch.object(gsb.epoll, "register") as m_reg, patch.object(
                gsb.epoll, "unregister"
            ) as m_unreg:
                srv.start()
                assert srv._started is True
                m_reg.assert_called_once_with(srv)

                srv.shutdown()
                assert srv._started is False
                m_unreg.assert_called_once_with(srv)
        finally:
            srv.server_close()

    def test_shutdown_not_started_noop(self):
        """测试未启动时 shutdown 为无操作"""
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        try:
            with patch.object(gsb.epoll, "unregister") as m_unreg:
                srv.shutdown()
                m_unreg.assert_not_called()
        finally:
            srv.server_close()


@requires_epoll
class TestFinishRequestIntegration:
    """finish_request → _finish_request → greenlet 切换链路集成测试"""

    def _setup(self):
        from litefs.server import greenlet_server_base as gsb

        srv = gsb.TCPServer(("127.0.0.1", 0), Mock)
        # make_environ 依赖 server_name/server_port（HTTPServer 子类负责赋值）
        srv.server_name = "localhost"
        srv.server_port = "8000"
        cli = socket.socket()
        cli.settimeout(3)
        cli.connect(srv.socket.getsockname())
        return gsb, srv, cli

    def _run_child(self, gsb, srv, cli, handler):
        """驱动 finish_request 子 greenlet 完成整个请求处理"""
        srv.RequestHandlerClass = handler
        cli.sendall(b"GET /idx HTTP/1.1\r\nHost: t\r\n\r\n")
        request, addr = srv.socket.accept()
        fileno = request.fileno()

        # 第一次 switch：子 greenlet 阻塞在 readinto
        srv.finish_request(request, addr)
        assert fileno in gsb.epoll._greenlets

        # 后续 switch：驱动解析、处理与响应发送，直至 greenlet 退出
        for _ in range(4):
            if fileno not in gsb.epoll._greenlets:
                break
            gsb.epoll._greenlets[fileno].switch()

        return request, fileno

    def test_full_request_response(self):
        """测试完整请求-响应链路：解析 → 处理 → 响应 → 清理"""
        gsb, srv, cli = self._setup()
        try:
            def handler(request, rw, environ, server):
                rw.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nhi")
                rw.flush()

            request, fileno = self._run_child(gsb, srv, cli, handler)

            response = cli.recv(4096)
            assert b"HTTP/1.1 200 OK" in response
            assert response.endswith(b"hi")
            assert fileno not in gsb.epoll._greenlets
        finally:
            cli.close()
            srv.server_close()

    def test_http_error_response(self):
        """测试处理器抛出 HttpError 时的错误响应链路"""
        from litefs.exceptions import HttpError

        gsb, srv, cli = self._setup()
        try:
            def handler(request, rw, environ, server):
                raise HttpError(404, "Not Found")

            request, fileno = self._run_child(gsb, srv, cli, handler)

            response = cli.recv(4096)
            assert b"404" in response
            assert b"Not Found" in response
            assert fileno not in gsb.epoll._greenlets
        finally:
            cli.close()
            srv.server_close()

    def test_epipe_handler_exits_greenlet(self):
        """测试处理器抛 EPIPE 时 greenlet 以 GreenletExit 退出并清理"""
        gsb, srv, cli = self._setup()
        try:
            def handler(request, rw, environ, server):
                raise socket.error(errno.EPIPE, "broken pipe")

            request, fileno = self._run_child(gsb, srv, cli, handler)

            assert fileno not in gsb.epoll._greenlets
        finally:
            cli.close()
            srv.server_close()

    def test_invalid_request_line(self):
        """测试非法请求行使 greenlet 退出并关闭连接"""
        gsb, srv, cli = self._setup()
        try:
            request, fileno = self._run_child_with_raw(
                gsb, srv, cli, b"\r\nHost: t\r\n\r\n"
            )

            # make_environ 解析空请求行抛 ValueError，greenlet 终止并关闭连接
            assert fileno not in gsb.epoll._greenlets
            assert cli.recv(4096) == b""
        finally:
            cli.close()
            srv.server_close()

    def _run_child_with_raw(self, gsb, srv, cli, raw):
        """以原始报文驱动子 greenlet（用于非法请求场景）"""
        cli.sendall(raw)
        request, addr = srv.socket.accept()
        fileno = request.fileno()

        srv.finish_request(request, addr)
        for _ in range(4):
            if fileno not in gsb.epoll._greenlets:
                break
            gsb.epoll._greenlets[fileno].switch()

        return request, fileno


@requires_greenlet
class TestMakeEnvironBranches:
    """make_environ 边界分支测试"""

    def _server(self, **attrs):
        server = Mock()
        server.server_name = "localhost"
        server.server_port = "8000"
        for k, v in attrs.items():
            setattr(server, k, v)
        if "max_request_size" not in attrs:
            del server.max_request_size
        return server

    def test_empty_request_line_raises(self):
        """测试空请求行抛出 HttpError"""
        from litefs.server.greenlet import make_environ
        from litefs.exceptions import HttpError

        server = self._server()
        rw = BytesIO(b"")
        with pytest.raises(HttpError):
            make_environ(server, rw, ("127.0.0.1", 1))

    def test_content_length_exceeds_limit(self):
        """测试请求体超过 max_request_size 抛出 413"""
        from litefs.server.greenlet import make_environ
        from litefs.exceptions import HttpError

        server = self._server(max_request_size=10)
        data = b"POST / HTTP/1.1\r\nContent-Length: 100\r\n\r\n"
        with pytest.raises(HttpError) as exc_info:
            make_environ(server, BytesIO(data), ("127.0.0.1", 1))
        assert exc_info.value.status_code == 413

    def test_content_type_default_and_charset(self):
        """测试默认 Content-Type 与 charset 解析"""
        from litefs.server.greenlet import make_environ

        server = self._server()
        data = b"GET / HTTP/1.1\r\n\r\n"
        environ = make_environ(server, BytesIO(data), ("127.0.0.1", 1))

        assert environ["CONTENT_TYPE"] == "text/plain; charset=utf-8"
        assert environ["CHARSET"] == "utf-8"

    def test_no_charset_param(self):
        """测试 Content-Type 无 charset 时 CHARSET 为 None"""
        from litefs.server.greenlet import make_environ

        server = self._server()
        data = b"GET / HTTP/1.1\r\nContent-Type: application/json\r\n\r\n"
        environ = make_environ(server, BytesIO(data), ("127.0.0.1", 1))

        assert environ["CONTENT_TYPE"] == "application/json"
        assert environ["CHARSET"] is None

    def test_root_path_script_name(self):
        """测试根路径请求 SCRIPT_NAME 回退为 index.html"""
        from litefs.server.greenlet import make_environ

        server = self._server()
        data = b"GET / HTTP/1.1\r\n\r\n"
        environ = make_environ(server, BytesIO(data), ("127.0.0.1", 1))

        assert environ["SCRIPT_NAME"] == "index.html"
        assert environ["REQUEST_METHOD"] == "GET"

    def test_query_string_decoded(self):
        """测试查询串解码"""
        from litefs.server.greenlet import make_environ

        server = self._server()
        data = b"GET /s?q=%E4%B8%AD%E6%96%87 HTTP/1.1\r\n\r\n"
        environ = make_environ(server, BytesIO(data), ("127.0.0.1", 1))

        assert environ["QUERY_STRING"] == "q=中文"


@requires_greenlet
class TestMainloop:
    """mainloop 与模块级辅助测试"""

    def test_mainloop_calls_poll(self):
        """测试 mainloop 委托 epoll.poll"""
        from litefs.server import greenlet_server_base as gsb

        with patch.object(gsb.epoll, "poll") as m_poll:
            gsb.mainloop(0.02)
            m_poll.assert_called_once_with(poll_interval=0.02)

    def test_mainloop_swallows_keyboard_interrupt(self):
        """测试 mainloop 吞掉 KeyboardInterrupt"""
        from litefs.server import greenlet_server_base as gsb

        with patch.object(gsb.epoll, "poll", side_effect=KeyboardInterrupt):
            gsb.mainloop(0.02)  # 不应抛出

    def test_server_forever_alias(self):
        """测试模块级 server_forever 为 mainloop 别名"""
        from litefs.server import greenlet_server_base as gsb

        assert gsb.server_forever is gsb.mainloop
