#!/usr/bin/env python
# coding: utf-8

"""
配置加密解密 Mixin

内部拆分模块：由 litefs.config.core 装配进 Config，不构成公共 API。
"""

from typing import Any, Dict

from .._json import dumps, loads


class ConfigCryptoMixin:
    """配置加密解密能力

    依赖宿主 ``Config`` 装配的实例属性，
    以下声明仅供类型检查使用，运行时无开销。
    """

    _config: Dict[str, Any]

    @staticmethod
    def _derive_fernet_key(secret_key: str) -> bytes:
        """
        从用户提供的密钥派生合规的 Fernet 密钥

        Fernet 要求密钥为 32 字节 base64 编码（即 44 字符 URL-safe base64），
        其中前 16 字节为 signing key，后 16 字节为 encryption key。
        直接用 '0' 填充或截断都是不安全的。

        本方法使用 HKDF-SHA256 进行密钥派生，确保：
        1. 任意长度的输入密钥都能派生出合规的 Fernet 密钥
        2. 不同的输入密钥产生不同的派生密钥
        3. 符合密码学最佳实践

        Args:
            secret_key: 用户提供的原始密钥

        Returns:
            合规的 Fernet 密钥（base64 编码的 32 字节）
        """
        import base64
        import hashlib
        import hmac

        # 使用 HKDF-SHA256 从用户密钥派生 32 字节密钥
        # 1. Extract: 从输入密钥提取伪随机密钥
        salt = b'litefs-config-encryption-salt'
        prk = hmac.new(salt, secret_key.encode('utf-8'), hashlib.sha256).digest()

        # 2. Expand: 扩展为 32 字节密钥
        info = b'litefs-fernet-key'
        t = hmac.new(prk, info + b'\x01', hashlib.sha256).digest()

        # 3. 编码为 Fernet 所需的 base64 格式
        return base64.urlsafe_b64encode(t)

    def encrypt_config(self, key: str, value: Any) -> str:
        """
        加密配置值

        Args:
            key: 配置键
            value: 配置值

        Returns:
            加密后的字符串
        """
        import base64
        from cryptography.fernet import Fernet

        secret_key = self._config.get('config_secret_key')
        if not secret_key:
            raise ValueError("配置加密密钥未设置")

        # 使用 HKDF 派生合规的 Fernet 密钥
        fernet_key = self._derive_fernet_key(secret_key)
        fernet = Fernet(fernet_key)

        # 序列化值
        serialized_value = dumps(value)

        # 加密
        encrypted = fernet.encrypt(serialized_value)

        return base64.b64encode(encrypted).decode()

    def decrypt_config(self, encrypted_value: str) -> Any:
        """
        解密配置值

        Args:
            encrypted_value: 加密后的字符串

        Returns:
            解密后的值
        """
        import base64
        from cryptography.fernet import Fernet

        secret_key = self._config.get('config_secret_key')
        if not secret_key:
            raise ValueError("配置加密密钥未设置")

        # 使用 HKDF 派生合规的 Fernet 密钥
        fernet_key = self._derive_fernet_key(secret_key)
        fernet = Fernet(fernet_key)

        # 解密
        encrypted = base64.b64decode(encrypted_value.encode())
        decrypted = fernet.decrypt(encrypted)

        # 反序列化
        return loads(decrypted)
