#!/usr/bin/env python
# coding: utf-8

"""
性能回归比对脚本测试

覆盖阈值加载、结果索引、指标比对、报告格式化与命令行入口的退出码语义。
"""

import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "benchmarks",
    ),
)

from compare_benchmark import (  # noqa: E402
    build_key,
    collect_results,
    compare,
    format_report,
    load_json,
    main,
)


def _make_result(server_type, workers, connections, rps, p99):
    """构造单条基准结果

    Args:
        server_type: 服务器类型
        workers: 进程数
        connections: 并发连接数
        rps: 每秒请求数
        p99: P99 延迟（毫秒）

    Returns:
        结果字典
    """
    return {
        "server_type": server_type,
        "workers": workers,
        "connections": connections,
        "requests_per_sec": rps,
        "latency_p99_ms": p99,
    }


class TestBuildKey(unittest.TestCase):
    """阈值索引键构造"""

    def test_key_format(self):
        """键格式为 workers-connections"""
        self.assertEqual(build_key(6, 500), "6-500")

    def test_key_with_large_values(self):
        """大数值同样适用"""
        self.assertEqual(build_key(16, 2000), "16-2000")


class TestLoadJson(unittest.TestCase):
    """JSON 加载"""

    def test_missing_file_returns_none(self):
        """文件不存在返回 None"""
        self.assertIsNone(load_json("/nonexistent/path/data.json"))

    def test_invalid_json_returns_none(self):
        """格式错误返回 None"""
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fp:
            fp.write("{invalid json")
            path = fp.name
        try:
            self.assertIsNone(load_json(path))
        finally:
            os.unlink(path)

    def test_valid_json_loaded(self):
        """正常文件被解析"""
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fp:
            json.dump({"a": 1}, fp)
            path = fp.name
        try:
            self.assertEqual(load_json(path), {"a": 1})
        finally:
            os.unlink(path)

    def test_non_dict_payload_returns_none(self):
        """顶层非字典返回 None"""
        import tempfile

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fp:
            json.dump([1, 2, 3], fp)
            path = fp.name
        try:
            self.assertIsNone(load_json(path))
        finally:
            os.unlink(path)


class TestCollectResults(unittest.TestCase):
    """结果索引"""

    def test_indexes_by_type_and_key(self):
        """按服务器类型与场景键建立索引"""
        data = {
            "results": [
                _make_result("litefs_greenlet", 6, 500, 16560.28, 75.33),
                _make_result("fastapi", 1, 1000, 5327.1, 209.88),
            ]
        }

        indexed = collect_results(data)

        self.assertIn(("litefs_greenlet", "6-500"), indexed)
        self.assertIn(("fastapi", "1-1000"), indexed)
        self.assertEqual(
            indexed[("litefs_greenlet", "6-500")]["requests_per_sec"], 16560.28
        )

    def test_skips_incomplete_items(self):
        """缺少关键字段的条目被跳过"""
        data = {
            "results": [
                {"server_type": "x"},
                {"workers": 1, "connections": 100},
                "not-a-dict",
            ]
        }

        self.assertEqual(collect_results(data), {})

    def test_empty_results(self):
        """空结果集"""
        self.assertEqual(collect_results({"results": []}), {})


class TestCompare(unittest.TestCase):
    """指标比对"""

    def setUp(self):
        """构造比对场景"""
        self.results = collect_results(
            {
                "results": [
                    _make_result("litefs_greenlet", 6, 500, 16560.28, 75.33),
                ]
            }
        )
        self.thresholds = {
            "litefs_greenlet": {
                "6-500": {"min_rps": 14000.0, "max_p99_ms": 98.0},
            }
        }

    def test_all_pass(self):
        """全部指标在阈值内"""
        comparisons = compare(self.results, self.thresholds)

        self.assertEqual(len(comparisons), 2)
        self.assertTrue(all(item[6] for item in comparisons))

    def test_rps_below_threshold_fails(self):
        """吞吐低于下限判定失败"""
        thresholds = {
            "litefs_greenlet": {
                "6-500": {"min_rps": 999999.0, "max_p99_ms": 98.0},
            }
        }

        comparisons = compare(self.results, thresholds)

        rps_item = [item for item in comparisons if item[3] == "requests_per_sec"][0]
        self.assertFalse(rps_item[6])

    def test_p99_above_threshold_fails(self):
        """P99 超过上限判定失败"""
        thresholds = {
            "litefs_greenlet": {
                "6-500": {"min_rps": 14000.0, "max_p99_ms": 50.0},
            }
        }

        comparisons = compare(self.results, thresholds)

        p99_item = [item for item in comparisons if item[3] == "latency_p99_ms"][0]
        self.assertFalse(p99_item[6])

    def test_boundary_values_pass(self):
        """恰好等于阈值判定通过"""
        thresholds = {
            "litefs_greenlet": {
                "6-500": {"min_rps": 16560.28, "max_p99_ms": 75.33},
            }
        }

        comparisons = compare(self.results, thresholds)

        self.assertTrue(all(item[6] for item in comparisons))

    def test_missing_scenario_skipped(self):
        """基线中不存在的场景不做判定"""
        thresholds = {
            "litefs_greenlet": {
                "1-100": {"min_rps": 999999.0, "max_p99_ms": 1.0},
            }
        }

        self.assertEqual(compare(self.results, thresholds), [])

    def test_only_rps_threshold_checked(self):
        """只配置吞吐阈值时只检查吞吐"""
        thresholds = {
            "litefs_greenlet": {
                "6-500": {"min_rps": 14000.0},
            }
        }

        comparisons = compare(self.results, thresholds)

        self.assertEqual(len(comparisons), 1)
        self.assertEqual(comparisons[0][3], "requests_per_sec")

    def test_invalid_threshold_entries_ignored(self):
        """非法阈值条目被忽略"""
        thresholds = {
            "litefs_greenlet": {
                "6-500": {"min_rps": "not-a-number", "max_p99_ms": None},
            },
            "not-a-dict": "oops",
        }

        self.assertEqual(compare(self.results, thresholds), [])


