#!/usr/bin/env python
# coding: utf-8

"""
依赖安全审计脚本测试

覆盖命令构造、JSON 摘要解析、输出落盘与未安装 pip-audit 时的降级行为。
"""

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
    ),
)

from audit_deps import (  # noqa: E402
    build_command,
    build_parser,
    main,
    summarize_json,
    write_output,
)


class TestBuildParser(unittest.TestCase):
    """命令行参数"""

    def test_defaults(self):
        """默认审计 requirements.txt 且输出为文本"""
        args = build_parser().parse_args([])

        self.assertEqual(args.requirement, "requirements.txt")
        self.assertEqual(args.format, "text")
        self.assertFalse(args.env)

    def test_ignore_vuln_accumulates(self):
        """忽略漏洞编号可重复传入"""
        args = build_parser().parse_args(
            ["--ignore-vuln", "GHSA-a", "--ignore-vuln", "GHSA-b"]
        )

        self.assertEqual(args.ignore_vuln, ["GHSA-a", "GHSA-b"])

    def test_invalid_format_rejected(self):
        """非法输出格式被拒绝"""
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["--format", "yaml"])


class TestBuildCommand(unittest.TestCase):
    """命令构造"""

    def test_requirement_mode(self):
        """requirements 模式带 -r 参数"""
        args = build_parser().parse_args(["--requirement", "req.txt"])
        command = build_command(args)

        self.assertIn("-r", command)
        self.assertIn("req.txt", command)
        self.assertNotIn("--skip-editable", command)

    def test_env_mode_ignores_requirement(self):
        """环境模式不带 -r 参数"""
        args = build_parser().parse_args(["--env"])
        command = build_command(args)

        self.assertNotIn("-r", command)
        self.assertNotIn("--skip-editable", command)

    def test_env_mode_with_skip_editable(self):
        """环境模式可跳过可编辑安装包"""
        args = build_parser().parse_args(["--env", "--skip-editable"])
        command = build_command(args)

        self.assertIn("--skip-editable", command)

    def test_json_format(self):
        """JSON 输出模式带 --format json"""
        args = build_parser().parse_args(["--format", "json"])
        command = build_command(args)

        self.assertIn("--format", command)
        self.assertIn("json", command)

    def test_ignore_vuln_passed_through(self):
        """忽略漏洞参数透传"""
        args = build_parser().parse_args(["--ignore-vuln", "GHSA-a"])
        command = build_command(args)

        self.assertIn("--ignore-vuln", command)
        self.assertIn("GHSA-a", command)


class TestSummarizeJson(unittest.TestCase):
    """JSON 摘要解析"""

    def test_no_vulnerabilities(self):
        """无漏洞时摘要给出明确结论"""
        payload = json.dumps({"dependencies": [{"name": "foo", "vulns": []}]})

        summary = summarize_json(payload)

        self.assertIn("扫描依赖数: 1", summary)
        self.assertIn("未发现已知漏洞", summary)

    def test_with_vulnerabilities(self):
        """存在漏洞时列出漏洞与修复版本"""
        payload = json.dumps(
            {
                "dependencies": [
                    {
                        "name": "foo",
                        "vulns": [
                            {
                                "id": "PYSEC-2026-1",
                                "aliases": ["GHSA-aaaa-bbbb-cccc"],
                                "fix_versions": ["1.2.3"],
                            }
                        ],
                    }
                ]
            }
        )

        summary = summarize_json(payload)

        self.assertIn("存在漏洞的依赖数: 1", summary)
        self.assertIn("PYSEC-2026-1", summary)
        self.assertIn("GHSA-aaaa-bbbb-cccc", summary)
        self.assertIn("1.2.3", summary)

    def test_invalid_json_returns_raw(self):
        """非法 JSON 返回原始内容片段"""
        summary = summarize_json("not a json at all")

        self.assertIn("not a json at all", summary)

    def test_non_dict_payload(self):
        """顶层非字典返回原始内容片段"""
        summary = summarize_json("[1, 2, 3]")

        self.assertIn("[1, 2, 3]", summary)


