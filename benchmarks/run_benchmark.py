#!/usr/bin/env python3
"""性能基准测试脚本 - 重新设计版本"""

import subprocess
import time
import os
import sys
import json
import signal
import random
import shutil
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from pathlib import Path

# 配置
APPS_DIR = "/home/zhanglei3/Desktop/dev/litefs/benchmarks/apps"
RESULTS_DIR = "/home/zhanglei3/Desktop/dev/litefs/benchmarks/results"
WRK_THREADS = 4
TEST_DURATION = 10  # 秒

# 简化 PATH，避免 "参数列表过长" 错误
import os as _os
_home = _os.path.expanduser("~")
_extra_paths = f"{_home}/Installed"
_base_paths = "/usr/local/bin:/usr/bin:/bin"
_pyenv_paths = f"{_home}/.pyenv/shims:{_home}/.pyenv/bin"
_os.environ["PATH"] = f"{_pyenv_paths}:{_extra_paths}:{_base_paths}"


@dataclass
class TestConfig:
    """测试配置"""
    name: str           # 测试名称 (如 LiteFS-Greenlet)
    short_name: str     # 短名称 (如 greenlet)
    server_type: str    # 服务器类型
    cmd_template: str   # 启动命令模板，{port} 和 {workers} 占位
    cwd: str            # 工作目录
    default_workers: int = 1


@dataclass
class BenchmarkResult:
    """单次测试结果"""
    test_name: str
    server_type: str
    workers: int
    connections: int
    requests_per_sec: float = 0.0
    latency_avg_ms: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p75_ms: float = 0.0
    latency_p90_ms: float = 0.0
    latency_p99_ms: float = 0.0
    latency_max_ms: float = 0.0
    throughput_mb_s: float = 0.0
    total_requests: int = 0
    errors_count: int = 0
    errors_percent: float = 0.0


# 测试配置矩阵
PYTHON_CMD = "python"  # 使用系统 PATH 中的 python

TEST_CONFIGS = [
    # LiteFS Greenlet - 原生 HTTP 服务器
    TestConfig(
        name="LiteFS-Greenlet",
        short_name="litefs_greenlet",
        server_type="litefs_greenlet",
        cmd_template="python hello_greenlet.py --port {port}",
        cwd=APPS_DIR,
    ),
    # LiteFS ASGI + Uvicorn
    TestConfig(
        name="LiteFS-ASGI/Uvicorn",
        short_name="litefs_asgi_uvicorn",
        server_type="litefs_asgi",
        cmd_template="python -m uvicorn hello_asgi:application --host 0.0.0.0 --port {port} --workers {workers}",
        cwd=APPS_DIR,
    ),
    # LiteFS WSGI + Gunicorn (gevent)
    TestConfig(
        name="LiteFS-WSGI/Gunicorn",
        short_name="litefs_wsgi_gunicorn",
        server_type="litefs_wsgi",
        cmd_template="python -m gunicorn hello_wsgi:application -b 0.0.0.0:{port} -w {workers} -k gevent --worker-connections 1000",
        cwd=APPS_DIR,
    ),
    # FastAPI + Uvicorn
    TestConfig(
        name="FastAPI/Uvicorn",
        short_name="fastapi_uvicorn",
        server_type="fastapi",
        cmd_template="python -m uvicorn hello_fastapi:app --host 0.0.0.0 --port {port} --workers {workers}",
        cwd=APPS_DIR,
    ),
]

# 进程数配置
WORKERS_LIST = [1, 6]

# 并发数配置
CONNECTIONS_LIST = [500, 1000]


def find_free_port(start_port: int = 18000, end_port: int = 19000) -> int:
    """查找空闲端口"""
    for _ in range(end_port - start_port):
        port = random.randint(start_port, end_port)
        result = subprocess.run(
            f"lsof -i :{port} 2>/dev/null | grep LISTEN || true",
            shell=True, capture_output=True, text=True
        )
        if not result.stdout.strip():
            return port
    raise RuntimeError("无法找到空闲端口")


def is_port_in_use(port: int) -> bool:
    """检查端口是否被占用"""
    result = subprocess.run(
        f"lsof -i :{port} 2>/dev/null | grep LISTEN || true",
        shell=True, capture_output=True, text=True
    )
    return bool(result.stdout.strip())


