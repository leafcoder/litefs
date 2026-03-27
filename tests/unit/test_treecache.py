#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.cache import TreeCache


class TestTreeCache(unittest.TestCase):
    """测试 TreeCache"""

    def setUp(self):
        """设置测试环境"""
        self.cache = TreeCache(clean_period=60, expiration_time=3600)

    def test_init(self):
        """测试初始化"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        self.assertEqual(cache.clean_period, 60)
        self.assertEqual(cache.expiration_time, 3600)
        self.assertEqual(len(cache), 0)

    def test_put(self):
        """测试 put 方法"""
        caches = {
            'k_int': 1,
            'k_str': 'hello',
            'k_float': 0.5
        }
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        for k, v in caches.items():
            cache.put(k, v)
        
        self.assertEqual(len(cache), len(caches))

    def test_get(self):
        """测试 get 方法"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('test_key', 'test_value')
        result = cache.get('test_key')
        
        self.assertEqual(result, 'test_value')

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        result = cache.get('nonexistent_key')
        
        self.assertIsNone(result)

    def test_delete(self):
        """测试 delete 方法"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        cache_key = 'delete_key'
        
        cache.put(cache_key, 'delete me')
        size_before_delete = len(cache)
        cache.delete(cache_key)
        size_after_delete = len(cache)
        
        self.assertEqual(size_before_delete, size_after_delete + 1)
        self.assertIsNone(cache.get(cache_key))

    def test_delete_with_wildcard(self):
        """测试删除带通配符的键"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('/path1/file1', 'value1')
        cache.put('/path1/file2', 'value2')
        cache.put('/path2/file3', 'value3')
        
        cache.delete('/path1')
        
        self.assertIsNone(cache.get('/path1/file1'))
        self.assertIsNone(cache.get('/path1/file2'))
        self.assertEqual(cache.get('/path2/file3'), 'value3')

    def test_expiration(self):
        """测试过期机制"""
        cache = TreeCache(clean_period=1, expiration_time=1)
        
        cache.put('expire_key', 'expire_value')
        self.assertIsNotNone(cache.get('expire_key'))
        
        time.sleep(2)
        
        result = cache.get('expire_key')
        self.assertIsNone(result)

    def test_auto_clean(self):
        """测试自动清理"""
        cache = TreeCache(clean_period=1, expiration_time=1)
        
        for i in range(10):
            cache.put(f'key{i}', f'value{i}')
        
        self.assertEqual(len(cache), 10)
        
        time.sleep(2)
        
        cache.get('key0')
        
        self.assertEqual(len(cache), 0)

    def test_update_existing_key(self):
        """测试更新已存在的键"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('test_key', 'old_value')
        cache.put('test_key', 'new_value')
        
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get('test_key'), 'new_value')

    def test_complex_data_types(self):
        """测试复杂数据类型"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('list_key', [1, 2, 3])
        cache.put('dict_key', {'nested': 'value'})
        cache.put('int_key', 123)
        cache.put('float_key', 3.14)
        cache.put('bool_key', True)
        cache.put('none_key', None)
        
        self.assertEqual(cache.get('list_key'), [1, 2, 3])
        self.assertEqual(cache.get('dict_key'), {'nested': 'value'})
        self.assertEqual(cache.get('int_key'), 123)
        self.assertEqual(cache.get('float_key'), 3.14)
        self.assertEqual(cache.get('bool_key'), True)
        self.assertIsNone(cache.get('none_key'))

    def test_path_like_keys(self):
        """测试路径风格的键"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('/api/users', 'users')
        cache.put('/api/posts', 'posts')
        cache.put('/api/comments', 'comments')
        
        self.assertEqual(len(cache), 3)
        self.assertEqual(cache.get('/api/users'), 'users')
        self.assertEqual(cache.get('/api/posts'), 'posts')
        self.assertEqual(cache.get('/api/comments'), 'comments')

    def test_delete_nested_path(self):
        """测试删除嵌套路径"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('/api/v1/users', 'v1_users')
        cache.put('/api/v1/posts', 'v1_posts')
        cache.put('/api/v2/users', 'v2_users')
        cache.put('/api/v2/posts', 'v2_posts')
        
        cache.delete('/api/v1')
        
        self.assertIsNone(cache.get('/api/v1/users'))
        self.assertIsNone(cache.get('/api/v1/posts'))
        self.assertEqual(cache.get('/api/v2/users'), 'v2_users')
        self.assertEqual(cache.get('/api/v2/posts'), 'v2_posts')

    def test_no_expiration(self):
        """测试长时间不过期"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('no_expire_key', 'no_expire_value')
        
        time.sleep(1)
        
        result = cache.get('no_expire_key')
        self.assertEqual(result, 'no_expire_value')


if __name__ == '__main__':
    unittest.main()
