#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.session import Session


class TestSession(unittest.TestCase):
    """测试 Session"""

    def test_init(self):
        """测试初始化"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        self.assertEqual(session.id, session_id)
        self.assertEqual(session.data, {})

    def test_str_representation(self):
        """测试字符串表示"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        session_str = str(session)
        
        self.assertIn(session_id, session_str)
        self.assertIn('Session', session_str)

    def test_data_attribute(self):
        """测试 data 属性"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        self.assertIsInstance(session.data, dict)
        self.assertEqual(len(session.data), 0)

    def test_data_modification(self):
        """测试 data 修改"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        session.data['key1'] = 'value1'
        session.data['key2'] = 'value2'
        
        self.assertEqual(session.data['key1'], 'value1')
        self.assertEqual(session.data['key2'], 'value2')
        self.assertEqual(len(session.data), 2)

    def test_data_deletion(self):
        """测试 data 删除"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        session.data['key1'] = 'value1'
        del session.data['key1']
        
        self.assertNotIn('key1', session.data)

    def test_data_update(self):
        """测试 data 更新"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        session.data['key1'] = 'value1'
        session.data['key1'] = 'new_value'
        
        self.assertEqual(session.data['key1'], 'new_value')

    def test_data_clear(self):
        """测试 data 清空"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        session.data['key1'] = 'value1'
        session.data['key2'] = 'value2'
        session.data.clear()
        
        self.assertEqual(len(session.data), 0)

    def test_multiple_sessions(self):
        """测试多个会话"""
        session1 = Session('session1')
        session2 = Session('session2')
        
        session1.data['key'] = 'value1'
        session2.data['key'] = 'value2'
        
        self.assertEqual(session1.data['key'], 'value1')
        self.assertEqual(session2.data['key'], 'value2')
        self.assertNotEqual(session1.data['key'], session2.data['key'])

    def test_complex_data_types(self):
        """测试复杂数据类型"""
        session_id = 'test_session_id'
        session = Session(session_id)
        
        session.data['list'] = [1, 2, 3]
        session.data['dict'] = {'nested': 'value'}
        session.data['int'] = 123
        session.data['float'] = 3.14
        session.data['bool'] = True
        session.data['none'] = None
        
        self.assertEqual(session.data['list'], [1, 2, 3])
        self.assertEqual(session.data['dict'], {'nested': 'value'})
        self.assertEqual(session.data['int'], 123)
        self.assertEqual(session.data['float'], 3.14)
        self.assertEqual(session.data['bool'], True)
        self.assertIsNone(session.data['none'])


if __name__ == '__main__':
    unittest.main()