def cleanup_port(port: int) -> None:
    """清理指定端口"""
    subprocess.run(f"fuser -k {port}/tcp 2>/dev/null || true", shell=True)
    time.sleep(0.5)


def cleanup_all_ports(used_ports: List[int]) -> None:
    """统一清理所有使用的端口"""
    print("\n" + "="*60)
    print("清理测试端口...")
    print("="*60)
    
    for port in used_ports:
        cleanup_port(port)
        if not is_port_in_use(port):
            print(f"  ✅ 端口 {port} 已释放")
        else:
            print(f"  ⚠️ 端口 {port} 释放失败")
    
    # 额外清理可能残留的测试进程
    for pattern in ["hello_greenlet", "hello_asgi", "hello_wsgi", "hello_fastapi", 
                    "uvicorn", "gunicorn"]:
        subprocess.run(f"pkill -9 -f {pattern} 2>/dev/null || true", shell=True)
    
    time.sleep(1)
    print("清理完成\n")


def get_process_count_by_port(port: int) -> int:
    """通过端口获取进程个数（包括子进程）"""
    # 获取主进程 PID
    result = subprocess.run(
        f"lsof -ti:{port} 2>/dev/null",
        shell=True, capture_output=True, text=True
    )
    pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
    if not pids:
        return 1
    
    # 通过主进程获取其子进程数
    count = 0
    for pid in pids:
        try:
            # 获取子进程
            pgrep_result = subprocess.run(
                f"pgrep -P {pid}",
                shell=True, capture_output=True, text=True
            )
            children = [p.strip() for p in pgrep_result.stdout.strip().split('\n') if p.strip()]
            count += 1 + len(children)  # 主进程 + 子进程
        except Exception:
            count += 1
    
    return max(count, 1)


def start_server(cmd_template: str, port: int, workers: int, cwd: str) -> Optional[subprocess.Popen]:
    """启动服务器"""
    cmd = cmd_template.format(port=port, workers=workers)
    cmd_list = cmd.split()
    
    env = os.environ.copy()
    env["WORKERS"] = str(workers)  # 设置 WORKERS 环境变量
    
    print(f"    启动命令: {cmd}")
    print(f"    工作目录: {cwd}")
    print(f"    WORKERS={workers}")
    
    try:
        proc = subprocess.Popen(
            cmd_list,
            cwd=cwd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )
        
        # 等待端口就绪
        for _ in range(30):
            if is_port_in_use(port):
                # 验证服务响应
                time.sleep(0.5)
                result = subprocess.run(
                    f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{port}/",
                    shell=True, capture_output=True, text=True, timeout=3
                )
                if result.stdout.strip() in ["200", "404"]:
                    return proc
            time.sleep(0.2)
        
        # 超时，终止进程
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        return None
        
    except Exception as e:
        print(f"  启动服务器失败: {e}")
        return None


def stop_server(proc: subprocess.Popen) -> None:
    """停止服务器"""
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        proc.wait(timeout=3)
    except:
        try:
            pgid = os.getpgid(proc.pid)
            os.killpg(pgid, signal.SIGKILL)
        except:
            pass


def run_wrk_test(url: str, connections: int, duration: int) -> Optional[Dict[str, Any]]:
    """运行 wrk 测试并解析结果"""
    cmd = [
        "wrk",
        "-t", str(WRK_THREADS),
        "-c", str(connections),
        "-d", f"{duration}s",
        "--latency",
        url
    ]
    
    print(f"    测试命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=duration + 30
        )
        return parse_wrk_output(result.stdout)
    except subprocess.TimeoutExpired:
        print(f"    wrk 测试超时")
        return None
    except FileNotFoundError:
        print(f"    wrk 未安装")
        return None


