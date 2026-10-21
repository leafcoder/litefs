#!/usr/bin/env python
# coding: utf-8

"""
翻译器

封装标准库 :mod:`gettext`，提供：

- 按 locale 加载并缓存翻译表（``.mo`` 文件缺失时回退原文）
- 复数形式翻译（``ngettext``）
- 请求级 locale 感知：翻译函数自动使用当前请求协商出的 locale

翻译表目录约定（gettext 标准结构）::

    <locale_dir>/<locale>/LC_MESSAGES/<domain>.mo
"""

import gettext as _gettext
import threading
from typing import Dict, Optional, Tuple

# 默认翻译域
DEFAULT_DOMAIN = "messages"

# 默认翻译文件根目录
DEFAULT_LOCALE_DIR = "locales"

# 翻译表缓存：{(locale_dir, locale, domain): Translations}
_TRANSLATION_CACHE: Dict[Tuple[str, str, str], _gettext.NullTranslations] = {}

# 翻译表缓存锁
_CACHE_LOCK = threading.Lock()

# 请求级 locale 存储（线程局部，避免跨请求污染）
_current_locale = threading.local()

# 请求级翻译目录存储
_current_locale_dir = threading.local()


def get_current_locale_dir() -> str:
    """
    获取当前请求使用的翻译目录

    Returns:
        翻译目录，未设置时返回默认的 locales
    """
    return getattr(_current_locale_dir, "value", None) or DEFAULT_LOCALE_DIR


def get_translations(
    locale: str,
    locale_dir: Optional[str] = None,
    domain: str = DEFAULT_DOMAIN,
) -> _gettext.NullTranslations:
    """
    获取指定 locale 的翻译表

    翻译文件缺失时返回 :class:`gettext.NullTranslations`，
    调用其翻译方法将原样返回原文，不会抛出异常。

    Args:
        locale: 目标 locale
        locale_dir: 翻译文件根目录，None 时使用当前请求的翻译目录
        domain: 翻译域

    Returns:
        翻译表对象
    """
    if locale_dir is None:
        locale_dir = get_current_locale_dir()

    key = (locale_dir, locale, domain)
    cached = _TRANSLATION_CACHE.get(key)
    if cached is not None:
        return cached

    with _CACHE_LOCK:
        cached = _TRANSLATION_CACHE.get(key)
        if cached is not None:
            return cached

        try:
            translations = _gettext.translation(
                domain=domain,
                localedir=locale_dir,
                languages=[locale],
                fallback=True,
            )
        except OSError:
            # 翻译目录不存在时同样回退到原文
            translations = _gettext.NullTranslations()

        _TRANSLATION_CACHE[key] = translations
        return translations


def clear_translation_cache() -> None:
    """清空翻译表缓存（测试与热重载场景使用）"""
    with _CACHE_LOCK:
        _TRANSLATION_CACHE.clear()


class Translator:
    """
    翻译器

    绑定固定的 locale 与翻译目录，适合在非请求上下文中使用。

    使用示例::

        translator = Translator('locales', 'zh_CN')
        translator.gettext('Hello')
    """

    def __init__(
        self,
        locale_dir: Optional[str] = None,
        locale: str = "en",
        domain: str = DEFAULT_DOMAIN,
    ) -> None:
        """
        初始化翻译器

        Args:
            locale_dir: 翻译文件根目录，None 时使用当前请求的翻译目录
            locale: 目标 locale
            domain: 翻译域
        """
        self.locale_dir = locale_dir
        self.locale = locale
        self.domain = domain

    @property
    def translations(self) -> _gettext.NullTranslations:
        """
        当前翻译表

        Returns:
            翻译表对象
        """
        return get_translations(self.locale, self.locale_dir, self.domain)

    def gettext(self, message: str) -> str:
        """
        翻译单数形式的文本

        Args:
            message: 原文

        Returns:
            译文，未配置翻译时返回原文
        """
        return self.translations.gettext(message)

    def ngettext(self, singular: str, plural: str, n: int) -> str:
        """
        按数量翻译文本

        Args:
            singular: 单数形式原文
            plural: 复数形式原文
            n: 数量

        Returns:
            译文，未配置翻译时返回对应的原文
        """
        return self.translations.ngettext(singular, plural, n)

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Translator locale={self.locale!r} dir={self.locale_dir!r}>"


def set_current_locale(locale: Optional[str]) -> None:
    """
    设置当前请求的 locale

    Args:
        locale: 目标 locale，None 表示清除
    """
    _current_locale.value = locale


def set_current_locale_dir(locale_dir: Optional[str]) -> None:
    """
    设置当前请求使用的翻译目录

    Args:
        locale_dir: 翻译文件根目录，None 表示清除
    """
    _current_locale_dir.value = locale_dir


def get_current_locale() -> Optional[str]:
    """
    获取当前请求的 locale

    Returns:
        当前 locale，未设置时返回 None
    """
    return getattr(_current_locale, "value", None)


def gettext(message: str, locale: Optional[str] = None) -> str:
    """
    翻译文本（请求级）

    未显式指定 locale 时，使用当前请求协商出的 locale；
    若当前无请求上下文，则原样返回原文。

    Args:
        message: 原文
        locale: 显式指定 locale

    Returns:
        译文
    """
    target = locale or get_current_locale()
    if not target:
        return message
    return get_translations(target).gettext(message)


def ngettext(
    singular: str,
    plural: str,
    n: int,
    locale: Optional[str] = None,
) -> str:
    """
    按数量翻译文本（请求级）

    Args:
        singular: 单数形式原文
        plural: 复数形式原文
        n: 数量
        locale: 显式指定 locale

    Returns:
        译文
    """
    target = locale or get_current_locale()
    if not target:
        return singular if n == 1 else plural
    return get_translations(target).ngettext(singular, plural, n)


def install_translations(
    locale: str = "en",
    locale_dir: Optional[str] = None,
    domain: str = DEFAULT_DOMAIN,
) -> None:
    """
    将翻译函数安装到内置命名空间

    安装后可直接使用 ``_('Hello')``，这是 gettext 的传统用法。
    多次调用会覆盖之前的安装结果。

    Args:
        locale: 目标 locale
        locale_dir: 翻译文件根目录
        domain: 翻译域
    """
    translations = get_translations(locale, locale_dir, domain)
    translations.install()


__all__ = [
    "DEFAULT_DOMAIN",
    "DEFAULT_LOCALE_DIR",
    "Translator",
    "clear_translation_cache",
    "get_current_locale",
    "get_current_locale_dir",
    "get_translations",
    "gettext",
    "install_translations",
    "ngettext",
    "set_current_locale",
    "set_current_locale_dir",
]
