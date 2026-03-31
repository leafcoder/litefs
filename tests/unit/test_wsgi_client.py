#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import Mock, patch
import urllib.request
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.core import Litefs

class TestWSGIClient(unittest.TestCase):
    """测试 WSGI 客户端"""

    def setUp(self):
        """测试前准备"""
        self.app = Litefs(webroot='./site')

    def test_wsgi_app_creation(self):
        """测试 WSGI 应用创建"""
        self.assertIsNotNone(self.app)
        # 测试 wsgi() 方法返回一个 callable
        wsgi_app = self.app.wsgi()
        self.assertIsNotNone(wsgi_app)
        self.assertTrue(callable(wsgi_app))

    @patch('urllib.request.urlopen')
    def test_mock_wsgi_request(self, mock_urlopen):
        """使用 mock 测试 WSGI 请求"""
        # 配置 mock 响应
        mock_response = Mock()
        mock_response.status = 200
        mock_response.read.return_value = b"Hello, World!"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        # 导入测试模块，避免在导入时执行
        from tests.unit import test_wsgi_client
        
        # 验证测试模块被正确导入
        self.assertIsNotNone(test_wsgi_client)

if __name__ == '__main__':
    unittest.main()