def parse_wrk_output(output: str) -> Dict[str, Any]:
    """解析 wrk 输出"""
    import re
    
    data = {
        "requests_per_sec": 0.0,
        "latency_avg_ms": 0.0,
        "latency_p50_ms": 0.0,
        "latency_p75_ms": 0.0,
        "latency_p90_ms": 0.0,
        "latency_p99_ms": 0.0,
        "latency_max_ms": 0.0,
        "throughput_mb_s": 0.0,
        "total_requests": 0,
        "errors_count": 0,
        "errors_percent": 0.0,
    }
    
    # Requests/sec: 12345.67
    rps_match = re.search(r"Requests/sec:\s+([\d.]+)", output)
    if rps_match:
        data["requests_per_sec"] = float(rps_match.group(1))
    
    # Latency   1.23ms
    avg_match = re.search(r"Latency\s+([\d.]+)(ms|us|s)\s+[\d.]+%", output)
    if avg_match:
        val = float(avg_match.group(1))
        unit = avg_match.group(2)
        if unit == "us":
            val /= 1000
        elif unit == "s":
            val *= 1000
        data["latency_avg_ms"] = val
    
    # 解析百分位延迟
    for line in output.split("\n"):
        m = re.search(r"(\d+)%\s+([\d.]+)(ms|us|s)", line)
        if m:
            pct = int(m.group(1))
            val = float(m.group(2))
            unit = m.group(3)
            if unit == "us":
                val /= 1000
            elif unit == "s":
                val *= 1000
            
            if pct == 50:
                data["latency_p50_ms"] = val
            elif pct == 75:
                data["latency_p75_ms"] = val
            elif pct == 90:
                data["latency_p90_ms"] = val
            elif pct == 99:
                data["latency_p99_ms"] = val
    
    # Max: 123.45ms
    max_match = re.search(r"Max:\s+([\d.]+)(ms|us|s)", output)
    if max_match:
        val = float(max_match.group(1))
        unit = max_match.group(2)
        if unit == "us":
            val /= 1000
        elif unit == "s":
            val *= 1000
        data["latency_max_ms"] = val
    
    # Transfer/sec: 1.23MB/s
    throughput_match = re.search(r"Transfer/sec:\s+([\d.]+)(KB/s|MB/s)", output)
    if throughput_match:
        val = float(throughput_match.group(1))
        if throughput_match.group(2) == "KB/s":
            val /= 1024
        data["throughput_mb_s"] = val
    
    # Total requests
    req_match = re.search(r"(\d+)\s+requests in", output)
    if req_match:
        data["total_requests"] = int(req_match.group(1))
    
    # Non-2xx or 3xx responses
    error_match = re.search(r"Non-2xx or 3xx responses:\s+(\d+)", output)
    if error_match:
        data["errors_count"] = int(error_match.group(1))
    
    if data["total_requests"] > 0:
        data["errors_percent"] = data["errors_count"] / data["total_requests"] * 100
    
    return data


def run_single_test(config: TestConfig, workers: int, connections: int, port: int) -> Optional[BenchmarkResult]:
    """运行单个测试"""
    test_name = f"{config.name}-{workers}P-c{connections}"
    print(f"\n  测试: {test_name} (端口 {port})")
    
    # 启动服务器
    proc = start_server(config.cmd_template, port, workers, config.cwd)
    if not proc:
        print(f"    ❌ 服务器启动失败")
        return None
    
    try:
        # 运行 wrk 测试
        url = f"http://127.0.0.1:{port}/"
        wrk_data = run_wrk_test(url, connections, TEST_DURATION)
        
        if not wrk_data:
            print(f"    ❌ wrk 测试失败")
            return None
        
        # 获取实际进程数（通过端口）
        proc_count = get_process_count_by_port(port)
        
        result = BenchmarkResult(
            test_name=test_name,
            server_type=config.server_type,
            workers=workers,
            connections=connections,
            **wrk_data
        )
        
        print(f"    ✅ RPS: {result.requests_per_sec:.2f}, P99: {result.latency_p99_ms:.2f}ms, 进程: {proc_count}")
        return result
        
    finally:
        stop_server(proc)


def save_results(results: List[BenchmarkResult], timestamp: str) -> str:
    """保存测试结果到 JSON"""
    results_dir = Path(RESULTS_DIR) / timestamp
    results_dir.mkdir(parents=True, exist_ok=True)
    
    data_file = results_dir / "data.json"
    
    data = {
        "timestamp": timestamp,
        "test_config": {
            "wrk_threads": WRK_THREADS,
            "test_duration": TEST_DURATION,
            "workers": WORKERS_LIST,
            "connections": CONNECTIONS_LIST,
        },
        "results": [asdict(r) for r in results]
    }
    
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 更新 latest 链接
    latest_dir = Path(RESULTS_DIR) / "latest"
    if latest_dir.is_symlink() or latest_dir.exists():
        if latest_dir.is_symlink():
            latest_dir.unlink()
        elif latest_dir.is_dir():
            import shutil as _shutil
            _shutil.rmtree(latest_dir)
    latest_dir.symlink_to(results_dir, target_is_directory=True)
    
    return str(data_file)


