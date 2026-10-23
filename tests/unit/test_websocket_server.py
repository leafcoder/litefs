#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WebSocket 连接与服务器测试

覆盖 :mod:`litefs.websocket.connection` 的 ``WebSocketConnection``、
:mod:`litefs.websocket.server` 的 ``WebSocketServer`` 与 ``WebSocket``。
连接收发基于真实 socketpair / 回环端口，不依赖外部服务。
"""

import json
import socket
import struct
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from litefs.websocket.protocol import (
    Frame,
    Opcode,
    CloseCode,
    FrameTooLargeError,
    compute_accept_key,
    parse_close_payload,
)
from litefs.websocket.connection import (
    WebSocketConnection,
    ConnectionManager,
)
from litefs.websocket.server import WebSocketServer, WebSocket


def _make_pair_conn(**kwargs):
    """创建 socketpair 并返回 (连接对象[读 a 端], 对端 b, a)"""
    a, b = socket.socketpair()
    defaults = dict(
        socket=a,
        address=("127.0.0.1", 12345),
        path="/ws",
        query_string="",
        headers={},
    )
    defaults.update(kwargs)
    conn = WebSocketConnection(**defaults)
    return conn, b, a


class TestWebSocketConnectionProperties:
    """连接属性测试"""

    def test_init_defaults(self):
        """测试初始化默认状态"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.path == "/ws"
            assert conn.headers == {}
            assert conn.is_closed is False
            assert conn.user is None
            assert conn.rooms == set()
            assert "<WebSocketConnection" in repr(conn)
        finally:
            a.close()
            b.close()

    def test_query_params_lazy_parse(self):
        """测试查询参数惰性解析"""
        conn, b, a = _make_pair_conn(query_string="room=lobby&lang=zh")
        try:
            params = conn.query_params
            assert params["room"] == ["lobby"]
            assert params["lang"] == ["zh"]
            assert conn.query_params is params  # 缓存
        finally:
            a.close()
            b.close()

    def test_user_setter(self):
        """测试 user 属性读写"""
        conn, b, a = _make_pair_conn()
        try:
            user = Mock()
            conn.user = user
            assert conn.user is user
        finally:
            a.close()
            b.close()


class TestWebSocketConnectionSend:
    """消息发送测试"""

    def test_send_dict_json(self):
        """测试发送 dict 自动 JSON 序列化为 TEXT 帧"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.send({"ok": True}) is True
            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.TEXT
            assert json.loads(frame.payload) == {"ok": True}
        finally:
            a.close()
            b.close()

    def test_send_str(self):
        """测试发送 str 走 TEXT 帧"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.send("hello") is True
            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.TEXT
            assert frame.payload == b"hello"
        finally:
            a.close()
            b.close()

    def test_send_bytes_binary(self):
        """测试发送 bytes 走 BINARY 帧"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.send(b"\x01\x02") is True
            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.BINARY
            assert frame.payload == b"\x01\x02"
        finally:
            a.close()
            b.close()

    def test_send_other_type_as_text(self):
        """测试其他类型转为字符串发送"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.send(42) is True
            frame, _ = Frame.parse(b.recv(4096))
            assert frame.payload == b"42"
        finally:
            a.close()
            b.close()

    def test_send_on_closed(self):
        """测试已关闭连接发送返回 False"""
        conn, b, a = _make_pair_conn()
        try:
            conn._closed = True
            assert conn.send("x") is False
        finally:
            a.close()
            b.close()

    def test_send_failure_marks_closed(self):
        """测试发送失败时标记连接关闭"""
        conn, b, a = _make_pair_conn()
        try:
            a.close()  # 底层已关闭，sendall 抛异常
            assert conn.send("x") is False
            assert conn.is_closed is True
        finally:
            b.close()

    def test_send_bytes(self):
        """测试 send_bytes 走 BINARY 帧"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.send_bytes(b"data") is True
            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.BINARY
            assert frame.payload == b"data"
        finally:
            a.close()
            b.close()

    def test_send_bytes_on_closed(self):
        """测试已关闭连接 send_bytes 返回 False"""
        conn, b, a = _make_pair_conn()
        try:
            conn._closed = True
            assert conn.send_bytes(b"x") is False
        finally:
            a.close()
            b.close()

    def test_ping(self):
        """测试发送 Ping 帧并更新时间戳"""
        conn, b, a = _make_pair_conn()
        try:
            last = conn._last_ping
            time.sleep(0.001)
            assert conn.ping() is True
            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.PING
            assert conn._last_ping > last
        finally:
            a.close()
            b.close()

    def test_ping_on_closed(self):
        """测试已关闭连接 ping 返回 False"""
        conn, b, a = _make_pair_conn()
        try:
            conn._closed = True
            assert conn.ping() is False
        finally:
            a.close()
            b.close()


class TestWebSocketConnectionClose:
    """连接关闭测试"""

    def test_close_sends_frame_and_notifies_manager(self):
        """测试关闭发送 CLOSE 帧并从管理器移除"""
        conn, b, a = _make_pair_conn()
        manager = ConnectionManager()
        manager.add(conn)
        try:
            assert conn.close(code=CloseCode.NORMAL, reason="bye") is True
            assert conn.is_closed is True
            assert manager.connection_count == 0

            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.CLOSE
        finally:
            a.close()
            b.close()

    def test_close_idempotent(self):
        """测试重复关闭返回 False"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.close() is True
            assert conn.close() is False
        finally:
            a.close()
            b.close()

    def test_close_failure_marks_closed(self):
        """测试关闭失败时仍标记关闭"""
        conn, b, a = _make_pair_conn()
        try:
            a.close()
            assert conn.close() is False
            assert conn.is_closed is True
        finally:
            b.close()


