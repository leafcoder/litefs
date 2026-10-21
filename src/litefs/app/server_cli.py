#!/usr/bin/env python
# coding: utf-8

"""
内置测试服务器命令行入口

提供 `python -m litefs.core` 直接启动演示服务器的参数解析与装配逻辑。
注意：为避免循环导入，本模块对 Litefs 采用函数内延迟导入。
"""

import argparse
import sys


def _cmd_args(args):
    title = args[0] if args else "litefs"
    parser = argparse.ArgumentParser(title, description=__doc__)
    parser.add_argument(
        "-H", "--host", dest="host", required=False, default="localhost",
        help="bind server to HOST"
    )
    parser.add_argument(
        "-P",
        "--port",
        action="store",
        dest="port",
        type=int,
        required=False,
        default=9090,
        help="bind server to PORT",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        dest="debug",
        required=False,
        default=False,
        help="start server in debug mode",
    )

    parser.add_argument(
        "--log", dest="log", required=False, default="./default.log",
        help="save log to LOG"
    )
    parser.add_argument(
        "--listen", dest="listen", type=int, required=False, default=1024,
        help="server LISTEN"
    )
    parser.add_argument(
        "--max-request-size",
        dest="max_request_size",
        required=False,
        type=int,
        default=10485760,
        help="maximum request body size in bytes (default: 10MB)",
    )
    parser.add_argument(
        "--max-upload-size",
        dest="max_upload_size",
        required=False,
        type=int,
        default=52428800,
        help="maximum file upload size in bytes (default: 50MB)",
    )
    parser.add_argument(
        "--config",
        dest="config_file",
        required=False,
        default=None,
        help="path to configuration file (YAML, JSON, or TOML)",
    )
    parser.add_argument(
        "--processes",
        dest="processes",
        type=int,
        required=False,
        default=1,
        help="number of worker processes (default: 1)",
    )
    args = parser.parse_args(args and args[1:])
    return args


def test_server():
    """使用默认中间件装配并启动内置测试服务器"""
    # 延迟导入避免与 litefs.core 循环依赖
    from litefs.core import Litefs
    from litefs.middleware import (
        CORSMiddleware,
        CSRFMiddleware,
        LoggingMiddleware,
        SecurityMiddleware,
    )

    args = _cmd_args(sys.argv)
    kwargs = vars(args)
    processes = kwargs.pop('processes', 1)
    litefs = (
        Litefs(**kwargs)
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
        .add_middleware(CSRFMiddleware)
    )
    litefs.run(poll_interval=0.1, processes=processes)
