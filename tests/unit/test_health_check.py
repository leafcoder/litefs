#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.middleware import HealthCheck
from litefs.handlers import Response


class MockRequestHandler:
    """模拟请求处理器"""
    def __init__(self):
        self._environ = {}
        self._status_code = 200
        self._headers = []
        self._response_headers = []
    
    def start_response(self, status_code, headers):
        """模拟 start_response"""
        self._status_code = status_code
        self._headers = headers
    
    def handle_response(self, result):
        """模拟 handle_response"""
        if isinstance(result, Response):
            self._status_code = result.status_code
            for header, value in result.headers:
                self._add_header(header, value)
            return result.content
        return result
    
    def _add_header(self, key, value):
        """模拟 _add_header"""
        self._response_headers.append((key, value))


class TestHealthCheck(unittest.TestCase):
    """测试健康检查中间件"""

    def setUp(self):
        """设置测试环境"""
        self.app = None
        self.health_check = HealthCheck(self.app, path='/health', ready_path='/health/ready')

    def test_init_default(self):
        """测试默认初始化"""
        health_check = HealthCheck(self.app)
        
        self.assertEqual(health_check.path, '/health')
        self.assertEqual(health_check.ready_path, '/health/ready')
        self.assertEqual(health_check._checks, {})
        self.assertEqual(health_check._ready_checks, {})

    def test_init_custom_paths(self):
        """测试自定义路径初始化"""
        health_check = HealthCheck(self.app, path='/status', ready_path='/status/ready')
        
        self.assertEqual(health_check.path, '/status')
        self.assertEqual(health_check.ready_path, '/status/ready')

    def test_add_check(self):
        """测试添加健康检查"""
        def check_func():
            return True
        
        self.health_check.add_check('database', check_func)
        
        self.assertIn('database', self.health_check._checks)
        self.assertEqual(self.health_check._checks['database'], check_func)

    def test_add_ready_check(self):
        """测试添加就绪检查"""
        def check_func():
            return True
        
        self.health_check.add_ready_check('migrations', check_func)
        
        self.assertIn('migrations', self.health_check._ready_checks)
        self.assertEqual(self.health_check._ready_checks['migrations'], check_func)

    def test_process_request_non_health_endpoint(self):
        """测试非健康检查端点请求"""
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/api/test',
            'REQUEST_METHOD': 'GET'
        }
        
        result = self.health_check.process_request(request_handler)
        
        self.assertIsNone(result)

    def test_process_request_non_get_method(self):
        """测试非 GET 方法请求"""
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health',
            'REQUEST_METHOD': 'POST'
        }
        
        result = self.health_check.process_request(request_handler)
        
        self.assertIsNone(result)

    def test_health_check_all_pass(self):
        """测试所有检查通过"""
        def check1():
            return True
        
        def check2():
            return True
        
        self.health_check.add_check('database', check1)
        self.health_check.add_check('cache', check2)
        
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health',
            'REQUEST_METHOD': 'GET'
        }
        
        response = self.health_check.process_request(request_handler)
        
        self.assertIsNotNone(response)
        response_content = request_handler.handle_response(response)
        response_data = json.loads(response_content)
        
        self.assertEqual(response_data['status'], 'healthy')
        self.assertIn('timestamp', response_data)
        self.assertIn('checks', response_data)
        self.assertEqual(response_data['checks']['database']['status'], 'pass')
        self.assertEqual(response_data['checks']['cache']['status'], 'pass')

    def test_health_check_one_fail(self):
        """测试一个检查失败"""
        def check1():
            return True
        
        def check2():
            return False
        
        self.health_check.add_check('database', check1)
        self.health_check.add_check('cache', check2)
        
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health',
            'REQUEST_METHOD': 'GET'
        }
        
        response = self.health_check.process_request(request_handler)
        
        self.assertIsNotNone(response)
        response_data = json.loads(request_handler.handle_response(response))
        
        self.assertEqual(response_data['status'], 'unhealthy')
        self.assertEqual(response_data['checks']['database']['status'], 'pass')
        self.assertEqual(response_data['checks']['cache']['status'], 'fail')

    def test_health_check_exception(self):
        """测试检查抛出异常"""
        def check1():
            return True
        
        def check2():
            raise Exception('Database connection failed')
        
        self.health_check.add_check('database', check1)
        self.health_check.add_check('cache', check2)
        
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health',
            'REQUEST_METHOD': 'GET'
        }
        
        response = self.health_check.process_request(request_handler)
        
        self.assertIsNotNone(response)
        response_data = json.loads(request_handler.handle_response(response))
        
        self.assertEqual(response_data['status'], 'unhealthy')
        self.assertEqual(response_data['checks']['database']['status'], 'pass')
        self.assertEqual(response_data['checks']['cache']['status'], 'error')
        self.assertIn('error', response_data['checks']['cache'])

    def test_ready_check_all_pass(self):
        """测试所有就绪检查通过"""
        def check1():
            return True
        
        def check2():
            return True
        
        self.health_check.add_ready_check('migrations', check1)
        self.health_check.add_ready_check('config', check2)
        
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health/ready',
            'REQUEST_METHOD': 'GET'
        }
        
        response = self.health_check.process_request(request_handler)
        
        self.assertIsNotNone(response)
        response_data = json.loads(request_handler.handle_response(response))
        
        self.assertEqual(response_data['status'], 'ready')
        self.assertIn('timestamp', response_data)
        self.assertIn('checks', response_data)
        self.assertEqual(response_data['checks']['migrations']['status'], 'pass')
        self.assertEqual(response_data['checks']['config']['status'], 'pass')

    def test_ready_check_one_fail(self):
        """测试一个就绪检查失败"""
        def check1():
            return True
        
        def check2():
            return False
        
        self.health_check.add_ready_check('migrations', check1)
        self.health_check.add_ready_check('config', check2)
        
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health/ready',
            'REQUEST_METHOD': 'GET'
        }
        
        response = self.health_check.process_request(request_handler)
        
        self.assertIsNotNone(response)
        response_data = json.loads(request_handler.handle_response(response))
        
        self.assertEqual(response_data['status'], 'not_ready')
        self.assertEqual(response_data['checks']['migrations']['status'], 'pass')
        self.assertEqual(response_data['checks']['config']['status'], 'fail')

    def test_no_checks(self):
        """测试没有检查时的响应"""
        request_handler = MockRequestHandler()
        request_handler._environ = {
            'PATH_INFO': '/health',
            'REQUEST_METHOD': 'GET'
        }
        
        response = self.health_check.process_request(request_handler)
        
        self.assertIsNotNone(response)
        response_data = json.loads(request_handler.handle_response(response))
        
        self.assertEqual(response_data['status'], 'healthy')
        self.assertEqual(response_data['checks'], {})


if __name__ == '__main__':
    unittest.main()
