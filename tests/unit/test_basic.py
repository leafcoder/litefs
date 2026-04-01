#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))


class TestBasicFunctionality(unittest.TestCase):
    """测试基本功能"""

    def test_version(self):
        """测试版本号"""
        import litefs
        
        self.assertIsNotNone(litefs.__version__)
        self.assertIsInstance(litefs.__version__, str)

    def test_make_config(self):
        """测试 make_config 函数"""
        import litefs
        
        config = litefs.make_config()
        
        self.assertIsNotNone(config)
        self.assertEqual(config.host, 'localhost')
        self.assertEqual(config.port, 9090)

    def test_make_logger(self):
        """测试 make_logger 函数"""
        import litefs
        
        logger = litefs.make_logger('test', level=20)
        
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'test')

    def test_parse_form(self):
        """测试 parse_form 函数"""
        from litefs.handlers.request import parse_form
        
        test_query = "name=test&value=123"
        form = parse_form(test_query)
        
        self.assertEqual(form['name'], 'test')
        self.assertEqual(form['value'], '123')

    def test_import_modules(self):
        """测试导入模块"""
        from litefs import Litefs
        from litefs.cache import MemoryCache, TreeCache
        from litefs.session import Session
        from litefs.middleware import Middleware, MiddlewareManager
        
        self.assertIsNotNone(Litefs)
        self.assertIsNotNone(MemoryCache)
        self.assertIsNotNone(TreeCache)
        self.assertIsNotNone(Session)
        self.assertIsNotNone(Middleware)
        self.assertIsNotNone(MiddlewareManager)


if __name__ == '__main__':
    unittest.main()
