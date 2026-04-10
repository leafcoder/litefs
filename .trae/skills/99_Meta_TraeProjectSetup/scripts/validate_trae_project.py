#!/usr/bin/env python3
"""
Trae 项目配置验证脚本

用法:
    python validate_trae_project.py --path /path/to/project

功能:
    - 验证 .trae 目录结构
    - 验证 USER_PREFERENCES.md 格式
    - 验证 project_rules.md 格式
    - 验证 Skill 目录结构
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple


def validate_yaml_frontmatter(file_path: Path) -> Tuple[bool, str]:
    """
    验证文件的 YAML frontmatter 格式。

    Args:
        file_path: 文件路径

    Returns:
        Tuple[bool, str]: (是否有效, 错误消息)
    """
    try:
        content = file_path.read_text(encoding="utf-8")

        if not content.startswith("---"):
            return False, "缺少 YAML frontmatter 起始标记"

        end_marker = content.find("\n---", 4)
        if end_marker == -1:
            return False, "缺少 YAML frontmatter 结束标记"

        frontmatter = content[4:end_marker]

        if "name:" not in frontmatter:
            return False, "缺少必需字段: name"

        if "description:" not in frontmatter:
            return False, "缺少必需字段: description"

        return True, "YAML frontmatter 格式正确"

    except Exception as e:
        return False, f"读取文件失败: {e}"


def validate_skill_name(name: str) -> Tuple[bool, str]:
    """
    验证 Skill 名称格式。

    支持两种命名格式：
    - kebab-case: 小写字母、数字和连字符（推荐）
    - 分类前缀格式: XX_Category_Name（现有项目使用）

    Args:
        name: Skill 名称

    Returns:
        Tuple[bool, str]: (是否有效, 错误消息)
    """
    if not name:
        return False, "Skill 名称不能为空"

    if len(name) > 50:
        return False, "Skill 名称长度不能超过 50 个字符"

    if re.match(r'^[a-z0-9-]+$', name):
        if name.startswith("-") or name.endswith("-"):
            return False, "Skill 名称不能以连字符开头或结尾"
        if "--" in name:
            return False, "Skill 名称不能包含连续连字符"
        return True, "Skill 名称格式正确 (kebab-case)"

    if re.match(r'^\d{2}_[A-Z][a-zA-Z0-9_]*$', name):
        return True, "Skill 名称格式正确 (分类前缀格式)"

    if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
        return True, "Skill 名称格式正确"

    return False, "Skill 名称格式不正确"


def validate_skill_directory(skill_dir: Path) -> List[Tuple[bool, str]]:
    """
    验证 Skill 目录结构。

    Args:
        skill_dir: Skill 目录路径

    Returns:
        List[Tuple[bool, str]]: 验证结果列表
    """
    results = []

    skill_name = skill_dir.name
    valid, msg = validate_skill_name(skill_name)
    results.append((valid, f"Skill 名称 '{skill_name}': {msg}"))

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        results.append((False, f"缺少必需文件: SKILL.md"))
        return results

    valid, msg = validate_yaml_frontmatter(skill_md)
    results.append((valid, f"SKILL.md: {msg}"))

    optional_dirs = ["scripts", "references", "assets"]
    for dir_name in optional_dirs:
        dir_path = skill_dir / dir_name
        if dir_path.exists() and not dir_path.is_dir():
            results.append((False, f"{dir_name} 存在但不是目录"))

    agents_md = skill_dir / "AGENTS.md"
    if agents_md.exists():
        valid, msg = validate_yaml_frontmatter(agents_md)
        results.append((valid, f"AGENTS.md: {msg}"))

    return results


def validate_user_preferences(file_path: Path) -> List[Tuple[bool, str]]:
    """
    验证 USER_PREFERENCES.md 文件。

    Args:
        file_path: 文件路径

    Returns:
        List[Tuple[bool, str]]: 验证结果列表
    """
    results = []

    if not file_path.exists():
        results.append((False, "缺少 USER_PREFERENCES.md 文件"))
        return results

    try:
        content = file_path.read_text(encoding="utf-8")

        required_sections = [
            "技术栈偏好",
            "交互风格",
            "角色覆盖",
            "禁令"
        ]

        for section in required_sections:
            if section not in content:
                results.append((False, f"缺少章节: {section}"))

        if len(results) == 0:
            results.append((True, "USER_PREFERENCES.md 格式正确"))

    except Exception as e:
        results.append((False, f"读取 USER_PREFERENCES.md 失败: {e}"))

    return results


def validate_project_rules(file_path: Path) -> List[Tuple[bool, str]]:
    """
    验证 project_rules.md 文件。

    Args:
        file_path: 文件路径

    Returns:
        List[Tuple[bool, str]]: 验证结果列表
    """
    results = []

    if not file_path.exists():
        results.append((False, "缺少 project_rules.md 文件"))
        return results

    try:
        content = file_path.read_text(encoding="utf-8")

        required_sections = [
            "构建与验证命令",
            "代码规范",
            "Git 规范"
        ]

        for section in required_sections:
            if section not in content:
                results.append((False, f"缺少章节: {section}"))

        if len(results) == 0:
            results.append((True, "project_rules.md 格式正确"))

    except Exception as e:
        results.append((False, f"读取 project_rules.md 失败: {e}"))

    return results


def validate_trae_project(project_path: Path) -> bool:
    """
    验证 Trae 项目配置。

    Args:
        project_path: 项目根目录路径

    Returns:
        bool: 验证通过返回 True
    """
    all_passed = True
    total_errors = 0
    total_warnings = 0

    print(f"🔍 验证 Trae 项目配置")
    print(f"   项目路径: {project_path}")
    print()

    trae_dir = project_path / ".trae"

    if not trae_dir.exists():
        print("❌ 错误: .trae 目录不存在")
        print("   运行 init_trae_project.py 初始化项目配置")
        return False

    print("📁 验证目录结构")
    print("-" * 50)

    required_dirs = [trae_dir, trae_dir / "rules", trae_dir / "Skills"]
    for dir_path in required_dirs:
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_path.relative_to(project_path)}")
        else:
            print(f"❌ {dir_path.relative_to(project_path)} (不存在)")
            all_passed = False
            total_errors += 1

    print()
    print("📄 验证 USER_PREFERENCES.md")
    print("-" * 50)

    user_prefs = trae_dir / "USER_PREFERENCES.md"
    results = validate_user_preferences(user_prefs)
    for valid, msg in results:
        if valid:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
            all_passed = False
            total_errors += 1

    print()
    print("📄 验证 project_rules.md")
    print("-" * 50)

    project_rules = trae_dir / "rules" / "project_rules.md"
    results = validate_project_rules(project_rules)
    for valid, msg in results:
        if valid:
            print(f"✅ {msg}")
        else:
            print(f"❌ {msg}")
            all_passed = False
            total_errors += 1

    print()
    print("📦 验证 Skills")
    print("-" * 50)

    skills_dir = trae_dir / "Skills"
    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]

    if not skill_dirs:
        print("ℹ️  未找到任何 Skill")

    for skill_dir in skill_dirs:
        skill_name = skill_dir.name
        results = validate_skill_directory(skill_dir)

        print(f"\n📦 Skill: {skill_name}")
        for valid, msg in results:
            if valid:
                print(f"  ✅ {msg}")
            else:
                print(f"  ❌ {msg}")
                all_passed = False
                total_errors += 1

    print()
    print("=" * 50)
    if all_passed:
        print("✅ 验证通过！所有配置文件格式正确")
    else:
        print(f"❌ 验证失败: {total_errors} 个错误")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Trae 项目配置验证脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    validate_trae_project.py --path /path/to/project
    validate_trae_project.py --path .
        """
    )

    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="项目根目录路径 (默认: 当前目录)"
    )

    args = parser.parse_args()
    project_path = Path(args.path).resolve()

    success = validate_trae_project(project_path)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
