#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.handlers.request import parse_form


class TestParseForm(unittest.TestCase):
    """测试 parse_form 函数"""

    def test_simple_form(self):
        """测试简单表单"""
        query_string = "name=tom&value=123"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], 'tom')
        self.assertEqual(form['value'], '123')

    def test_url_encoded_form(self):
        """测试 URL 编码的表单"""
        query_string = "name=%E6%B1%A4%E5%A7%86&value=%E6%9D%B0%E7%91%9E"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], '汤姆')
        self.assertEqual(form['value'], '杰瑞')

    def test_array_notation(self):
        """测试数组表示法"""
        query_string = "tags[]=tag1&tags[]=tag2&tags[]=tag3"
        form = parse_form(query_string)
        
        self.assertIsInstance(form['tags'], list)
        self.assertEqual(len(form['tags']), 3)
        self.assertEqual(form['tags'], ['tag1', 'tag2', 'tag3'])

    def test_dict_notation(self):
        """测试字典表示法"""
        query_string = "user[name]=tom&user[age]=25"
        form = parse_form(query_string)
        
        self.assertIsInstance(form['user'], dict)
        self.assertEqual(form['user']['name'], 'tom')
        self.assertEqual(form['user']['age'], '25')

    def test_mixed_notation(self):
        """测试混合表示法"""
        query_string = "name=tom&tags[]=tag1&user[name]=jerry"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], 'tom')
        self.assertIsInstance(form['tags'], list)
        self.assertEqual(form['tags'], ['tag1'])
        self.assertIsInstance(form['user'], dict)
        self.assertEqual(form['user']['name'], 'jerry')

    def test_empty_value(self):
        """测试空值"""
        query_string = "name=&value=123"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], '')
        self.assertEqual(form['value'], '123')

    def test_no_value(self):
        """测试没有值的键"""
        query_string = "name&value=123"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], '')
        self.assertEqual(form['value'], '123')

    def test_special_characters(self):
        """测试特殊字符"""
        query_string = "name=hello%20world&value=test%40email.com"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], 'hello world')
        self.assertEqual(form['value'], 'test@email.com')

    def test_multiple_same_keys(self):
        """测试相同的键"""
        query_string = "name=tom&name=jerry&name=spike"
        form = parse_form(query_string)
        
        self.assertIsInstance(form['name'], list)
        self.assertEqual(form['name'], ['tom', 'jerry', 'spike'])

    def test_empty_query_string(self):
        """测试空查询字符串"""
        query_string = ""
        form = parse_form(query_string)
        
        self.assertEqual(form, {})

    def test_complex_form(self):
        """测试复杂表单"""
        query_string = "name=tom&age=25&tags[]=python&tags[]=django&user[name]=jerry&user[age]=30"
        form = parse_form(query_string)
        
        self.assertEqual(form['name'], 'tom')
        self.assertEqual(form['age'], '25')
        self.assertIsInstance(form['tags'], list)
        self.assertEqual(form['tags'], ['python', 'django'])
        self.assertIsInstance(form['user'], dict)
        self.assertEqual(form['user']['name'], 'jerry')
        self.assertEqual(form['user']['age'], '30')


if __name__ == '__main__':
    unittest.main()
