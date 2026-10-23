#!/usr/bin/env python
# coding: utf-8

"""
表单数据解析模块

提供表单数据解析功能，支持 URL 编码表单和 multipart 表单
"""

import re
from io import BytesIO
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


def _append_form_value(mapping, name, value):
    """
    向表单字典写入字段值，同名多值字段语义与 urlencoded 路径对齐

    首次出现存为标量，重复出现转为列表（与 parse_form 的重复键行为一致），
    修复同名多值字段被直接覆盖的缺陷。

    Args:
        mapping: 目标字典（posts 或 files）
        name: 字段名
        value: 字段值
    """
    if name in mapping:
        existing = mapping[name]
        if isinstance(existing, list):
            existing.append(value)
        else:
            mapping[name] = [existing, value]
    else:
        mapping[name] = value


def _parse_multipart_fp(fp, boundary, max_upload_size=52428800,
                        read_limit=None, chunk_size=65536):
    """
    从二进制流增量解析 multipart/form-data（流式核心实现）

    边界感知：仅识别行首的 ``--boundary``（首个边界允许无 CRLF 前缀，
    其余必须带 CRLF 前缀，RFC 2046），文件内容中出现与 boundary 相同的
    字节序列不会导致解析损坏。

    流式：逐块读取输入流，文件部分边解析边写入临时文件，
    请求体不在内存中全量驻留；边界分隔符前的 CRLF 属于分隔符，
    不计入部件内容。

    Args:
        fp: 二进制输入流（需支持 read）
        boundary: multipart boundary（str 或 bytes）
        max_upload_size: 实际读取字节数上限，超限抛 HttpError 413
        read_limit: 从流中读取的最大字节数（如 Content-Length，
            防止读取越过请求体边界）；None 表示不限制
        chunk_size: 每次从流中读取的字节数

    Returns:
        (posts, files): 表单字段字典和上传文件字典，
        同名多值字段为列表
    """
    from ..exceptions import HttpError

    if isinstance(boundary, str):
        boundary = boundary.encode("utf-8")
    first_marker = b"--" + boundary
    delimiter = b"\r\n" + first_marker

    posts = {}
    files = {}
    state = {"buf": b"", "eof": False, "total_read": 0}

    def _fill(minimum):
        """确保缓冲区至少有 minimum 字节（到达 read_limit 或流末尾提前返回）"""
        while len(state["buf"]) < minimum and not state["eof"]:
            if read_limit is not None and state["total_read"] >= read_limit:
                state["eof"] = True
                break
            want = chunk_size
            if read_limit is not None:
                want = min(want, read_limit - state["total_read"])
            data = fp.read(want)
            if not data:
                state["eof"] = True
                break
            state["buf"] += data
            state["total_read"] += len(data)
            if state["total_read"] > max_upload_size:
                raise HttpError(
                    413,
                    f"Request body too large. Maximum size is {max_upload_size} bytes"
                )

    def _consume(n):
        state["buf"] = state["buf"][n:]

    def _expect_boundary_end():
        """消费边界行尾部：``--`` 表示结束返回 False，CRLF 后进入下一部件返回 True"""
        _fill(2)
        if state["buf"].startswith(b"--"):
            _consume(2)
            return False
        # 跳过传输填充（LWSP）
        while True:
            _fill(1)
            if not state["buf"]:
                return False
            if state["buf"][:1] in (b" ", b"\t"):
                _consume(1)
                continue
            break
        if state["buf"].startswith(b"\r\n"):
            _consume(2)
            return True
        if state["buf"][:1] == b"\n":
            _consume(1)
            return True
        # 非法边界行尾：宽容处理为流结束
        return False

    # 定位首个边界行：RFC 2046 允许 body 起始处无 CRLF 前缀
    _fill(len(first_marker))
    started = False
    if state["buf"].startswith(first_marker):
        nxt = state["buf"][len(first_marker):len(first_marker) + 1]
        if nxt in (b"-", b"\r", b"\n", b" ", b"\t", b""):
            _consume(len(first_marker))
            started = _expect_boundary_end()
    if not started:
        # 丢弃 preamble，查找 CRLF 前缀的边界
        keep = len(delimiter) - 1
        while True:
            idx = state["buf"].find(delimiter)
            if idx >= 0:
                _consume(idx + len(delimiter))
                break
            if len(state["buf"]) > keep:
                _consume(len(state["buf"]) - keep)
            if state["eof"]:
                return posts, files
            _fill(len(state["buf"]) + 1)
        if not _expect_boundary_end():
            return posts, files

    # 逐部件解析
    while True:
        # 读取部件头（直到空行 CRLFCRLF）
        header_end = -1
        while True:
            header_end = state["buf"].find(b"\r\n\r\n")
            if header_end >= 0:
                break
            if state["eof"]:
                header_end = -1
                break
            before = len(state["buf"])
            _fill(before + chunk_size)
            if len(state["buf"]) == before:
                header_end = -1
                break
        if header_end < 0:
            # 头部被截断，流异常结束：返回已解析部分
            break
        headers_part = state["buf"][:header_end]
        _consume(header_end + 4)

        headers = {}
        for line in headers_part.split(b"\r\n"):
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.strip().upper().decode("utf-8")] = v.strip().decode("utf-8")

        _, params = parse_header(headers.get("CONTENT-DISPOSITION", ""))
        name = params.get("name", "")
        filename = params.get("filename")
        is_file = bool(filename)

        # 扫描部件内容直到下一个边界（内容不含边界前的 CRLF）
        sink = TemporaryFile(mode="w+b") if is_file else bytearray()
        keep = len(delimiter) - 1

        def _write(data):
            if data:
                if is_file:
                    sink.write(data)
                else:
                    sink.extend(data)

        while True:
            idx = state["buf"].find(delimiter)
            if idx >= 0:
                _write(state["buf"][:idx])
                _consume(idx + len(delimiter))
                break
            # 保留末尾 keep 字节防止分隔符跨块截断，其余写入 sink
            if len(state["buf"]) > keep:
                emitted = len(state["buf"]) - keep
                _write(state["buf"][:emitted])
                _consume(emitted)
            if state["eof"]:
                break
            before_total = state["total_read"]
            _fill(len(state["buf"]) + 1)
            if state["total_read"] == before_total and not state["eof"]:
                break

        if is_file:
            sink.seek(0)
            _append_form_value(files, name, sink)
        else:
            _append_form_value(posts, name, bytes(sink).decode("utf-8"))

        if not _expect_boundary_end():
            break

    return posts, files


