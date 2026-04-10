#!/usr/bin/env python3
"""
Trae 项目初始化脚本 - 快速生成 Trae 配置文件

用法:
    python init_trae_project.py --path /path/to/project
    python init_trae_project.py --path /path/to/project --with-skill my-skill

功能:
    - 创建 .trae 目录结构
    - 生成 USER_PREFERENCES.md 模板
    - 生成 project_rules.md 模板
    - 可选：创建新的 Skill 模板
"""

import argparse
import sys
from pathlib import Path


USER_PREFERENCES_TEMPLATE = """# User Preferences

本文件定义 Trae 的全局行为偏好，所有 Skill 和 Agent 都会遵循这些设置。

## 1. 技术栈偏好 (Tech Stack)

*   **前端框架**: React / Vue / Flutter / 其他
*   **CSS 方案**: Tailwind CSS / CSS Modules / Styled Components
*   **状态管理**: Zustand / Redux / Riverpod / 其他
*   **测试框架**: Vitest / Jest / Pytest / 其他
*   **语言偏好**: TypeScript (Strict Mode) / JavaScript / Python

## 2. 交互风格 (Communication Style)

*   **语言**: 请始终使用**中文**回复，技术术语保留英文
*   **详细程度**: 资深开发者 / 初学者友好
*   **Emoji**: 启用 / 禁用

## 3. 角色覆盖 (Role Overrides)

在此定义特定角色的行为覆盖：

*   **@Backend Developer**:
    *   优先使用 FastAPI / Express / 其他
*   **@Frontend Developer**:
    *   优先使用 Next.js / Vite / 其他
*   **@DevOps Engineer**:
    *   K8s Manifest 必须包含 Resource Limits

## 4. 禁令 (Constraints)

定义项目中的禁止事项：

*   严禁使用 `any` 类型
*   严禁创建 `.env` 文件（使用 config map）
*   严禁在代码中硬编码密钥

## 5. 地区特定配置

*   **时区**: Asia/Shanghai
*   **外链库**: 需在中国可访问（使用国内镜像）
"""

PROJECT_RULES_TEMPLATE = """# Project Rules

本文件定义项目特定的开发规范，Trae 会在开发过程中遵循这些规则。

## 构建与验证命令

定义项目的构建、测试和验证命令：

*   **Lint**: npm run lint
*   **TypeCheck**: npm run typecheck
*   **Test**: npm run test
*   **Build**: npm run build
*   **Dev**: npm run dev

## 代码规范

### 注释规范

*   **函数注释**: 必须添加函数级注释，说明参数和返回值
*   **语言要求**: 中文注释，技术术语保留英文
*   **外链库**: 确保在中国可访问

### 命名规范

*   **变量**: camelCase
*   **常量**: UPPER_SNAKE_CASE
*   **类名**: PascalCase
*   **文件名**: kebab-case

### 代码风格

*   **缩进**: 2 空格 / 4 空格
*   **引号**: 单引号 / 双引号
*   **分号**: 使用 / 不使用

## Git 规范

### Commit 规范

遵循 Conventional Commits 规范：

*   `feat:` 新功能
*   `fix:` 修复 Bug
*   `docs:` 文档更新
*   `style:` 代码格式调整
*   `refactor:` 重构
*   `test:` 测试相关
*   `chore:` 构建/工具相关

### 分支规范

*   `main` - 主分支
*   `develop` - 开发分支
*   `feature/*` - 功能分支
*   `fix/*` - 修复分支
*   `release/*` - 发布分支

## 项目特定规则

在此添加项目特定的规则：

*   [添加项目特定规则]
*   [添加项目特定规则]
"""

SKILL_TEMPLATE = """---
name: {skill_name}
description: [TODO: 完善 Skill 描述，说明功能和触发条件。包含 WHEN to use - 触发场景、文件类型或任务。]
---

# {skill_title}

## Overview

[TODO: 1-2 句话说明此 Skill 的功能]

## Workflow

1. [TODO: 步骤一]
2. [TODO: 步骤二]
3. [TODO: 步骤三]

## Usage

[TODO: 使用示例]

## Resources

### scripts/
存放可执行脚本。

### references/
存放参考文档。

### assets/
存放资源文件（模板、图片等）。
"""

AGENTS_TEMPLATE = """---
name: {agent_name}
description: [TODO: Agent 描述，说明角色定位和使用场景]
---

# {agent_title}

## 角色定义 (Persona)

*   **专长**: [TODO: 描述专业领域]
*   **风格**: [TODO: 描述工作风格]
*   **背景**: [TODO: 描述角色背景]

## 核心能力

*   [TODO: 能力一]
*   [TODO: 能力二]
*   [TODO: 能力三]

## 工作流程

1. **需求理解**: [TODO: 描述]
2. **方案设计**: [TODO: 描述]
3. **实施执行**: [TODO: 描述]
4. **验证交付**: [TODO: 描述]

## MCP 增强

建议配合以下 MCP 工具使用：

*   [TODO: MCP 工具一]
*   [TODO: MCP 工具二]
"""


