#!/usr/bin/env python
# coding: utf-8
"""
性能对比测试：greenlet vs asyncio

测试两种 HTTP 服务器实现的性能差异：
1. greenlet 版本：使用 epoll + greenlet 实现协程
2. asyncio 版本：使用 asyncio 原生事件循环和协程
"""

import subprocess
import time
import os
import sys
import signal
import requests
from typing import Dict, List, Tuple

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

# 测试配置
test_duration = "10s"  # 测试持续时间
cores = [1, 2, 4, 8]   # 测试的核心数
endpoints = ["/", "/async", "/user/123"]  # 测试的端点


def check_url_health(url: str, max_retries: int = 5, retry_interval: int = 1) -> bool:
    """检查 URL 是否健康"""
    for i in range(max_retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ URL {url} 健康检查通过")
                return True
            else:
                print(f"❌ URL {url} 健康检查失败，状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ URL {url} 健康检查失败，错误: {str(e)}")
        
        if i < max_retries - 1:
            print(f"⏳ 等待 {retry_interval} 秒后重试...")
            time.sleep(retry_interval)
    
    print(f"❌ URL {url} 健康检查多次失败，放弃测试")
    return False


def run_ab(url: str, duration: str) -> Tuple[float, float]:
    """运行 ab 测试并解析结果"""
    if not check_url_health(url):
        return 0.0, 0.0
    
    cmd = f"ab -n 10000 -c 100 {url}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    lines = result.stdout.split('\n')
    qps = 0.0
    latency = 0.0
    
    for line in lines:
        if 'Requests per second:' in line:
            qps = float(line.split(':')[1].strip().split()[0])
        elif 'Time per request:' in line and 'mean' in line:
            latency = float(line.split(':')[1].strip().split()[0])
    
    return qps, latency


def create_test_app(port: int) -> str:
    """创建测试应用文件"""
    app_content = f'''
#!/usr/bin/env python
# coding: utf-8
"""
性能测试应用
"""

import sys
import os
import asyncio
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs

app = Litefs(
    host='127.0.0.1',
    port={port},
    debug=False
)


@app.add_get('/', name='index')
async def index_handler(request):
    """首页"""
    return 'Hello from Litefs!'


@app.add_get('/async', name='async_example')
async def async_handler(request):
    """异步处理示例"""
    await asyncio.sleep(0.01)
    return {{
        'message': 'Hello from async handler!',
        'timestamp': time.time(),
        'async': True
    }}


@app.add_get('/user/{{id}}', name='user_detail')
async def user_detail_handler(request, id):
    """路径参数示例"""
    return {{
        'user_id': id,
        'message': f'User details for ID: {{id}}'
    }}


if __name__ == '__main__':
    app.run()
'''
    return app_content


def start_greenlet_server(port: int, worker_count: int) -> subprocess.Popen:
    """启动 greenlet 版本的服务器"""
    # 创建临时目录
    subprocess.run('mkdir -p temp_greenlet_test', shell=True, capture_output=True)
    
    # 创建应用文件
    app_content = create_test_app(port)
    with open('temp_greenlet_test/app.py', 'w') as f:
        f.write(app_content)
    
    # 启动服务器
    cmd = f"cd temp_greenlet_test && python app.py"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    
    return process


def start_asyncio(port: int) -> subprocess.Popen:
    """启动 asyncio 版本的服务器"""
    # 创建临时目录
    subprocess.run('mkdir -p temp_asyncio_test', shell=True, capture_output=True)
    
    # 创建应用文件
    app_content = create_test_app(port)
    app_content += '''

if __name__ == '__main__':
    from litefs.server.asyncio import run_asyncio
    run_asyncio(app, host='127.0.0.1', port={port}, processes=1)
'''
    app_content = app_content.replace('{port}', str(port))
    
    with open('temp_asyncio_test/app.py', 'w') as f:
        f.write(app_content)
    
    # 启动服务器
    cmd = f"cd temp_asyncio_test && python app.py"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)
    
    return process


def stop_server(process: subprocess.Popen):
    """停止服务器"""
    try:
        process.terminate()
        process.wait(timeout=5)
    except:
        process.kill()
    
    # 清理临时目录
    subprocess.run('rm -rf temp_greenlet_test temp_asyncio_test', shell=True, capture_output=True)


def test_server_mode(mode_name: str, start_func, port_base: int, worker_count: int = 1):
    """测试指定服务器模式的性能"""
    print(f"\n=== Testing {mode_name} (Workers: {worker_count}) ===")
    
    port = port_base + worker_count * 10
    results = {}
    
    # 启动服务器
    if mode_name == "Greenlet HTTP Server":
        process = start_greenlet_server(port, worker_count)
    else:
        process = start_asyncio(port)
    
    try:
        # 测试每个端点
        for endpoint in endpoints:
            url = f"http://127.0.0.1:{port}{endpoint}"
            print(f"Testing {endpoint}...")
            
            qps, latency = run_ab(url, test_duration)
            print(f"  QPS: {qps:.2f}, Latency: {latency:.2f}ms")
            
            results[endpoint] = {
                'qps': qps,
                'latency': latency
            }
    finally:
        # 停止服务器
        stop_server(process)
    
    return results