def parse_multipart_wsgi(wsgi_input, boundary, content_length, max_upload_size=52428800):
    """
    解析 WSGI 环境下的 multipart 表单数据（流式，请求体不整包驻留内存）

    Args:
        wsgi_input: WSGI 输入流
        boundary: multipart boundary
        content_length: 内容长度（作为读取上限，防止越过请求体边界）
        max_upload_size: 最大上传大小，超限抛 HttpError 413

    Returns:
        (posts, files): 表单字段字典和上传文件字典
    """
    if content_length > max_upload_size:
        from ..exceptions import HttpError
        raise HttpError(413, f"Request body too large. Maximum size is {max_upload_size} bytes")

    return _parse_multipart_fp(
        wsgi_input, boundary, max_upload_size=max_upload_size, read_limit=content_length
    )


def parse_multipart_asgi(body, boundary, max_upload_size=52428800):
    """
    解析 ASGI 环境下的 multipart 表单数据

    Args:
        body: 请求体字节数据
        boundary: multipart boundary
        max_upload_size: 最大上传大小，超限抛 HttpError 413

    Returns:
        (posts, files): 表单字段字典和上传文件字典
    """
    if len(body) > max_upload_size:
        from ..exceptions import HttpError
        raise HttpError(413, f"Request body too large. Maximum size is {max_upload_size} bytes")

    return _parse_multipart_fp(BytesIO(body), boundary, max_upload_size=max_upload_size)


def parse_multipart_stream(rw, boundary, max_upload_size=52428800, DEFAULT_BUFFER_SIZE=8192):
    """
    解析流式环境下的 multipart 表单数据

    实际读取字节数超过 max_upload_size 抛 HttpError 413。

    Args:
        rw: 读写流对象
        boundary: multipart boundary
        max_upload_size: 最大上传大小
        DEFAULT_BUFFER_SIZE: 每次从流中读取的字节数（参数名保持向后兼容）

    Returns:
        (posts, files): 表单字段字典和上传文件字典
    """
    return _parse_multipart_fp(
        rw, boundary, max_upload_size=max_upload_size, chunk_size=DEFAULT_BUFFER_SIZE
    )


def read_chunked_body(readline, read, max_size=10485760):
    """
    读取并解码 chunked 传输编码的请求体（同步版）

    支持 chunk 扩展声明（``size;ext``）与 trailer 头部；解码字节数超过
    max_size 抛 HttpError 413，格式非法或数据截断抛 HttpError 400。

    Args:
        readline: 读取一行的可调用对象（返回 bytes，含行尾换行符）
        read: 按字节数读取的可调用对象（返回 bytes）
        max_size: 解码后请求体最大字节数

    Returns:
        解码后的完整请求体 bytes
    """
    from ..exceptions import HttpError

    body = bytearray()
    while True:
        size_line = readline()
        if not size_line:
            raise HttpError(400, "Invalid chunked body")
        size_str = size_line.strip().split(b";", 1)[0]
        try:
            size = int(size_str, 16)
        except ValueError:
            raise HttpError(400, "Invalid chunk size")
        if size < 0:
            raise HttpError(400, "Invalid chunk size")
        if size == 0:
            # 消费 trailer 头部（直到空行）
            while True:
                line = readline()
                if not line or not line.strip():
                    break
            return bytes(body)
        if len(body) + size > max_size:
            raise HttpError(413, f"Request body too large. Maximum size is {max_size} bytes")
        data = read(size)
        if len(data) < size:
            raise HttpError(400, "Truncated chunked body")
        body.extend(data)
        # 消费 chunk 数据后的 CRLF
        crlf = readline()
        if crlf.strip():
            raise HttpError(400, "Invalid chunk delimiter")


__all__ = [
    'parse_header',
    'parse_form',
    'parse_multipart_wsgi',
    'parse_multipart_asgi',
    'parse_multipart_stream',
    'read_chunked_body',
    '_form_cache',
    'form_dict_match',
]
