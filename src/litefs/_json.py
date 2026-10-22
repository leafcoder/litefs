#!/usr/bin/env python
# coding: utf-8

"""
JSON 序列化抽象层（基于 orjson）

Litefs 内部统一使用本模块替代标准库 ``json``。orjson 基于 Rust 实现，
在常见场景下序列化吞吐量为标准库的 3~5 倍，且不依赖全局编码器状态。

设计约定
--------
1. **统一出口**：框架内所有 JSON 读写均经由本模块，业务代码不得直接
   ``import json``，避免出现行为分叉。
2. **显式区分 bytes 与 str**：orjson 原生返回 ``bytes``，而框架内部分调用点
   依赖 ``str``（memcache 客户端要求值为字符串、SQLAlchemy ``TEXT`` 列、
   以及对外暴露的公共属性 ``Response.content``），因此同时提供
   :func:`dumps` 与 :func:`dumps_str` 两个出口。
3. **语义对齐标准库**：
   - ``OPT_NON_STR_KEYS`` —— 非字符串字典键转字符串，与标准库默认行为一致；
   - ``OPT_PASSTHROUGH_DATETIME`` / ``OPT_PASSTHROUGH_DATACLASS``
     —— 交由 ``default`` 回调处理，使 ``default=str`` 的输出与标准库一致
     （标准库为 ``"2026-10-22 12:30:00"``，orjson 原生为 ISO
     ``"2026-10-22T12:30:00"``）。
4. **异常类型保持兼容**：``JSONDecodeError`` 继承自标准库
   ``json.JSONDecodeError``，``JSONEncodeError`` 继承自 ``TypeError``，
   现有捕获链无需修改即可继续工作。
5. **ASCII 安全出口**：标准库 ``json.dumps`` 默认 ``ensure_ascii=True``，
   而 orjson 始终输出原始 UTF-8。``pymemcache`` 的 ``Client.encoding`` 默认
   为 ``"ascii"``，非 ASCII 值会直接写入失败。凡是写入要求纯 ASCII 的
   通道（memcache）必须使用 :func:`dumps_ascii`，以保证值契约与迁移前
   完全一致，并兼容迁移前写入的旧缓存数据。

与标准库的差异
--------------
以下差异为 orjson 的固有行为，无法通过选项关闭，使用时需注意：

========================  =======================  ==========================
差异点                     标准库                   orjson
========================  =======================  ==========================
``NaN`` / ``Infinity``     序列化为字面量            序列化为 ``null``
超过 64 位范围的整数        任意精度                  抛出 ``TypeError``
``UUID``                   需 ``default`` 回调       原生序列化为字符串
分隔符                      ``", "`` / ``": "``       ``","`` / ``":"``
========================  =======================  ==========================
"""

from typing import IO, Any, Callable, Optional, Union

import orjson

__all__ = [
    "JSONDecodeError",
    "JSONEncodeError",
    "dump",
    "dumps",
    "dumps_ascii",
    "dumps_str",
    "load",
    "loads",
]

#: 反序列化异常，继承自标准库 ``json.JSONDecodeError``
JSONDecodeError = orjson.JSONDecodeError

#: 序列化异常，继承自 ``TypeError``
JSONEncodeError = orjson.JSONEncodeError

#: 公共序列化选项
#:
#: - ``OPT_NON_STR_KEYS``：int/float/bool/None 字典键转字符串，对齐标准库；
#: - ``OPT_PASSTHROUGH_DATETIME``/``OPT_PASSTHROUGH_DATACLASS``：
#:   datetime 与 dataclass 交由 ``default`` 回调处理，对齐标准库
#:   ``default=str`` 的输出格式。
_BASE_OPTION = (
    orjson.OPT_NON_STR_KEYS
    | orjson.OPT_PASSTHROUGH_DATETIME
    | orjson.OPT_PASSTHROUGH_DATACLASS
)

#: 可接受的反序列化输入类型
_JSONInput = Union[str, bytes, bytearray, memoryview]


