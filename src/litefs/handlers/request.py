#!/usr/bin/env python
# coding: utf-8

import importlib.util
import itertools
import json
import re
import sys
from collections import UserDict
from email.message import Message
from errno import EAGAIN, EWOULDBLOCK
from functools import lru_cache, partial
from hashlib import sha256
from http.cookies import SimpleCookie
from io import DEFAULT_BUFFER_SIZE, BufferedRWPair, BytesIO, RawIOBase, StringIO
from os import urandom
from posixpath import abspath as path_abspath
from posixpath import exists as path_exists
from posixpath import isdir as path_isdir
from posixpath import isfile as path_isfile
from posixpath import join as path_join
from posixpath import realpath as path_realpath
from posixpath import split as path_split
from posixpath import splitext as path_splitext
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile, TemporaryFile
from time import time
from uuid import uuid4
from weakref import proxy


@lru_cache(maxsize=512)
def parse_header(line):
    msg = Message()
    msg["content-type"] = line
    return msg.get_params()[0][0], dict(msg.get_params()[1:])


import socket
from http.client import responses as http_status_codes
from io import BytesIO as StringIO
from urllib.parse import unquote_plus

from ..exceptions import HttpError
from ..session import Session
from ..utils import gmt_date, log_debug, log_error, render_error
from mako.lookup import TemplateLookup
from ..cache import FormCache

default_page = "index"
default_404 = "not_found"
# 会话配置默认值
default_content_type = "application/json; charset=utf-8"

# 创建表单数据缓存实例
_form_cache = FormCache(max_size=1000, default_ttl=300)

EOFS = ("", "\n", "\r\n")
POSTS_HEADER_NAME = "litefs.posts"
FILES_HEADER_NAME = "litefs.files"
should_retry_error = (EWOULDBLOCK, EAGAIN)
double_slash_sub = re.compile(r"\/{2,}").sub
startswith_dot_sub = re.compile(r"\/\.+").sub
suffixes = (".py", ".pyc", ".pyo", ".so")
form_dict_match = re.compile(r"(.+)\[([^\[\]]+)\]").match
server_info = "litefs/%s python/%s" % ("0.5.0", sys.version.split()[0])

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
        import json
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
        import os
        from mimetypes import guess_type
        
        if not os.path.exists(file_path):
            return cls("File not found", 404)
        
        # 猜测文件的 MIME 类型
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
        from http.client import responses
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
        import os
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


def is_bytes(s):
    return isinstance(s, bytes)


def imap(func, iterable):
    return map(func, iterable)


def parse_form(query_string):
    """
    解析表单数据，支持缓存
    
    Args:
        query_string: 查询字符串
        
    Returns:
        解析后的表单数据字典
    """
    # 生成缓存键
    cache_key = f"form:{query_string}"
    
    # 尝试从缓存获取
    cached = _form_cache.get(cache_key)
    if cached is not None:
        return cached
    
    # 解析表单数据
    form = {}
    # 处理 bytes 类型输入
    if isinstance(query_string, bytes):
        query_string = query_string.decode('utf-8')
    query_string = unquote_plus(query_string)
    for s in query_string.split("&"):
        if not s:
            continue
        kv = s.split("=", 1)
        if 2 == len(kv):
            k, v = kv
        else:
            k, v = kv[0], ""
        k, v = unquote_plus(k), unquote_plus(v)
        if k.endswith("[]"):
            k = k[:-2]
            if k in form:
                result = form[k]
                if isinstance(result, dict):
                    raise ValueError("invalid form data %s" % query_string)
                if isinstance(result, list):
                    form[k].append(v)
                else:
                    form[k] = [result, v]
            else:
                form[k] = [v]
            continue
        matched = form_dict_match(k)
        if matched is None:
            if k in form:
                result = form[k]
                if isinstance(result, dict):
                    raise ValueError("invalid form data %s" % query_string)
                if isinstance(result, list):
                    form[k].append(v)
                else:
                    form[k] = [result, v]
            else:
                form[k] = v
        else:
            key, prefix = matched.groups()
            if key in form:
                result = form[key]
                if not isinstance(result, dict):
                    raise ValueError("invalid form data %s" % query_string)
                if prefix in result:
                    result[prefix] = [result[prefix], v]
                else:
                    result[prefix] = v
            else:
                form[key] = {prefix: v}
    
    # 存入缓存
    _form_cache.set(cache_key, form)
    
    return form


