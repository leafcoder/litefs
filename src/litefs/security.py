#!/usr/bin/env python
# coding: utf-8

"""
安全相关工具函数

提供安全的路径处理、CSRF防护等功能
"""

import os
import secrets
from typing import Optional


def secure_path_join(base: str, path: str) -> Optional[str]:
    """
    安全的路径拼接，防止路径遍历攻击
    
    Args:
        base: 基础目录
        path: 相对路径
        
    Returns:
        安全的完整路径，如果路径不安全则返回 None
    """
    # 规范化路径
    full_path = os.path.normpath(os.path.join(base, path))
    base = os.path.abspath(base)
    
    # 确保基础目录以分隔符结尾
    if not base.endswith(os.sep):
        base += os.sep
    
    # 检查规范化后的路径是否在基础目录下
    normalized_full_path = os.path.abspath(full_path)
    if not normalized_full_path.startswith(base) and normalized_full_path != base.rstrip(os.sep):
        return None
    
    return full_path


def generate_csrf_token() -> str:
    """
    生成 CSRF 令牌
    
    Returns:
        CSRF 令牌字符串
    """
    return secrets.token_hex(32)


def validate_csrf_token(token: str, session_token: str) -> bool:
    """
    验证 CSRF 令牌
    
    Args:
        token: 请求中的 CSRF 令牌
        session_token: Session 中的 CSRF 令牌
        
    Returns:
        验证是否通过
    """
    if not token or not session_token:
        return False
    
    return secrets.compare_digest(token, session_token)


__all__ = [
    'secure_path_join',
    'generate_csrf_token',
    'validate_csrf_token',
]
