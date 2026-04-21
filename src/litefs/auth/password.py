#!/usr/bin/env python
# coding: utf-8

"""
密码哈希和验证

提供安全的密码哈希和验证功能。
"""

import hashlib
import os
import secrets
import string
import re
from typing import Optional, Tuple


try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False


def hash_password(password: str, rounds: int = 12) -> str:
    """
    哈希密码
    
    Args:
        password: 明文密码
        rounds: 哈希轮数（仅 bcrypt）
        
    Returns:
        哈希后的密码
    """
    if HAS_BCRYPT:
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    else:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        return f"pbkdf2${salt}${hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码
    
    Args:
        password: 明文密码
        password_hash: 哈希后的密码
        
    Returns:
        是否匹配
    """
    if not password or not password_hash:
        return False
    
    if HAS_BCRYPT and password_hash.startswith('$2b$'):
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception:
            return False
    
    if password_hash.startswith('pbkdf2$'):
        parts = password_hash.split('$')
        if len(parts) != 3:
            return False
        
        _, salt, stored_hash = parts
        computed_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
        
        return secrets.compare_digest(computed_hash, stored_hash)
    
    return False


def generate_password(length: int = 16) -> str:
    """
    生成随机密码
    
    Args:
        length: 密码长度
        
    Returns:
        随机密码
    """
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def validate_password_strength(password: str) -> Tuple[bool, list]:
    """
    验证密码强度
    
    Args:
        password: 密码
        
    Returns:
        (是否通过, 错误消息列表)
    """
    errors = []
    
    if len(password) < 8:
        errors.append('密码长度至少 8 个字符')
    
    if len(password) > 128:
        errors.append('密码长度不能超过 128 个字符')
    
    if not re.search(r'[a-z]', password):
        errors.append('密码必须包含小写字母')
    
    if not re.search(r'[A-Z]', password):
        errors.append('密码必须包含大写字母')
    
    if not re.search(r'\d', password):
        errors.append('密码必须包含数字')
    
    common_passwords = [
        'password', '123456', 'qwerty', 'abc123', 'letmein',
        'admin', 'welcome', 'monkey', 'dragon', 'master',
    ]
    
    if password.lower() in common_passwords:
        errors.append('密码过于常见，请使用更复杂的密码')
    
    return len(errors) == 0, errors


def check_password_breach(password: str) -> bool:
    """
    检查密码是否在已知泄露数据库中
    
    注意：这是一个简化的实现，实际应该调用 Have I Been Pwned API
    
    Args:
        password: 密码
        
    Returns:
        True 表示已泄露，False 表示安全
    """
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    
    common_hashes = {
        '5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8',  # password
        '7C4A8D09CA3762AF61E59520943DC26494F8941B',  # 123456
        'B1B3773A05C0ED0176787A4F1574FF0075F7521E',  # qwerty
        'E99A18C428CB38D5F260853678922E03ABD',       # abc123
    }
    
    return sha1_hash in common_hashes