class BaseRequestHandler(object):
    """
    请求处理器基类，提供通用的请求处理功能
    """

    def __init__(self, app, environ):
        self._app = app
        self._environ = environ
        self._headers_responsed = False
        self._status_code = 200
        self._get = {}
        self._post = {}
        self._body = ""
        self._files = {}
        self._session_id = None
        self._session = None
        self._session_modified = False
        self._template_lookup = None
        # 初始化 _headers 属性，用于存储响应头
        self._headers = []

    def render_template(self, template_name, **kwargs):
        """
        渲染模板

        Args:
            template_name: 模板文件名
            **kwargs: 模板变量

        Returns:
            渲染后的 HTML 字符串
        """
        import os

        # 延迟初始化模板查找器
        if self._template_lookup is None:
            # 获取模板目录路径
            template_dir = getattr(self._app.config, 'template_dir', 'templates')
            if not os.path.isabs(template_dir):
                # 如果是相对路径，相对于当前工作目录
                template_dir = os.path.join(os.getcwd(), template_dir)

            # 创建模板查找器
            self._template_lookup = TemplateLookup(
                directories=[template_dir],
                input_encoding='utf-8',
                default_filters=['decode.utf8']
            )

        try:
            # 获取模板
            template = self._template_lookup.get_template(template_name)
            # 渲染模板
            content = template.render(**kwargs)
            
            # 直接返回渲染后的内容，不设置 Content-Type
            # Content-Type 会在 _response 方法中设置
            return content
        except Exception as e:
            # 模板渲染失败，返回错误信息
            error_content = f"<h1>Template Error</h1><p>Failed to render template '{template_name}': {str(e)}</p>"
            
            # 直接返回错误内容，不设置 Content-Type
            # Content-Type 会在 _response 方法中设置
            return error_content

    def start_response(self, status_code=200, headers=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        self._status_code = int(status_code)
        if headers is not None:
            for header in headers:
                if not isinstance(header, (list, tuple)):
                    header = header.encode("utf-8")
                    k, v = header.split(":")
                    k, v = k.strip(), v.strip()
                else:
                    k, v = header
                self._add_header(k, v)
        self._headers_responsed = True

    def _add_header(self, key, value):
        raise NotImplementedError("Subclasses must implement _add_header")

    def _response(self, status_code, headers=None, content=None):
        status_code = int(status_code)
        status_text = http_status_codes.get(status_code, "Unknown")
        status = "%d %s" % (status_code, status_text)

        # 创建响应头列表
        response_headers = []
        response_headers.append(("Server", server_info))
        response_headers.append(("X-Content-Type-Options", "nosniff"))
        response_headers.append(("X-Frame-Options", "SAMEORIGIN"))
        response_headers.append(("X-XSS-Protection", "1; mode=block"))

        # 添加 self._headers 中的内容
        if hasattr(self, '_headers'):
            response_headers.extend(self._headers)

        # 添加传入的 headers 参数
        if headers:
            response_headers.extend(headers)

        # 保存 Session 数据到 Session 存储（只有在会话被修改且已加载时）
        app = self._app
        session_key = None
        if hasattr(self, '_session_loaded') and self._session_loaded:
            session_key = self._session_id or self.session.id
            if self._session_modified:
                app.sessions.put(session_key, self.session)
        elif self._session_id or self._session:
            # 对于没有 _session_loaded 属性的旧版本，保持兼容
            session_key = self._session_id or self.session.id
            if self._session_modified:
                app.sessions.put(session_key, self.session)

        # 设置 session cookie（只有在会话已加载时）
        if session_key:
            session_name = self._app.config.session_name
            session_secure = self._app.config.session_secure
            session_http_only = self._app.config.session_http_only
            session_same_site = self._app.config.session_same_site
            cookie_header = SimpleCookie()
            cookie_header[session_name] = session_key
            cookie_header[session_name]['path'] = "/"
            if session_secure:
                cookie_header[session_name]['secure'] = True
            if session_http_only:
                cookie_header[session_name]['httponly'] = True
            if session_same_site:
                cookie_header[session_name]['samesite'] = session_same_site
            response_headers.append(("Set-Cookie", str(cookie_header[session_name])))

        # 检查是否已经有 Content-Type 响应头
        has_content_type = any(h[0].lower() == 'content-type' for h in response_headers)

        # 如果没有 Content-Type 响应头，根据状态码和内容类型设置默认的 Content-Type
        if not has_content_type:
            if status_code >= 400:
                response_headers.append(("Content-Type", "text/html; charset=utf-8"))
            else:
                from collections.abc import Iterable

                # 优先检查字符串和字节类型，设置为 text/plain
                if isinstance(content, (str, bytes)):
                    response_headers.append(("Content-Type", "text/plain; charset=utf-8"))
                # 检查可迭代对象（如生成器）
                elif not isinstance(content, (dict, list, tuple, type(None))) and isinstance(content, Iterable):
                    response_headers.append(("Content-Type", "text/plain; charset=utf-8"))
                # dict 类型设置为 application/json
                elif isinstance(content, dict):
                    response_headers.append(("Content-Type", "application/json; charset=utf-8"))
                # list/tuple 类型设置为 application/json
                elif isinstance(content, (list, tuple)):
                    response_headers.append(("Content-Type", "application/json; charset=utf-8"))
                # 其他类型使用默认的 application/json
                else:
                    response_headers.append(("Content-Type", default_content_type))

        # 标记响应头已发送
        self._headers_responsed = True

        # 如果 content 为 None，设置默认的错误信息
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                "code": status_code,
                "message": status_text,
                "explain": status_text,
            }

        # 检查是否已经有 Content-Length 或 Transfer-Encoding 头
        has_content_length = any(h[0].lower() == 'content-length' for h in response_headers)
        has_transfer_encoding = any(h[0].lower() == 'transfer-encoding' for h in response_headers)

        # 处理不同类型的 content
        from collections.abc import Iterable
        if not has_content_length and not has_transfer_encoding:
            if isinstance(content, (str, bytes)):
                # 对于字符串或字节，计算长度并添加 Content-Length 头
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                    content_length = len(content_bytes)
                else:
                    content_length = len(content)
                response_headers.append(("Content-Length", str(content_length)))
            elif not isinstance(content, (dict, list, tuple, type(None))) and isinstance(content, Iterable):
                # 对于生成器等可迭代对象，使用 Transfer-Encoding: chunked
                response_headers.append(("Transfer-Encoding", "chunked"))

        # 返回响应
        return status, response_headers, content

    def _add_response_headers(self, headers):
        raise NotImplementedError("Subclasses must implement _add_response_headers")

    def set_cookie(self, key, value, **kwargs):
        raise NotImplementedError("Subclasses must implement set_cookie")

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def get(self):
        return self._get

    @property
    def post(self):
        return self._post

    @property
    def body(self):
        return self._body

    @property
    def files(self):
        return self._files

    @property
    def form(self):
        """
        表单数据，与 post 属性相同

        Returns:
            表单数据字典
        """
        return self._post

    @property
    def app(self):
        """
        获取应用实例

        Returns:
            应用实例
        """
        return self._app


