#!/usr/bin/env python3
"""
LiteFS 性能测试脚本 - 简化版
直接使用 wrk 命令并解析输出
"""
import subprocess
import time
import json
import signal
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

@dataclass
class BenchmarkResult:
    name: str
    server_type: str
    workers: int
    scenario: str
    requests_total: int
    requests_per_sec: float
    duration_sec: float
    latency_avg_ms: float
    latency_p99_ms: float
    latency_max_ms: float
    throughput_mb_per_sec: float
    errors: int
    status: str = "success"

def run_command(cmd, cwd=None, capture_output=True):
    """运行命令"""
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd,
            capture_output=capture_output, 
            text=True, 
            timeout=60
        )
        return result
    except subprocess.TimeoutExpired:
        return None

def parse_wrk_output(output):
    """解析 wrk 输出"""
    lines = output.strip().split('\n')
    
    rps = 0.0
    avg_lat = 0.0
    p99_lat = 0.0
    max_lat = 0.0
    total_req = 0
    duration = 0.0
    errors = 0
    throughput = 0.0
    
    for line in lines:
        line = line.strip()
        # 解析Requests/sec
        if 'Requests/sec:' in line:
            parts = line.split(':')
            if len(parts) > 1:
                rps = float(parts[1].strip())
        # 解析平均延迟
        elif 'Latency' in line and 'Avg' in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == 'Avg':
                    val = parts[i+1].rstrip(',')
                    if 'ms' in val:
                        avg_lat = float(val.replace('ms', ''))
                    elif 'us' in val:
                        avg_lat = float(val.replace('us', '')) / 1000
        # 解析 P99 延迟
        elif '99%' in line:
            parts = line.split()
            for p in parts:
                if 'ms' in p:
                    p99_lat = float(p.replace('ms', ''))
                    break
                elif 'us' in p:
                    p99_lat = float(p.replace('us', '')) / 1000
                    break
        # 解析最大延迟
        elif 'Max' in line and not 'Latency' in line:
            parts = line.split(':')
            if len(parts) > 1:
                val = parts[1].strip().rstrip(',')
                if 'ms' in val:
                    max_lat = float(val.replace('ms', ''))
                elif 'us' in val:
                    max_lat = float(val.replace('us', '')) / 1000
        # 解析总请求数
        elif 'requests in' in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == 'in':
                    total_req = int(parts[i-1].replace(',', ''))
        # 解析测试时长
        elif 'Socket errors' in line:
            continue
        elif 'Non-2xx' in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if p == 'Non-2xx':
                    errors = int(parts[i+1])
        # 解析传输量
        elif 'requests in' in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if 'requests' in p:
                    duration = float(parts[i-1].replace(',', ''))
                    break
        # 解析每秒传输字节
        elif 'requests in' in line or 'GB' in line or 'MB' in line or 'KB' in line:
            pass
        # 解析 Socket errors
        elif 'connect:' in line:
            parts = line.split()
            for p in parts:
                if p.isdigit():
                    errors += int(p)
    
    # 如果无法解析，尝试备用方法
    if rps == 0 and total_req > 0 and duration > 0:
        rps = total_req / duration
    
    # 估算吞吐量 (假设响应大小约 1KB)
    throughput = rps * 1.0 / 1024  # MB/s
    
    return {
        'rps': rps,
        'avg_lat': avg_lat,
        'p99_lat': p99_lat,
        'max_lat': max_lat,
        'total_req': total_req,
        'duration': duration,
        'errors': errors,
        'throughput': throughput
    }

