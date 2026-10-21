#!/usr/bin/env python
# coding: utf-8

"""
邮件模板渲染

基于 Mako 实现邮件正文模板，支持纯文本（``.txt``）与 HTML（``.html``）配对模板：

- 仅存在 ``.txt``：渲染为纯文本正文
- 仅存在 ``.html``：渲染为 HTML 正文
- 两者同时存在：生成 ``multipart/alternative`` 邮件

模板查找器带缓存，避免每封邮件重复解析模板文件。
"""

import os
from typing import Any, Dict, Optional, Tuple

from mako.lookup import TemplateLookup

# 模板查找器缓存：{模板目录: TemplateLookup}
_LOOKUP_CACHE: Dict[str, TemplateLookup] = {}


def get_template_lookup(
    template_dir: str,
    debug: bool = False,
) -> TemplateLookup:
    """
    获取（并缓存）指定目录的 Mako 模板查找器

    Args:
        template_dir: 模板目录，None 或空串表示不做限制
        debug: 调试模式，关闭模板缓存以立即生效

    Returns:
        模板查找器
    """
    key = f"{os.path.abspath(template_dir) if template_dir else ''}|{debug}"
    cached = _LOOKUP_CACHE.get(key)
    if cached is not None:
        return cached

    directories = [template_dir] if template_dir else []
    lookup = TemplateLookup(
        directories=directories,
        input_encoding="utf-8",
        encoding_errors="replace",
        cache_enabled=not debug,
    )
    _LOOKUP_CACHE[key] = lookup
    return lookup


def render_mail_template(
    template_name: str,
    template_dir: str,
    debug: bool = False,
    **kwargs: Any,
) -> Tuple[Optional[str], Optional[str]]:
    """
    渲染邮件模板

    Args:
        template_name: 模板基础名（如 ``welcome``），也可带扩展名
        template_dir: 模板目录
        debug: 调试模式，关闭模板缓存
        **kwargs: 模板变量

    Returns:
        (纯文本正文, HTML 正文)，未找到的模板对应项为 None
    """
    lookup = get_template_lookup(template_dir, debug=debug)

    base, ext = os.path.splitext(template_name)
    text_name = template_name
    html_name = template_name

    if ext == ".txt":
        html_name = base + ".html"
    elif ext == ".html":
        text_name = base + ".txt"
    else:
        text_name = base + ".txt"
        html_name = base + ".html"

    text = _render_one(lookup, text_name, kwargs)
    html = _render_one(lookup, html_name, kwargs)
    return text, html


def _render_one(
    lookup: TemplateLookup,
    template_name: str,
    kwargs: Dict[str, Any],
) -> Optional[str]:
    """
    渲染单个模板，模板不存在时返回 None

    Args:
        lookup: 模板查找器
        template_name: 模板文件名
        kwargs: 模板变量

    Returns:
        渲染结果，模板不存在时返回 None
    """
    try:
        template = lookup.get_template(template_name)
    except Exception:
        # 模板不存在时由调用方决定回退策略
        return None
    return str(template.render(**kwargs))


def build_mail_body(
    template_name: str,
    template_dir: str,
    debug: bool = False,
    **kwargs: Any,
) -> Tuple[str, Optional[str]]:
    """
    渲染邮件正文并保证至少有一份可用正文

    Args:
        template_name: 模板基础名
        template_dir: 模板目录
        debug: 调试模式
        **kwargs: 模板变量

    Returns:
        (纯文本正文, HTML 正文)

    Raises:
        FileNotFoundError: 找不到任何可用模板
    """
    text, html = render_mail_template(
        template_name, template_dir, debug=debug, **kwargs
    )
    if text is None and html is None:
        raise FileNotFoundError(
            f"邮件模板不存在: {template_name}（目录: {template_dir or '.'}）"
        )
    return text or "", html


__all__ = [
    "build_mail_body",
    "get_template_lookup",
    "render_mail_template",
]