class WSGIRequestHandler(BaseRequestHandler):
    """
    WSGI 请求处理器，用于在 gunicorn、uWSGI 等 WSGI 服务器中运行

    符合 PEP 3333 规范，处理 WSGI environ 并返回标准响应
    """

    def __init__(self, app, environ):
        super(WSGIRequestHandler, self).__init__(app, environ)
        self._environ = self._normalize_environ(environ)
        self._headers = []
        self._get = parse_form(self._environ.get("QUERY_STRING", ""))

        content_type = self._environ.get("CONTENT_TYPE", "")
        if content_type:
            content_type_raw = content_type
            content_type, params = parse_header(content_type)
            content_length_str = self._environ.get("CONTENT_LENGTH") or "0"
            content_length = int(content_length_str) if content_length_str.strip() else 0

            if content_length > 0:
                max_request_size = getattr(app.config, "max_request_size", 10485760)
                if content_length > max_request_size:
                    raise HttpError(
                        413, f"Request body too large. Maximum size is {max_request_size} bytes"
                    )

            if content_type_raw == "application/x-www-form-urlencoded":
                if content_length > 0:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        post_content = wsgi_input.read(content_length)
                        post_content = post_content.decode("utf-8")
                        self._post = parse_form(post_content)
            elif content_type_raw.startswith("multipart/form-data"):
                boundary = params.get("boundary")
                if boundary:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        content_length_str = self._environ.get("CONTENT_LENGTH") or "0"
                        content_length = (
                            int(content_length_str) if content_length_str.strip() else 0
                        )
                        if content_length > 0:
                            self._parse_multipart(wsgi_input, boundary, content_length)
            else:
                if content_length > 0:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        self._body = wsgi_input.read(content_length)
                        self._body = self._body.decode("utf-8")

        self._session_id, self._session = self._get_session()
        self._middlewares = app._get_middleware_instances()

    def _normalize_environ(self, environ):
        normalized = dict(environ)

        if "PATH_INFO" not in normalized:
            normalized["PATH_INFO"] = "/"

        if "REQUEST_METHOD" not in normalized:
            normalized["REQUEST_METHOD"] = "GET"

        if "QUERY_STRING" not in normalized:
            normalized["QUERY_STRING"] = ""

        if "CONTENT_LENGTH" not in normalized:
            normalized["CONTENT_LENGTH"] = "0"
        else:
            content_length = normalized.get("CONTENT_LENGTH", "0")
            if content_length == "" or content_length is None:
                normalized["CONTENT_LENGTH"] = "0"

        if "CONTENT_TYPE" not in normalized:
            normalized["CONTENT_TYPE"] = ""

        if "HTTP_HOST" not in normalized:
            host = normalized.get("SERVER_NAME", "localhost")
            port = normalized.get("SERVER_PORT", "80")
            if port != "80":
                normalized["HTTP_HOST"] = "%s:%s" % (host, port)
            else:
                normalized["HTTP_HOST"] = host

        return normalized

    def _parse_multipart(self, wsgi_input, boundary, content_length):
        app = self._app
        max_upload_size = getattr(app.config, "max_upload_size", 52428800)

        if content_length > max_upload_size:
            raise HttpError(413, f"Request body too large. Maximum size is {max_upload_size} bytes")

        boundary = boundary.encode("utf-8")
        begin_boundary = b"--" + boundary
        end_boundary = b"--" + boundary + b"--"

        posts = {}
        files = {}

        data = wsgi_input.read(content_length)

        parts = data.split(begin_boundary)

        for part in parts[1:]:
            if part.strip() == end_boundary:
                break

            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue

            headers_part = part[:header_end]
            content = part[header_end + 4 :]

            headers = {}
            for line in headers_part.split(b"\r\n"):
                if b":" in line:
                    k, v = line.split(b":", 1)
                    k = k.strip().upper()
                    v = v.strip()
                    k = k.decode("utf-8")
                    v = v.decode("utf-8")
                    headers[k] = v

            disposition = headers.get("CONTENT-DISPOSITION", "")
            disposition, params = parse_header(disposition)
            name = params.get("name", "")

            filename = params.get("filename")
            if filename:
                fp = TemporaryFile(mode="w+b")
                fp.write(content)
                fp.seek(0)
                files[name] = fp
            else:
                content = content.decode("utf-8")
                posts[name] = content.strip()

        self._post = posts
        self._files = files

    def _get_session(self):
        app = self._app
        sessions = app.sessions
        session_name = app.config.session_name
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie(cookie_str)
        morsel = cookie.get(session_name)
        if morsel is not None:
            session_id = morsel.value
            session = sessions.get(session_id)
            if session is not None:
                # 设置存储后端实例，确保数据修改时自动保存
                session.store = sessions
                return session_id, session

        session_id = self._new_session_id()
        # 创建 Session 对象时传入存储后端实例
        session = Session(session_id, store=sessions)
        sessions.put(session_id, session)
        return None, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    @property
    def config(self):
        return self._app.config

    @property
    def files(self):
        return self._files or {}

    @property
    def body(self):
        return self._body

    @property
    def json(self):
        body = self._body
        if not body:
            return {}
        content_type = self._environ.get("CONTENT_TYPE", "")
        content_type, _ = parse_header(content_type)
        content_type = content_type.lower()
        if content_type not in ("application/json", "application/json-rpc"):
            return {}
        return json.loads(body)

    @property
    def environ(self):
        return self._environ

    @property
    def params(self):
        return self._get

    @property
    def data(self):
        return self._post

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def request_method(self):
        return self._environ.get("REQUEST_METHOD", "GET")

    method = request_method

    @property
    def server_protocol(self):
        return self._environ.get("SERVER_PROTOCOL", "HTTP/1.1")

    @property
    def content_type(self):
        return self._environ.get("CONTENT_TYPE")

    @property
    def charset(self, default="UTF-8"):
        content_type = self.content_type
        if content_type:
            _, params = parse_header(content_type)
            return params.get("charset", default)
        return default

    @property
    def content_length(self):
        return int(self._environ.get("CONTENT_LENGTH", 0) or 0)

    @property
    def path_info(self):
        return self._environ.get("PATH_INFO", "/")

    @property
    def query_string(self):
        return self._environ.get("QUERY_STRING", "")

    @property
    def request_uri(self):
        path_info = self.path_info
        query_string = self.query_string
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self._environ.get("HTTP_REFERER")

    @property
    def cookie(self):
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def _add_header(self, key, value):
        self._headers.append((key, value))

    def _add_response_headers(self, headers):
        headers.extend(self._headers)

    def set_cookie(self, key, value, **kwargs):
        cookie = SimpleCookie()
        cookie[key] = value
        for k, v in kwargs.items():
            if not v:
                continue
            cookie[key][k] = v
        self._headers.append(("Set-Cookie", str(cookie[key])))

    def handler(self):
        app = self._app

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
            if isinstance(middleware_result, Response):
                return self.handle_response(middleware_result)
            return middleware_result

        try:
            environ = self._environ
            path_info = environ.get("PATH_INFO", "/")
            request_method = environ.get("REQUEST_METHOD", "GET")

            # 尝试使用路由系统处理请求
            route_match = app.router.match(path_info, request_method)
            if route_match:
                handler, params = route_match
                try:
                    # 将路由参数添加到请求对象
                    setattr(self, 'route_params', params)
                    result = handler(self, **params)
                    
                    # 处理 Response 对象
                    if isinstance(result, Response):
                        # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                        app = self._app
                        session_key = self._session_id or self.session.id
                        if self._session_modified:
                            app.sessions.put(session_key, self.session)

                        # 设置 session cookie（每次都设置，确保 cookie 不会丢失）
                        session_name = app.config.session_name
                        session_secure = app.config.session_secure
                        session_http_only = app.config.session_http_only
                        session_same_site = app.config.session_same_site
                        cookie_header = SimpleCookie()
                        cookie_header[session_name] = session_key
                        cookie_header[session_name]['path'] = "/"
                        if session_secure:
                            cookie_header[session_name]['secure'] = True
                        if session_http_only:
                            cookie_header[session_name]['httponly'] = True
                        if session_same_site:
                            cookie_header[session_name]['samesite'] = session_same_site
                        result.headers.append(("Set-Cookie", str(cookie_header[session_name])))
                        
                        status_code = result.status_code
                        status_text = http_status_codes.get(status_code, "Unknown")
                        status = "%d %s" % (status_code, status_text)
                        return app.middleware_manager.process_response(
                            self, (status, result.headers, result.content)
                        )
                    
                    if self._headers_responsed:
                        # 保存 Session 数据到 Session 存储
                        app = self._app
                        session_key = self._session_id or self.session.id
                        app.sessions.put(session_key, self.session)

                        # 设置 session cookie（每次都设置，确保 cookie 不会丢失）
                        session_name = app.config.session_name
                        session_secure = app.config.session_secure
                        session_http_only = app.config.session_http_only
                        session_same_site = app.config.session_same_site
                        self.set_cookie(session_name, session_key, path="/", secure=session_secure, httponly=session_http_only, samesite=session_same_site)

                        status_code = int(self._status_code)
                        status_text = http_status_codes.get(status_code, "Unknown")
                        status = "%d %s" % (status_code, status_text)

                        response_headers = [("Server", server_info)]
                        response_headers.extend(self._headers)

                        return app.middleware_manager.process_response(
                            self, (status, response_headers, result)
                        )
                    return app.middleware_manager.process_response(
                        self, self._response(200, content=result)
                    )
                except Exception:
                    log_error(app.logger)
                    if app.config.debug:
                        content = render_error()
                        return app.middleware_manager.process_response(
                            self, self._response(500, content=content)
                        )
                    return app.middleware_manager.process_response(self, self._response(500))

            # 路由未匹配，返回 404
            return app.middleware_manager.process_response(self, self._response(404))
        except Exception as e:
            middleware_result = app.middleware_manager.process_exception(self, e)
            if middleware_result is not None:
                return middleware_result
            raise
    def _redirect(self, url):
        url = "/" if url is None else url
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Location", url)]
        status_code = 302
        status_text = http_status_codes.get(status_code, "Found")
        content = "%d %s" % (status_code, status_text)
        return self._response(status_code, headers=headers, content=content)


