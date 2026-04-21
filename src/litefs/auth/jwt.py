#!/usr/bin/env python
# coding: utf-8

"""
JWT Token 管理

提供 JWT Token 的生成、验证和刷新功能。
"""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional


class JWTManager:
    """JWT Token 管理器"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = 'HS256',
        access_token_expires: int = 3600,
        refresh_token_expires: int = 604800,
    ):
        """
        初始化 JWT 管理器
        
        Args:
            secret_key: 密钥
            algorithm: 算法（目前仅支持 HS256）
            access_token_expires: Access Token 过期时间（秒）
            refresh_token_expires: Refresh Token 过期时间（秒）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expires = access_token_expires
        self.refresh_token_expires = refresh_token_expires
        
        self._blacklist = set()
    
    def _base64url_encode(self, data: bytes) -> str:
        """Base64 URL 安全编码"""
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    def _base64url_decode(self, data: str) -> bytes:
        """Base64 URL 安全解码"""
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        return base64.urlsafe_b64decode(data)
    
    def _create_signature(self, header: str, payload: str) -> str:
        """创建签名"""
        message = f"{header}.{payload}".encode('utf-8')
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message,
            hashlib.sha256
        ).digest()
        return self._base64url_encode(signature)
    
    def create_token(self, payload: Dict[str, Any], expires_in: int = None) -> str:
        """
        创建 JWT Token
        
        Args:
            payload: 载荷数据
            expires_in: 过期时间（秒）
            
        Returns:
            JWT Token 字符串
        """
        header = {
            'alg': self.algorithm,
            'typ': 'JWT'
        }
        
        now = int(time.time())
        token_payload = payload.copy()
        token_payload['iat'] = now
        
        if expires_in:
            token_payload['exp'] = now + expires_in
        
        header_encoded = self._base64url_encode(json.dumps(header).encode('utf-8'))
        payload_encoded = self._base64url_encode(json.dumps(token_payload).encode('utf-8'))
        
        signature = self._create_signature(header_encoded, payload_encoded)
        
        return f"{header_encoded}.{payload_encoded}.{signature}"
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        解码 JWT Token
        
        Args:
            token: JWT Token 字符串
            
        Returns:
            载荷数据或 None
        """
        if token in self._blacklist:
            return None
        
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            header_encoded, payload_encoded, signature = parts
            
            expected_signature = self._create_signature(header_encoded, payload_encoded)
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            payload = json.loads(self._base64url_decode(payload_encoded))
            
            if 'exp' in payload:
                if payload['exp'] < int(time.time()):
                    return None
            
            return payload
            
        except Exception:
            return None
    
    def create_access_token(self, payload: Dict[str, Any]) -> str:
        """
        创建 Access Token
        
        Args:
            payload: 载荷数据
            
        Returns:
            Access Token
        """
        token_payload = payload.copy()
        token_payload['type'] = 'access'
        return self.create_token(token_payload, self.access_token_expires)
    
    def create_refresh_token(self, payload: Dict[str, Any]) -> str:
        """
        创建 Refresh Token
        
        Args:
            payload: 载荷数据
            
        Returns:
            Refresh Token
        """
        token_payload = payload.copy()
        token_payload['type'] = 'refresh'
        return self.create_token(token_payload, self.refresh_token_expires)
    
    def revoke_token(self, token: str):
        """
        撤销 Token（加入黑名单）
        
        Args:
            token: JWT Token
        """
        self._blacklist.add(token)
    
    def is_token_revoked(self, token: str) -> bool:
        """
        检查 Token 是否已撤销
        
        Args:
            token: JWT Token
            
        Returns:
            是否已撤销
        """
        return token in self._blacklist


def create_token(
    payload: Dict[str, Any],
    secret_key: str,
    expires_in: int = 3600,
    algorithm: str = 'HS256'
) -> str:
    """
    创建 JWT Token（便捷函数）
    
    Args:
        payload: 载荷数据
        secret_key: 密钥
        expires_in: 过期时间（秒）
        algorithm: 算法
        
    Returns:
        JWT Token
    """
    manager = JWTManager(secret_key, algorithm)
    return manager.create_token(payload, expires_in)


def decode_token(
    token: str,
    secret_key: str,
    algorithm: str = 'HS256'
) -> Optional[Dict[str, Any]]:
    """
    解码 JWT Token（便捷函数）
    
    Args:
        token: JWT Token
        secret_key: 密钥
        algorithm: 算法
        
    Returns:
        载荷数据或 None
    """
    manager = JWTManager(secret_key, algorithm)
    return manager.decode_token(token)
