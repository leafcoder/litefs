"""SQL 查询性能测试"""

import pytest
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.server import ServerManager, ServerConfig, kill_port
from utils.benchmark import Benchmark
from utils.report import TestReport, print_summary, generate_html_report
from dataclasses import asdict


# 测试配置
PORT_BASE = 9000
THREADS = 4
CONNECTIONS = 50
DURATION = 10
WARMUP = 2
APPS_DIR = Path(__file__).parent.parent / "apps"

# SQL 测试服务器配置
SQL_SERVER_CONFIGS = [
    # LiteFS 原生 HTTP 服务器
    ("LiteFS-HTTP-SQL-1P", "litefs_http", ["python", "sql_app.py"], 1),
    ("LiteFS-HTTP-SQL-6P", "litefs_http", ["python", "sql_app.py"], 6),

    # LiteFS WSGI + Gunicorn
    ("LiteFS-WSGI-SQL-1P", "litefs_wsgi", ["gunicorn", "-w", "1", "-b", "0.0.0.0:{port}", "sql_app:application"], 1),
    ("LiteFS-WSGI-SQL-6P", "litefs_wsgi", ["gunicorn", "-w", "6", "-b", "0.0.0.0:{port}", "sql_app:application"], 6),

    # LiteFS ASGI + Gunicorn + UvicornWorker
    ("LiteFS-ASGI-SQL-1P", "litefs_asgi", ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "sql_app:application"], 1),
    ("LiteFS-ASGI-SQL-6P", "litefs_asgi", ["gunicorn", "-w", "6", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "sql_app:application"], 6),
]


@pytest.fixture(scope="module")
def results_dir():
    """创建结果目录"""
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_path = Path(__file__).parent.parent / "results" / timestamp
    dir_path.mkdir(parents=True, exist_ok=True)
    return str(dir_path)


@pytest.fixture(scope="module")
def benchmark_results():
    """存储所有测试结果"""
    return []


def build_cmd(cmd_list, port, workers):
    """构建命令"""
    actual_cmd = []
    for c in cmd_list:
        if isinstance(c, str):
            c = c.replace("{port}", str(port))
        actual_cmd.append(c)
    return actual_cmd, str(APPS_DIR)


@pytest.mark.parametrize("name,server_type,cmd,workers", SQL_SERVER_CONFIGS)
def test_sql_query_benchmark(
    name, server_type, cmd, workers,
    benchmark_results, results_dir
):
    """SQL 查询性能测试"""
    port = PORT_BASE + SQL_SERVER_CONFIGS.index((name, server_type, cmd, workers))

    # 清理端口
    kill_port(port)

    # 构建命令
    actual_cmd, cwd = build_cmd(cmd, port, workers)

    # 设置环境变量
    env = os.environ.copy()
    env["WORKERS"] = str(workers)

    config = ServerConfig(
        cmd=actual_cmd,
        port=port,
        name=name,
        wait_ready=5 if workers > 1 else 3,
        cwd=cwd,
    )

    benchmarker = Benchmark(
        host="127.0.0.1",
        port=port,
        threads=THREADS,
        connections=CONNECTIONS,
        duration=DURATION,
        warmup=WARMUP,
    )

    with ServerManager(config):
        result = benchmarker.run(
            path="/query",
            name=name,
            server_type=server_type,
            workers=workers,
            scenario="sql_query",
        )

        benchmark_results.append(asdict(result))

        print(f"\n[{name}] RPS: {result.requests_per_sec:.2f} | "
              f"延迟 AVG: {result.latency_avg_ms:.2f}ms | "
              f"P99: {result.latency_p99_ms:.2f}ms | "
              f"错误率: {result.errors_percent:.2f}%")


def test_generate_sql_report(benchmark_results, results_dir):
    """生成 SQL 测试报告"""
    if not benchmark_results:
        pytest.skip("没有测试结果")

    # 保存 JSON
    report = TestReport.from_results(
        benchmark_results,
        duration=DURATION,
        connections=CONNECTIONS,
        threads=THREADS,
    )
    report.to_json(os.path.join(results_dir, "sql_query.json"))

    # 生成 HTML
    generate_html_report(
        benchmark_results,
        duration=DURATION,
        connections=CONNECTIONS,
        threads=THREADS,
        output_dir=results_dir,
    )

    # 打印摘要
    print_summary(benchmark_results)