def print_summary(results: List[BenchmarkResult]) -> None:
    """打印测试汇总"""
    print("\n" + "="*80)
    print("性能测试汇总")
    print("="*80)
    
    # 按服务器类型分组
    servers = {}
    for r in results:
        key = r.server_type
        if key not in servers:
            servers[key] = []
        servers[key].append(r)
    
    for server, server_results in servers.items():
        print(f"\n【{server.upper()}】")
        print(f"{'测试名称':<30} {'进程':>4} {'并发':>6} {'RPS':>12} {'P99延迟':>10} {'错误率':>8}")
        print("-"*80)
        
        for r in sorted(server_results, key=lambda x: (x.workers, x.connections)):
            err_pct = f"{r.errors_percent:.2f}%" if r.errors_percent > 0 else "-"
            print(f"{r.test_name:<30} {r.workers:>4} {r.connections:>6} {r.requests_per_sec:>12.2f} {r.latency_p99_ms:>9.2f}ms {err_pct:>8}")


def main():
    # 打印系统信息
    print("="*80)
    print("系统配置信息")
    print("="*80)
    try:
        # CPU 信息
        cpu_info = subprocess.run(
            "lscpu | grep -E 'Model name|Socket|Core|Thread|CPU\\(s\\)' | head -5",
            shell=True, capture_output=True, text=True
        )
        print(cpu_info.stdout.strip() if cpu_info.stdout.strip() else f"CPU 核心数: {os.cpu_count()}")
        
        # 内存信息
        mem_info = subprocess.run("free -h | head -2", shell=True, capture_output=True, text=True)
        print(mem_info.stdout.strip())
        
        # Python 版本
        py_ver = subprocess.run(["python", "--version"], capture_output=True, text=True)
        print(f"Python: {py_ver.stdout.strip()}")
        
        # 操作系统
        os_info = subprocess.run("uname -a", shell=True, capture_output=True, text=True)
        print(f"OS: {os_info.stdout.strip()}")
        
        # wrk 版本
        wrk_ver = subprocess.run(["wrk", "--version"], capture_output=True, text=True, timeout=3)
        if wrk_ver.stdout:
            print(f"wrk: {wrk_ver.stdout.strip().splitlines()[0]}")
    except Exception:
        pass
    
    print("\n" + "="*80)
    print("性能基准测试")
    print(f"测试服务器: {len(TEST_CONFIGS)} 种")
    print(f"进程数: {WORKERS_LIST}")
    print(f"并发数: {CONNECTIONS_LIST}")
    print(f"测试时长: {TEST_DURATION}s")
    print(f"预计测试次数: {len(TEST_CONFIGS) * len(WORKERS_LIST) * len(CONNECTIONS_LIST)}")
    print("="*80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results: List[BenchmarkResult] = []
    used_ports: List[int] = []
    
    try:
        total_tests = len(TEST_CONFIGS) * len(WORKERS_LIST) * len(CONNECTIONS_LIST)
        current_test = 0
        
        for config in TEST_CONFIGS:
            for workers in WORKERS_LIST:
                for connections in CONNECTIONS_LIST:
                    current_test += 1
                    print(f"\n[{current_test}/{total_tests}] {config.name} - {workers}进程 - {connections}并发")
                    
                    # 分配端口
                    port = find_free_port()
                    used_ports.append(port)
                    
                    # 运行测试
                    result = run_single_test(config, workers, connections, port)
                    if result:
                        results.append(result)
                    
                    # 清理端口
                    cleanup_port(port)
                    time.sleep(1)
        
        # 保存结果
        if results:
            result_file = save_results(results, timestamp)
            print(f"\n结果已保存: {result_file}")
            print_summary(results)
    
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    
    finally:
        # 统一清理
        cleanup_all_ports(used_ports)
    
    return results


if __name__ == "__main__":
    main()
