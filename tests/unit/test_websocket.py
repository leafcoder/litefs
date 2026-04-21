#!/usr/bin/env python
# coding: utf-8

"""
WebSocket 模块单元测试
"""

import sys
import os
import unittest
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.websocket.protocol import (
    Frame, Opcode, CloseCode, 
    compute_accept_key, parse_close_payload, build_close_payload
)
from litefs.websocket.connection import ConnectionManager


class TestProtocol(unittest.TestCase):
    """协议测试"""
    
    def test_compute_accept_key(self):
        """测试 Accept Key 计算"""
        key = "dGhlIHNhbXBsZSBub25jZQ=="
        accept = compute_accept_key(key)
        self.assertEqual(accept, "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")
    
    def test_frame_build_text(self):
        """测试构建文本帧"""
        frame = Frame(opcode=Opcode.TEXT, payload=b'Hello')
        data = frame.build()
        
        self.assertEqual(data[0] & 0x0F, Opcode.TEXT)
        self.assertTrue(data[0] & 0x80)
    
    def test_frame_build_binary(self):
        """测试构建二进制帧"""
        frame = Frame(opcode=Opcode.BINARY, payload=b'\x00\x01\x02')
        data = frame.build()
        
        self.assertEqual(data[0] & 0x0F, Opcode.BINARY)
    
    def test_frame_build_masked(self):
        """测试构建掩码帧"""
        frame = Frame(opcode=Opcode.TEXT, payload=b'Hello')
        data = frame.build(mask=True, masking_key=b'\x00\x00\x00\x00')
        
        self.assertTrue(data[1] & 0x80)
    
    def test_frame_parse(self):
        """测试解析帧"""
        original = Frame(opcode=Opcode.TEXT, payload=b'Hello World')
        data = original.build()
        
        parsed, consumed = Frame.parse(data)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.opcode, Opcode.TEXT)
        self.assertEqual(parsed.payload, b'Hello World')
        self.assertTrue(parsed.fin)
    
    def test_frame_parse_masked(self):
        """测试解析掩码帧"""
        original = Frame(opcode=Opcode.TEXT, payload=b'Test')
        data = original.build(mask=True)
        
        parsed, consumed = Frame.parse(data)
        
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.payload, b'Test')
    
    def test_frame_parse_partial(self):
        """测试解析不完整帧"""
        data = b'\x81\x05Hel'
        
        parsed, consumed = Frame.parse(data)
        
        self.assertIsNone(parsed)
        self.assertEqual(consumed, 0)
    
    def test_close_payload(self):
        """测试关闭帧负载"""
        payload = build_close_payload(CloseCode.NORMAL, 'Goodbye')
        code, reason = parse_close_payload(payload)
        
        self.assertEqual(code, CloseCode.NORMAL)
        self.assertEqual(reason, 'Goodbye')


class TestConnectionManager(unittest.TestCase):
    """连接管理器测试"""
    
    def setUp(self):
        self.manager = ConnectionManager()
    
    def test_add_connection(self):
        """测试添加连接"""
        class MockConnection:
            def __init__(self):
                self._rooms = set()
                self._manager = None
        
        conn = MockConnection()
        self.manager.add(conn)
        
        self.assertEqual(self.manager.connection_count, 1)
    
    def test_remove_connection(self):
        """测试移除连接"""
        class MockConnection:
            def __init__(self):
                self._rooms = set()
                self._manager = None
        
        conn = MockConnection()
        self.manager.add(conn)
        self.manager.remove(conn)
        
        self.assertEqual(self.manager.connection_count, 0)
    
    def test_room_management(self):
        """测试房间管理"""
        class MockConnection:
            def __init__(self):
                self._rooms = set()
                self._manager = None
        
        conn = MockConnection()
        self.manager.add(conn)
        
        self.manager._join_room(conn, 'room1')
        self.assertIn('room1', self.manager._rooms)
        self.assertIn(conn, self.manager._rooms['room1'])
        
        self.manager._leave_room(conn, 'room1')
        self.assertNotIn('room1', self.manager._rooms)
    
    def test_broadcast(self):
        """测试广播"""
        messages = []
        
        class MockConnection:
            def __init__(self, id):
                self.id = id
                self._rooms = set()
                self._manager = None
            
            def send(self, data):
                messages.append((self.id, data))
        
        conn1 = MockConnection(1)
        conn2 = MockConnection(2)
        
        self.manager.add(conn1)
        self.manager.add(conn2)
        
        self.manager.broadcast({'message': 'hello'})
        
        self.assertEqual(len(messages), 2)
    
    def test_broadcast_to_room(self):
        """测试房间广播"""
        messages = []
        
        class MockConnection:
            def __init__(self, id):
                self.id = id
                self._rooms = set()
                self._manager = None
            
            def send(self, data):
                messages.append((self.id, data))
        
        conn1 = MockConnection(1)
        conn2 = MockConnection(2)
        conn3 = MockConnection(3)
        
        self.manager.add(conn1)
        self.manager.add(conn2)
        self.manager.add(conn3)
        
        self.manager._join_room(conn1, 'room1')
        self.manager._join_room(conn2, 'room1')
        
        self.manager.broadcast_to_room('room1', {'message': 'hello'})
        
        self.assertEqual(len(messages), 2)


class TestOpcode(unittest.TestCase):
    """操作码测试"""
    
    def test_opcode_values(self):
        """测试操作码值"""
        self.assertEqual(Opcode.CONTINUATION, 0x0)
        self.assertEqual(Opcode.TEXT, 0x1)
        self.assertEqual(Opcode.BINARY, 0x2)
        self.assertEqual(Opcode.CLOSE, 0x8)
        self.assertEqual(Opcode.PING, 0x9)
        self.assertEqual(Opcode.PONG, 0xA)


class TestCloseCode(unittest.TestCase):
    """关闭码测试"""
    
    def test_close_code_values(self):
        """测试关闭码值"""
        self.assertEqual(CloseCode.NORMAL, 1000)
        self.assertEqual(CloseCode.GOING_AWAY, 1001)
        self.assertEqual(CloseCode.PROTOCOL_ERROR, 1002)
        self.assertEqual(CloseCode.UNAUTHORIZED, 4001)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestProtocol))
    suite.addTests(loader.loadTestsFromTestCase(TestConnectionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestOpcode))
    suite.addTests(loader.loadTestsFromTestCase(TestCloseCode))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
