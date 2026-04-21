#!/usr/bin/env python
# coding: utf-8

"""
HTTP 响应对象和响应构建工具

提供 Response 类和相关的响应构建方法
"""

import json
import os
import sys
from http.client import responses as http_status_codes

from .._version import __version__

# 默认配置
default_content_type = "text/html; charset=utf-8"
json_content_type = "application/json; charset=utf-8"

# 服务器信息
server_info = "litefs/%s python/%s" % (__version__, sys.version.split()[0])

# 默认错误页面模板
DEFAULT_STATUS_MESSAGE = """\
<html>
    <head>
        <meta charset="utf-8">
        <title>HTTP response</title>
    </head>
    <body>
        <h1>HTTP response</h1>
        <p>HTTP status %(code)d.
        <p>Message: %(message)s.
        <p>HTTP code explanation: %(code)s = %(explain)s.
    </body>
</html>"""


class Response:
    """
    响应对象，提供更丰富的响应方法
    """

    def __init__(self, content=None, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or []

    @classmethod
    def json(cls, data, status_code=200, headers=None):
        """
        返回 JSON 响应
        """
        content = json.dumps(data, ensure_ascii=False)
        headers = headers or []
        # 确保设置正确的 Content-Type
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)
        if not has_content_type:
            headers.insert(0, ("Content-Type", "application/json; charset=utf-8"))
        return cls(content, status_code, headers)

    @classmethod
    def html(cls, content, status_code=200, headers=None):
        """
        返回 HTML 响应
        """
        headers = headers or []
        # 确保设置正确的 Content-Type
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)
        if not has_content_type:
            headers.insert(0, ("Content-Type", "text/html; charset=utf-8"))
        return cls(content, status_code, headers)

    @classmethod
    def text(cls, content, status_code=200, headers=None):
        """
        返回纯文本响应
        """
        headers = headers or []
        # 确保设置正确的 Content-Type
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)
        if not has_content_type:
            headers.insert(0, ("Content-Type", "text/plain; charset=utf-8"))
        return cls(content, status_code, headers)

    @classmethod
    def file(cls, file_path, status_code=200, headers=None):
        """
        返回文件响应
        """
        if not os.path.exists(file_path):
            return cls("File not found", 404)

        # 猜测文件的 MIME 类型
        from mimetypes import guess_type
        mime_type, encoding = guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        # 读取文件内容
        with open(file_path, 'rb') as f:
            content = f.read()

        headers = headers or []
        # 确保设置正确的 Content-Type
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)
        if not has_content_type:
            headers.insert(0, ("Content-Type", mime_type))
        # 添加 Content-Disposition 头，使浏览器下载文件
        headers.append(("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}"))
        headers.append(("Content-Length", str(len(content))))

        return cls(content, status_code, headers)

    @classmethod
    def redirect(cls, url, status_code=302, headers=None):
        """
        返回重定向响应
        """
        headers = headers or []
        headers.insert(0, ("Location", url))
        headers.insert(0, ("Content-Type", "text/html; charset=utf-8"))
        return cls(f"Redirecting to {url}", status_code, headers)

    @classmethod
    def error(cls, status_code, message=None, headers=None):
        """
        返回错误响应
        """
        status_text = responses.get(status_code, "Unknown Error")
        message = message or status_text
        content = DEFAULT_STATUS_MESSAGE % {
            "code": status_code,
            "message": message,
            "explain": status_text,
        }
        headers = headers or []
        headers.insert(0, ("Content-Type", "text/html; charset=utf-8"))
        return cls(content, status_code, headers)

    @classmethod
    def stream(cls, content, status_code=200, headers=None):
        """
        返回流式响应

        Args:
            content: 可迭代对象，如生成器、迭代器，用于流式返回数据
            status_code: HTTP 状态码
            headers: 响应头列表

        Returns:
            Response 对象
        """
        headers = headers or []
        # 确保设置正确的 Content-Type
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)
        if not has_content_type:
            headers.insert(0, ("Content-Type", "text/plain; charset=utf-8"))
        # 对于流式响应，不设置 Content-Length，使用 Transfer-Encoding: chunked
        has_transfer_encoding = any(h[0].lower() == 'transfer-encoding' for h in headers)
        if not has_transfer_encoding:
            headers.append(("Transfer-Encoding", "chunked"))
        return cls(content, status_code, headers)

    @classmethod
    def sse(cls, content, status_code=200):
        """
        返回 Server-Sent Events 流式响应

        Args:
            content: 可迭代对象，如生成器、迭代器，用于流式返回 SSE 数据
            status_code: HTTP 状态码

        Returns:
            Response 对象
        """
        headers = [
            ("Content-Type", "text/event-stream"),
            ("Cache-Control", "no-cache"),
            ("Connection", "keep-alive")
        ]
        return cls.stream(content, status_code, headers)

    @classmethod
    def file_stream(cls, file_path, status_code=200):
        """
        流式返回文件

        Args:
            file_path: 文件路径
            status_code: HTTP 状态码

        Returns:
            Response 对象
        """
        from mimetypes import guess_type

        if not os.path.exists(file_path):
            return cls.error(404, "File not found")

        # 猜测文件的 MIME 类型
        mime_type, encoding = guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        def generate_file():
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(1024 * 8)  # 每次读取 8KB
                    if not chunk:
                        break
                    yield chunk

        headers = [
            ("Content-Disposition", f"attachment; filename={os.path.basename(file_path)}"),
            ("Content-Type", mime_type)
        ]
        return cls.stream(generate_file(), status_code, headers)

    def set_cookie(self, key, value, max_age=None, expires=None, path='/',
                   domain=None, secure=False, httponly=False, samesite='Lax'):
        """
        设置 Cookie

        Args:
            key: Cookie 名称
            value: Cookie 值
            max_age: 最大存活时间（秒）
            expires: 过期时间
            path: Cookie 路径
            domain: Cookie 域名
            secure: 是否仅 HTTPS
            httponly: 是否禁止 JavaScript 访问
            samesite: SameSite 属性 (Strict, Lax, None)
        """
        from http.cookies import SimpleCookie

        cookie = SimpleCookie()
        cookie[key] = value

        if max_age is not None:
            cookie[key]['max-age'] = str(max_age)
        if expires is not None:
            cookie[key]['expires'] = expires
        if path:
            cookie[key]['path'] = path
        if domain:
            cookie[key]['domain'] = domain
        if secure:
            cookie[key]['secure'] = True
        if httponly:
            cookie[key]['httponly'] = True
        if samesite:
            cookie[key]['samesite'] = samesite

        self.headers.append(("Set-Cookie", cookie[key].OutputString()))
        return self

    def delete_cookie(self, key, path='/', domain=None):
        """
        删除 Cookie

        Args:
            key: Cookie 名称
            path: Cookie 路径
            domain: Cookie 域名
        """
        from http.cookies import SimpleCookie
        from datetime import datetime, timedelta

        cookie = SimpleCookie()
        cookie[key] = ''
        cookie[key]['path'] = path
        cookie[key]['expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        if domain:
            cookie[key]['domain'] = domain

        self.headers.append(("Set-Cookie", cookie[key].OutputString()))
        return self


# 别名，保持向后兼容
responses = http_status_codes

__all__ = [
    'Response',
    'DEFAULT_STATUS_MESSAGE',
    'default_content_type',
    'json_content_type',
    'server_info',
    'http_status_codes',
]
