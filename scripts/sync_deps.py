#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""将 pyproject.toml 中声明的核心依赖同步到 requirements.txt。

仅重写 requirements.txt 的「核心依赖」段落，其余可选依赖注释段落原样保留。
供 `make sync-deps` 调用。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.8 ~ 3.10
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:  # pragma: no cover - 缺少 TOML 解析库
        tomllib = None  # type: ignore[assignment]

CORE_HEADER = "# Litefs 核心依赖"
PYPROJECT_PATH = Path("pyproject.toml")
REQUIREMENTS_PATH = Path("requirements.txt")


def load_core_dependencies(path: Path) -> List[str]:
    """读取 pyproject.toml 中声明的核心依赖列表。"""
    if tomllib is None:
        raise RuntimeError("缺少 TOML 解析库，请先安装 tomli（Python < 3.11）")
    with path.open("rb") as fp:
        config: Dict[str, Any] = tomllib.load(fp)
    return list(config.get("project", {}).get("dependencies", []))


def split_sections(lines: List[str]) -> List[List[str]]:
    """按空行将 requirements.txt 的行拆分为多个段落。"""
    sections: List[List[str]] = []
    current: List[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            sections.append(current)
            current = []
    if current:
        sections.append(current)
    return sections


def render_core_section(dependencies: List[str]) -> List[str]:
    """生成新的核心依赖段落内容。"""
    return [CORE_HEADER, *dependencies]


def sync(dependencies: List[str], text: str) -> str:
    """重写核心依赖段落，返回新的 requirements.txt 内容。"""
    sections = split_sections(text.splitlines())
    if not sections:
        return text

    for index, section in enumerate(sections):
        if section and section[0].strip() == CORE_HEADER:
            sections[index] = render_core_section(dependencies)
            break
    else:
        sections.insert(0, render_core_section(dependencies))

    return "\n\n".join("\n".join(section) for section in sections) + "\n"


def main() -> int:
    """命令行入口。"""
    dependencies = load_core_dependencies(PYPROJECT_PATH)
    original = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    updated = sync(dependencies, original)
    if updated != original:
        REQUIREMENTS_PATH.write_text(updated, encoding="utf-8")
        print("已同步 %d 条核心依赖到 %s" % (len(dependencies), REQUIREMENTS_PATH))
    else:
        print("核心依赖无变化，无需写入")
    return 0


if __name__ == "__main__":
    sys.exit(main())
