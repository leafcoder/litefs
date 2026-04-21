#!/usr/bin/env python
# coding: utf-8

"""
WebSocket 协议解析模块

实现 RFC 6455 WebSocket 协议。
"""

import struct
import hashlib
import base64
from enum import IntEnum
from typing import Tuple, Optional, Union


class Opcode(IntEnum):
    """WebSocket 操作码"""
    CONTINUATION = 0x0
    TEXT = 0x1
    BINARY = 0x2
    CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


class CloseCode(IntEnum):
    """WebSocket 关闭状态码"""
    NORMAL = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    NO_STATUS = 1005
    ABNORMAL = 1006
    INVALID_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXT = 1010
    INTERNAL_ERROR = 1011
    SERVICE_RESTART = 1012
    TRY_AGAIN_LATER = 1013
    UNAUTHORIZED = 4001


class Frame:
    """WebSocket 帧"""
    
    def __init__(
        self,
        opcode: int,
        payload: bytes,
        fin: bool = True,
        rsv1: bool = False,
        rsv2: bool = False,
        rsv3: bool = False,
        masked: bool = False,
        masking_key: bytes = None,
    ):
        self.opcode = opcode
        self.payload = payload
        self.fin = fin
        self.rsv1 = rsv1
        self.rsv2 = rsv2
        self.rsv3 = rsv3
        self.masked = masked
        self.masking_key = masking_key
    
    @classmethod
    def parse(cls, data: bytes) -> Tuple['Frame', int]:
        """
        解析 WebSocket 帧
        
        Args:
            data: 原始字节数据
            
        Returns:
            (Frame 对象, 消耗的字节数)
        """
        if len(data) < 2:
            return None, 0
        
        first_byte = data[0]
        second_byte = data[1]
        
        fin = bool(first_byte & 0x80)
        rsv1 = bool(first_byte & 0x40)
        rsv2 = bool(first_byte & 0x20)
        rsv3 = bool(first_byte & 0x10)
        opcode = first_byte & 0x0F
        
        masked = bool(second_byte & 0x80)
        payload_len = second_byte & 0x7F
        
        offset = 2
        
        if payload_len == 126:
            if len(data) < offset + 2:
                return None, 0
            payload_len = struct.unpack('!H', data[offset:offset+2])[0]
            offset += 2
        elif payload_len == 127:
            if len(data) < offset + 8:
                return None, 0
            payload_len = struct.unpack('!Q', data[offset:offset+8])[0]
            offset += 8
        
        masking_key = None
        if masked:
            if len(data) < offset + 4:
                return None, 0
            masking_key = data[offset:offset+4]
            offset += 4
        
        if len(data) < offset + payload_len:
            return None, 0
        
        payload = data[offset:offset+payload_len]
        
        if masked and masking_key:
            payload = cls._apply_mask(payload, masking_key)
        
        frame = cls(
            opcode=opcode,
            payload=payload,
            fin=fin,
            rsv1=rsv1,
            rsv2=rsv2,
            rsv3=rsv3,
            masked=masked,
            masking_key=masking_key,
        )
        
        return frame, offset + payload_len
    
    def build(self, mask: bool = False, masking_key: bytes = None) -> bytes:
        """
        构建 WebSocket 帧字节
        
        Args:
            mask: 是否掩码
            masking_key: 掩码密钥
            
        Returns:
            帧字节数据
        """
        first_byte = self.opcode
        
        if self.fin:
            first_byte |= 0x80
        if self.rsv1:
            first_byte |= 0x40
        if self.rsv2:
            first_byte |= 0x20
        if self.rsv3:
            first_byte |= 0x10
        
        payload = self.payload
        payload_len = len(payload)
        
        if mask:
            if masking_key is None:
                import os
                masking_key = os.urandom(4)
            payload = self._apply_mask(payload, masking_key)
        
        second_byte = 0
        if mask:
            second_byte |= 0x80
        
        header = bytes([first_byte])
        
        if payload_len <= 125:
            header += bytes([second_byte | payload_len])
        elif payload_len <= 65535:
            header += bytes([second_byte | 126])
            header += struct.pack('!H', payload_len)
        else:
            header += bytes([second_byte | 127])
            header += struct.pack('!Q', payload_len)
        
        if mask:
            header += masking_key
        
        return header + payload
    
    @staticmethod
    def _apply_mask(data: bytes, mask: bytes) -> bytes:
        """应用掩码"""
        result = bytearray(len(data))
        for i, byte in enumerate(data):
            result[i] = byte ^ mask[i % 4]
        return bytes(result)


def compute_accept_key(key: str) -> str:
    """
    计算 Sec-WebSocket-Accept 值
    
    Args:
        key: Sec-WebSocket-Key 值
        
    Returns:
        Sec-WebSocket-Accept 值
    """
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1((key + GUID).encode()).digest()
    return base64.b64encode(sha1).decode()


def parse_close_payload(payload: bytes) -> Tuple[int, str]:
    """
    解析关闭帧负载
    
    Args:
        payload: 关闭帧负载
        
    Returns:
        (状态码, 原因)
    """
    if len(payload) < 2:
        return CloseCode.NO_STATUS, ''
    
    code = struct.unpack('!H', payload[:2])[0]
    reason = payload[2:].decode('utf-8', errors='replace')
    
    return code, reason


def build_close_payload(code: int, reason: str = '') -> bytes:
    """
    构建关闭帧负载
    
    Args:
        code: 状态码
        reason: 原因
        
    Returns:
        负载字节
    """
    payload = struct.pack('!H', code)
    if reason:
        payload += reason.encode('utf-8')
    return payload