class ASGIRequestHandler(BaseRequestHandler):
    """
    ASGI 请求处理器，用于在 uvicorn、daphne 等 ASGI 服务器中运行

    符合 ASGI 3.0 规范，处理 ASGI scope、receive 和 send 并返回标准响应
    """

    def __init__(self, app, scope, receive, send):
        # 构建 environ 字典
        environ = {
            'ASGI_SCOPE': scope,
            'ASGI_RECEIVE': receive,
            'ASGI_SEND': send,
            'REQUEST_METHOD': scope['method'],
            'PATH_INFO': scope['path'],
            'QUERY_STRING': scope.get('query_string', b'').decode('utf-8'),
            'SERVER_NAME': scope['server'][0],
            'SERVER_PORT': str(scope['server'][1]),
            'REMOTE_ADDR': scope['client'][0],
            'REMOTE_PORT': str(scope['client'][1]),
            'SERVER_PROTOCOL': f'HTTP/{scope.get("http_version", "1.1")}',
        }
        
        # 处理 headers
        headers = scope.get('headers', [])
        for name, value in headers:
            name = name.decode('utf-8').upper().replace('-', '_')
            if name not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                name = f'HTTP_{name}'
            environ[name] = value.decode('utf-8')
        
        super(ASGIRequestHandler, self).__init__(app, environ)
        self._scope = scope
        self._receive = receive
        self._send = send
        self._headers = []
        self._get = parse_form(self._environ.get("QUERY_STRING", ""))
        self._body = None
        self._post = None
        self._files = None

        # 延迟处理请求体，在需要时异步处理
        self._content_type = self._environ.get("CONTENT_TYPE", "")
        self._content_type_raw = self._content_type
        if self._content_type:
            self._content_type, self._params = parse_header(self._content_type)
        else:
            self._params = {}

        # 延迟加载会话，只在需要时获取
        self._session_id = None
        self._session = None
        self._session_loaded = False
        # 缓存中间件实例，避免重复创建
        self._middlewares = app._get_middleware_instances()
    
    async def _process_request_body(self):
        """
        异步处理请求体
        """
        if not self._content_type:
            return
        
        # 检查是否已经处理过请求体
        if self._body is not None or self._post is not None:
            return
        
        # 异步读取请求体
        body = await self._read_body()
        
        if not body:
            return
        
        content_length = len(body)
        max_request_size = getattr(self._app.config, "max_request_size", 10485760)
        if content_length > max_request_size:
            raise HttpError(
                413, f"Request body too large. Maximum size is {max_request_size} bytes"
            )

        if self._content_type_raw == "application/x-www-form-urlencoded":
            post_content = body.decode("utf-8")
            self._post = parse_form(post_content)
        elif self._content_type_raw.startswith("multipart/form-data"):
            boundary = self._params.get("boundary")
            if boundary:
                self._parse_multipart(body, boundary)
        else:
            self._body = body.decode("utf-8")

    async def _read_body(self):
        """
        异步读取请求体
        """
        # 使用字节缓冲区，减少字符串拼接开销
        import io
        body_buffer = io.BytesIO()
        
        while True:
            message = await self._receive()
            if message['type'] == 'http.request':
                body = message.get('body', b'')
                if body:
                    body_buffer.write(body)
                if not message.get('more_body', False):
                    break
        
        return body_buffer.getvalue()

    def _parse_multipart(self, body, boundary):
        app = self._app
        max_upload_size = getattr(app.config, "max_upload_size", 52428800)

        if len(body) > max_upload_size:
            raise HttpError(413, f"Request body too large. Maximum size is {max_upload_size} bytes")

        boundary = boundary.encode("utf-8")
        begin_boundary = b"--" + boundary
        end_boundary = b"--" + boundary + b"--"

        posts = {}
        files = {}

        parts = body.split(begin_boundary)

        for part in parts[1:]:
            if part.strip() == end_boundary:
                break

            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue

            headers_part = part[:header_end]
            content = part[header_end + 4 :]

            headers = {}
            for line in headers_part.split(b"\r\n"):
                if b":" in line:
                    k, v = line.split(b":", 1)
                    k = k.strip().upper()
                    v = v.strip()
                    k = k.decode("utf-8")
                    v = v.decode("utf-8")
                    headers[k] = v

            disposition = headers.get("CONTENT-DISPOSITION", "")
            disposition, params = parse_header(disposition)
            name = params.get("name", "")

            filename = params.get("filename")
            if filename:
                fp = TemporaryFile(mode="w+b")
                fp.write(content)
                fp.seek(0)
                files[name] = fp
            else:
                content = content.decode("utf-8")
                posts[name] = content.strip()

        self._post = posts
        self._files = files

    def _get_session(self):
        app = self._app
        sessions = app.sessions
        session_name = app.config.session_name
        
        # 从 headers 中获取 cookie
        cookie_str = ""
        headers = self._scope.get('headers', [])
        for name, value in headers:
            if name.decode('utf-8').lower() == 'cookie':
                cookie_str = value.decode('utf-8')
                break
        
        # 尝试从 cookie 中获取会话
        if cookie_str:
            cookie = SimpleCookie(cookie_str)
            morsel = cookie.get(session_name)
            if morsel is not None:
                session_id = morsel.value
                # 尝试从会话存储中获取会话
                session = sessions.get(session_id)
                if session is not None:
                    # 设置存储后端实例，确保数据修改时自动保存
                    session.store = sessions
                    return session_id, session

        # 生成新的会话 ID
        session_id = self._new_session_id()
        # 创建 Session 对象时传入存储后端实例
        session = Session(session_id, store=sessions)
        # 只在需要时才保存会话
        self._session_modified = False
        return None, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    @property
    def config(self):
        return self._app.config

    @property
    def files(self):
        return self._files or {}

    @property
    def body(self):
        return self._body

    @property
    def json(self):
        body = self._body
        if not body:
            return {}
        content_type = self._environ.get("CONTENT_TYPE", "")
        content_type, _ = parse_header(content_type)
        content_type = content_type.lower()
        if content_type not in ("application/json", "application/json-rpc"):
            return {}
        return json.loads(body)

    @property
    def environ(self):
        return self._environ

    @property
    def params(self):
        return self._get

    @property
    def data(self):
        return self._post

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def request_method(self):
        return self._environ.get("REQUEST_METHOD", "GET")

    method = request_method

    @property
    def server_protocol(self):
        return self._environ.get("SERVER_PROTOCOL", "HTTP/1.1")

    @property
    def content_type(self):
        return self._environ.get("CONTENT_TYPE")

    @property
    def charset(self, default="UTF-8"):
        content_type = self.content_type
        if content_type:
            _, params = parse_header(content_type)
            return params.get("charset", default)
        return default

    @property
    def content_length(self):
        return int(self._environ.get("CONTENT_LENGTH", 0) or 0)

    @property
    def path_info(self):
        return self._environ.get("PATH_INFO", "/")

    @property
    def query_string(self):
        return self._environ.get("QUERY_STRING", "")

    @property
    def request_uri(self):
        path_info = self.path_info
        query_string = self.query_string
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self._environ.get("HTTP_REFERER")

    @property
    def cookie(self):
        cookie_str = ""
        headers = self._scope.get('headers', [])
        for name, value in headers:
            if name.decode('utf-8').lower() == 'cookie':
                cookie_str = value.decode('utf-8')
                break
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def _add_header(self, key, value):
        self._headers.append((key, value))

    def _add_response_headers(self, headers):
        headers.extend(self._headers)

    def set_cookie(self, key, value, **kwargs):
        cookie = SimpleCookie()
        cookie[key] = value
        for k, v in kwargs.items():
            if not v:
                continue
            cookie[key][k] = v
        self._headers.append(("Set-Cookie", str(cookie[key])))

    async def handler(self):
        """
        异步处理请求
        """
        app = self._app

        # 处理请求体
        await self._process_request_body()

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
            return middleware_result

        try:
            environ = self._environ
            path_info = environ.get("PATH_INFO", "/")
            request_method = environ.get("REQUEST_METHOD", "GET")

            # 尝试使用路由系统处理请求
            route_match = app.router.match(path_info, request_method)
            if route_match:
                handler, params = route_match
                try:
                    # 将路由参数添加到请求对象
                    setattr(self, 'route_params', params)
                    
                    # 处理同步和异步处理器
                    import asyncio
                    if asyncio.iscoroutinefunction(handler):
                        result = await handler(self, **params)
                    else:
                        result = handler(self, **params)
                    
                    # 处理 Response 对象
                    if isinstance(result, Response):
                        # 确保会话已加载
                        session_key = None
                        if self._session_loaded:
                            # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                            if self._session_modified:
                                session_key = self._session_id or self.session.id
                                app.sessions.put(session_key, self.session)
                            else:
                                session_key = self._session_id or self.session.id
                        else:
                            # 会话未加载，不需要设置 cookie
                            pass

                        # 设置 session cookie（只有在会话已加载时）
                        if session_key:
                            session_name = app.config.session_name
                            session_secure = app.config.session_secure
                            session_http_only = app.config.session_http_only
                            session_same_site = app.config.session_same_site
                            cookie_header = SimpleCookie()
                            cookie_header[session_name] = session_key
                            cookie_header[session_name]['path'] = "/"
                            if session_secure:
                                cookie_header[session_name]['secure'] = True
                            if session_http_only:
                                cookie_header[session_name]['httponly'] = True
                            if session_same_site:
                                cookie_header[session_name]['samesite'] = session_same_site
                            result.headers.append(("Set-Cookie", str(cookie_header[session_name])))
                        
                        status_code = result.status_code
                        status_text = http_status_codes.get(status_code, "Unknown")
                        status = "%d %s" % (status_code, status_text)
                        return app.middleware_manager.process_response(
                            self, (status, result.headers, result.content)
                        )
                    
                    if self._headers_responsed:
                        # 确保会话已加载
                        session_key = None
                        if self._session_loaded:
                            # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                            if self._session_modified:
                                session_key = self._session_id or self.session.id
                                app.sessions.put(session_key, self.session)
                            else:
                                session_key = self._session_id or self.session.id

                        # 设置 session cookie（只有在会话已加载时）
                        if session_key:
                            session_name = app.config.session_name
                            session_secure = app.config.session_secure
                            session_http_only = app.config.session_http_only
                            session_same_site = app.config.session_same_site
                            self.set_cookie(session_name, session_key, path="/", secure=session_secure, httponly=session_http_only, samesite=session_same_site)

                        status_code = int(self._status_code)
                        status_text = http_status_codes.get(status_code, "Unknown")
                        status = "%d %s" % (status_code, status_text)

                        response_headers = [("Server", server_info)]
                        response_headers.extend(self._headers)

                        return app.middleware_manager.process_response(
                            self, (status, response_headers, result)
                        )
                    
                    # 确保会话已加载
                    session_key = None
                    if self._session_loaded:
                        # 保存 Session 数据到 Session 存储（只有在会话被修改时）
                        if self._session_modified:
                            session_key = self._session_id or self.session.id
                            app.sessions.put(session_key, self.session)
                        else:
                            session_key = self._session_id or self.session.id

                    # 设置 session cookie（只有在会话已加载时）
                    if session_key:
                        session_name = app.config.session_name
                        session_secure = app.config.session_secure
                        session_http_only = app.config.session_http_only
                        session_same_site = app.config.session_same_site
                        self.set_cookie(session_name, session_key, path="/", secure=session_secure, httponly=session_http_only, samesite=session_same_site)
                    
                    return app.middleware_manager.process_response(
                        self, self._response(200, content=result)
                    )
                except Exception:
                    log_error(app.logger)
                    if app.config.debug:
                        content = render_error()
                        return app.middleware_manager.process_response(
                            self, self._response(500, content=content)
                        )
                    return app.middleware_manager.process_response(self, self._response(500))

            # 路由未匹配，返回 404
            return app.middleware_manager.process_response(self, self._response(404))
        except Exception as e:
            middleware_result = app.middleware_manager.process_exception(self, e)
            if middleware_result is not None:
                return middleware_result
            raise
    async def _redirect(self, url):
        url = "/" if url is None else url
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Location", url)]
        status_code = 302
        status_text = http_status_codes.get(status_code, "Found")
        content = "%d %s" % (status_code, status_text)
        return self._response(status_code, headers=headers, content=content)


