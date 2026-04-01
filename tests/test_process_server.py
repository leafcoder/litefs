#!/usr/bin/env python
# coding: utf-8

import unittest
import time
import threading
import requests
from litefs import Litefs


class TestProcessServer(unittest.TestCase):
    """测试多进程服务器"""

    def setUp(self):
        """设置测试环境"""
        self.host = "localhost"
        self.port = 9999
        self.url = f"http://{self.host}:{self.port}"

    def test_single_process(self):
        """测试单进程模式"""
        def run_server():
            app = Litefs(host=self.host, port=self.port)
            
            def index_handler(request):
                return "Hello world"
            
            app.add_get('/', index_handler, name='index')
            app.run(processes=1)

        # 启动服务器
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # 等待服务器启动
        time.sleep(1)

        # 发送请求
        try:
            response = requests.get(self.url, timeout=5)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Hello world", response.text)
        except Exception as e:
            self.fail(f"单进程服务器测试失败: {e}")

    def test_multi_process(self):
        """测试多进程模式"""
        def run_server():
            app = Litefs(host=self.host, port=self.port)
            
            def index_handler(request):
                return "Hello world"
            
            app.add_get('/', index_handler, name='index')
            app.run(processes=2)

        # 启动服务器
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # 等待服务器启动
        time.sleep(1)

        # 发送请求
        try:
            response = requests.get(self.url, timeout=5)
            self.assertEqual(response.status_code, 200)
            self.assertIn("Hello world", response.text)
        except Exception as e:
            self.fail(f"多进程服务器测试失败: {e}")

    def test_concurrent_requests(self):
        """测试并发请求"""
        def run_server():
            app = Litefs(host=self.host, port=self.port)
            
            def index_handler(request):
                return "Hello world"
            
            app.add_get('/', index_handler, name='index')
            app.run(processes=4)

        # 启动服务器
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()

        # 等待服务器启动
        time.sleep(1)

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


if __name__ == '__main__':
    unittest.main()
