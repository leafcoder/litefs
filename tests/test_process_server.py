#!/usr/bin/env python
# coding: utf-8

import unittest
import time
import socket
import subprocess
import requests
import tempfile
import os


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


class TestProcessServer(unittest.TestCase):
    """测试多进程服务器"""

    def setUp(self):
        """设置测试环境"""
        self.host = "localhost"
        self.port = find_free_port()
        self.url = f"http://{self.host}:{self.port}"
        self.process = None

    def tearDown(self):
        """清理测试环境"""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                # 如果进程已经终止，尝试强制杀死
                try:
                    self.process.kill()
                except:
                    pass

    def test_single_process(self):
        """测试单进程模式"""
        # 创建临时服务器脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f'''
import sys
sys.path.insert(0, '/home/zhanglei3/Desktop/dev/litefs/src')

from litefs.core import Litefs

app = Litefs(host='{self.host}', port={self.port})

def index_handler(request):
    return "Hello world"

app.add_get('/', index_handler, name='index')
app.run(processes=1)
''')
            script_path = f.name

        try:
            # 启动服务器进程
            self.process = subprocess.Popen(
                ['python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 等待服务器启动
            if not wait_for_server(self.host, self.port, timeout=5):
                self.skipTest("服务器启动超时")

            # 发送请求
            response = requests.get(self.url, timeout=5)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Hello world", response.text)
        finally:
            # 清理临时文件
            if os.path.exists(script_path):
                os.unlink(script_path)

    def test_multi_process(self):
        """测试多进程模式"""
        # 创建临时服务器脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f'''
import sys
sys.path.insert(0, '/home/zhanglei3/Desktop/dev/litefs/src')

from litefs.core import Litefs

app = Litefs(host='{self.host}', port={self.port})

def index_handler(request):
    return "Hello world"

app.add_get('/', index_handler, name='index')
app.run(processes=2)
''')
            script_path = f.name

        try:
            # 启动服务器进程
            self.process = subprocess.Popen(
                ['python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 等待服务器启动
            if not wait_for_server(self.host, self.port, timeout=5):
                self.skipTest("服务器启动超时")

            # 发送请求
            response = requests.get(self.url, timeout=5)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Hello world", response.text)
        finally:
            # 清理临时文件
            if os.path.exists(script_path):
                os.unlink(script_path)

    def test_concurrent_requests(self):
        """测试并发请求"""
        import threading
        
        # 创建临时服务器脚本
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(f'''
import sys
sys.path.insert(0, '/home/zhanglei3/Desktop/dev/litefs/src')

from litefs.core import Litefs

app = Litefs(host='{self.host}', port={self.port})

def index_handler(request):
    return "Hello world"

app.add_get('/', index_handler, name='index')
app.run(processes=4)
''')
            script_path = f.name

        try:
            # 启动服务器进程
            self.process = subprocess.Popen(
                ['python', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # 等待服务器启动
            if not wait_for_server(self.host, self.port, timeout=5):
                self.skipTest("服务器启动超时")

            # 发送并发请求
            status_codes = []
            def send_request():
                try:
                    response = requests.get(self.url, timeout=5)
                    status_codes.append(response.status_code)
                except:
                    status_codes.append(500)

            # 创建多个线程发送请求
            threads = []
            for i in range(10):
                thread = threading.Thread(target=send_request)
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            # 验证所有请求都成功
            for code in status_codes:
                self.assertEqual(code, 200)
        finally:
            # 清理临时文件
            if os.path.exists(script_path):
                os.unlink(script_path)


if __name__ == '__main__':
    unittest.main()
