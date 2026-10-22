#!/usr/bin/env python
# coding: utf-8

"""
应用辅助函数

提供响应内容序列化、配置对象创建、服务器套接字创建与
Session 管理器初始化等无状态辅助逻辑。
"""

import socket
from collections.abc import Iterable
from typing import Any, Dict, List, Tuple

from .._json import dumps
from ..config import Config, load_config


def _guess_content_type(content) -> str:
    """根据内容类型猜测 Content-Type"""
    if isinstance(content, (dict, list, tuple)):
        return "application/json; charset=utf-8"
    if isinstance(content, str) and content.startswith('<'):
        return "text/html; charset=utf-8"
    if isinstance(content, bytes):
        return "application/octet-stream"
    return "text/html; charset=utf-8"


def _serialize_content(content, is_json: bool = False) -> List[bytes]:
    """
    将响应内容序列化为 bytes 列表

    统一 WSGI/ASGI 的内容序列化逻辑，消除重复代码。

    Args:
        content: 响应内容（任意类型）
        is_json: Content-Type 是否包含 application/json

    Returns:
        list[bytes]: 序列化后的字节列表
    """
    if isinstance(content, (dict,)):
        return [dumps(content)]

    if isinstance(content, (list, tuple)):
        if is_json:
            return [dumps(content, default=str)]
        result = []
        for item in content:
            if isinstance(item, str):
                result.append(item.encode("utf-8"))
            elif isinstance(item, bytes):
                result.append(item)
            else:
                result.append(str(item).encode("utf-8"))
        return result

    if isinstance(content, str):
        if is_json:
            return [dumps(content)]
        return [content.encode("utf-8")]

    if isinstance(content, bytes):
        return [content]

    if content is None:
        return [b""]

    # 可迭代对象（生成器等）
    if isinstance(content, Iterable):
        def _gen():
            for item in content:
                if isinstance(item, str):
                    yield item.encode("utf-8")
                elif isinstance(item, bytes):
                    yield item
                else:
                    yield str(item).encode("utf-8")
        return list(_gen())

    return [str(content).encode("utf-8")]


def _parse_result_tuple(result) -> Tuple[str, list, Any]:
    """
    解析处理函数返回的结果元组

    Args:
        result: 处理函数的返回值

    Returns:
        (status, headers, content) 三元组
    """
    if (
        isinstance(result, (list, tuple))
        and len(result) == 3
        and isinstance(result[0], str)
        and isinstance(result[1], list)
    ):
        return result[0], result[1], result[2]
    content = result
    content_type = _guess_content_type(content)
    return "200 OK", [("Content-Type", content_type)], content


def make_config(**kwargs: Any) -> Config:
    """
    创建配置对象

    支持多种配置来源：
    1. 默认配置
    2. 配置文件（通过 config_file 参数）
    3. 环境变量（LITEFS_*）
    4. 代码中的配置（kwargs）

    Args:
        **kwargs: 配置项

    Returns:
        Config 对象
    """
    config_file = kwargs.pop('config_file', None)
    config = load_config(config_file=config_file, **kwargs)
    return config


def make_server(host: str, port: int, request_size: int = -1) -> socket.socket:
    """
    创建并绑定监听套接字

    Args:
        host: 监听地址
        port: 监听端口
        request_size: listen backlog，-1 表示使用默认值 1024

    Returns:
        已绑定并监听的 socket 对象
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    if -1 == request_size:
        request_size = 1024
    sock.listen(request_size)
    sock.setblocking(False)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


def is_port_available(host: str, port: int) -> bool:
    """
    检查端口是否可用

    Args:
        host: 主机地址
        port: 端口号

    Returns:
        bool: 端口是否可用
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def init_session_manager(config: Config) -> Any:
    """
    根据配置初始化全局 Session 管理器

    使用全局 Session 管理器，确保 Session 对象常驻内存，
    不会因为 Litefs 实例的创建和销毁而丢失数据。

    Args:
        config: 应用配置对象

    Returns:
        Session 缓存实例
    """
    from ..session.factory import SessionBackend
    from ..session.manager import SessionManager

    # 获取 session 相关配置
    session_backend = getattr(config, 'session_backend', SessionBackend.MEMORY)
    session_config: Dict[str, Any] = {}
    if session_backend == SessionBackend.REDIS:
        session_config = {
            "host": getattr(config, "redis_host", "localhost"),
            "port": getattr(config, "redis_port", 6379),
            "db": getattr(config, "redis_db", 0),
            "password": getattr(config, "redis_password", None),
            "key_prefix": getattr(
                config, "redis_session_key_prefix", "litefs:session:"),
            "expiration_time": getattr(
                config, "session_expiration_time", 3600),
        }
    elif session_backend == SessionBackend.DATABASE:
        session_config = {
            "db_path": getattr(config, "database_path", ":memory:"),
            "table_name": getattr(config, "database_session_table", "sessions"),
            "expiration_time": getattr(config, "session_expiration_time", 3600),
        }
    elif session_backend == SessionBackend.MEMCACHE:
        session_config = {
            "servers": getattr(config, "memcache_servers", ["localhost:11211"]),
            "key_prefix": getattr(
                config, "memcache_session_key_prefix", "litefs:session:"),
            "expiration_time": getattr(config, "session_expiration_time", 3600),
        }
    elif session_backend == SessionBackend.MEMORY:
        session_config = {
            "max_size": getattr(config, "session_max_size", 1000000),
        }
    # 使用 SessionManager 管理 Session 实例
    return SessionManager.get_session_cache(
        backend=session_backend,
        cache_key='default',
        **session_config
    )