class TestWebSocketConnectionRooms:
    """房间管理测试"""

    def test_join_leave_with_manager(self):
        """测试加入/离开房间同步到管理器"""
        conn, b, a = _make_pair_conn()
        manager = ConnectionManager()
        manager.add(conn)
        try:
            conn.join("room1")
            assert conn.rooms == {"room1"}
            assert manager.get_room_connections("room1") == {conn}

            conn.leave("room1")
            assert conn.rooms == set()
            assert manager.room_count == 0
        finally:
            a.close()
            b.close()

    def test_join_leave_without_manager(self):
        """测试无管理器时仅维护本地状态"""
        conn, b, a = _make_pair_conn()
        try:
            conn.join("room1")
            conn.join("room1")  # 重复加入
            assert conn.rooms == {"room1"}
            conn.leave("room1")
            conn.leave("not-joined")  # 离开未加入的房间
            assert conn.rooms == set()
        finally:
            a.close()
            b.close()

    def test_broadcast_and_to_room(self):
        """测试连接级广播与房间广播委托"""
        conn, b, a = _make_pair_conn()
        manager = ConnectionManager()
        manager.add(conn)
        conn.join("room1")
        try:
            manager.broadcast = Mock()
            conn.broadcast("msg", exclude_self=False)
            manager.broadcast.assert_called_once_with("msg", exclude=None)

            manager.broadcast_to_room = Mock()
            conn.to_room("room1", "msg")
            manager.broadcast_to_room.assert_called_once_with(
                "room1", "msg", exclude=[conn]
            )
        finally:
            a.close()
            b.close()

    def test_broadcast_without_manager_noop(self):
        """测试无管理器时广播为无操作"""
        conn, b, a = _make_pair_conn()
        try:
            conn.broadcast("msg")  # 不抛异常
            conn.to_room("room1", "msg")
        finally:
            a.close()
            b.close()


