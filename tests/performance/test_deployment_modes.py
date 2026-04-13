#!/usr/bin/env python
# coding: utf-8
"""
测试不同部署方式下的 Litefs 性能

测试 Litefs 在以下三种部署方式下的性能表现：
1. 自有 HTTP 服务器
2. Gunicorn + WSGI
3. Gunicorn + Uvicorn + ASGI

测试不同核心数（1, 2, 4, 8）下的性能
"""

import subprocess
import time
import json
import os

# 测试配置
cores = [1, 2, 4, 8]
test_duration = "10s"  # 测试时长

# 存储测试结果
results = {}

# 测试端点
endpoints = ["/", "/async", "/user/123"]


def check_url_health(url, max_retries=5, retry_interval=1):
    """检查 URL 是否健康（能正常返回数据）"""
    import requests
    
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

def run_ab(url, duration):
    """运行 ab 测试并解析结果"""
    # 先检查 URL 健康状态
    if not check_url_health(url):
        return 0, 0
    
    # 使用 ab 命令，-n 总请求数，-c 并发数
    cmd = f"ab -n 10000 -c 100 {url}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    # 解析结果
    lines = result.stdout.split('\n')
    qps = 0
    latency = 0
    
    for line in lines:
        if 'Requests per second:' in line:
            qps = float(line.split(':')[1].strip().split()[0])
        elif 'Time per request:' in line and 'mean' in line:
            # 提取平均延迟
            latency = float(line.split(':')[1].strip().split()[0])
    
    return qps, latency


def start_own_server(worker_count):
    """启动 Litefs 自有 HTTP 服务器"""
    port = 8000 + worker_count * 10
    
    # 清理可能占用端口的进程
    subprocess.run(f'lsof -ti :{port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    
    # 创建临时目录，创建包含所有端点的 app.py 文件
    subprocess.run('mkdir -p temp_hello_world', shell=True, capture_output=True)
    
    # 创建包含所有必要端点的 app.py 文件
    with open('temp_hello_world/app.py', 'w') as f:
        content = '''
#!/usr/bin/env python
# coding: utf-8
"""
Litefs 服务器示例

包含所有必要的测试端点
"""

import sys
import os
import asyncio
import time

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs

# 创建应用实例
app = Litefs(
    host='127.0.0.1',
    port={port},
    debug=True
)

# 定义首页处理函数
@app.add_get('/', name='index')
async def index_handler(request):
    """首页"""
    return 'Hello from Litefs!'

# 定义异步处理函数
@app.add_get('/async', name='async_example')
async def async_handler(request):
    """异步处理示例"""
    # 模拟异步操作
    await asyncio.sleep(0.01)
    return {
        'message': 'Hello from async handler!',
        'timestamp': time.time(),
        'async': True
    }

# 定义用户详情处理函数
@app.add_get('/user/{id}', name='user_detail')
async def user_detail_handler(request, id):
    """用户详情"""
    return {
        'user_id': id,
        'message': f'User details for ID: {id}'
    }

if __name__ == '__main__':
    print("=" * 60)
    print("Litefs Server Example")
    print("=" * 60)
    print(f"访问地址: http://localhost:{port}")
    print("=" * 60)
    print("可用路由:")
    print("  GET /         - 首页")
    print("  GET /async    - 异步处理示例")
    print("  GET /user/{{id}} - 用户详情")
    print("=" * 60)
    
    app.run(processes={worker_count})
'''
        # 替换端口和进程数
        content = content.replace('{port}', str(port))
        content = content.replace('{worker_count}', str(worker_count))
        f.write(content)
    
    # 启动服务器
    cmd = f"cd temp_hello_world && python app.py"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)  # 等待服务器启动
    
    return port, process


def start_gunicorn_wsgi(worker_count):
    """启动 Gunicorn + WSGI 服务器"""
    port = 8100 + worker_count * 10
    
    # 清理可能占用端口的进程
    subprocess.run(f'lsof -ti :{port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    
    # 创建临时 WSGI 应用文件，包含所有必要的端点
    with open('temp_wsgi.py', 'w') as f:
        f.write('''
import sys
import os
import asyncio
import time

# 添加 src 目录到 Python 路径
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs

# 创建应用实例
app = Litefs()

# 定义首页处理函数
@app.add_get('/', name='index')
def index_handler(request):
    """首页"""
    return 'Hello from Litefs WSGI!'

# 定义异步处理函数
@app.add_get('/async', name='async_example')
def async_handler(request):
    """异步处理示例"""
    # 模拟异步操作
    time.sleep(0.01)
    return {
        'message': 'Hello from async handler!',
        'timestamp': time.time(),
        'async': True
    }

# 定义用户详情处理函数
@app.add_get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    """用户详情"""
    return {
        'user_id': id,
        'message': f'User details for ID: {id}'
    }

# 创建 WSGI 应用
application = app.wsgi()
''')
    
    # 启动服务器
    cmd = f"gunicorn -w {worker_count} temp_wsgi:application --bind 127.0.0.1:{port} --log-level error"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)  # 等待服务器启动
    
    return port, process


