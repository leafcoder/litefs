#!/usr/bin/env python
# coding: utf-8

"""
调试工具模块单元测试
"""

import sys
import os
import unittest
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.debug import (
    is_debug_enabled, RequestDebug, SQLQuery, 
    DebugToolbar, TerminalFormatter
)


class TestDebugEnabled(unittest.TestCase):
    """调试启用测试"""
    
    def test_debug_disabled_by_default(self):
        """默认禁用调试"""
        original = os.environ.get('LITEFS_DEBUG')
        if 'LITEFS_DEBUG' in os.environ:
            del os.environ['LITEFS_DEBUG']
        
        self.assertFalse(is_debug_enabled())
        
        if original:
            os.environ['LITEFS_DEBUG'] = original
    
    def test_debug_enabled_with_env(self):
        """环境变量启用调试"""
        original = os.environ.get('LITEFS_DEBUG')
        os.environ['LITEFS_DEBUG'] = '1'
        
        self.assertTrue(is_debug_enabled())
        
        if original:
            os.environ['LITEFS_DEBUG'] = original
        elif 'LITEFS_DEBUG' in os.environ:
            del os.environ['LITEFS_DEBUG']


class TestSQLQuery(unittest.TestCase):
    """SQL 查询测试"""
    
    def test_sql_query_creation(self):
        """测试 SQL 查询创建"""
        query = SQLQuery(
            sql='SELECT * FROM users WHERE id = ?',
            params=(1,),
            duration=5.5,
        )
        
        self.assertEqual(query.sql, 'SELECT * FROM users WHERE id = ?')
        self.assertEqual(query.params, (1,))
        self.assertEqual(query.duration, 5.5)
    
    def test_sql_query_str(self):
        """测试 SQL 查询字符串表示"""
        query = SQLQuery(sql='SELECT * FROM users', params=())
        self.assertEqual(str(query), 'SELECT * FROM users')
        
        query_with_params = SQLQuery(sql='SELECT * FROM users WHERE id = ?', params=(1,))
        self.assertIn('params: (1,)', str(query_with_params))


class TestRequestDebug(unittest.TestCase):
    """请求调试测试"""
    
    def test_request_debug_creation(self):
        """测试请求调试创建"""
        debug = RequestDebug(request_id=1, method='GET', path='/api/users')
        
        self.assertEqual(debug.request_id, 1)
        self.assertEqual(debug.method, 'GET')
        self.assertEqual(debug.path, '/api/users')
        self.assertEqual(len(debug.sql_queries), 0)
        self.assertEqual(len(debug.errors), 0)
    
    def test_add_sql_query(self):
        """测试添加 SQL 查询"""
        debug = RequestDebug(request_id=1)
        
        debug.add_sql_query('SELECT * FROM users', (), 5.0)
        debug.add_sql_query('SELECT * FROM orders', (), 10.0)
        
        self.assertEqual(len(debug.sql_queries), 2)
        self.assertEqual(debug.db_time, 15.0)
    
    def test_add_error(self):
        """测试添加错误"""
        debug = RequestDebug(request_id=1)
        
        try:
            raise ValueError('Test error')
        except ValueError as e:
            debug.add_error(e, 'Test context')
        
        self.assertEqual(len(debug.errors), 1)
        self.assertEqual(debug.errors[0]['type'], 'ValueError')
        self.assertEqual(debug.errors[0]['message'], 'Test error')
        self.assertEqual(debug.errors[0]['context'], 'Test context')
    
    def test_total_time(self):
        """测试总耗时计算"""
        debug = RequestDebug(request_id=1)
        time.sleep(0.01)
        
        total = debug.total_time
        self.assertGreater(total, 0)
        
        debug.finish()
        finished_total = debug.total_time
        self.assertGreater(finished_total, 0)


class TestDebugToolbar(unittest.TestCase):
    """调试工具栏测试"""
    
    def test_start_request(self):
        """测试开始请求"""
        debug = DebugToolbar.start_request('GET', '/test', 'foo=bar')
        
        self.assertIsNotNone(debug)
        self.assertEqual(debug.method, 'GET')
        self.assertEqual(debug.path, '/test')
        self.assertEqual(debug.query_string, 'foo=bar')
    
    def test_request_counter(self):
        """测试请求计数器"""
        DebugToolbar._request_counter = 0
        
        debug1 = DebugToolbar.start_request('GET', '/test1')
        debug2 = DebugToolbar.start_request('GET', '/test2')
        
        self.assertEqual(debug1.request_id, 1)
        self.assertEqual(debug2.request_id, 2)


class TestTerminalFormatter(unittest.TestCase):
    """终端格式化测试"""
    
    def setUp(self):
        self.formatter = TerminalFormatter()
    
    def test_color(self):
        """测试颜色输出"""
        text = self.formatter.color('Hello', 'red')
        self.assertIn('Hello', text)
        self.assertIn('\033[91m', text)
    
    def test_box(self):
        """测试边框盒子"""
        lines = ['Line 1', 'Line 2']
        result = self.formatter.box(lines)
        
        self.assertIn('┌', result)
        self.assertIn('└', result)
        self.assertIn('Line 1', result)
        self.assertIn('Line 2', result)
    
    def test_separator(self):
        """测试分隔线"""
        result = self.formatter.separator('═', 10)
        self.assertEqual(result, '═' * 10)
    
    def test_format_size(self):
        """测试文件大小格式化"""
        self.assertEqual(self.formatter._format_size(500), '500.0B')
        self.assertEqual(self.formatter._format_size(1024), '1.0KB')
        self.assertEqual(self.formatter._format_size(1024 * 1024), '1.0MB')
    
    def test_mask_sensitive(self):
        """测试敏感信息遮蔽"""
        result = self.formatter._mask_sensitive('abcdefghijklmnop')
        self.assertEqual(result, 'abcde***lmnop')
        
        short_result = self.formatter._mask_sensitive('abc')
        self.assertEqual(short_result, '***')


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDebugEnabled))
    suite.addTests(loader.loadTestsFromTestCase(TestSQLQuery))
    suite.addTests(loader.loadTestsFromTestCase(TestRequestDebug))
    suite.addTests(loader.loadTestsFromTestCase(TestDebugToolbar))
    suite.addTests(loader.loadTestsFromTestCase(TestTerminalFormatter))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
