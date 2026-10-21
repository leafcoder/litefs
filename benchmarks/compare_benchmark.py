#!/usr/bin/env python3
# coding: utf-8

"""
性能回归比对脚本

读取基准测试结果与阈值基线，逐项比对吞吐（RPS）与 P99 延迟，
任一项越界即判定为性能回退并返回非零退出码。

用法::

    python benchmarks/compare_benchmark.py
    python benchmarks/compare_benchmark.py --results path/to/data.json
    python benchmarks/compare_benchmark.py --thresholds path/to/thresholds.json
    python benchmarks/compare_benchmark.py --strict      # 缺少阈值时也判定失败

设计要点：
- 仅依赖标准库，便于在 CI 容器中零安装运行
- 阈值文件或结果文件缺失时输出「跳过」而非直接失败，避免误伤流水线
- 支持 ``--json`` 输出机器可读结果，便于 CI 归档
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

# 脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 默认结果文件与阈值文件
DEFAULT_RESULTS = os.path.join(SCRIPT_DIR, "results", "latest", "data.json")
DEFAULT_THRESHOLDS = os.path.join(SCRIPT_DIR, "thresholds.json")

# 单项比对结果
# (server_type, workers, connections, 指标名, 实际值, 阈值, 是否通过)
Comparison = Tuple[str, int, int, str, float, float, bool]


def build_key(workers: int, connections: int) -> str:
    """
    构造阈值索引键

    Args:
        workers: 进程数
        connections: 并发连接数

    Returns:
        形如 ``6-500`` 的索引键
    """
    return f"{workers}-{connections}"


def load_json(path: str) -> Optional[Dict[str, Any]]:
    """
    读取 JSON 文件

    Args:
        path: 文件路径

    Returns:
        解析后的字典，文件不存在或格式错误时返回 None
    """
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def collect_results(data: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """
    从基准结果中提取可比较的数据

    Args:
        data: ``data.json`` 解析结果

    Returns:
        {(server_type, "workers-connections"): 结果项}
    """
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in data.get("results", []):
        if not isinstance(item, dict):
            continue
        server_type = item.get("server_type")
        workers = item.get("workers")
        connections = item.get("connections")
        if not server_type or workers is None or connections is None:
            continue
        key = (str(server_type), build_key(int(workers), int(connections)))
        indexed[key] = item
    return indexed


def compare(
    results: Dict[Tuple[str, str], Dict[str, Any]],
    thresholds: Dict[str, Any],
) -> List[Comparison]:
    """
    比对结果与阈值

    Args:
        results: 基准结果索引
        thresholds: 阈值配置，结构为 ``{server_type: {"workers-connections": {...}}}``

    Returns:
        比对明细列表
    """
    comparisons: List[Comparison] = []

    for server_type, cases in thresholds.items():
        if not isinstance(cases, dict):
            continue
        for case_key, limits in cases.items():
            if not isinstance(limits, dict):
                continue

            result = results.get((server_type, case_key))
            if result is None:
                # 基线中缺少该场景，不做判定
                continue

            workers, _, connections = case_key.partition("-")
            workers_num = int(workers) if workers.isdigit() else 0
            connections_num = int(connections) if connections.isdigit() else 0

            actual_rps = float(result.get("requests_per_sec", 0.0))
            actual_p99 = float(result.get("latency_p99_ms", 0.0))

            min_rps = limits.get("min_rps")
            if isinstance(min_rps, (int, float)):
                comparisons.append(
                    (
                        server_type,
                        workers_num,
                        connections_num,
                        "requests_per_sec",
                        actual_rps,
                        float(min_rps),
                        actual_rps >= float(min_rps),
                    )
                )

            max_p99 = limits.get("max_p99_ms")
            if isinstance(max_p99, (int, float)):
                comparisons.append(
                    (
                        server_type,
                        workers_num,
                        connections_num,
                        "latency_p99_ms",
                        actual_p99,
                        float(max_p99),
                        actual_p99 <= float(max_p99),
                    )
                )

    return comparisons


def format_report(comparisons: List[Comparison]) -> str:
    """
    格式化比对报告

    Args:
        comparisons: 比对明细

    Returns:
        可读文本报告
    """
    lines = []
    lines.append("=" * 78)
    lines.append("性能回归比对报告")
    lines.append("=" * 78)
    lines.append(
        f"{'场景':<28}{'指标':<22}{'实际值':>12}{'阈值':>12}  结论"
    )
    lines.append("-" * 78)

    failures = 0
    for server_type, workers, connections, metric, actual, limit, passed in comparisons:
        scenario = f"{server_type}-{workers}P-c{connections}"
        if metric == "requests_per_sec":
            actual_text = f"{actual:.2f} rps"
            limit_text = f">= {limit:.0f}"
        else:
            actual_text = f"{actual:.2f} ms"
            limit_text = f"<= {limit:.0f}"
        verdict = "PASS" if passed else "FAIL"
        if not passed:
            failures += 1
        lines.append(
            f"{scenario:<28}{metric:<22}{actual_text:>12}{limit_text:>12}  {verdict}"
        )

    lines.append("-" * 78)
    total = len(comparisons)
    lines.append(f"合计: {total} 项检查，{total - failures} 项通过，{failures} 项失败")
    lines.append("=" * 78)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """
    构造命令行参数解析器

    Returns:
        参数解析器
    """
    parser = argparse.ArgumentParser(
        description="Litefs 性能回归比对工具",
    )
    parser.add_argument(
        "--results",
        default=DEFAULT_RESULTS,
        help=f"基准结果文件路径（默认: {DEFAULT_RESULTS}）",
    )
    parser.add_argument(
        "--thresholds",
        default=DEFAULT_THRESHOLDS,
        help=f"阈值文件路径（默认: {DEFAULT_THRESHOLDS}）",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="结果或阈值缺失时判定为失败（默认仅提示跳过）",
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="以 JSON 格式输出结果，便于 CI 归档",
    )
    return parser


def _emit(as_json: bool, message: str) -> None:
    """
    输出结论信息

    JSON 模式下结论写入 stderr，保证 stdout 为纯净 JSON，便于 CI 解析。

    Args:
        as_json: 是否处于 JSON 输出模式
        message: 结论文本
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
        退出码：0 通过，1 存在回退，2 输入缺失且处于严格模式
    """
    args = build_parser().parse_args(argv)

    threshold_data = load_json(args.thresholds)
    result_data = load_json(args.results)

    if threshold_data is None:
        message = f"阈值文件缺失或格式错误: {args.thresholds}"
        if args.strict:
            print(f"[FAIL] {message}")
            return 2
        print(f"[SKIP] {message}，跳过性能回归比对")
        return 0

    if result_data is None:
        message = f"基准结果缺失或格式错误: {args.results}"
        if args.strict:
            print(f"[FAIL] {message}")
            return 2
        print(f"[SKIP] {message}，跳过性能回归比对")
        return 0

    thresholds = threshold_data.get("thresholds", {})
    if not isinstance(thresholds, dict) or not thresholds:
        message = f"阈值文件中没有有效的 thresholds 配置: {args.thresholds}"
        if args.strict:
            print(f"[FAIL] {message}")
            return 2
        print(f"[SKIP] {message}，跳过性能回归比对")
        return 0

    results = collect_results(result_data)
    comparisons = compare(results, thresholds)

    if not comparisons:
        message = "基线结果与阈值没有可比较的共同场景，跳过性能回归比对"
        if args.strict:
            print(f"[FAIL] {message}")
            return 2
        print(f"[SKIP] {message}")
        return 0

    failures = [item for item in comparisons if not item[6]]

    if args.as_json:
        payload = {
            "results_file": args.results,
            "thresholds_file": args.thresholds,
            "total": len(comparisons),
            "failed": len(failures),
            "passed": len(comparisons) - len(failures),
            "comparisons": [
                {
                    "server_type": server_type,
                    "workers": workers,
                    "connections": connections,
                    "metric": metric,
                    "actual": actual,
                    "limit": limit,
                    "passed": passed,
                }
                for server_type, workers, connections, metric, actual, limit, passed
                in comparisons
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_report(comparisons))

    if failures:
        print("")
        _emit(args.as_json, "[FAIL] 检测到性能回退，详见上方 FAIL 项")
        return 1

    print("")
    _emit(args.as_json, "[PASS] 性能回归比对通过，未检测到回退")
    return 0


if __name__ == "__main__":
    sys.exit(main())
