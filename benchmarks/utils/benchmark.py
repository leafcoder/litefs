"""基准测试工具 - wrk 调用封装"""

import subprocess
import re
import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    server_type: str
    workers: int
    scenario: str
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
    duration_seconds: int = 10
    threads: int = 4
    connections: int = 100


class Benchmark:
    """wrk 基准测试封装"""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        threads: int = 4,
        connections: int = 100,
        duration: int = 10,
        warmup: int = 2,
    ):
        self.host = host
        self.port = port
        self.threads = threads
        self.connections = connections
        self.duration = duration
        self.warmup = warmup

    def run(
        self,
        path: str = "/",
        name: str = "test",
        server_type: str = "unknown",
        workers: int = 1,
        scenario: str = "hello_world",
    ) -> BenchmarkResult:
        """运行基准测试"""
        url = f"http://{self.host}:{self.port}{path}"

        # 使用 curl 预热
        print(f"[{name}] 预热...")
        warmup_success = False
        for i in range(self.warmup * 5):
            try:
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.stdout.strip() == "200":
                    warmup_success = True
                    print(f"[{name}] 预热成功")
                    break
            except Exception:
                pass
            time.sleep(0.2)

        if not warmup_success:
            print(f"[{name}] 预热失败，跳过测试")
            return self._create_empty_result(name, server_type, workers, scenario)

        time.sleep(1)

        # 运行 wrk 测试
        print(f"[{name}] 开始测试 ({self.duration}s)...")
        cmd = [
            "wrk",
            "-t", str(self.threads),
            "-c", str(self.connections),
            "-d", f"{self.duration}s",
            "--latency",
            url
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.duration + 30
            )
            output = result.stdout
            print(f"[{name}] wrk 输出:\n{output[:500]}")
        except subprocess.TimeoutExpired:
            print(f"[{name}] 测试超时")
            return self._create_empty_result(name, server_type, workers, scenario)
        except FileNotFoundError:
            print(f"[{name}] wrk 未安装")
            return self._create_empty_result(name, server_type, workers, scenario)

        return self._parse_output(name, server_type, workers, scenario, output)

    def _parse_output(self, name, server_type, workers, scenario, output) -> BenchmarkResult:
        """解析 wrk 输出"""
        rps = latency_avg = latency_p50 = latency_p75 = latency_p90 = latency_p99 = latency_max = throughput = 0.0
        total_requests = errors_count = 0

        # Requests/sec: 12345.67
        rps_match = re.search(r"Requests/sec:\s+([\d.]+)", output)
        if rps_match:
            rps = float(rps_match.group(1))

        # Latency   1.23ms   4.56%     7.89ms   12.34%    23.45ms
        avg_match = re.search(r"Latency\s+([\d.]+)(ms|us|s)\s+[\d.]+%", output)
        if avg_match:
            latency_avg = float(avg_match.group(1))
            if avg_match.group(2) == "us":
                latency_avg /= 1000
            elif avg_match.group(2) == "s":
                latency_avg *= 1000

        # 解析百分位延迟
        for line in output.split("\n"):
            if "50%" in line:
                m = re.search(r"50%\s+([\d.]+)(ms|us|s)", line)
                if m:
                    latency_p50 = float(m.group(1))
                    if m.group(2) == "us":
                        latency_p50 /= 1000
                    elif m.group(2) == "s":
                        latency_p50 *= 1000
            elif "75%" in line:
                m = re.search(r"75%\s+([\d.]+)(ms|us|s)", line)
                if m:
                    latency_p75 = float(m.group(1))
                    if m.group(2) == "us":
                        latency_p75 /= 1000
                    elif m.group(2) == "s":
                        latency_p75 *= 1000
            elif "90%" in line:
                m = re.search(r"90%\s+([\d.]+)(ms|us|s)", line)
                if m:
                    latency_p90 = float(m.group(1))
                    if m.group(2) == "us":
                        latency_p90 /= 1000
                    elif m.group(2) == "s":
                        latency_p90 *= 1000
            elif "99%" in line:
                m = re.search(r"99%\s+([\d.]+)(ms|us|s)", line)
                if m:
                    latency_p99 = float(m.group(1))
                    if m.group(2) == "us":
                        latency_p99 /= 1000
                    elif m.group(2) == "s":
                        latency_p99 *= 1000

        # Transfer/sec: 1.23MB/s
        throughput_match = re.search(r"Transfer/sec:\s+([\d.]+)(KB/s|MB/s)", output)
        if throughput_match:
            throughput = float(throughput_match.group(1))
            if throughput_match.group(2) == "KB/s":
                throughput /= 1024

        # 12345 requests in 10.00s
        req_match = re.search(r"(\d+)\s+requests in", output)
        if req_match:
            total_requests = int(req_match.group(1))

        # Non-2xx or 3xx responses: 123
        error_match = re.search(r"Non-2xx or 3xx responses:\s+(\d+)", output)
        if error_match:
            errors_count = int(error_match.group(1))

        errors_percent = (errors_count / total_requests * 100) if total_requests > 0 else 0

        return BenchmarkResult(
            name=name, server_type=server_type, workers=workers, scenario=scenario,
            requests_per_sec=rps, latency_avg_ms=latency_avg, latency_p50_ms=latency_p50,
            latency_p75_ms=latency_p75, latency_p90_ms=latency_p90, latency_p99_ms=latency_p99,
            latency_max_ms=latency_max, throughput_mb_s=throughput, total_requests=total_requests,
            errors_count=errors_count, errors_percent=errors_percent, duration_seconds=self.duration,
            threads=self.threads, connections=self.connections,
        )

    def _create_empty_result(self, name, server_type, workers, scenario) -> BenchmarkResult:
        return BenchmarkResult(
            name=name, server_type=server_type, workers=workers, scenario=scenario,
            requests_per_sec=0, latency_avg_ms=0, latency_p50_ms=0, latency_p75_ms=0,
            latency_p90_ms=0, latency_p99_ms=0, latency_max_ms=0, throughput_mb_s=0,
            total_requests=0, errors_count=0, errors_percent=0, duration_seconds=self.duration,
            threads=self.threads, connections=self.connections,
        )
