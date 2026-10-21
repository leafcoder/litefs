#!/usr/bin/env python
# coding: utf-8

"""
Locale 协商

负责解析 ``Accept-Language`` 请求头，并在受支持的语言列表中
选出最合适的 locale。

匹配规则（按优先级）：
1. 精确匹配（``zh_CN`` 命中 ``zh_CN``）
2. 前缀回退（``zh_CN`` 回退到 ``zh``）
3. 失败时返回默认 locale
"""

from typing import List, Optional, Sequence, Tuple

# 通配符，表示接受任意语言
WILDCARD = "*"


def normalize_locale(locale: str) -> str:
    """
    规范化 locale 字符串

    将 ``zh-CN`` / ``zh_cn`` 统一为 gettext 目录命名约定 ``zh_CN``。

    Args:
        locale: 原始 locale 字符串

    Returns:
        规范化后的 locale
    """
    if not locale:
        return ""

    normalized = locale.strip().replace("-", "_")
    if "_" not in normalized:
        return normalized.lower()

    parts = normalized.split("_")
    language = parts[0].lower()
    territory = parts[1]
    # 仅地区代码（2 位字母或 3 位数字）转为大写，变体标识保持原样
    if len(territory) == 2 and territory.isalpha():
        territory = territory.upper()
    elif territory.isdigit():
        territory = territory.zfill(3)
    result = f"{language}_{territory}"

    # 变体标识（如 zh_Hans_CN）保持原样，仅做下划线替换
    for part in parts[2:]:
        if part:
            result += f"_{part}"

    return result


def parse_accept_language(header: str) -> List[Tuple[str, float]]:
    """
    解析 ``Accept-Language`` 请求头

    Args:
        header: 请求头原始值

    Returns:
        ``[(locale, q 值), ...]``，按 q 值降序排列；q 值相同时保持原顺序
    """
    if not header:
        return []

    candidates: List[Tuple[str, float, int]] = []
    for index, part in enumerate(header.split(",")):
        part = part.strip()
        if not part:
            continue

        pieces = part.split(";")
        raw_locale = pieces[0].strip()
        if not raw_locale:
            continue

        quality = 1.0
        for piece in pieces[1:]:
            piece = piece.strip()
            if piece.startswith("q="):
                try:
                    quality = float(piece[2:].strip())
                except ValueError:
                    quality = 0.0
                break

        candidates.append((raw_locale, quality, index))

    # 稳定排序：q 值降序，同 q 值保持请求头中的原始顺序
    candidates.sort(key=lambda item: (-item[1], item[2]))
    return [(locale, quality) for locale, quality, _ in candidates]


def match_locale(requested: str, supported: Sequence[str]) -> Optional[str]:
    """
    在受支持列表中匹配 locale

    Args:
        requested: 期望的 locale
        supported: 受支持的 locale 列表

    Returns:
        命中的 locale，未命中返回 None
    """
    if not requested or not supported:
        return None

    normalized_supported = [normalize_locale(item) for item in supported]
    normalized_requested = normalize_locale(requested)

    # 1. 精确匹配
    if normalized_requested in normalized_supported:
        return supported[normalized_supported.index(normalized_requested)]

    # 2. 前缀回退：zh_CN -> zh
    prefix = normalized_requested.split("_")[0]
    if prefix in normalized_supported:
        return supported[normalized_supported.index(prefix)]

    return None


def negotiate_locale(
    supported: Sequence[str],
    default_locale: str = "en",
    accept_language: Optional[str] = None,
    cookie_locale: Optional[str] = None,
    param_locale: Optional[str] = None,
) -> str:
    """
    协商本次请求使用的 locale

    优先级：URL 参数 > Cookie > ``Accept-Language`` 请求头 > 默认 locale。

    Args:
        supported: 受支持的 locale 列表
        default_locale: 默认 locale
        accept_language: ``Accept-Language`` 请求头
        cookie_locale: Cookie 中保存的 locale
        param_locale: URL 查询参数中的 locale

    Returns:
        选定的 locale
    """
    fallback = default_locale or "en"

    # 1. URL 查询参数（显式指定，优先级最高）
    if param_locale:
        matched = match_locale(param_locale, supported)
        if matched:
            return matched

    # 2. Cookie
    if cookie_locale:
        matched = match_locale(cookie_locale, supported)
        if matched:
            return matched

    # 3. Accept-Language 请求头
    if accept_language:
        for candidate, _quality in parse_accept_language(accept_language):
            if candidate == WILDCARD:
                # 通配符表示接受任意语言，直接使用默认 locale
                return fallback
            matched = match_locale(candidate, supported)
            if matched:
                return matched

    # 4. 默认 locale
    return fallback


__all__ = [
    "WILDCARD",
    "match_locale",
    "negotiate_locale",
    "normalize_locale",
    "parse_accept_language",
]
