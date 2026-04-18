#!/usr/bin/env python
"""运行性能测试"""

import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.server import ServerManager, ServerConfig, kill_port
from utils.benchmark import Benchmark
from utils.report import generate_html_report, print_summary
from dataclasses import asdict
import json
import shutil

# 测试配置
PORT_BASE = 8000
THREADS = 4
CONNECTIONS = 100
DURATION = 5  # 缩短测试时间以便快速验证
WARMUP = 1
APPS_DIR = Path(__file__).parent / "apps"

# 完整的测试配置
TEST_CONFIGS = [
    # LiteFS 原生 HTTP
    ("LiteFS-HTTP-1P", "litefs_http", ["python", "hello_greenlet.py"], 1),
    ("LiteFS-HTTP-6P", "litefs_http", ["python", "hello_greenlet.py"], 6),

    # LiteFS Asyncio
    ("LiteFS-Asyncio-1P", "litefs_asyncio", ["python", "hello_asyncio.py"], 1),
    ("LiteFS-Asyncio-6P", "litefs_asyncio", ["python", "hello_asyncio.py"], 6),

    # WSGI + Gunicorn
    ("LiteFS-WSGI-1P", "litefs_wsgi", ["gunicorn", "-w", "1", "-b", "0.0.0.0:{port}", "hello_wsgi:application"], 1),
    ("LiteFS-WSGI-6P", "litefs_wsgi", ["gunicorn", "-w", "6", "-b", "0.0.0.0:{port}", "hello_wsgi:application"], 6),

    # ASGI + Uvicorn
    ("LiteFS-ASGI-Uvicorn-1P", "litefs_asgi", ["uvicorn", "hello_asgi:application", "--host", "0.0.0.0", "--port", "{port}", "--workers", "1"], 1),
    ("LiteFS-ASGI-Uvicorn-6P", "litefs_asgi", ["uvicorn", "hello_asgi:application", "--host", "0.0.0.0", "--port", "{port}", "--workers", "6"], 6),

    # ASGI + Gunicorn
    ("LiteFS-ASGI-Gunicorn-1P", "litefs_asgi", ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "hello_asgi:application"], 1),
    ("LiteFS-ASGI-Gunicorn-6P", "litefs_asgi", ["gunicorn", "-w", "6", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "hello_asgi:application"], 6),

    # FastAPI 对照组
    ("FastAPI-Uvicorn-1P", "fastapi", ["uvicorn", "hello_fastapi:app", "--host", "0.0.0.0", "--port", "{port}", "--workers", "1"], 1),
    ("FastAPI-Uvicorn-6P", "fastapi", ["uvicorn", "hello_fastapi:app", "--host", "0.0.0.0", "--port", "{port}", "--workers", "6"], 6),
]

# SQL 测试配置
SQL_CONFIGS = [
    ("LiteFS-HTTP-SQL-1P", "litefs_http", ["python", "sql_app.py"], 1),
    ("LiteFS-HTTP-SQL-6P", "litefs_http", ["python", "sql_app.py"], 6),
    ("LiteFS-WSGI-SQL-1P", "litefs_wsgi", ["gunicorn", "-w", "1", "-b", "0.0.0.0:{port}", "sql_app:application"], 1),
    ("LiteFS-WSGI-SQL-6P", "litefs_wsgi", ["gunicorn", "-w", "6", "-b", "0.0.0.0:{port}", "sql_app:application"], 6),
    ("LiteFS-ASGI-SQL-1P", "litefs_asgi", ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "sql_app:application"], 1),
    ("LiteFS-ASGI-SQL-6P", "litefs_asgi", ["gunicorn", "-w", "6", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:{port}", "sql_app:application"], 6),
]


def build_cmd(cmd_list, port, workers):
    actual_cmd = []
    for c in cmd_list:
        if isinstance(c, str):
            c = c.replace("{port}", str(port))
        actual_cmd.append(c)
    return actual_cmd, str(APPS_DIR)


def run_benchmark(name, server_type, cmd, workers, port, path="/", scenario="hello_world"):
    """运行单个基准测试"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")

    kill_port(port)

    actual_cmd, cwd = build_cmd(cmd, port, workers)

    config = ServerConfig(cmd=actual_cmd, port=port, name=name, wait_ready=5 if workers > 1 else 3, cwd=cwd)
    benchmarker = Benchmark(
        host="127.0.0.1",
        port=port,
        threads=THREADS,
        connections=CONNECTIONS,
        duration=DURATION,
        warmup=WARMUP,
    )

    try:
        with ServerManager(config):
            result = benchmarker.run(path=path, name=name, server_type=server_type, workers=workers, scenario=scenario)
            print(f"[{name}] RPS: {result.requests_per_sec:.2f} | 延迟: {result.latency_avg_ms:.2f}ms | P99: {result.latency_p99_ms:.2f}ms")
            return asdict(result)
    except Exception as e:
        print(f"[{name}] 测试失败: {e}")
        return None


def main():
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(__file__).parent / "results" / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)

    all_results = []

    # Hello World 测试
    print("\n" + "="*70)
    print("Hello World 性能测试")
    print("="*70)

    for i, (name, server_type, cmd, workers) in enumerate(TEST_CONFIGS):
        port = PORT_BASE + i
        result = run_benchmark(name, server_type, cmd, workers, port, "/", "hello_world")
        if result:
            all_results.append(result)

    # SQL 查询测试
    print("\n" + "="*70)
    print("SQL 查询性能测试")
    print("="*70)

    # 初始化数据库
    sql_port = 8900
    print("\n初始化 SQL 测试数据库...")
    kill_port(sql_port)
    init_cmd = ["python", "sql_app.py"]
    from utils.server import ServerConfig
    init_config = ServerConfig(cmd=init_cmd, port=sql_port, name="sql_init", wait_ready=3, cwd=str(APPS_DIR))

    try:
        import httpx
        with ServerManager(init_config):
            httpx.get(f"http://127.0.0.1:{sql_port}/init", timeout=5)
            print("数据库初始化完成")
    except Exception as e:
        print(f"数据库初始化失败: {e}")

    for i, (name, server_type, cmd, workers) in enumerate(SQL_CONFIGS):
        port = 8901 + i
        result = run_benchmark(name, server_type, cmd, workers, port, "/query", "sql_query")
        if result:
            all_results.append(result)

    # 保存结果
    json_path = results_dir / "data.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nJSON 结果已保存: {json_path}")

    # 生成 HTML 报告
    html_path = generate_html_report(all_results, duration=DURATION, connections=CONNECTIONS, threads=THREADS, output_dir=str(results_dir))

    # 打印摘要
    print_summary(all_results)

    print(f"\n测试完成！")
    print(f"报告位置: {html_path}")


if __name__ == "__main__":
    main()