class RequestHandler(BaseRequestHandler):

    default_headers = {
        "Content-Type": default_content_type,
        "Server": "litefs/0.5.0",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "SAMEORIGIN",
        "X-XSS-Protection": "1; mode=block"
    }

    def __init__(self, app, rw, environ, request):
        super(RequestHandler, self).__init__(app, environ)
        self._request = request
        self._rw = rw
        self._buffers = StringIO()
        self._response_headers = {}
        self._headers = []  # 显式初始化 _headers 属性，确保它存在
        self._cookies = None
        self._get = parse_form(environ["QUERY_STRING"])
        content_type = environ.get("CONTENT_TYPE", "")
        self.content_type_raw = content_type_raw = content_type
        content_type, content_type_params = parse_header(content_type)
        self._post = {}
        self._body = ""
        self._files = {}
        # 读取请求体并设置到 POST_CONTENT
        if content_type:
            content_length_value = environ.get("CONTENT_LENGTH") or 0
            content_length = int(content_length_value) if content_length_value else 0

            if content_length > 0:
                max_request_size = getattr(app.config, "max_request_size", 10485760)
                if content_length > max_request_size:
                    raise HttpError(
                        413, f"Request body too large. Maximum size is {max_request_size} bytes"
                    )
            if content_length:
                if content_type_raw == "application/x-www-form-urlencoded":
                    post_content = rw.read(int(content_length))
                    self._post = parse_form(post_content)
                    self._body = post_content
                elif content_type_raw.startswith("multipart/form-data"):
                    boundary = content_type_params.get("boundary", None)
                    self._post, self._files = self._parse_multipart(rw, boundary)
                else:
                    post_content = rw.read(int(content_length))
                    environ["POST_CONTENT"] \
                        = unquote_plus(post_content.decode("utf-8"))
                    self._body = post_content
        self._session_id, self._session = self._get_session(environ)
        self._middlewares = app._get_middleware_instances()

    def _parse_multipart(self, rw, boundary):
        boundary = boundary.encode("utf-8")
        begin_boundary = b"--%s" % boundary
        end_boundary = b"--%s--" % boundary
        posts = {}
        files = {}
        s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
        while True:
            if s.strip() != begin_boundary:
                assert s.strip() == end_boundary
                break
            headers = {}
            s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
            while s:
                s = s.decode("utf-8")
                k, v = s.split(":", 1)
                headers[k.strip().upper()] = v.strip()
                s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
            disposition = headers["CONTENT-DISPOSITION"]
            disposition, params = parse_header(disposition)
            name = params["name"]
            filename = params.get("filename")
            if filename:
                fp = TemporaryFile(mode="w+b")
                s = rw.readline(DEFAULT_BUFFER_SIZE)
                while s.strip() != begin_boundary and s.strip() != end_boundary:
                    fp.write(s)
                    s = rw.readline(DEFAULT_BUFFER_SIZE)
                fp.seek(0)
                files[name] = fp
            else:
                fp = StringIO()
                s = rw.readline(DEFAULT_BUFFER_SIZE)
                while s.strip() != begin_boundary and s.strip() != end_boundary:
                    fp.write(s)
                    s = rw.readline(DEFAULT_BUFFER_SIZE)
                fp.seek(0)
                posts[name] = fp.getvalue().strip().decode("utf-8")
        return posts, files

    def _get_session(self, environ):
        app = self._app
        sessions = app.sessions
        session_name = app.config.session_name
        cookie = environ.get("HTTP_COOKIE")
        cookie = SimpleCookie(cookie)
        morsel = cookie.get(session_name)
        if morsel is not None:
            session_id = morsel.value
            session = sessions.get(session_id)
            if session is not None:
                # 设置存储后端实例，确保数据修改时自动保存
                session.store = sessions
                return session_id, session
        
        session_id = self._new_session_id()
        # 创建 Session 对象时传入存储后端实例
        session = Session(session_id, store=sessions)
        sessions.put(session_id, session)
        return None, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    @property
    def config(self):
        return self._app.config

    @property
    def files(self):
        return self._files or {}

    @property
    def body(self):
        return self._body

    @property
    def json(self):
        body = self._body
        if not self._body:
            return {}
        content_type = self.content_type
        content_type, _ = parse_header(content_type)
        content_type = content_type.lower()
        if content_type not in ("application/json", "application/json-rpc"):
            return {}
        return json.loads(body)

    @property
    def environ(self):
        return self._environ

    @property
    def params(self):
        return self._get

    @property
    def data(self):
        return self._post

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def request_method(self):
        return self.environ["REQUEST_METHOD"]

    method = request_method

    @property
    def server_protocol(self):
        return self.environ["SERVER_PROTOCOL"]

    @property
    def content_type(self):
        return self.environ.get("CONTENT_TYPE")

    @property
    def charset(self, default="UTF-8"):
        _, params = parse_header(self.content_type)
        return params.get("charset", default)

    @property
    def content_length(self):
        return int(self.environ.get("CONTENT_LENGTH") or -1)

    @property
    def path_info(self):
        return self.environ["PATH_INFO"]

    @property
    def query_string(self):
        return self.environ["QUERY_STRING"]

    @property
    def request_uri(self):
        environ = self.environ
        path_info = environ["PATH_INFO"]
        query_string = environ["QUERY_STRING"]
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self.environ.get("HTTP_REFERER")

    @property
    def cookie(self):
        cookie_str = self.environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def _add_header(self, key, value):
        # 添加到 _response_headers 字典中
        response_headers = self._response_headers
        response_headers[key] = value

    def _add_response_headers(self, headers):
        for header, value in headers:
            self._response_headers[header] = value

    def set_cookie(self, name, value, **options):
        if self._cookies is None:
            self._cookies = {}
        cookie = SimpleCookie()
        cookie[name] = value
        for key, val in options.items():
            # 将下划线参数转换为连字符形式（如 max_age -> max-age）
            cookie_key = key.replace('_', '-')
            cookie[name][cookie_key] = val
        self._cookies[name] = cookie

    def redirect(self, url=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        url = "/" if url is None else url
        response_headers = self._response_headers
        response_headers["Content-Type"] = "text/html;charset=utf-8"
        host = self._environ.get("HTTP_HOST")
        if not host:
            server_name = self._environ.get("SERVER_NAME", "localhost")
            server_port = self._environ.get("SERVER_PORT", "80")
            if server_port not in ("80", "443"):
                host = "%s:%s" % (server_name, server_port)
            else:
                host = server_name
        scheme = (
            "https"
            if self._environ.get("HTTPS") == "on" or self._environ.get("SERVER_PORT") == "443"
            else "http"
        )
        response_headers["Location"] = "%s://%s%s" % (scheme, host, url)
        status_code = 302
        status_text = http_status_codes[status_code]
        content = "%d %s" % (status_code, status_text)
        headers = response_headers.items()
        self.start_response(status_code, headers=headers)
        return content

    def _cast(self, s=None):
        response_headers = self._response_headers
        
        if not s:
            if "Content-Length" not in response_headers:
                response_headers["Content-Length"] = 0
            return []

        # 对于 3xx 重定向响应，设置 Content-Type 为 text/html; charset=utf-8
        if 300 <= self._status_code < 400:
            response_headers["Content-Type"] = "text/html; charset=utf-8"
            # 直接返回空字符串，不需要转换为 JSON 格式
            return [b""]

        content_type = response_headers.get("Content-Type", "")
        is_json_response = "application/json" in content_type

        # 先处理 dict 类型（dict 是 Iterable 但需要特殊处理）
        if isinstance(s, dict):
            if is_json_response:
                import json
                try:
                    s = json.dumps(s, ensure_ascii=False)
                except (TypeError, ValueError) as e:
                    raise TypeError("Response data cannot be JSON serialized: %s" % e)
            else:
                s = str(s)
        
        # 先检查是否是可迭代对象（但不是字符串、字节、元组、列表或字典）
        from collections.abc import Iterable
        if not isinstance(s, (str, bytes, tuple, list, dict, type(None))) and isinstance(s, Iterable):
            try:
                iter_s = iter(s)
                first = next(iter_s)
                while not first:
                    first = next(iter_s)
            except StopIteration:
                return self._cast()
            if is_bytes(first):
                new_iter_s = itertools.chain([first], iter_s)
            elif isinstance(first, str):
                encoder = lambda item: str(item).encode("utf-8")
                new_iter_s = itertools.chain([first], iter_s)
                new_iter_s = imap(encoder, new_iter_s)
            else:
                raise TypeError("response type is not allowd: %s" % type(first))
            return new_iter_s

        if isinstance(s, (tuple, list)):
            if is_json_response:
                import json

                s = [json.dumps(item, ensure_ascii=False) for item in s]
                s = "[" + ",".join(s) + "]"
            else:
                if len(s) > 0 and (isinstance(s[0], str) or is_bytes(s[0])):
                    first_type = type(s[0])
                    if isinstance(first_type, type) and issubclass(first_type, str):
                        s = [item if isinstance(item, str) else str(item) for item in s]
                        join_chr = s[0][:0]
                        s = join_chr.join(s)
                    else:
                        s = [item if is_bytes(item) else str(item).encode("utf-8") for item in s]
                        join_chr = s[0][:0]
                        s = join_chr.join(s)
                else:
                    s = [str(item) for item in s]
                    s = "".join(s)
        elif not (isinstance(s, str) or is_bytes(s)):
            if is_json_response:
                import json

                try:
                    s = json.dumps(s, ensure_ascii=False)
                except (TypeError, ValueError) as e:
                    raise TypeError("Response data cannot be JSON serialized: %s" % e)
            else:
                s = str(s)

        if isinstance(s, str):
            s = s.encode("utf-8")
        if is_bytes(s):
            if "Content-Length" not in response_headers:
                response_headers["Content-Length"] = len(s)
            return [s]
        return []
    
    def handle_response(self, result):
        """
        处理响应结果，支持 Response 对象
        """
        if isinstance(result, Response):
            self._status_code = result.status_code
            for header, value in result.headers:
                self._add_header(header, value)
            content = result.content
            if isinstance(content, dict):
                import json
                return json.dumps(content, ensure_ascii=False)
            return content
        return result

    def finish(self, content):
        try:
            rw = self._rw
            
            if (
                isinstance(content, (list, tuple))
                and len(content) == 3
                and isinstance(content[0], str)
                and isinstance(content[1], list)
            ):
                status_line, response_headers, response_content = content
                status_code = int(status_line.split()[0])
                status_text = http_status_codes.get(status_code, "Unknown")
                
                for header_name, header_value in response_headers:
                    if header_name.lower() == 'set-cookie':
                        if self._cookies is None:
                            self._cookies = {}
                        from http.cookies import SimpleCookie
                        cookie = SimpleCookie()
                        cookie.load(header_value)
                        for key, morsel in cookie.items():
                            self._cookies[key] = morsel
                    else:
                        self._response_headers[header_name] = header_value
                
                content = response_content
            else:
                status_code = self._status_code
                status_text = http_status_codes[status_code]
            
            line = "HTTP/1.1 %d %s\r\n" % (status_code, status_text)
            line = line.encode("utf-8")
            rw.write(line)
            headers = self._response_headers.copy()
            
            # 添加标准头部（如果不存在）
            standard_headers = {
                "Server": "litefs/0.4.0",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "SAMEORIGIN",
                "X-XSS-Protection": "1; mode=block"
            }
            
            for header, value in standard_headers.items():
                if header not in headers:
                    headers[header] = value
            
            # 如果没有 Content-Type 头部，添加默认值
            if "Content-Type" not in headers:
                # 对于 3xx 重定向响应，设置 Content-Type 为 text/html; charset=utf-8
                if 300 <= status_code < 400:
                    content_type_value = "text/html; charset=utf-8"
                else:
                    # 对于其他响应，检查是否是 HTML 内容
                    if isinstance(content, str) and content.startswith('<'):
                        content_type_value = "text/html; charset=utf-8"
                    else:
                        content_type_value = default_content_type
                headers["Content-Type"] = content_type_value
                self._response_headers["Content-Type"] = content_type_value
            
            # 检查是否已经有 Content-Length 或 Transfer-Encoding 头
            has_content_length = "Content-Length" in headers
            has_transfer_encoding = "Transfer-Encoding" in headers
            
            # 处理不同类型的 content
            from collections.abc import Iterable
            if not has_content_length and not has_transfer_encoding:
                if isinstance(content, (str, bytes)):
                    # 对于字符串或字节，计算长度并添加 Content-Length 头
                    if isinstance(content, str):
                        content_bytes = content.encode('utf-8')
                        content_length = len(content_bytes)
                    else:
                        content_length = len(content)
                    headers["Content-Length"] = str(content_length)
                elif not isinstance(content, (dict, list, tuple, type(None))) and isinstance(content, Iterable):
                    # 对于生成器等可迭代对象，使用 Transfer-Encoding: chunked
                    headers["Transfer-Encoding"] = "chunked"
            
            # 写入头部
            for header, value in headers.items():
                line = "%s: %s\r\n" % (header, value)
                line = line.encode("utf-8")
                rw.write(line)
            if self._cookies:
                for c in self._cookies.values():
                    # 直接使用 cookie 的输出，它已经包含了完整的 Set-Cookie 头部
                    line = str(c) + "\r\n"
                    line = line.encode("utf-8")
                    rw.write(line)
            rw.write("\r\n".encode("utf-8"))
            # 对于 3xx 重定向响应，直接返回空字符串，不需要转换为 JSON 格式
            if 300 <= status_code < 400:
                rw.write(b"")
            else:
                # 检查是否使用 chunked 编码
                if has_transfer_encoding and headers.get("Transfer-Encoding", "").lower() == "chunked":
                    # 使用 chunked 编码格式写入数据
                    for chunk in self._cast(content):
                        # 计算 chunk 长度并转换为十六进制
                        chunk_length = len(chunk)
                        # 写入 chunk 长度（十六进制）+ 回车换行
                        rw.write(f"{chunk_length:x}\r\n".encode("utf-8"))
                        # 写入 chunk 数据
                        rw.write(chunk)
                        # 写入回车换行
                        rw.write(b"\r\n")
                    # 写入结束 chunk
                    rw.write(b"0\r\n\r\n")
                else:
                    # 普通方式写入数据
                    for _ in self._cast(content):
                        rw.write(_)
            rw.close()
        except Exception:
            if not self._headers_responsed:
                try:
                    from ..utils import log_error, render_error

                    log_error(self._app.logger)
                    rw = self._rw
                    status_code = 500
                    status_text = http_status_codes[status_code]
                    line = "HTTP/1.1 %d %s\r\n" % (status_code, status_text)
                    line = line.encode("utf-8")
                    rw.write(line)
                    rw.write("Content-Type: text/html; charset=utf-8\r\n".encode("utf-8"))
                    rw.write("Server: litefs/0.4.0\r\n".encode("utf-8"))
                    rw.write("X-Content-Type-Options: nosniff\r\n".encode("utf-8"))
                    rw.write("X-Frame-Options: SAMEORIGIN\r\n".encode("utf-8"))
                    rw.write("X-XSS-Protection: 1; mode=block\r\n".encode("utf-8"))
                    rw.write("\r\n".encode("utf-8"))
                    if self._app.config.debug:
                        error_content = render_error()
                        if isinstance(error_content, str):
                            error_content = error_content.encode("utf-8")
                        rw.write(error_content)
                    else:
                        rw.write(b"500 Internal Server Error")
                    rw.close()
                except Exception:
                    pass
            else:
                try:
                    from ..utils import log_error

                    log_error(self._app.logger)
                except Exception:
                    pass
            raise

    def __del__(self):
        files = self._environ.get(FILES_HEADER_NAME)
        if not files:
            return
        for fp in files.values():
            fp.close()

    def _response(self, status_code, headers=None, content=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        status_code = int(status_code)
        status_text = http_status_codes[status_code]

        if headers is None:
            headers = []

        # 添加 self._response_headers 中的响应头
        existing_header_names = [h[0].lower() for h in headers]
        for header, value in self._response_headers.items():
            if header.lower() not in existing_header_names:
                headers.append((header, value))

        # 添加标准头部
        standard_headers = [
            ("Server", "litefs/0.4.0"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "SAMEORIGIN"),
            ("X-XSS-Protection", "1; mode=block")
        ]
        
        # 检查并添加标准头部，避免重复
        existing_header_names = [h[0].lower() for h in headers]
        for header in standard_headers:
            if header[0].lower() not in existing_header_names:
                headers.append(header)

        # 检查是否已经有 Content-Type 响应头
        has_content_type = any(h[0].lower() == 'content-type' for h in headers)
        
        if status_code >= 400:
            if not has_content_type:
                html_headers = [("Content-Type", "text/html; charset=utf-8")]
                headers = html_headers + list(headers)
        elif not has_content_type:
            from collections.abc import Iterable

            if not isinstance(content, (str, bytes, dict, list, tuple, type(None))) and isinstance(
                content, Iterable
            ):
                headers = [("Content-Type", "text/plain; charset=utf-8")] + list(headers)
            else:
                headers = [("Content-Type", default_content_type)] + list(headers)

        # 设置 session cookie
        if self.session_id is None:
            session_name = self._app.config.session_name
            session_secure = self._app.config.session_secure
            session_http_only = self._app.config.session_http_only
            session_same_site = self._app.config.session_same_site
            self.set_cookie(session_name, self.session.id, path="/", secure=session_secure, httponly=session_http_only, samesite=session_same_site)

        # 保存 Session 数据到 Session 存储
        app = self._app
        app.sessions.put(self.session.id, self.session)

        # 检查是否已经有 Content-Length 或 Transfer-Encoding 头
        has_content_length = any(h[0].lower() == 'content-length' for h in headers)
        has_transfer_encoding = any(h[0].lower() == 'transfer-encoding' for h in headers)
        
        # 处理不同类型的 content
        from collections.abc import Iterable
        if not has_content_length and not has_transfer_encoding:
            if isinstance(content, (str, bytes)):
                # 对于字符串或字节，计算长度并添加 Content-Length 头
                if isinstance(content, str):
                    content_bytes = content.encode('utf-8')
                    content_length = len(content_bytes)
                else:
                    content_length = len(content)
                headers.append(("Content-Length", str(content_length)))
            elif not isinstance(content, (dict, list, tuple, type(None))) and isinstance(content, Iterable):
                # 对于生成器等可迭代对象，使用 Transfer-Encoding: chunked
                headers.append(("Transfer-Encoding", "chunked"))

        self.start_response(status_code, headers=headers)
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                "code": status_code,
                "message": status_text,
                "explain": status_text,
            }
        return content

    def handler(self):
        app = self._app

        middleware_result = app.middleware_manager.process_request(self)
        if middleware_result is not None:
            content = self.handle_response(middleware_result)
            return app.middleware_manager.process_response(self, content)

        try:
            environ = self.environ
            path_info = environ["PATH_INFO"]
            request_method = environ["REQUEST_METHOD"]

            # 尝试使用路由系统处理请求
            route_match = app.router.match(path_info, request_method)
            if route_match:
                handler, params = route_match
                try:
                    # 将路由参数添加到请求对象
                    setattr(self, 'route_params', params)
                    result = handler(self, **params)
                    
                    # 处理 Response 对象
                    content = self.handle_response(result)
                    
                    if self._headers_responsed:
                        return app.middleware_manager.process_response(self, content)
                    return app.middleware_manager.process_response(
                        self, self._response(200, content=content)
                    )
                except Exception:
                    log_error(app.logger)
                    if app.config.debug:
                        content = render_error()
                        return app.middleware_manager.process_response(
                            self, self._response(500, content=content)
                        )
                    return app.middleware_manager.process_response(self, self._response(500))

            # 路由未匹配，返回 404
            return app.middleware_manager.process_response(self, self._response(404))
        except Exception as e:
            middleware_result = app.middleware_manager.process_exception(self, e)
            if middleware_result is not None:
                return middleware_result
            raise
