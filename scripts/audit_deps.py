#!/usr/bin/env python
# coding: utf-8

"""
依赖安全审计脚本

调用 `pip-audit` 扫描项目依赖，输出已知漏洞清单。

设计要点：
- 纯标准库实现，通过子进程调用 `python -m pip_audit`，避免引入额外依赖
- 默认审计运行时依赖清单 `requirements.txt`（即发布给用户的依赖面），
  也可用 `--env` 审计整个当前环境
- `pip-audit` 未安装时给出明确安装指引并返回非零退出码
- 支持文本与 JSON 两种输出格式，JSON 模式 stdout 保持纯净，便于 CI 归档
- 支持 `--ignore-vuln` 忽略指定漏洞编号（如已评估为不可利用的项）

用法::

    python scripts/audit_deps.py
    python scripts/audit_deps.py --format json --output reports/audit.json
    python scripts/audit_deps.py --env --skip-editable
    python scripts/audit_deps.py --ignore-vuln GHSA-xxxx-xxxx-xxxx
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import List, Optional

# 安装指引
INSTALL_HINT = (
    "未安装 pip-audit，请执行 pip install 'pip-audit>=2.7.3' "
    "或 pip install pip-audit"
)


def _module_available(module_name: str) -> bool:
    """
    判断 Python 模块是否可导入

    Args:
        module_name: 模块名

    Returns:
        可导入时返回 True
    """
    try:
        __import__(module_name)
    except ImportError:
        return False
    return True


def _pip_audit_executable() -> Optional[str]:
    """
    查找 pip-audit 可执行文件

    Returns:
        可执行文件路径，未安装时返回 None
    """
    return shutil.which("pip-audit")


def build_parser() -> argparse.ArgumentParser:
    """
    构造命令行参数解析器

    Returns:
        参数解析器
    """
    parser = argparse.ArgumentParser(
        description="Litefs 依赖安全审计工具",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="输出格式（默认: text）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="结果落盘路径，未指定时仅输出到标准输出",
    )
    parser.add_argument(
        "--ignore-vuln",
        action="append",
        default=[],
        metavar="ID",
        help="忽略指定漏洞编号，可重复传入",
    )
    parser.add_argument(
        "--requirement",
        default="requirements.txt",
        help=(
            "审计指定的 requirements 文件（默认: requirements.txt，"
            "即运行时依赖清单）；与 --env 互斥"
        ),
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="审计当前 Python 环境而非 requirements 文件",
    )
    parser.add_argument(
        "--skip-editable",
        action="store_true",
        help="跳过以可编辑模式安装的包（本项目自身）",
    )
    return parser


def build_command(args: argparse.Namespace) -> List[str]:
    """
    构造 pip-audit 调用命令

    Args:
        args: 命令行参数

    Returns:
        命令参数列表
    """
    command = [sys.executable, "-m", "pip_audit"]

    if args.format == "json":
        command.extend(["--format", "json"])

    if args.env:
        if args.skip_editable:
            command.append("--skip-editable")
    elif args.requirement:
        command.extend(["-r", args.requirement])

    for vuln_id in args.ignore_vuln:
        command.extend(["--ignore-vuln", vuln_id])

    return command


def write_output(content: str, output_path: Optional[str]) -> None:
    """
    写出审计结果

    Args:
        content: 结果内容
        output_path: 落盘路径，None 时不落盘
    """
    if not output_path:
        return
    directory = os.path.dirname(os.path.abspath(output_path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write(content)


def summarize_json(content: str) -> str:
    """
    解析 JSON 审计结果并生成摘要

    Args:
        content: JSON 内容

    Returns:
        摘要文本；解析失败时返回原始内容前若干字符
    """
    try:
        payload = json.loads(content)
    except ValueError:
        return content[:2000]

    if not isinstance(payload, dict):
        return content[:2000]

    dependencies = payload.get("dependencies", [])
    if not isinstance(dependencies, list):
        return content[:2000]

    vulnerable = []
    for item in dependencies:
        if not isinstance(item, dict):
            continue
        vulns = item.get("vulns", [])
        if vulns:
            vulnerable.append((item.get("name", "?"), vulns))

    lines = ["依赖安全审计摘要", "=" * 60]
    lines.append(f"扫描依赖数: {len(dependencies)}")
    lines.append(f"存在漏洞的依赖数: {len(vulnerable)}")
    lines.append("-" * 60)

    for name, vulns in vulnerable:
        lines.append(f"{name}")
        for vuln in vulns:
            if not isinstance(vuln, dict):
                continue
            vuln_id = vuln.get("id", "?")
            aliases = ",".join(vuln.get("aliases", []) or [])
            fix_versions = ",".join(vuln.get("fix_versions", []) or [])
            lines.append(f"  - {vuln_id} ({aliases}) 修复版本: {fix_versions or '暂无'}")

    if not vulnerable:
        lines.append("未发现已知漏洞")

    lines.append("=" * 60)
    return "\n".join(lines)


def _emit(as_json: bool, message: str) -> None:
    """
    输出结论信息

    JSON 模式下 stdout 需保持纯净（仅输出 JSON 文档），
    因此结论信息统一写入 stderr。

    Args:
        as_json: 是否为 JSON 输出模式
        message: 待输出文本
    """
    if as_json:
        print(message, file=sys.stderr)
    else:
        print(message)


def main(argv: Optional[List[str]] = None) -> int:
    """
    命令行入口

    Args:
        argv: 参数列表，None 时读取进程参数

    Returns:
        退出码：0 未发现漏洞，1 发现漏洞，2 工具不可用或执行异常
    """
    args = build_parser().parse_args(argv)
    as_json = args.format == "json"

    if not _module_available("pip_audit") and not _pip_audit_executable():
        print(f"[FAIL] {INSTALL_HINT}", file=sys.stderr)
        return 2

    command = build_command(args)

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"[FAIL] 执行 pip-audit 失败: {exc}", file=sys.stderr)
        return 2

    content = completed.stdout or ""
    error_content = completed.stderr or ""

    if content.strip():
        write_output(content, args.output)

    if as_json:
        # JSON 模式下 stdout 仅保留 JSON 文档，摘要与结论写入 stderr
        if content.strip():
            print(content)
        summary = summarize_json(content) if content.strip() else ""
        if summary:
            print(summary, file=sys.stderr)
        if error_content.strip():
            print(error_content, file=sys.stderr)
    else:
        if content.strip():
            print(content)
        if error_content.strip():
            print(error_content, file=sys.stderr)

    # pip-audit 以 1 表示发现漏洞，无漏洞时返回 0
    if completed.returncode == 0:
        _emit(as_json, "[PASS] 未发现已知依赖漏洞")
        return 0

    if completed.returncode == 1:
        _emit(as_json, "[FAIL] 发现已知依赖漏洞，详见上方输出")
        return 1

    print(f"[FAIL] pip-audit 执行异常，退出码: {completed.returncode}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
