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
import time
from typing import Optional, Tuple, Dict
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


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


_PASSWORD_BREACH_CACHE: Dict[str, Tuple[bool, float]] = {}
_CACHE_TTL = 3600
_HIBP_API_URL = "https://api.pwnedpasswords.com/range/{}"
_HIBP_USER_AGENT = "LiteFS-Password-Check/1.0"
_REQUEST_TIMEOUT = 5


def check_password_breach(password: str, use_cache: bool = True, timeout: int = _REQUEST_TIMEOUT) -> bool:
    """
    检查密码是否在已知泄露数据库中
    
    使用 Have I Been Pwned (HIBP) API 的 k-anonymity 模型：
    1. 计算密码的 SHA-1 哈希
    2. 只发送哈希的前5个字符到 API
    3. API 返回所有以这5个字符开头的哈希后缀和出现次数
    4. 在本地检查完整的哈希是否在返回的列表中
    
    这种方式既保护了密码隐私，又能有效检查泄露情况。
    
    Args:
        password: 密码
        use_cache: 是否使用缓存（默认 True）
        timeout: API 请求超时时间（秒，默认 5）
        
    Returns:
        True 表示已泄露，False 表示安全
        
    Raises:
        无异常抛出，网络错误时返回 False 并记录警告
        
    Example:
        >>> is_breached = check_password_breach("password123")
        >>> if is_breached:
        ...     print("密码已泄露，请更换")
    """
    if not password:
        return False
    
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    hash_prefix = sha1_hash[:5]
    hash_suffix = sha1_hash[5:]
    
    if use_cache:
        cache_key = hash_prefix
        if cache_key in _PASSWORD_BREACH_CACHE:
            cached_result, cached_time = _PASSWORD_BREACH_CACHE[cache_key]
            if time.time() - cached_time < _CACHE_TTL:
                return cached_result
    
    try:
        request = Request(
            _HIBP_API_URL.format(hash_prefix),
            headers={'User-Agent': _HIBP_USER_AGENT}
        )
        
        with urlopen(request, timeout=timeout) as response:
            response_data = response.read().decode('utf-8')
        
        for line in response_data.splitlines():
            parts = line.strip().split(':')
            if len(parts) == 2:
                suffix, count = parts
                if suffix == hash_suffix:
                    result = True
                    if use_cache:
                        _PASSWORD_BREACH_CACHE[cache_key] = (result, time.time())
                    return result
        
        result = False
        if use_cache:
            _PASSWORD_BREACH_CACHE[cache_key] = (result, time.time())
        return result
        
    except (URLError, HTTPError, Exception) as e:
        import warnings
        warnings.warn(f"无法连接到 HIBP API: {e}. 使用本地常见密码检查作为降级方案。")
        
        common_hashes = {
            '5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8': 'password',
            '7C4A8D09CA3762AF61E59520943DC26494F8941B': '123456',
            'B1B3773A05C0ED0176787A4F1574FF0075F7521E': 'qwerty',
            'E99A18C428CB38D5F260853678922E03ABD8F1F': 'abc123',
        }
        
        result = sha1_hash in common_hashes
        return result


def clear_breach_cache() -> None:
    """
    清空密码泄露检查缓存
    
    在需要强制刷新缓存数据时调用此函数。
    """
    global _PASSWORD_BREACH_CACHE
    _PASSWORD_BREACH_CACHE.clear()


def get_breach_count(password: str, timeout: int = _REQUEST_TIMEOUT) -> int:
    """
    获取密码在泄露数据库中的出现次数
    
    Args:
        password: 密码
        timeout: API 请求超时时间（秒，默认 5）
        
    Returns:
        泄露次数，0 表示未泄露，-1 表示查询失败
        
    Example:
        >>> count = get_breach_count("password123")
        >>> if count > 0:
        ...     print(f"密码已泄露 {count} 次")
    """
    if not password:
        return 0
    
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    hash_prefix = sha1_hash[:5]
    hash_suffix = sha1_hash[5:]
    
    try:
        request = Request(
            _HIBP_API_URL.format(hash_prefix),
            headers={'User-Agent': _HIBP_USER_AGENT}
        )
        
        with urlopen(request, timeout=timeout) as response:
            response_data = response.read().decode('utf-8')
        
        for line in response_data.splitlines():
            parts = line.strip().split(':')
            if len(parts) == 2:
                suffix, count = parts
                if suffix == hash_suffix:
                    return int(count)
        
        return 0
        
    except (URLError, HTTPError, Exception) as e:
        import warnings
        warnings.warn(f"无法连接到 HIBP API: {e}")
        return -1