class TestWebSocketConnectionReceive:
    """消息接收测试"""

    def test_receive_text_json(self):
        """测试接收 TEXT 帧自动 JSON 解析"""
        conn, b, a = _make_pair_conn()
        try:
            b.sendall(Frame(opcode=Opcode.TEXT, payload=b'{"a":1}').build())
            assert conn.receive() == {"a": 1}
        finally:
            a.close()
            b.close()

    def test_receive_text_non_json(self):
        """测试接收非 JSON 文本时返回原始字符串"""
        conn, b, a = _make_pair_conn()
        try:
            b.sendall(Frame(opcode=Opcode.TEXT, payload=b"plain text").build())
            assert conn.receive() == "plain text"
        finally:
            a.close()
            b.close()

    def test_receive_binary(self):
        """测试接收 BINARY 帧返回原始字节"""
        conn, b, a = _make_pair_conn()
        try:
            b.sendall(Frame(opcode=Opcode.BINARY, payload=b"\x01\x02").build())
            assert conn.receive() == b"\x01\x02"
        finally:
            a.close()
            b.close()

    def test_receive_ping_replies_pong(self):
        """测试收到 Ping 帧回复 Pong 后继续等待消息"""
        conn, b, a = _make_pair_conn()
        try:
            b.sendall(Frame(opcode=Opcode.PING, payload=b"hb").build())
            b.sendall(Frame(opcode=Opcode.TEXT, payload=b"after").build())

            assert conn.receive() == "after"

            frame, _ = Frame.parse(b.recv(4096))
            assert frame.opcode == Opcode.PONG
            assert frame.payload == b"hb"
        finally:
            a.close()
            b.close()

    def test_receive_close_frame(self):
        """测试收到 CLOSE 帧后关闭连接并返回 None"""
        conn, b, a = _make_pair_conn()
        try:
            b.sendall(Frame(opcode=Opcode.CLOSE, payload=b"\x03\xe8").build())
            assert conn.receive() is None
            assert conn.is_closed is True
        finally:
            a.close()
            b.close()

    def test_receive_on_closed(self):
        """测试已关闭连接接收返回 None"""
        conn, b, a = _make_pair_conn()
        try:
            conn._closed = True
            assert conn.receive() is None
        finally:
            a.close()
            b.close()

    def test_receive_peer_closed(self):
        """测试对端关闭时接收返回 None 并标记关闭"""
        conn, b, a = _make_pair_conn()
        try:
            b.close()
            assert conn.receive() is None
            assert conn.is_closed is True
        finally:
            a.close()

    def test_receive_partial_frame_buffering(self):
        """测试分片到达的帧被缓冲后完整解析"""
        conn, b, a = _make_pair_conn()
        try:
            data = Frame(opcode=Opcode.TEXT, payload=b"chunked").build()
            b.sendall(data[:3])
            time.sleep(0.05)
            b.sendall(data[3:])

            assert conn.receive() == "chunked"
        finally:
            a.close()
            b.close()

    def test_iterator_yields_until_closed(self):
        """测试消息迭代器持续产出直至连接关闭"""
        conn, b, a = _make_pair_conn()
        try:
            b.sendall(Frame(opcode=Opcode.TEXT, payload=b'"m1"').build())
            b.sendall(Frame(opcode=Opcode.TEXT, payload=b'"m2"').build())
            b.close()  # 之后 receive 返回 None，迭代结束

            assert list(conn) == ["m1", "m2"]
        finally:
            a.close()


class TestConnectionManagerAdvanced:
    """连接管理器补充测试"""

    def test_get_room_connections_unknown_room(self):
        """测试获取未知房间返回空集合"""
        manager = ConnectionManager()
        assert manager.get_room_connections("nope") == set()

    def test_broadcast_to_unknown_room_noop(self):
        """测试向未知房间广播为无操作"""
        manager = ConnectionManager()
        manager.broadcast_to_room("nope", "msg")  # 不抛异常

    def test_broadcast_with_exclude(self):
        """测试广播时排除指定连接"""
        messages = []

        class FakeConn:
            def __init__(self, id):
                self.id = id
                self._rooms = set()
                self._manager = None

            def send(self, data):
                messages.append(self.id)

        c1, c2, c3 = FakeConn(1), FakeConn(2), FakeConn(3)
        manager = ConnectionManager()
        for c in (c1, c2, c3):
            manager.add(c)

        manager.broadcast("msg", exclude=[c2])

        assert sorted(messages) == [1, 3]

    def test_remove_cleans_rooms(self):
        """测试移除连接时清理其所在房间"""
        manager = ConnectionManager()
        conn = Mock()
        conn._rooms = {"r1", "r2"}
        manager.add(conn)

        manager.remove(conn)

        assert manager.room_count == 0
        assert manager.connection_count == 0

    def test_get_all_connections_copy(self):
        """测试获取连接集合为副本"""
        manager = ConnectionManager()
        conn = Mock()
        conn._rooms = set()
        manager.add(conn)

        conns = manager.get_all_connections()
        assert conn in conns
        conns.clear()
        assert manager.connection_count == 1