class TestWriteOutput(unittest.TestCase):
    """输出落盘"""

    def test_writes_file(self):
        """内容写入指定路径"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "nested", "audit.json")
            write_output("hello", path)

            self.assertTrue(os.path.isfile(path))
            with open(path, "r", encoding="utf-8") as fp:
                self.assertEqual(fp.read(), "hello")

    def test_none_path_is_noop(self):
        """路径为 None 时不落盘"""
        write_output("hello", None)


class TestMain(unittest.TestCase):
    """命令行入口"""

    def test_missing_tool_returns_two(self):
        """pip-audit 不可用时返回 2 并给出安装指引"""
        import audit_deps

        original = audit_deps._module_available
        original_which = audit_deps._pip_audit_executable
        audit_deps._module_available = lambda name: False
        audit_deps._pip_audit_executable = lambda: None
        try:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["--requirement", "requirements.txt"])
        finally:
            audit_deps._module_available = original
            audit_deps._pip_audit_executable = original_which

        self.assertEqual(code, 2)
        self.assertIn("pip-audit", stderr.getvalue())

    def test_vulnerability_returns_one(self):
        """发现漏洞返回 1"""
        import audit_deps

        original = audit_deps._module_available
        original_which = audit_deps._pip_audit_executable
        original_run = audit_deps.subprocess.run

        audit_deps._module_available = lambda name: True
        audit_deps._pip_audit_executable = lambda: "/usr/bin/pip-audit"

        class _Completed:
            """模拟 subprocess.run 返回值"""

            returncode = 1
            stdout = "foo 1.0.0 PYSEC-2026-1 1.0.1\n"
            stderr = ""

        audit_deps.subprocess.run = lambda *args, **kwargs: _Completed()
        try:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["--requirement", "requirements.txt"])
        finally:
            audit_deps._module_available = original
            audit_deps._pip_audit_executable = original_which
            audit_deps.subprocess.run = original_run

        self.assertEqual(code, 1)
        self.assertIn("PYSEC-2026-1", stdout.getvalue())

    def test_clean_returns_zero(self):
        """无漏洞返回 0"""
        import audit_deps

        original = audit_deps._module_available
        original_which = audit_deps._pip_audit_executable
        original_run = audit_deps.subprocess.run

        audit_deps._module_available = lambda name: True
        audit_deps._pip_audit_executable = lambda: "/usr/bin/pip-audit"

        class _Completed:
            """模拟 subprocess.run 返回值"""

            returncode = 0
            stdout = "No known vulnerabilities found\n"
            stderr = ""

        audit_deps.subprocess.run = lambda *args, **kwargs: _Completed()
        try:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["--requirement", "requirements.txt"])
        finally:
            audit_deps._module_available = original
            audit_deps._pip_audit_executable = original_which
            audit_deps.subprocess.run = original_run

        self.assertEqual(code, 0)
        self.assertIn("PASS", stdout.getvalue())

    def test_unexpected_returncode_returns_two(self):
        """异常退出码返回 2"""
        import audit_deps

        original = audit_deps._module_available
        original_which = audit_deps._pip_audit_executable
        original_run = audit_deps.subprocess.run

        audit_deps._module_available = lambda name: True
        audit_deps._pip_audit_executable = lambda: "/usr/bin/pip-audit"

        class _Completed:
            """模拟 subprocess.run 返回值"""

            returncode = 3
            stdout = ""
            stderr = "boom"

        audit_deps.subprocess.run = lambda *args, **kwargs: _Completed()
        try:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--requirement", "requirements.txt"])
        finally:
            audit_deps._module_available = original
            audit_deps._pip_audit_executable = original_which
            audit_deps.subprocess.run = original_run

        self.assertEqual(code, 2)
        self.assertIn("boom", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
