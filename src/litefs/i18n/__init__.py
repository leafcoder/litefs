#!/usr/bin/env python
# coding: utf-8

"""
国际化模块

基于标准库 :mod:`gettext` 提供多语言支持：

- :class:`LocaleMiddleware`：请求级 locale 协商中间件
- :func:`negotiate_locale`：按 ``Accept-Language`` / Cookie / 查询参数协商 locale
- :func:`gettext` / :func:`ngettext`：请求级翻译函数
- :func:`inject_translations`：向模板变量注入翻译函数

使用示例::

    from litefs.i18n import LocaleMiddleware

    app.add_middleware(LocaleMiddleware, supported_locales=['zh_CN', 'en'])
"""

from .locale import (
    WILDCARD,
    match_locale,
    negotiate_locale,
    normalize_locale,
    parse_accept_language,
)
from .middleware import LocaleMiddleware
from .template import inject_translations
from .translator import (
    DEFAULT_DOMAIN,
    DEFAULT_LOCALE_DIR,
    Translator,
    clear_translation_cache,
    get_current_locale,
    get_current_locale_dir,
    get_translations,
    gettext,
    install_translations,
    ngettext,
    set_current_locale,
    set_current_locale_dir,
)

__all__ = [
    "WILDCARD",
    "match_locale",
    "negotiate_locale",
    "normalize_locale",
    "parse_accept_language",
    "LocaleMiddleware",
    "inject_translations",
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