def print_comparison_table(greenlet_results: Dict, asyncio_results: Dict):
    """打印对比表格"""
    print("\n" + "=" * 80)
    print("性能对比结果")
    print("=" * 80)
    
    print("\nQPS 对比:")
    print("-" * 80)
    print(f"{'端点':<20} {'Greenlet':<20} {'AsyncIO':<20} {'差异':<20}")
    print("-" * 80)
    
    for endpoint in endpoints:
        greenlet_qps = greenlet_results.get(endpoint, {}).get('qps', 0)
        asyncio_qps = asyncio_results.get(endpoint, {}).get('qps', 0)
        
        if greenlet_qps > 0 and asyncio_qps > 0:
            diff = ((asyncio_qps - greenlet_qps) / greenlet_qps) * 100
            diff_str = f"{diff:+.2f}%"
        else:
            diff_str = "N/A"
        
        print(f"{endpoint:<20} {greenlet_qps:<20.2f} {asyncio_qps:<20.2f} {diff_str:<20}")
    
    print("\n延迟对比 (ms):")
    print("-" * 80)
    print(f"{'端点':<20} {'Greenlet':<20} {'AsyncIO':<20} {'差异':<20}")
    print("-" * 80)
    
    for endpoint in endpoints:
        greenlet_latency = greenlet_results.get(endpoint, {}).get('latency', 0)
        asyncio_latency = asyncio_results.get(endpoint, {}).get('latency', 0)
        
        if greenlet_latency > 0 and asyncio_latency > 0:
            diff = ((asyncio_latency - greenlet_latency) / greenlet_latency) * 100
            diff_str = f"{diff:+.2f}%"
        else:
            diff_str = "N/A"
        
        print(f"{endpoint:<20} {greenlet_latency:<20.2f} {asyncio_latency:<20.2f} {diff_str:<20}")
    
    print("=" * 80)


def main():
    """主测试函数"""
    print("=" * 80)
    print("Litefs HTTP 服务器性能对比测试")
    print("Greenlet vs AsyncIO")
    print("=" * 80)
    
    # 测试 greenlet 版本（单进程）
    print("\n" + "=" * 80)
    print("测试 1: Greenlet HTTP Server (单进程)")
    print("=" * 80)
    greenlet_results = test_server_mode(
        "Greenlet HTTP Server", 
        start_greenlet_server, 
        port_base=9000,
        worker_count=1
    )
    
    # 测试 asyncio 版本（单进程）
    print("\n" + "=" * 80)
    print("测试 2: AsyncIO HTTP Server (单进程)")
    print("=" * 80)
    asyncio_results = test_server_mode(
        "AsyncIO HTTP Server", 
        start_asyncio, 
        port_base=9100
    )
    
    # 打印对比结果
    print_comparison_table(greenlet_results, asyncio_results)
    
    # 分析结果
    print("\n" + "=" * 80)
    print("性能分析")
    print("=" * 80)
    
    print("\n1. Greenlet 版本特点:")
    print("   - 使用 epoll + greenlet 实现协程")
    print("   - 成熟的实现，经过生产验证")
    print("   - 支持多进程模式")
    print("   - 在 Linux 上性能优异")
    
    print("\n2. AsyncIO 版本特点:")
    print("   - 使用 Python 原生 asyncio")
    print("   - 更现代的实现方式")
    print("   - 更好的异步生态兼容性")
    print("   - 单进程模式，需要外部进程管理器")
    
    print("\n3. 性能差异原因分析:")
    print("   - greenlet 使用 C 扩展，上下文切换更快")
    print("   - asyncio 是纯 Python 实现，有一定开销")
    print("   - epoll 在 Linux 上性能优异")
    print("   - asyncio 的事件循环有额外开销")
    
    print("\n4. 使用建议:")
    print("   - 追求极致性能：使用 greenlet 版本")
    print("   - 需要异步生态：使用 asyncio 版本")
    print("   - 生产环境：greenlet 版本更成熟")
    print("   - 开发体验：asyncio 版本更现代")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理所有临时文件和进程
        subprocess.run('rm -rf temp_greenlet_test temp_asyncio_test', shell=True, capture_output=True)
        subprocess.run('pkill -f "temp_greenlet_test" && pkill -f "temp_asyncio_test"', shell=True, capture_output=True)