def test_server(name, server_cmd, cwd, port, test_path='/', threads=4, connections=100, duration=5, workers=1):
    """测试单个服务器"""
    print(f"\n{'='*50}")
    print(f"测试: {name}")
    print(f"命令: {' '.join(server_cmd)}")
    print(f"{'='*50}")
    
    # 清理可能存在的进程
    subprocess.run(f"lsof -ti:{port} | xargs -r kill -9 2>/dev/null", shell=True)
    time.sleep(0.5)
    
    # 启动服务器
    server_process = subprocess.Popen(
        server_cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待服务器启动
    print(f"等待服务器启动 (端口 {port})...")
    for i in range(20):
        try:
            result = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', f'http://127.0.0.1:{port}/'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.stdout == '200':
                print(f"服务器已就绪!")
                break
        except:
            pass
        time.sleep(0.5)
    else:
        print("服务器启动超时!")
        server_process.kill()
        return None
    
    # 预热
    print("预热服务器...")
    for _ in range(5):
        subprocess.run(['curl', '-s', f'http://127.0.0.1:{port}{test_path}'], capture_output=True)
    time.sleep(1)
    
    # 运行 wrk 测试
    print(f"运行 wrk 测试 (线程={threads}, 连接={connections}, 时长={duration}s)...")
    wrk_cmd = [
        'wrk',
        '-t', str(threads),
        '-c', str(connections),
        '-d', f'{duration}s',
        '--latency',
        f'http://127.0.0.1:{port}{test_path}'
    ]
    
    result = subprocess.run(wrk_cmd, capture_output=True, text=True, timeout=duration + 30)
    
    # 解析 wrk 输出
    parsed = parse_wrk_output(result.stdout)
    print(f"wrk 输出:\n{result.stdout}")
    
    # 关闭服务器
    server_process.terminate()
    try:
        server_process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        server_process.kill()
    
    # 清理端口
    subprocess.run(f"lsof -ti:{port} | xargs -r kill -9 2>/dev/null", shell=True)
    time.sleep(0.5)
    
    # 构建结果
    return BenchmarkResult(
        name=name,
        server_type=name.split('-')[0].lower() if '-' in name else name.lower(),
        workers=workers,
        scenario='hello_world',
        requests_total=parsed['total_req'],
        requests_per_sec=parsed['rps'],
        duration_sec=parsed['duration'] or duration,
        latency_avg_ms=parsed['avg_lat'],
        latency_p99_ms=parsed['p99_lat'],
        latency_max_ms=parsed['max_lat'],
        throughput_mb_per_sec=parsed['throughput'],
        errors=parsed['errors']
    )

def main():
    # 测试配置
    APPS_DIR = Path(__file__).parent / 'apps'
    RESULTS_DIR = Path(__file__).parent / 'results' / datetime.now().strftime('%Y%m%d_%H%M%S')
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 基础配置
    BASE_PORT = 8200
    THREADS = 4
    CONNECTIONS = 100
    DURATION = 5
    
    # 测试场景
    test_configs = [
        ('LiteFS-HTTP-1P', ['python', 'hello_greenlet.py'], APPS_DIR, BASE_PORT, 1),
        ('LiteFS-Asyncio-1P', ['python', 'hello_asyncio.py'], APPS_DIR, BASE_PORT + 1, 1),
        ('FastAPI-Uvicorn-1P', ['uvicorn', 'hello_fastapi:app', '--host', '0.0.0.0', '--port', str(BASE_PORT + 2), '--workers', '1'], APPS_DIR, BASE_PORT + 2, 1),
    ]
    
    results = []
    
    for name, cmd, cwd, port, workers in test_configs:
        result = test_server(
            name=name,
            server_cmd=cmd,
            cwd=str(cwd),
            port=port,
            threads=THREADS,
            connections=CONNECTIONS,
            duration=DURATION,
            workers=workers
        )
        if result:
            results.append(result)
            print(f"\n结果: RPS={result.requests_per_sec:.2f}, 延迟={result.latency_avg_ms:.2f}ms, P99={result.latency_p99_ms:.2f}ms")
    
    # 保存结果
    if results:
        data = [asdict(r) for r in results]
        data_path = RESULTS_DIR / 'data.json'
        with open(data_path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n结果已保存: {data_path}")
        
        # 打印汇总表
        print("\n" + "="*80)
        print("性能测试汇总")
        print("="*80)
        print(f"{'服务器':<25} {'RPS':>12} {'延迟(Avg)':>12} {'P99':>12} {'吞吐量':>12}")
        print("-"*80)
        for r in results:
            print(f"{r.name:<25} {r.requests_per_sec:>12.2f} {r.latency_avg_ms:>10.2f}ms {r.latency_p99_ms:>10.2f}ms {r.throughput_mb_per_sec:>10.2f}MB/s")
    
    return results

if __name__ == '__main__':
    main()