class TestFormatReport(unittest.TestCase):
    """报告格式化"""

    def test_report_contains_summary(self):
        """报告包含汇总信息"""
        comparisons = [
            ("litefs_greenlet", 6, 500, "requests_per_sec", 16560.28, 14000.0, True),
            ("litefs_greenlet", 6, 500, "latency_p99_ms", 75.33, 98.0, False),
        ]

        report = format_report(comparisons)

        self.assertIn("性能回归比对报告", report)
        self.assertIn("PASS", report)
        self.assertIn("FAIL", report)
        self.assertIn("2 项检查，1 项通过，1 项失败", report)


class TestMain(unittest.TestCase):
    """命令行入口"""

    def setUp(self):
        """准备临时结果与阈值文件"""
        import tempfile

        self.tmpdir = tempfile.mkdtemp()
        self.results_path = os.path.join(self.tmpdir, "data.json")
        self.thresholds_path = os.path.join(self.tmpdir, "thresholds.json")

        with open(self.results_path, "w", encoding="utf-8") as fp:
            json.dump(
                {
                    "results": [
                        _make_result("litefs_greenlet", 6, 500, 16560.28, 75.33),
                    ]
                },
                fp,
            )

    def tearDown(self):
        """清理临时目录"""
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_thresholds(self, payload):
        """写入阈值文件

        Args:
            payload: 阈值内容
        """
        with open(self.thresholds_path, "w", encoding="utf-8") as fp:
            json.dump(payload, fp)

    def test_pass_returns_zero(self):
        """全部通过返回 0"""
        self._write_thresholds(
            {
                "thresholds": {
                    "litefs_greenlet": {
                        "6-500": {"min_rps": 14000.0, "max_p99_ms": 98.0},
                    }
                }
            }
        )

        code = main(
            ["--results", self.results_path, "--thresholds", self.thresholds_path]
        )

        self.assertEqual(code, 0)

    def test_regression_returns_one(self):
        """存在回退返回 1"""
        self._write_thresholds(
            {
                "thresholds": {
                    "litefs_greenlet": {
                        "6-500": {"min_rps": 999999.0, "max_p99_ms": 98.0},
                    }
                }
            }
        )

        code = main(
            ["--results", self.results_path, "--thresholds", self.thresholds_path]
        )

        self.assertEqual(code, 1)

    def test_missing_files_skipped(self):
        """文件缺失时跳过并返回 0"""
        code = main(
            [
                "--results",
                os.path.join(self.tmpdir, "nope.json"),
                "--thresholds",
                os.path.join(self.tmpdir, "nope-th.json"),
            ]
        )

        self.assertEqual(code, 0)

    def test_missing_files_strict_returns_two(self):
        """严格模式下文件缺失返回 2"""
        code = main(
            [
                "--results",
                os.path.join(self.tmpdir, "nope.json"),
                "--thresholds",
                os.path.join(self.tmpdir, "nope-th.json"),
                "--strict",
            ]
        )

        self.assertEqual(code, 2)

    def test_empty_thresholds_skipped(self):
        """阈值为空时跳过"""
        self._write_thresholds({"thresholds": {}})

        code = main(
            ["--results", self.results_path, "--thresholds", self.thresholds_path]
        )

        self.assertEqual(code, 0)

    def test_json_output(self):
        """JSON 输出模式可用"""
        import io
        import contextlib

        self._write_thresholds(
            {
                "thresholds": {
                    "litefs_greenlet": {
                        "6-500": {"min_rps": 14000.0, "max_p99_ms": 98.0},
                    }
                }
            }
        )

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(
                [
                    "--results",
                    self.results_path,
                    "--thresholds",
                    self.thresholds_path,
                    "--json",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["total"], 2)
        self.assertEqual(payload["failed"], 0)


if __name__ == "__main__":
    unittest.main()