def start_gunicorn_uvicorn_asgi(worker_count):
    """启动 Gunicorn + Uvicorn + ASGI 服务器"""
    port = 8200 + worker_count * 10
    
    # 清理可能占用端口的进程
    subprocess.run(f'lsof -ti :{port} | xargs kill -9 2>/dev/null', shell=True, capture_output=True)
    
    # 启动服务器
    cmd = f"gunicorn -w {worker_count} -k uvicorn.workers.UvicornWorker examples.asgi_example:application --bind 127.0.0.1:{port} --log-level error"
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(3)  # 等待服务器启动
    
    return port, process


def stop_server(process):
    """停止服务器进程"""
    try:
        process.terminate()
        process.wait(timeout=5)
    except:
        process.kill()
    
    # 清理临时目录
    subprocess.run('rm -rf temp_hello_world', shell=True, capture_output=True)


def test_deployment_mode(mode_name, start_func):
    """测试指定部署模式的性能"""
    print(f"\n=== Testing {mode_name} ===")
    
    for core in cores:
        print(f"\nTesting with {core} cores...")
        
        # 启动服务器
        port, process = start_func(core)
        
        # 测试每个端点
        for endpoint in endpoints:
            url = f"http://127.0.0.1:{port}{endpoint}"
            print(f"Testing {endpoint}...")
            
            # 运行测试
            qps, latency = run_ab(url, test_duration)
            print(f"  QPS: {qps:.2f}, Latency: {latency:.2f}ms")
            
            # 存储结果
            if mode_name not in results:
                results[mode_name] = {}
            if core not in results[mode_name]:
                results[mode_name][core] = {}
            results[mode_name][core][endpoint] = {
                "qps": qps,
                "latency": latency
            }
        
        # 停止服务器
        stop_server(process)
        time.sleep(2)  # 等待端口释放


def generate_report():
    """生成性能分析报告"""
    print("\n=== Performance Analysis Report ===")
    
    # 打印表格
    print("\nQPS Results:")
    print("-" * 100)
    print(f"{'Mode':<25} {'Cores':<10} {'/':<15} {'/async':<15} {'/user/123':<15}")
    print("-" * 100)
    
    for mode in results:
        for core in results[mode]:
            row = f"{mode:<25} {core:<10}"
            for endpoint in endpoints:
                qps = results[mode][core][endpoint]["qps"]
                row += f"{qps:<15.2f}"
            print(row)
    
    print("-" * 100)
    
    print("\nLatency Results (ms):")
    print("-" * 100)
    print(f"{'Mode':<25} {'Cores':<10} {'/':<15} {'/async':<15} {'/user/123':<15}")
    print("-" * 100)
    
    for mode in results:
        for core in results[mode]:
            row = f"{mode:<25} {core:<10}"
            for endpoint in endpoints:
                latency = results[mode][core][endpoint]["latency"]
                row += f"{latency:<15.2f}"
            print(row)
    
    print("-" * 100)


def generate_charts():
    """生成性能对比图"""
    # 由于 matplotlib 依赖缺失，暂时跳过图表生成
    print("\nSkipping chart generation due to missing matplotlib dependency")


def main():
    """主函数"""
    # 测试自有 HTTP 服务器
    test_deployment_mode("Own HTTP Server", start_own_server)
    
    # 测试 Gunicorn + WSGI
    test_deployment_mode("Gunicorn + WSGI", start_gunicorn_wsgi)
    
    # 测试 Gunicorn + Uvicorn + ASGI
    test_deployment_mode("Gunicorn + Uvicorn + ASGI", start_gunicorn_uvicorn_asgi)
    
    # 保存结果
    with open('tests/performance/deployment_performance_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # 生成报告
    generate_report()
    
    # 生成图表
    generate_charts()


if __name__ == "__main__":
    main()