def _handshake_bytes(path="/ws", key="dGhlIHNhbXBsZSBub25jZQ=="):
    """构建 WebSocket 握手请求报文"""
    return (
        f"GET {path} HTTP/1.1\r\n"
        "Host: localhost\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode("utf-8")


@pytest.fixture
def running_server():
    """启动一个绑定随机端口的 WebSocket 服务器并自动清理"""
    srv = WebSocketServer(host="127.0.0.1", port=0)
    srv.start(blocking=False)
    yield srv
    srv.stop()
    if srv._thread is not None:
        srv._thread.join(timeout=3)


class TestWebSocketServerIntegration:
    """WebSocketServer 真实回环集成测试"""

    def test_full_handshake_and_echo(self, running_server):
        """测试握手、服务器主动推送与客户端回复的完整链路"""
        srv = running_server

        @srv.handler()
        def echo(conn):
            conn.send({"ok": True})
            return conn.receive(timeout=5)

        port = srv._server_socket.getsockname()[1]
        cli = socket.create_connection(("127.0.0.1", port), timeout=5)
        try:
            cli.sendall(_handshake_bytes())

            # 读取握手响应
            response = b""
            while b"\r\n\r\n" not in response:
                chunk = cli.recv(1024)
                if not chunk:
                    break
                response += chunk
            assert b"101 Switching Protocols" in response
            expected_accept = compute_accept_key("dGhlIHNhbXBsZSBub25jZQ==")
            assert expected_accept.encode() in response

            # 接收服务器主动推送（帧字节可能与握手响应同包到达）
            buf = response.split(b"\r\n\r\n", 1)[1]
            while True:
                frame, _consumed = Frame.parse(buf)
                if frame:
                    break
                chunk = cli.recv(4096)
                if not chunk:
                    break  # 对端关闭，避免空缓冲区忙循环
                buf += chunk
            assert frame is not None
            assert json.loads(frame.payload) == {"ok": True}

            # 回复一条消息供 handler.receive 消费
            reply = Frame(opcode=Opcode.TEXT, payload=b'"done"').build(mask=True)
            cli.sendall(reply)

            # handler 结束后连接被服务端关闭
            cli.settimeout(5)
            assert cli.recv(1024) == b""
        finally:
            cli.close()

        assert srv._manager.connection_count == 0

    def test_bad_handshake_gets_400(self, running_server):
        """测试缺少握手头的请求返回 400"""
        port = running_server._server_socket.getsockname()[1]
        cli = socket.create_connection(("127.0.0.1", port), timeout=3)
        try:
            cli.sendall(b"GET /ws HTTP/1.1\r\nHost: x\r\n\r\n")

            response = b""
            while b"\r\n\r\n" not in response:
                chunk = cli.recv(1024)
                if not chunk:
                    break
                response += chunk

            assert b"400 Bad Request" in response
        finally:
            cli.close()

    def test_non_get_request_closed(self, running_server):
        """测试非 GET 请求被直接关闭"""
        port = running_server._server_socket.getsockname()[1]
        cli = socket.create_connection(("127.0.0.1", port), timeout=3)
        try:
            cli.sendall(b"POST /ws HTTP/1.1\r\nHost: x\r\n\r\n")
            cli.settimeout(3)
            assert cli.recv(1024) == b""
        finally:
            cli.close()

    def test_immediate_disconnect(self, running_server):
        """测试客户端连接后立即断开不引发异常"""
        port = running_server._server_socket.getsockname()[1]
        cli = socket.create_connection(("127.0.0.1", port), timeout=3)
        cli.close()
        time.sleep(0.2)  # 等待服务端线程处理

    def test_auth_rejected(self):
        """测试认证失败的连接被拒绝"""
        srv = WebSocketServer(
            host="127.0.0.1",
            port=0,
            auth_required=True,
            auth_handler=lambda conn: False,
        )
        srv.start(blocking=False)
        try:
            port = srv._server_socket.getsockname()[1]
            cli = socket.create_connection(("127.0.0.1", port), timeout=3)
            try:
                cli.sendall(_handshake_bytes())

                response = b""
                while b"\r\n\r\n" not in response:
                    chunk = cli.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                assert b"101" in response

                # 随后收到 CLOSE 帧（UNAUTHORIZED）
                # 帧字节可能与握手响应同包到达，需并入缓冲
                buf = response.split(b"\r\n\r\n", 1)[1]
                frame = None
                while frame is None:
                    frame, _consumed = Frame.parse(buf)
                    if frame:
                        break
                    chunk = cli.recv(4096)
                    if not chunk:
                        break  # 对端关闭，避免空缓冲区忙循环
                    buf += chunk
                assert frame is not None
                assert frame.opcode == Opcode.CLOSE

                cli.settimeout(3)
                assert cli.recv(1024) == b""
            finally:
                cli.close()
        finally:
            srv.stop()
            srv._thread.join(timeout=3)

    def test_auth_accepted(self):
        """测试认证通过的连接进入管理器"""
        srv = WebSocketServer(
            host="127.0.0.1",
            port=0,
            auth_required=True,
            auth_handler=lambda conn: True,
        )
        srv.start(blocking=False)
        try:

            @srv.handler()
            def hold(conn):
                time.sleep(0.2)

            port = srv._server_socket.getsockname()[1]
            cli = socket.create_connection(("127.0.0.1", port), timeout=3)
            try:
                cli.sendall(_handshake_bytes())

                response = b""
                while b"\r\n\r\n" not in response:
                    chunk = cli.recv(1024)
                    if not chunk:
                        break
                    response += chunk

                deadline = time.time() + 2
                while time.time() < deadline:
                    if srv._manager.connection_count == 1:
                        break
                    time.sleep(0.02)
                assert srv._manager.connection_count == 1

                cli.settimeout(3)
                assert cli.recv(1024) == b""  # handler 结束后关闭
            finally:
                cli.close()
        finally:
            srv.stop()
            srv._thread.join(timeout=3)


class TestWebSocketServerUnits:
    """WebSocketServer 单元级测试"""

    def test_handler_decorator_with_path(self):
        """测试装饰器显式路径注册"""
        srv = WebSocketServer()

        @srv.handler("/custom")
        def h(conn):
            pass

        assert srv._handlers["/custom"] is h

    def test_handler_decorator_default_path(self):
        """测试装饰器默认路径注册"""
        srv = WebSocketServer(path="/default")

        @srv.handler()
        def h(conn):
            pass

        assert srv._handlers["/default"] is h

    def test_broadcast_delegates(self):
        """测试广播方法委托给连接管理器"""
        srv = WebSocketServer()
        srv._manager.broadcast = Mock()
        srv._manager.broadcast_to_room = Mock()

        srv.broadcast("a")
        srv.broadcast_to_room("r", "b")

        srv._manager.broadcast.assert_called_once_with("a")
        srv._manager.broadcast_to_room.assert_called_once_with("r", "b")

    def test_stop_closes_connections_and_socket(self):
        """测试 stop 关闭所有连接与监听 socket"""
        srv = WebSocketServer()
        conn = Mock()
        srv._manager._connections.add(conn)
        fake_sock = Mock()
        srv._server_socket = fake_sock

        srv.stop()

        conn.close.assert_called_once()
        fake_sock.close.assert_called_once()
        assert srv._running is False

    def test_stop_without_socket(self):
        """测试未启动时 stop 为无操作"""
        srv = WebSocketServer()
        srv.stop()  # 不抛异常

    def test_validate_handshake_branches(self):
        """测试握手校验各失败分支"""
        srv = WebSocketServer()
        ok = {
            "upgrade": "websocket",
            "connection": "Upgrade",
            "sec-websocket-key": "k",
        }
        assert srv._validate_handshake(ok) is True
        assert srv._validate_handshake({**ok, "upgrade": "h2"}) is False
        assert srv._validate_handshake({**ok, "connection": "keep-alive"}) is False
        assert (
            srv._validate_handshake(
                {k: v for k, v in ok.items() if k != "sec-websocket-key"}
            )
            is False
        )

    def test_send_handshake_response(self):
        """测试握手响应包含正确的 Accept Key"""
        srv = WebSocketServer()
        sock = Mock()
        srv._send_handshake_response(sock, {"sec-websocket-key": "dGhlIHNhbXBsZSBub25jZQ=="})

        sent = sock.sendall.call_args[0][0]
        assert b"101 Switching Protocols" in sent
        assert b"s3pPLMBiTxaQ9kYGzzhZRbK+xOo=" in sent

    def test_send_bad_request(self):
        """测试 400 响应发送"""
        srv = WebSocketServer()
        sock = Mock()
        srv._send_bad_request(sock)
        assert b"400 Bad Request" in sock.sendall.call_args[0][0]

    def test_read_http_request_rejects_empty(self):
        """测试空请求返回 None"""
        srv = WebSocketServer()
        sock = Mock()
        sock.recv.side_effect = [b""]
        assert srv._read_http_request(sock) is None

    def test_read_http_request_recv_error(self):
        """测试接收异常返回 None"""
        srv = WebSocketServer()
        sock = Mock()
        sock.recv.side_effect = OSError("reset")
        assert srv._read_http_request(sock) is None

    def test_find_handler_exact(self):
        """测试精确路径查找"""
        srv = WebSocketServer()
        h = Mock()
        srv._handlers["/ws"] = h
        assert srv._find_handler("/ws") is h
        assert srv._find_handler("/other") is None

    def test_find_handler_pattern(self):
        """测试通配路径模式查找"""
        srv = WebSocketServer()
        h = Mock()
        srv._handlers["/room/{id}"] = h

        assert srv._find_handler("/room/42") is h
        assert srv._find_handler("/room/42/sub") is None

    def test_match_path(self):
        """测试路径匹配规则"""
        srv = WebSocketServer()
        assert srv._match_path("/a", "/a") is True
        assert srv._match_path("/a/{x}", "/a/bc") is True
        assert srv._match_path("/a/{x}", "/a/b/c") is False


class TestWebSocketIntegrationClass:
    """WebSocket 集成类测试"""

    def _free_port(self):
        """获取一个空闲端口"""
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def _make_app(self):
        """构造带 config 的假应用"""
        app = Mock()
        app.config.host = "127.0.0.1"
        app.config.port = 9000
        return app

    def test_init_with_app(self):
        """测试构造时初始化应用并注册互相引用"""
        app = self._make_app()
        ws = WebSocket(app=app, path="/ws")

        assert ws._app is app
        assert ws._ws_host == "127.0.0.1"
        assert ws._ws_port == 9001  # 默认端口 +1
        assert app._websocket is ws

    def test_init_app_with_explicit_host_port(self):
        """测试显式指定主机与端口"""
        app = self._make_app()
        ws = WebSocket()
        ws.init_app(app, host="0.0.0.0", port=7777)

        assert ws._ws_host == "0.0.0.0"
        assert ws._ws_port == 7777

    def test_handler_registration_and_start_stop(self):
        """测试 handler 注册与启停"""
        app = self._make_app()
        port = self._free_port()
        ws = WebSocket(app=app, path="/ws")

        @ws.handler("/push")
        def push(conn):
            pass

        assert ws._handlers["/push"] is push

        ws._ws_port = port
        ws.start()
        try:
            assert ws._server is not None
            assert ws._server._handlers["/push"] is push
            assert ws.manager is ws._server._manager
            assert ws.connection_count == 0

            ws.broadcast("msg")  # 无连接，不抛异常
            ws.broadcast_to_room("r", "msg")
        finally:
            ws.stop()

        assert ws._server._running is False

    def test_noop_without_server(self):
        """测试未启动时广播与属性为默认值"""
        ws = WebSocket()
        ws.broadcast("msg")  # 不抛异常
        ws.broadcast_to_room("r", "msg")
        assert ws.manager is None
        assert ws.connection_count == 0

    def test_stop_without_server(self):
        """测试未启动时 stop 为无操作"""
        ws = WebSocket()
        ws.stop()  # 不抛异常


class _EndlessByteSocket:
    """永远返回单个 0xFF 字节的伪 socket

    模拟无法组成有效帧的恶意流，用于验证接收缓冲区上限。
    """

    def __init__(self):
        self.sent = b''
        self.closed = False

    def recv(self, n):
        return b'\xff'

    def sendall(self, data):
        self.sent += data

    def close(self):
        self.closed = True


class TestWebSocketFrameLimits:
    """WebSocket 帧上限与接收缓冲区上限（超限回 1009 关闭帧并断连）"""

    @staticmethod
    def _recv_close_code(peer):
        """从对端读取数据直到 EOF，解析关闭帧状态码"""
        chunks = []
        while True:
            chunk = peer.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        frame, _ = Frame.parse(b''.join(chunks))
        assert frame is not None and frame.opcode == Opcode.CLOSE
        code, _ = parse_close_payload(frame.payload)
        return code

    def test_frame_parse_oversize_declared_length_raises(self):
        """测试声明负载超限的帧头在解析期立即拒绝"""
        data = b'\x82\xff' + struct.pack('!Q', 16 * 1024 * 1024) + b'\x00\x00\x00\x00'
        with pytest.raises(FrameTooLargeError):
            Frame.parse(data, max_payload_size=1024 * 1024)

    def test_frame_parse_within_limit_ok(self):
        """测试未超限帧正常解析"""
        data = Frame(opcode=Opcode.BINARY, payload=b'A' * 32).build()
        parsed, _ = Frame.parse(data, max_payload_size=1024)
        assert parsed is not None
        assert parsed.payload == b'A' * 32

    def test_frame_parse_unlimited_by_default(self):
        """测试默认不限制帧负载大小（向后兼容）"""
        data = Frame(opcode=Opcode.BINARY, payload=b'A' * 32).build()
        parsed, _ = Frame.parse(data)
        assert parsed is not None

    def test_connection_default_max_message_size(self):
        """测试连接默认消息上限为 1MB"""
        conn, b, a = _make_pair_conn()
        try:
            assert conn.max_message_size == 1048576
        finally:
            a.close()
            b.close()

    def test_receive_oversize_frame_closes_with_1009(self):
        """测试超限消息触发 1009 关闭帧并断连"""
        conn, b, a = _make_pair_conn(max_message_size=64)
        try:
            # 对端 b 发送超限帧，连接（a 端）接收
            b.sendall(Frame(opcode=Opcode.BINARY, payload=b'A' * 128).build())
            assert conn.receive() is None
            assert conn.is_closed is True
            assert self._recv_close_code(b) == CloseCode.MESSAGE_TOO_BIG
        finally:
            a.close()
            b.close()

    def test_receive_buffer_overflow_closes_with_1009(self):
        """测试接收缓冲区超限触发 1009 关闭帧并断连

        通过让 Frame.parse 持续返回"不完整"模拟流中始终无有效帧边界的
        恶意数据（如注入的字节流使帧头永远无法闭合），验证缓冲区上限
        的纵深防御逻辑。
        """
        fake = _EndlessByteSocket()
        conn = WebSocketConnection(
            socket=fake,
            address=("127.0.0.1", 12345),
            path="/ws",
            max_message_size=64,
        )
        with patch.object(
            Frame, 'parse',
            classmethod(lambda cls, data, max_payload_size=None: (None, 0)),
        ):
            assert conn.receive() is None

        assert conn.is_closed is True
        assert fake.closed is True
        frame, _ = Frame.parse(fake.sent)
        assert frame is not None and frame.opcode == Opcode.CLOSE
        code, _ = parse_close_payload(frame.payload)
        assert code == CloseCode.MESSAGE_TOO_BIG

    def test_server_read_http_request_rejects_oversized_header(self):
        """测试握手请求头超限时直接拒绝"""
        server = WebSocketServer(max_message_size=64)
        a, b = socket.socketpair()
        try:
            a.sendall(b'GET /ws HTTP/1.1\r\nX-Junk: ' + b'A' * 4096 + b'\r\n\r\n')
            assert server._read_http_request(b) is None
        finally:
            a.close()
            b.close()

    def test_init_app_reads_config_max_message_size(self):
        """测试 init_app 从应用配置读取消息上限"""
        app = SimpleNamespace(
            config=SimpleNamespace(
                host="127.0.0.1",
                port=9000,
                websocket_max_message_size=4096,
            )
        )
        ws = WebSocket()
        ws.init_app(app)
        assert ws._max_message_size == 4096

        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        ws._ws_port = port
        ws.start()
        try:
            assert ws._server.max_message_size == 4096
        finally:
            ws.stop()
