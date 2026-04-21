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


class TokenBlacklist:
    """
    Token 黑名单存储

    支持多种后端：内存、缓存（Redis 等）。
    黑名单条目自动过期清理，不会无限增长。
    """

    def __init__(self, backend=None):
        """
        初始化 Token 黑名单

        Args:
            backend: 缓存后端实例，需支持 get/put/delete 方法。
                     如果为 None，则使用内存字典（单实例模式）。
                     推荐使用 RedisCache 等分布式缓存实现多实例共享。
        """
        self._backend = backend
        self._memory_store = {}  # 内存后端：{token_hash: expire_timestamp}

    def _hash_token(self, token: str) -> str:
        """对 token 做哈希，避免存储原始 token"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def add(self, token: str, expires_in: int = 3600):
        """
        将 token 加入黑名单

        Args:
            token: JWT Token
            expires_in: 黑名单条目存活时间（秒），应 >= token 自身的 exp
        """
        token_hash = self._hash_token(token)
        expire_at = int(time.time()) + expires_in

        if self._backend is not None:
            self._backend.put(f"jwt:blacklist:{token_hash}", True, expiration=expires_in)
        else:
            self._memory_store[token_hash] = expire_at

    def is_blacklisted(self, token: str) -> bool:
        """
        检查 token 是否在黑名单中

        Args:
            token: JWT Token

        Returns:
            是否已撤销
        """
        token_hash = self._hash_token(token)

        if self._backend is not None:
            return self._backend.get(f"jwt:blacklist:{token_hash}") is not None

        # 内存后端：检查并清理过期条目
        expire_at = self._memory_store.get(token_hash)
        if expire_at is None:
            return False
        if time.time() > expire_at:
            del self._memory_store[token_hash]
            return False
        return True

    def cleanup(self):
        """
        清理内存后端中的过期条目

        仅对内存后端有效，缓存后端依赖自身的 TTL 机制自动清理。
        """
        if self._backend is not None:
            return

        now = time.time()
        expired_keys = [k for k, v in self._memory_store.items() if now > v]
        for key in expired_keys:
            del self._memory_store[key]

    def clear(self):
        """清空黑名单"""
        if self._backend is not None:
            # 缓存后端无法精确清空仅黑名单条目，跳过
            return
        self._memory_store.clear()

    def __len__(self) -> int:
        """黑名单条目数量"""
        if self._backend is not None:
            return 0  # 缓存后端无法精确统计
        self.cleanup()
        return len(self._memory_store)


class JWTManager:
    """JWT Token 管理器"""
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = 'HS256',
        access_token_expires: int = 3600,
        refresh_token_expires: int = 604800,
        blacklist_backend=None,
    ):
        """
        初始化 JWT 管理器
        
        Args:
            secret_key: 密钥
            algorithm: 算法（目前仅支持 HS256）
            access_token_expires: Access Token 过期时间（秒）
            refresh_token_expires: Refresh Token 过期时间（秒）
            blacklist_backend: 黑名单缓存后端（如 RedisCache），
                               为 None 则使用内存（单实例，重启丢失）
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expires = access_token_expires
        self.refresh_token_expires = refresh_token_expires
        
        self._blacklist = TokenBlacklist(backend=blacklist_backend)
    
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
        if self._blacklist.is_blacklisted(token):
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
        
        自动计算黑名单条目的 TTL，与 token 自身的 exp 对齐，
        token 过期后黑名单条目自动清理。
        
        Args:
            token: JWT Token
        """
        # 计算 token 剩余有效期，作为黑名单条目的 TTL
        try:
            parts = token.split('.')
            if len(parts) == 3:
                payload = json.loads(self._base64url_decode(parts[1]))
                exp = payload.get('exp', 0)
                ttl = max(exp - int(time.time()), 0)
                # 额外增加 60 秒缓冲，确保 token 过期后黑名单仍短暂有效
                ttl = ttl + 60 if ttl > 0 else 3600
            else:
                ttl = 3600
        except Exception:
            ttl = 3600

        self._blacklist.add(token, expires_in=ttl)
    
    def is_token_revoked(self, token: str) -> bool:
        """
        检查 Token 是否已撤销
        
        Args:
            token: JWT Token
            
        Returns:
            是否已撤销
        """
        return self._blacklist.is_blacklisted(token)

    def cleanup_blacklist(self):
        """
        清理黑名单中的过期条目

        仅对内存后端有效，缓存后端依赖自身 TTL 机制。
        """
        self._blacklist.cleanup()


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
