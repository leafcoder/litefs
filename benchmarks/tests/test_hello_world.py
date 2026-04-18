"""Hello World 性能测试"""

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
PORT_BASE = 8000
THREADS = 4
CONNECTIONS = 100
DURATION = 10
WARMUP = 2
APPS_DIR = Path(__file__).parent.parent / "apps"

# 所有服务器配置
# (名称, 服务器类型, 启动命令列表, 进程数)
SERVER_CONFIGS = [
    # LiteFS 原生 HTTP 服务器
    ("LiteFS-HTTP-1P", "litefs_http", ["python", "hello_greenlet.py"], 1),
    ("LiteFS-HTTP-6P", "litefs_http", ["python", "hello_greenlet.py"], 6),

    # LiteFS Asyncio 服务器
    ("LiteFS-Asyncio-1P", "litefs_asyncio", ["python", "hello_asyncio.py"], 1),
    ("LiteFS-Asyncio-6P", "litefs_asyncio", ["python", "hello_asyncio.py"], 6),

    # LiteFS WSGI + Gunicorn
    ("LiteFS-WSGI-Gunicorn-1P", "litefs_wsgi", ["gunicorn", "-w", "1", "-b", "0.0.0.0:{port}", "hello_wsgi:application"], 1),
    ("LiteFS-WSGI-Gunicorn-6P", "litefs_wsgi", ["gunicorn", "-w", "6", "-b", "0.0.0.0:{port}", "hello_wsgi:application"], 6),

    # LiteFS ASGI + Gunicorn + UvicornWorker
    ("LiteFS-ASGI-Gunicorn-1P", "litefs_asgi", ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "hello_asgi:application"], 1),
    ("LiteFS-ASGI-Gunicorn-6P", "litefs_asgi", ["gunicorn", "-w", "6", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "hello_asgi:application"], 6),

    # LiteFS ASGI + Uvicorn
    ("LiteFS-ASGI-Uvicorn-1P", "litefs_asgi", ["uvicorn", "hello_asgi:application", "--host", "0.0.0.0", "--port", "{port}", "--workers", "1"], 1),
    ("LiteFS-ASGI-Uvicorn-6P", "litefs_asgi", ["uvicorn", "hello_asgi:application", "--host", "0.0.0.0", "--port", "{port}", "--workers", "6"], 6),

    # FastAPI 对照组
    ("FastAPI-Uvicorn-1P", "fastapi", ["uvicorn", "hello_fastapi:app", "--host", "0.0.0.0", "--port", "{port}", "--workers", "1"], 1),
    ("FastAPI-Uvicorn-6P", "fastapi", ["uvicorn", "hello_fastapi:app", "--host", "0.0.0.0", "--port", "{port}", "--workers", "6"], 6),
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


def build_cmd(name, cmd_list, port, workers):
    """构建命令，设置环境变量和工作目录"""
    actual_cmd = []
    for c in cmd_list:
        if isinstance(c, str):
            c = c.replace("{port}", str(port))
        actual_cmd.append(c)

    # 设置工作目录
    cwd = str(APPS_DIR)

    return actual_cmd, cwd


@pytest.mark.parametrize("name,server_type,cmd,workers", SERVER_CONFIGS)
def test_hello_world_benchmark(
    name, server_type, cmd, workers,
    benchmark_results, results_dir
):
    """Hello World 性能测试"""
    port = PORT_BASE + SERVER_CONFIGS.index((name, server_type, cmd, workers))

    # 清理可能占用端口的进程
    kill_port(port)

    # 构建命令
    actual_cmd, cwd = build_cmd(name, cmd, port, workers)

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
            path="/",
            name=name,
            server_type=server_type,
            workers=workers,
            scenario="hello_world",
        )

        # 保存结果
        benchmark_results.append(asdict(result))

        # 打印结果
        print(f"\n[{name}] RPS: {result.requests_per_sec:.2f} | "
              f"延迟 AVG: {result.latency_avg_ms:.2f}ms | "
              f"P99: {result.latency_p99_ms:.2f}ms | "
              f"错误率: {result.errors_percent:.2f}%")


def test_generate_report(benchmark_results, results_dir):
    """生成测试报告"""
    if not benchmark_results:
        pytest.skip("没有测试结果")

    # 保存 JSON
    report = TestReport.from_results(
        benchmark_results,
        duration=DURATION,
        connections=CONNECTIONS,
        threads=THREADS,
    )
    report.to_json(os.path.join(results_dir, "hello_world.json"))

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
