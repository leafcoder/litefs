#!/usr/bin/env python
# coding: utf-8

"""
弃用机制

Litefs 统一的弃用声明与运行时告警工具。

设计要点
--------
1. 弃用告警统一使用 :class:`LitefsDeprecationWarning`（``DeprecationWarning`` 子类），
   用户可通过 ``warnings.filterwarnings`` 精确过滤本框架的告警。
2. 装饰器 :func:`deprecated` 与函数 :func:`warn_deprecated` 共用同一消息格式。
3. 弃用信息包含四要素：**宣告版本**、**移除版本**、**替代符号**、**废弃原因**。
4. 版本与替代符号的权威来源是 :mod:`litefs._stable` 的 ``DEPRECATED`` 登记表，
   本模块只做运行时告警，登记表是唯一的文档与计划来源。

使用示例
--------
.. code-block:: python

    from litefs.deprecation import deprecated

    @deprecated(replacement="new_api", since="0.10.0", removal="1.3.0")
    def old_api():
        ...
"""

import functools
import warnings
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

__all__ = [
    "LitefsDeprecationWarning",
    "deprecated",
    "format_deprecation_message",
    "warn_deprecated",
]


class LitefsDeprecationWarning(DeprecationWarning):
    """Litefs 专用弃用告警

    继承自标准库 ``DeprecationWarning``，因此默认遵循 Python 的告警可见性策略
    （默认忽略；``python -W default`` 或显式 ``filterwarnings`` 开启后可见）。
    """


def format_deprecation_message(
    symbol: str,
    since: Optional[str] = None,
    removal: Optional[str] = None,
    replacement: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """生成标准化的弃用告警消息

    Args:
        symbol: 废弃符号标识，格式为 ``模块:符号``
        since: 宣告废弃的版本
        removal: 计划移除的版本
        replacement: 推荐的替代符号
        reason: 废弃原因

    Returns:
        完整的弃用告警消息
    """
    parts = ["%s 已废弃" % symbol]
    if since:
        parts.append("自 %s 起" % since)
    if removal:
        parts.append("将于 %s 移除" % removal)
    message = "，".join(parts) + "。"
    if replacement:
        message += "请改用 %s。" % replacement
    if reason:
        message += "原因：%s。" % reason
    return message


def warn_deprecated(
    symbol: str,
    since: Optional[str] = None,
    removal: Optional[str] = None,
    replacement: Optional[str] = None,
    reason: Optional[str] = None,
    stacklevel: int = 3,
) -> None:
    """发出弃用告警

    未显式提供的版本信息与替代符号会从 :mod:`litefs._stable` 的
    ``DEPRECATED`` 登记表回填，保证运行时告警与文档计划一致。

    Args:
        symbol: 废弃符号标识，格式为 ``模块:符号``
        since: 宣告废弃的版本
        removal: 计划移除的版本
        replacement: 推荐的替代符号
        reason: 废弃原因
        stacklevel: 告警栈层级，指向调用方
    """
    from ._stable import DEPRECATED

    info = DEPRECATED.get(symbol)
    if info is not None:
        since = since or info.since
        removal = removal or info.removal
        replacement = replacement or info.replacement
        reason = reason or info.reason

    warnings.warn(
        format_deprecation_message(
            symbol,
            since=since,
            removal=removal,
            replacement=replacement,
            reason=reason,
        ),
        LitefsDeprecationWarning,
        stacklevel=stacklevel,
    )


def deprecated(
    replacement: Optional[str] = None,
    since: Optional[str] = None,
    removal: Optional[str] = None,
    reason: Optional[str] = None,
    symbol: Optional[str] = None,
) -> Callable[[F], F]:
    """标记函数或方法已废弃的装饰器

    被装饰对象在**调用时**发出 :class:`LitefsDeprecationWarning`，
    不会在导入期告警，以免污染下游应用的启动日志。

    Args:
        replacement: 推荐的替代符号
        since: 宣告废弃的版本
        removal: 计划移除的版本
        reason: 废弃原因
        symbol: 废弃符号标识，格式为 ``模块:符号``；
            缺省时由被装饰对象的 ``__module__`` 与 ``__qualname__`` 推导

    Returns:
        装饰器
    """

    def decorator(func: F) -> F:
        qualname = func.__qualname__
        if "<locals>." in qualname:
            # 嵌套函数去掉闭包路径，只保留函数名
            qualname = qualname.rsplit("<locals>.", 1)[-1]
        target = symbol or "%s:%s" % (func.__module__, qualname)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warn_deprecated(
                target,
                since=since,
                removal=removal,
                replacement=replacement,
                reason=reason,
                stacklevel=3,
            )
            return func(*args, **kwargs)

        wrapper.__deprecated__ = True  # type: ignore[attr-defined]
        wrapper.__deprecation_target__ = target  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
