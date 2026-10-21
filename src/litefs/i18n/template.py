#!/usr/bin/env python
# coding: utf-8

"""
模板翻译函数注入

向模板渲染上下文注入 ``_`` / ``gettext`` / ``ngettext`` 三个翻译函数。

**零行为变化保障**：当前无请求上下文、无 locale 或翻译表缺失时，
注入的函数为恒等函数（返回原文），因此未启用国际化的应用
渲染结果与未注入前完全一致。
"""

from typing import Any, Callable, Dict, Optional

from .translator import get_current_locale, get_translations


def _identity_gettext(message: str) -> str:
    """
    恒等翻译函数

    Args:
        message: 原文

    Returns:
        原文
    """
    return message


def _identity_ngettext(singular: str, plural: str, n: int) -> str:
    """
    恒等复数翻译函数

    Args:
        singular: 单数形式原文
        plural: 复数形式原文
        n: 数量

    Returns:
        对应的原文
    """
    return singular if n == 1 else plural


def inject_translations(
    context: Optional[Dict[str, Any]] = None,
    locale: Optional[str] = None,
) -> Dict[str, Any]:
    """
    向模板上下文注入翻译函数

    注入的键为 ``_`` / ``gettext`` / ``ngettext``，
    已存在的同名键不会被覆盖。

    Args:
        context: 模板上下文，None 时返回新建字典
        locale: 显式指定 locale，None 时使用当前请求的 locale

    Returns:
        注入翻译函数后的模板上下文
    """
    result: Dict[str, Any] = context if context is not None else {}

    target = locale or get_current_locale()
    if not target:
        # 无 locale 时注入恒等函数，保证渲染结果与未注入时一致
        result.setdefault("_", _identity_gettext)
        result.setdefault("gettext", _identity_gettext)
        result.setdefault("ngettext", _identity_ngettext)
        return result

    translations = get_translations(target)

    def do_gettext(message: str) -> str:
        """
        翻译文本

        Args:
            message: 原文

        Returns:
            译文
        """
        return translations.gettext(message)

    def do_ngettext(singular: str, plural: str, n: int) -> str:
        """
        按数量翻译文本

        Args:
            singular: 单数形式原文
            plural: 复数形式原文
            n: 数量

        Returns:
            译文
        """
        return translations.ngettext(singular, plural, n)

    result.setdefault("_", do_gettext)
    result.setdefault("gettext", do_gettext)
    result.setdefault("ngettext", do_ngettext)
    return result


def make_translation_callables(
    locale: Optional[str] = None,
) -> Dict[str, Callable[..., str]]:
    """
    构造独立的翻译函数字典

    适用于不经过模板引擎、直接在 Python 代码中复用的场景。

    Args:
        locale: 显式指定 locale，None 时使用当前请求的 locale

    Returns:
        包含 ``_`` / ``gettext`` / ``ngettext`` 的字典
    """
    return inject_translations(None, locale)


__all__ = [
    "inject_translations",
    "make_translation_callables",
]
