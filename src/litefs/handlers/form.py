#!/usr/bin/env python
# coding: utf-8

"""
表单数据解析模块

提供表单数据解析功能，支持 URL 编码表单和 multipart 表单
"""

import re
from tempfile import TemporaryFile
from urllib.parse import unquote_plus

from ..cache import FormCache
from email.message import Message


# 创建表单数据缓存实例
_form_cache = FormCache(max_size=1000, default_ttl=300)

# 正则表达式
form_dict_match = re.compile(r"(.+)\[([^\[\]]+)\]").match


def parse_header(line):
    """
    解析 HTTP 头部的 Content-Type 参数

    Args:
        line: HTTP Content-Type 头部值

    Returns:
        (mime_type, params_dict): MIME 类型和参数字典
    """
    msg = Message()
    msg["content-type"] = line
    return msg.get_params()[0][0], dict(msg.get_params()[1:])


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


def parse_multipart_wsgi(wsgi_input, boundary, content_length, max_upload_size=52428800):
    """
    解析 WSGI 环境下的 multipart 表单数据

    Args:
        wsgi_input: WSGI 输入流
        boundary: multipart boundary
        content_length: 内容长度
        max_upload_size: 最大上传大小

    Returns:
        (posts, files): 表单字段字典和上传文件字典
    """
    if content_length > max_upload_size:
        from ..exceptions import HttpError
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
        content = part[header_end + 4:]

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

    return posts, files


def parse_multipart_asgi(body, boundary, max_upload_size=52428800):
    """
    解析 ASGI 环境下的 multipart 表单数据

    Args:
        body: 请求体字节数据
        boundary: multipart boundary
        max_upload_size: 最大上传大小

    Returns:
        (posts, files): 表单字段字典和上传文件字典
    """
    if len(body) > max_upload_size:
        from ..exceptions import HttpError
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
        content = part[header_end + 4:]

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

    return posts, files


def parse_multipart_stream(rw, boundary, max_upload_size=52428800, DEFAULT_BUFFER_SIZE=8192):
    """
    解析流式环境下的 multipart 表单数据

    Args:
        rw: 读写流对象
        boundary: multipart boundary
        max_upload_size: 最大上传大小
        DEFAULT_BUFFER_SIZE: 默认缓冲区大小

    Returns:
        (posts, files): 表单字段字典和上传文件字典
    """
    from io import DEFAULT_BUFFER_SIZE as _DEFAULT_BUFFER_SIZE
    from io import StringIO

    boundary = boundary.encode("utf-8")
    begin_boundary = b"--%s" % boundary
    end_boundary = b"--%s--" % boundary
    posts = {}
    files = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE).strip()
    while True:
        if s.strip() != begin_boundary:
            assert s.strip() == end_boundary
            break
        headers = {}
        s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE).strip()
        while s:
            s = s.decode("utf-8")
            k, v = s.split(":", 1)
            headers[k.strip().upper()] = v.strip()
            s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE).strip()
        disposition = headers["CONTENT-DISPOSITION"]
        disposition, params = parse_header(disposition)
        name = params["name"]
        filename = params.get("filename")
        if filename:
            fp = TemporaryFile(mode="w+b")
            s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE)
            while s.strip() != begin_boundary and s.strip() != end_boundary:
                fp.write(s)
                s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE)
            fp.seek(0)
            files[name] = fp
        else:
            fp = StringIO()
            s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE)
            while s.strip() != begin_boundary and s.strip() != end_boundary:
                fp.write(s)
                s = rw.readline(DEFAULT_BUFFER_SIZE or _DEFAULT_BUFFER_SIZE)
            fp.seek(0)
            posts[name] = fp.getvalue().strip().decode("utf-8")
    return posts, files


__all__ = [
    'parse_header',
    'parse_form',
    'parse_multipart_wsgi',
    'parse_multipart_asgi',
    'parse_multipart_stream',
    '_form_cache',
    'form_dict_match',
]