def dumps(obj: Any, default: Optional[Callable[[Any], Any]] = None) -> bytes:
    """
    序列化为 UTF-8 编码的 JSON 字节串

    Args:
        obj: 待序列化对象
        default: 不可序列化类型的兜底转换函数，缺省时直接抛出 ``TypeError``

    Returns:
        bytes: JSON 字节串

    Raises:
        TypeError: 存在不可序列化且无 ``default`` 兜底的对象
    """
    return orjson.dumps(obj, default=default, option=_BASE_OPTION)


def dumps_str(obj: Any, default: Optional[Callable[[Any], Any]] = None) -> str:
    """
    序列化为 JSON 字符串

    与 :func:`dumps` 使用完全相同的序列化规则，仅返回类型不同，
    用于必须保持 ``str`` 类型的调用点。

    Args:
        obj: 待序列化对象
        default: 不可序列化类型的兜底转换函数，缺省时直接抛出 ``TypeError``

    Returns:
        str: JSON 字符串

    Raises:
        TypeError: 存在不可序列化且无 ``default`` 兜底的对象
    """
    return orjson.dumps(obj, default=default, option=_BASE_OPTION).decode("utf-8")


def _escape_non_ascii(text: str) -> str:
    """
    将字符串中的非 ASCII 字符与 DEL 控制符转义为 ``\\uXXXX`` 形式

    仅处理 JSON 输出中「不安全」的码点，ASCII 可打印区（``0x20``~``0x7E``）
    原样保留（含 orjson 已生成的 ``\\"`` / ``\\\\`` 等转义序列），
    因此结果仍是合法 JSON，且与标准库 ``ensure_ascii=True`` 的输出逐字节一致。

    Args:
        text: 待转义的字符串

    Returns:
        str: 纯 ASCII 字符串
    """
    if text.isascii() and "\x7f" not in text:
        return text

    chunks = []
    for char in text:
        code = ord(char)
        if 0x20 <= code <= 0x7E:
            chunks.append(char)
        elif code > 0xFFFF:
            # 星平面字符需拆分为 UTF-16 代理对
            code -= 0x10000
            chunks.append(
                "\\u%04x\\u%04x" % (0xD800 + (code >> 10), 0xDC00 + (code & 0x3FF))
            )
        else:
            chunks.append("\\u%04x" % code)
    return "".join(chunks)


def dumps_ascii(obj: Any, default: Optional[Callable[[Any], Any]] = None) -> str:
    """
    序列化为纯 ASCII 的 JSON 字符串

    用于写入要求 ASCII 编码的通道（如 ``pymemcache``，其 ``Client.encoding``
    默认为 ``"ascii"``）。非 ASCII 字符以 ``\\uXXXX`` 转义，与标准库
    ``json.dumps(..., ensure_ascii=True)`` 的输出等价。

    Args:
        obj: 待序列化对象
        default: 不可序列化类型的兜底转换函数，缺省时直接抛出 ``TypeError``

    Returns:
        str: 纯 ASCII 的 JSON 字符串

    Raises:
        TypeError: 存在不可序列化且无 ``default`` 兜底的对象
    """
    return _escape_non_ascii(dumps_str(obj, default))


def loads(data: _JSONInput) -> Any:
    """
    反序列化 JSON

    Args:
        data: JSON 文本或字节串

    Returns:
        Any: 反序列化后的对象

    Raises:
        JSONDecodeError: 输入不是合法 JSON
    """
    return orjson.loads(data)


def dump(
    obj: Any,
    fp: IO[bytes],
    default: Optional[Callable[[Any], Any]] = None,
) -> None:
    """
    序列化后写入二进制文件对象

    orjson 未提供文件级 API，此处基于其字节输出补齐。

    Args:
        obj: 待序列化对象
        fp: 以二进制模式打开的文件对象
        default: 不可序列化类型的兜底转换函数

    Raises:
        TypeError: 存在不可序列化且无 ``default`` 兜底的对象
    """
    fp.write(orjson.dumps(obj, default=default, option=_BASE_OPTION))


def load(fp: IO[bytes]) -> Any:
    """
    从二进制文件对象读取并反序列化 JSON

    Args:
        fp: 以二进制模式打开的文件对象

    Returns:
        Any: 反序列化后的对象

    Raises:
        JSONDecodeError: 文件内容不是合法 JSON
    """
    return orjson.loads(fp.read())
