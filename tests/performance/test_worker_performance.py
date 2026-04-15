#!/usr/bin/env python
# coding: utf-8
"""
测试不同 worker 数量下的性能

测试 Litefs 和 FastAPI 在不同 worker 数量下的性能表现
"""

import subprocess
import time
import json

# 测试配置
workers = [1, 2, 4, 8]
test_duration = "10s"  # 测试时长

# 存储测试结果
results = {}


def run_wrk(url, duration):
    """运行 wrk 测试并解析结果"""
    cmd = f"wrk -t4 -c100 -d{duration} {url}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # 解析结果
    lines = result.stdout.split('\n')
    qps = 0
    latency = 0
    
    for line in lines:
        if 'Requests/sec:' in line:
            qps = float(line.split(':')[1].strip())
        elif 'Latency' in line and 'Avg' in line:
            # 提取平均延迟
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'Avg':
                    latency_str = parts[i+1]
                    if 'ms' in latency_str:
                        latency = float(latency_str.replace('ms', ''))
                    break
    
    return qps, latency


def start_server(framework, worker_count):
    """启动服务器"""
    # 为不同的 worker 数量使用不同的端口
    litefs_port = 8000 + worker_count * 2
    fastapi_port = 8001 + worker_count * 2
    
    # 清理可能占用这些端口的进程
    subprocess.run(f'lsof -ti :{litefs_port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    subprocess.run(f'lsof -ti :{fastapi_port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    
    # 清理相关进程
    if framework == "litefs":
        subprocess.run('pkill -9 -f "gunicorn.*asgi_example"', shell=True, capture_output=True)
        subprocess.run('pkill -9 -f "uvicorn.*asgi_example"', shell=True, capture_output=True)
        port = litefs_port
    else:  # fastapi
        subprocess.run('pkill -9 -f "gunicorn.*fastapi_example"', shell=True, capture_output=True)
        subprocess.run('pkill -9 -f "uvicorn.*fastapi_example"', shell=True, capture_output=True)
        port = fastapi_port
    
    # 等待端口释放
    time.sleep(3)
    
    # 启动服务器（使用 gunicorn + uvicorn）
    if framework == "litefs":
        cmd = f"gunicorn -w {worker_count} -k uvicorn.workers.UvicornWorker examples.asgi_example:application --bind 127.0.0.1:{port} --log-level error"
    else:  # fastapi
        cmd = f"gunicorn -w {worker_count} -k uvicorn.workers.UvicornWorker fastapi_example:app --chdir examples --bind 127.0.0.1:{port} --log-level error"
    
    process = subprocess.Popen(cmd, shell=True)
    time.sleep(4)  # 给服务器启动时间（多 worker 需要更长时间）
    return process, port


def stop_server(framework):
    """停止服务器进程"""
    # 直接清理端口占用的进程
    if framework == "litefs":
        # 清理 8000 端口
        subprocess.run('lsof -ti :8000 | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    else:  # fastapi
        # 清理 8001 端口
        subprocess.run('lsof -ti :8001 | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    
    # 清理相关进程
    if framework == "litefs":
        subprocess.run('pkill -9 -f "gunicorn.*asgi_example"', shell=True, capture_output=True)
        subprocess.run('pkill -9 -f "uvicorn.*asgi_example"', shell=True, capture_output=True)
    else:
        subprocess.run('pkill -9 -f "gunicorn.*fastapi_example"', shell=True, capture_output=True)
        subprocess.run('pkill -9 -f "uvicorn.*fastapi_example"', shell=True, capture_output=True)


def main():
    """主测试函数"""
    # 测试前先清理所有进程
    # 清理所有可能的端口
    for port in range(8000, 8020):
        subprocess.run(f'lsof -ti :{port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    # 清理相关进程
    subprocess.run('pkill -9 -f "gunicorn.*asgi_example"', shell=True, capture_output=True)
    subprocess.run('pkill -9 -f "uvicorn.*asgi_example"', shell=True, capture_output=True)
    subprocess.run('pkill -9 -f "gunicorn.*fastapi_example"', shell=True, capture_output=True)
    subprocess.run('pkill -9 -f "uvicorn.*fastapi_example"', shell=True, capture_output=True)
    time.sleep(3)  # 等待端口释放
    
    endpoints = ["/", "/async", "/user/123"]
    
    for worker in workers:
        print(f"\n=== Testing with {worker} workers ===")
        results[worker] = {}
        
        # 测试 Litefs
        print("\nStarting Litefs server...")
        litefs_process, litefs_port = start_server("litefs", worker)
        litefs_base = f"http://127.0.0.1:{litefs_port}"
        
        results[worker]["litefs"] = {}
        for endpoint in endpoints:
            url = f"{litefs_base}{endpoint}"
            print(f"Testing Litefs {endpoint}...")
            qps, latency = run_wrk(url, test_duration)
            results[worker]["litefs"][endpoint] = {
                "qps": qps,
                "latency": latency
            }
            print(f"  QPS: {qps:.2f}, Latency: {latency:.2f}ms")
        
        # 停止 Litefs 服务器
        subprocess.run('pkill -9 -f "gunicorn.*asgi_example"', shell=True, capture_output=True)
        subprocess.run('pkill -9 -f "uvicorn.*asgi_example"', shell=True, capture_output=True)
        subprocess.run(f'lsof -ti :{litefs_port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
        time.sleep(3)  # 等待端口释放
        
        # 测试 FastAPI
        print("\nStarting FastAPI server...")
        fastapi_process, fastapi_port = start_server("fastapi", worker)
        fastapi_base = f"http://127.0.0.1:{fastapi_port}"
        
        results[worker]["fastapi"] = {}
        for endpoint in endpoints:
            url = f"{fastapi_base}{endpoint}"
            print(f"Testing FastAPI {endpoint}...")
            qps, latency = run_wrk(url, test_duration)
            results[worker]["fastapi"][endpoint] = {
                "qps": qps,
                "latency": latency
            }
            print(f"  QPS: {qps:.2f}, Latency: {latency:.2f}ms")
        
        # 停止 FastAPI 服务器
        subprocess.run('pkill -9 -f "gunicorn.*fastapi_example"', shell=True, capture_output=True)
        subprocess.run('pkill -9 -f "uvicorn.*fastapi_example"', shell=True, capture_output=True)
        subprocess.run(f'lsof -ti :{fastapi_port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
        time.sleep(3)  # 等待端口释放
    
    # 保存结果
    with open("performance_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print("\n=== Test Results Summary ===")
    endpoints = ["/", "/async", "/user/123"]
    for worker in workers:
        print(f"\n{worker} workers:")
        for framework in ["litefs", "fastapi"]:
            print(f"  {framework.capitalize()}:")
            for endpoint in endpoints:
                data = results[worker][framework][endpoint]
                print(f"    {endpoint}: QPS={data['qps']:.2f}, Latency={data['latency']:.2f}ms")


if __name__ == "__main__":
    main()
