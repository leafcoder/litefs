#!/usr/bin/env python
# coding: utf-8
"""
Keep-Alive 功能测试

测试 asyncio 和 greenlet 服务器的 keep-alive 功能
"""

import sys
import os
import time
import socket
import asyncio
import pytest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs.core import Litefs
from litefs.server.asyncio import run_asyncio


def find_free_port():
    """查找可用端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def wait_for_server(host, port, timeout=10):
    """等待服务器启动"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def create_test_app(port: int) -> Litefs:
    """创建测试应用"""
    app = Litefs(
        host='127.0.0.1',
        port=port,
        debug=True
    )
    
    @app.add_get('/', name='index')
    async def index_handler(request):
        """首页"""
        return 'Hello from Litefs!'
    
    @app.add_get('/test', name='test')
    async def test_handler(request):
        """测试端点"""
        return {
            'message': 'Test endpoint',
            'timestamp': time.time()
        }
    
    return app


def test_keep_alive_asyncio():
    """测试 asyncio 服务器的 keep-alive 功能"""
    print("\n" + "=" * 60)
    print("测试 AsyncIO 服务器的 Keep-Alive 功能")
    print("=" * 60)
    
    port = find_free_port()
    app = create_test_app(port)
    
    # 启动服务器（在后台）
    import subprocess
    import time
    
    # 创建临时测试文件
    test_file = 'temp_keepalive_test.py'
    with open(test_file, 'w') as f:
        f.write(f'''
import sys
import os
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs.core import Litefs
from litefs.server.asyncio import run_asyncio

app = Litefs(host='127.0.0.1', port={port}, debug=True)

@app.add_get('/', name='index')
async def index_handler(request):
    return 'Hello from Litefs!'

@app.add_get('/test', name='test')
async def test_handler(request):
    return {{'message': 'Test endpoint', 'timestamp': time.time()}}

if __name__ == '__main__':
    run_asyncio(app, host='127.0.0.1', port={port}, keep_alive_timeout=5.0)
''')
    
    # 启动服务器
    process = subprocess.Popen(['python', test_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # 等待服务器启动
    
    try:
        # 测试 keep-alive
        print("\n测试 1: 发送多个请求到同一连接")
        
        # 创建 socket 连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', port))
        sock.settimeout(5)
        
        # 发送第一个请求
        request1 = b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
        sock.sendall(request1)
        
        # 接收完整响应（包括响应体）
        response1 = b""
        content_length = None
        while True:
            chunk = sock.recv(4096)
            response1 += chunk
            
            # 解析 Content-Length
            if content_length is None and b"\r\n\r\n" in response1:
                headers_end = response1.index(b"\r\n\r\n") + 4
                headers = response1[:headers_end].decode('utf-8')
                
                # 查找 Content-Length
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        content_length = int(line.split(':')[1].strip())
                        break
                
                # 如果没有 Content-Length，读取到连接关闭
                if content_length is None:
                    break
                
            # 检查是否接收完整响应
            if content_length is not None:
                headers_end = response1.index(b"\r\n\r\n") + 4
                body_length = len(response1) - headers_end
                if body_length >= content_length:
                    break
        
        print(f"响应 1: {response1.decode('utf-8')[:200]}...")
        
        # 检查是否有 Connection: keep-alive 头
        if b"Connection: keep-alive" in response1 or b"Connection: Keep-Alive" in response1:
            print("✅ Keep-Alive 头存在")
        else:
            print("❌ Keep-Alive 头不存在")
        
        # 发送第二个请求（复用同一连接）
        request2 = b"GET /test HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
        sock.sendall(request2)
        
        # 接收完整响应（包括响应体）
        response2 = b""
        content_length = None
        while True:
            chunk = sock.recv(4096)
            response2 += chunk
            
            # 解析 Content-Length
            if content_length is None and b"\r\n\r\n" in response2:
                headers_end = response2.index(b"\r\n\r\n") + 4
                headers = response2[:headers_end].decode('utf-8')
                
                # 查找 Content-Length
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        content_length = int(line.split(':')[1].strip())
                        break
                
                # 如果没有 Content-Length，读取到连接关闭
                if content_length is None:
                    break
                
            # 检查是否接收完整响应
            if content_length is not None:
                headers_end = response2.index(b"\r\n\r\n") + 4
                body_length = len(response2) - headers_end
                if body_length >= content_length:
                    break
        
        print(f"响应 2: {response2.decode('utf-8')[:200]}...")
        
        # 关闭连接
        sock.close()
        
        print("\n测试 2: 发送 Connection: close 请求")
        
        # 创建新的 socket 连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', port))
        sock.settimeout(5)
        
        # 发送请求（要求关闭连接）
        request3 = b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
        sock.sendall(request3)
        
        # 接收响应
        response3 = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response3 += chunk
        
        print(f"响应 3: {response3.decode('utf-8')[:200]}...")
        
        # 检查是否有 Connection: close 头
        if b"Connection: close" in response3:
            print("✅ Connection: close 头存在")
        else:
            print("❌ Connection: close 头不存在")
        
        sock.close()
        
        print("\n✅ AsyncIO Keep-Alive 测试完成")
        
    finally:
        # 停止服务器
        process.terminate()
        process.wait()
        
        # 删除临时文件
        if os.path.exists(test_file):
            os.remove(test_file)


def test_keep_alive_greenlet():
    """
    测试 greenlet 服务器的 keep-alive 功能
    
    注意：由于 greenlet 服务器目前不支持 keep-alive 功能，
    此测试可能会失败或跳过。这是预期行为。
    
    TODO: 实现 greenlet 服务器的 keep-alive 支持后启用此测试
    """
    print("\n" + "=" * 60)
    print("测试 Greenlet 服务器的 Keep-Alive 功能")
    print("⚠️  注意：Greenlet 服务器暂不支持 Keep-Alive 功能")
    print("此测试仅供参考，实际运行会失败")
    print("=" * 60)
    
    port = find_free_port()
    
    # 创建临时测试文件
    test_file = 'temp_greenlet_keepalive_test.py'
    with open(test_file, 'w') as f:
        f.write(f'''
import sys
import os
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs.core import Litefs

app = Litefs(host='127.0.0.1', port={port}, debug=True)

@app.add_get('/', name='index')
async def index_handler(request):
    return 'Hello from Litefs!'

@app.add_get('/test', name='test')
async def test_handler(request):
    return {{'message': 'Test endpoint', 'timestamp': time.time()}}

if __name__ == '__main__':
    app.run(keep_alive_timeout=5.0)
''')
    
    # 启动服务器
    import subprocess
    import time
    
    # 添加环境变量以启用调试模式
    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    
    process = subprocess.Popen(
        ['python', test_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        preexec_fn=os.setsid  # 创建新进程组
    )
    
    # 使用更可靠的等待机制
    max_wait = 10  # 最多等待 10 秒
    wait_interval = 0.5
    server_started = False
    
    for i in range(int(max_wait / wait_interval)):
        time.sleep(wait_interval)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                server_started = True
                break
        except Exception:
            pass
    
    if not server_started:
        print(f"服务器启动超时，重试一次...")
        # 第一次启动失败，尝试重试一次
        process.terminate()
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except:
            pass
        
        time.sleep(5)  # 等待端口释放
        
        # 重试启动服务器
        process = subprocess.Popen(
            [sys.executable, test_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # 再次等待服务器启动
        server_started = False
        for i in range(int(max_wait / wait_interval)):
            time.sleep(wait_interval)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result == 0:
                    server_started = True
                    break
            except Exception:
                pass
        
        if not server_started:
            print(f"服务器启动重试失败，终止测试")
            process.terminate()
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            except:
                pass
            if os.path.exists(test_file):
                os.unlink(test_file)
            pytest.skip("服务器启动超时（重试后）")
    
    try:
        # 测试 keep-alive
        print("\n测试 1: 发送多个请求到同一连接")
        
        # 创建 socket 连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', port))
        sock.settimeout(5)
        
        # 发送第一个请求
        request1 = b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
        sock.sendall(request1)
        
        # 接收完整响应（包括响应体）
        response1 = b""
        content_length = None
        while True:
            chunk = sock.recv(4096)
            response1 += chunk
            
            # 解析 Content-Length
            if content_length is None and b"\r\n\r\n" in response1:
                headers_end = response1.index(b"\r\n\r\n") + 4
                headers = response1[:headers_end].decode('utf-8')
                
                # 查找 Content-Length
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        content_length = int(line.split(':')[1].strip())
                        break
                
                # 如果没有 Content-Length，读取到连接关闭
                if content_length is None:
                    break
                
            # 检查是否接收完整响应
            if content_length is not None:
                headers_end = response1.index(b"\r\n\r\n") + 4
                body_length = len(response1) - headers_end
                if body_length >= content_length:
                    break
        
        print(f"响应 1: {response1.decode('utf-8')[:200]}...")
        
        # 检查是否有 Connection: keep-alive 头
        if b"Connection: keep-alive" in response1 or b"Connection: Keep-Alive" in response1:
            print("✅ Keep-Alive 头存在")
        else:
            print("❌ Keep-Alive 头不存在")
        
        # 发送第二个请求（复用同一连接）
        request2 = b"GET /test HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
        sock.sendall(request2)
        
        # 接收完整响应（包括响应体）
        response2 = b""
        content_length = None
        while True:
            chunk = sock.recv(4096)
            response2 += chunk
            
            # 解析 Content-Length
            if content_length is None and b"\r\n\r\n" in response2:
                headers_end = response2.index(b"\r\n\r\n") + 4
                headers = response2[:headers_end].decode('utf-8')
                
                # 查找 Content-Length
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        content_length = int(line.split(':')[1].strip())
                        break
                
                # 如果没有 Content-Length，读取到连接关闭
                if content_length is None:
                    break
                
            # 检查是否接收完整响应
            if content_length is not None:
                headers_end = response2.index(b"\r\n\r\n") + 4
                body_length = len(response2) - headers_end
                if body_length >= content_length:
                    break
        
        print(f"响应 2: {response2.decode('utf-8')[:200]}...")
        
        # 关闭连接
        sock.close()
        
        print("\n测试 2: 发送 Connection: close 请求")
        
        # 创建新的 socket 连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', port))
        sock.settimeout(5)
        
        # 发送请求（要求关闭连接）
        request3 = b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
        sock.sendall(request3)
        
        # 接收响应
        response3 = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response3 += chunk
        
        print(f"响应 3: {response3.decode('utf-8')[:200]}...")
        
        # 检查是否有 Connection: close 头
        if b"Connection: close" in response3:
            print("✅ Connection: close 头存在")
        else:
            print("❌ Connection: close 头不存在")
        
        sock.close()
        
        print("\n✅ Greenlet Keep-Alive 测试完成")
        
    finally:
        # 停止服务器
        process.terminate()
        process.wait()
        
        # 删除临时文件
        if os.path.exists(test_file):
            os.remove(test_file)


if __name__ == '__main__':
    print("=" * 60)
    print("Keep-Alive 功能测试")
    print("=" * 60)
    
    # 测试 asyncio 服务器
    test_keep_alive_asyncio()
    
    # 测试 greenlet 服务器
    # 注意：greenlet 服务器目前不支持 keep-alive 功能
    # 该测试会跳过或失败，这是预期行为
    print("\n注意：Greenlet 服务器暂不支持 Keep-Alive 功能")
    print("跳过 test_keep_alive_greenlet 测试")
    # test_keep_alive_greenlet()
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)