def create_trae_directory(project_path: Path) -> bool:
    """
    创建 .trae 目录结构。

    Args:
        project_path: 项目根目录路径

    Returns:
        bool: 创建成功返回 True
    """
    trae_dir = project_path / ".trae"
    rules_dir = trae_dir / "rules"
    skills_dir = trae_dir / "Skills"

    try:
        trae_dir.mkdir(parents=True, exist_ok=True)
        rules_dir.mkdir(exist_ok=True)
        skills_dir.mkdir(exist_ok=True)
        print(f"✅ 创建目录: {trae_dir}")
        print(f"✅ 创建目录: {rules_dir}")
        print(f"✅ 创建目录: {skills_dir}")
        return True
    except Exception as e:
        print(f"❌ 创建目录失败: {e}")
        return False


def create_user_preferences(project_path: Path) -> bool:
    """
    创建 USER_PREFERENCES.md 文件。

    Args:
        project_path: 项目根目录路径

    Returns:
        bool: 创建成功返回 True
    """
    file_path = project_path / ".trae" / "USER_PREFERENCES.md"

    if file_path.exists():
        print(f"⚠️  文件已存在: {file_path}")
        return True

    try:
        file_path.write_text(USER_PREFERENCES_TEMPLATE, encoding="utf-8")
        print(f"✅ 创建文件: {file_path}")
        return True
    except Exception as e:
        print(f"❌ 创建文件失败: {e}")
        return False


def create_project_rules(project_path: Path) -> bool:
    """
    创建 project_rules.md 文件。

    Args:
        project_path: 项目根目录路径

    Returns:
        bool: 创建成功返回 True
    """
    file_path = project_path / ".trae" / "rules" / "project_rules.md"

    if file_path.exists():
        print(f"⚠️  文件已存在: {file_path}")
        return True

    try:
        file_path.write_text(PROJECT_RULES_TEMPLATE, encoding="utf-8")
        print(f"✅ 创建文件: {file_path}")
        return True
    except Exception as e:
        print(f"❌ 创建文件失败: {e}")
        return False


def create_skill(skill_name: str, project_path: Path) -> bool:
    """
    创建新的 Skill 模板。

    Args:
        skill_name: Skill 名称
        project_path: 项目根目录路径

    Returns:
        bool: 创建成功返回 True
    """
    skill_dir = project_path / ".trae" / "Skills" / skill_name

    if skill_dir.exists():
        print(f"❌ Skill 目录已存在: {skill_dir}")
        return False

    try:
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_title = " ".join(word.capitalize() for word in skill_name.split("-"))

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(SKILL_TEMPLATE.format(
            skill_name=skill_name,
            skill_title=skill_title
        ), encoding="utf-8")
        print(f"✅ 创建文件: {skill_md}")

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        print(f"✅ 创建目录: {scripts_dir}")

        references_dir = skill_dir / "references"
        references_dir.mkdir(exist_ok=True)
        print(f"✅ 创建目录: {references_dir}")

        assets_dir = skill_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        print(f"✅ 创建目录: {assets_dir}")

        return True
    except Exception as e:
        print(f"❌ 创建 Skill 失败: {e}")
        return False


def create_agent(agent_name: str, project_path: Path) -> bool:
    """
    创建新的 Agent 模板。

    Args:
        agent_name: Agent 名称
        project_path: 项目根目录路径

    Returns:
        bool: 创建成功返回 True
    """
    file_path = project_path / ".trae" / "Skills" / f"{agent_name}" / "AGENTS.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        print(f"⚠️  文件已存在: {file_path}")
        return True

    try:
        agent_title = " ".join(word.capitalize() for word in agent_name.split("-"))
        file_path.write_text(AGENTS_TEMPLATE.format(
            agent_name=agent_name,
            agent_title=agent_title
        ), encoding="utf-8")
        print(f"✅ 创建文件: {file_path}")
        return True
    except Exception as e:
        print(f"❌ 创建 Agent 失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Trae 项目初始化脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    init_trae_project.py --path /path/to/project
    init_trae_project.py --path /path/to/project --with-skill my-skill
    init_trae_project.py --path /path/to/project --with-agent my-agent
        """
    )

    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="项目根目录路径 (默认: 当前目录)"
    )

    parser.add_argument(
        "--with-skill",
        type=str,
        help="同时创建指定名称的 Skill 模板"
    )

    parser.add_argument(
        "--with-agent",
        type=str,
        help="同时创建指定名称的 Agent 模板"
    )

    args = parser.parse_args()
    project_path = Path(args.path).resolve()

    print(f"🚀 初始化 Trae 项目配置")
    print(f"   项目路径: {project_path}")
    print()

    success = True

    if not create_trae_directory(project_path):
        success = False

    if not create_user_preferences(project_path):
        success = False

    if not create_project_rules(project_path):
        success = False

    if args.with_skill:
        print()
        print(f"📦 创建 Skill: {args.with_skill}")
        if not create_skill(args.with_skill, project_path):
            success = False

    if args.with_agent:
        print()
        print(f"🤖 创建 Agent: {args.with_agent}")
        if not create_agent(args.with_agent, project_path):
            success = False

    print()
    if success:
        print("✅ Trae 项目配置初始化完成！")
        print()
        print("下一步:")
        print("1. 编辑 .trae/USER_PREFERENCES.md 设置用户偏好")
        print("2. 编辑 .trae/rules/project_rules.md 设置项目规则")
        print("3. 运行 validate_trae_project.py 验证配置")
    else:
        print("❌ 初始化过程中出现错误")
        sys.exit(1)


if __name__ == "__main__":
    main()
