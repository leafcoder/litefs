#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import time
import tempfile
import os

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.cache import MemoryCache, TreeCache, LiteFile


class TestMemoryCache(unittest.TestCase):
    """测试 MemoryCache"""

    def setUp(self):
        """设置测试环境"""
        self.cache = MemoryCache(max_size=100)
        self.cache_key = 'test_key'
        self.cache_value = 'test_val'

    def test_init(self):
        """测试初始化"""
        cache = MemoryCache(max_size=100)
        
        self.assertEqual(cache._max_size, 100)
        self.assertEqual(len(cache), 0)

    def test_put(self):
        """测试 put 方法"""
        cache = MemoryCache(max_size=100)
        
        for i in range(100):
            cache.put(f'{self.cache_key}-{i}', self.cache_value)
        
        self.assertEqual(len(cache), 100)

    def test_get(self):
        """测试 get 方法"""
        cache = MemoryCache(max_size=100)
        
        cache.put(self.cache_key, self.cache_value)
        result = cache.get(self.cache_key)
        
        self.assertEqual(result, self.cache_value)

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = MemoryCache(max_size=100)
        
        result = cache.get('nonexistent_key')
        
        self.assertIsNone(result)

    def test_delete(self):
        """测试 delete 方法"""
        cache = MemoryCache(max_size=100)
        size = len(cache)
        
        cache.put(self.cache_key, self.cache_value)
        cache.delete(self.cache_key)
        
        self.assertEqual(len(cache), size)
        self.assertIsNone(cache.get(self.cache_key))

    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        cache = MemoryCache(max_size=100)
        
        cache.delete('nonexistent_key')
        
        self.assertEqual(len(cache), 0)

    def test_out_of_max_size(self):
        """测试超过最大大小"""
        cache = MemoryCache(max_size=100)
        
        for i in range(1000):
            cache.put(f'{self.cache_key}-{i}', self.cache_value)
        
        self.assertEqual(len(cache), 100)
        
        for i in range(900):
            cache_key = f'{self.cache_key}-{i}'
            self.assertIsNone(cache.get(cache_key))

    def test_lru_eviction(self):
        """测试 LRU 淘汰策略"""
        cache = MemoryCache(max_size=3)
        
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')
        
        self.assertEqual(len(cache), 3)
        self.assertEqual(cache.get('key1'), 'value1')
        
        cache.put('key4', 'value4')
        
        self.assertEqual(len(cache), 3)
        self.assertIsNone(cache.get('key2'))
        self.assertEqual(cache.get('key1'), 'value1')
        self.assertEqual(cache.get('key3'), 'value3')
        self.assertEqual(cache.get('key4'), 'value4')

    def test_update_existing_key(self):
        """测试更新已存在的键"""
        cache = MemoryCache(max_size=100)
        
        cache.put(self.cache_key, 'old_value')
        cache.put(self.cache_key, 'new_value')
        
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get(self.cache_key), 'new_value')

    def test_str_representation(self):
        """测试字符串表示"""
        cache = MemoryCache(max_size=100)
        cache.put('key1', 'value1')
        
        cache_str = str(cache)
        
        self.assertIn('key1', cache_str)
        self.assertIn('value1', cache_str)


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


class TestLiteFile(unittest.TestCase):
    """测试 LiteFile"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, 'test.html')
        self.test_content = b'<html><body>Test Content</body></html>'
        
        with open(self.test_file, 'wb') as f:
            f.write(self.test_content)

    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_init(self):
        """测试初始化"""
        litefile = LiteFile(
            path=self.test_file,
            base='/',
            name='test.html',
            text=self.test_content,
            status_code=200
        )
        
        self.assertEqual(litefile.status_code, 200)
        self.assertEqual(litefile.text, self.test_content)
        self.assertIsNotNone(litefile.etag)
        self.assertIsNotNone(litefile.zlib_text)
        self.assertIsNotNone(litefile.gzip_text)
        self.assertIsNotNone(litefile.last_modified)

    def test_handler_with_no_compression(self):
        """测试不压缩的处理器"""
        from unittest.mock import Mock
        
        litefile = LiteFile(
            path=self.test_file,
            base='/',
            name='test.html',
            text=self.test_content,
            status_code=200
        )
        
        request = Mock()
        request.environ = {
            'HTTP_IF_MODIFIED_SINCE': '',
            'HTTP_IF_NONE_MATCH': '',
            'HTTP_ACCEPT_ENCODING': ''
        }
        
        response = litefile.handler(request)
        
        self.assertIsNotNone(response)
        status, headers, content = response
        self.assertEqual(status, 200)
        self.assertEqual(content, self.test_content)

    def test_handler_with_gzip(self):
        """测试 gzip 压缩的处理器"""
        from unittest.mock import Mock
        
        litefile = LiteFile(
            path=self.test_file,
            base='/',
            name='test.html',
            text=self.test_content,
            status_code=200
        )
        
        request = Mock()
        request.environ = {
            'HTTP_IF_MODIFIED_SINCE': '',
            'HTTP_IF_NONE_MATCH': '',
            'HTTP_ACCEPT_ENCODING': 'gzip'
        }
        
        response = litefile.handler(request)
        
        self.assertIsNotNone(response)
        status, headers, content = response
        self.assertEqual(status, 200)
        self.assertEqual(content, litefile.gzip_text)
        
        header_dict = dict(headers)
        self.assertIn('Content-Encoding', header_dict)
        self.assertEqual(header_dict['Content-Encoding'], 'gzip')

    def test_handler_with_deflate(self):
        """测试 deflate 压缩的处理器"""
        from unittest.mock import Mock
        
        litefile = LiteFile(
            path=self.test_file,
            base='/',
            name='test.html',
            text=self.test_content,
            status_code=200
        )
        
        request = Mock()
        request.environ = {
            'HTTP_IF_MODIFIED_SINCE': '',
            'HTTP_IF_NONE_MATCH': '',
            'HTTP_ACCEPT_ENCODING': 'deflate'
        }
        
        response = litefile.handler(request)
        
        self.assertIsNotNone(response)
        status, headers, content = response
        self.assertEqual(status, 200)
        self.assertEqual(content, litefile.zlib_text)
        
        header_dict = dict(headers)
        self.assertIn('Content-Encoding', header_dict)
        self.assertEqual(header_dict['Content-Encoding'], 'deflate')

    def test_handler_304_not_modified(self):
        """测试 304 Not Modified 响应"""
        from unittest.mock import Mock
        
        litefile = LiteFile(
            path=self.test_file,
            base='/',
            name='test.html',
            text=self.test_content,
            status_code=200
        )
        
        request = Mock()
        request.environ = {
            'HTTP_IF_MODIFIED_SINCE': litefile.last_modified,
            'HTTP_IF_NONE_MATCH': '',
            'HTTP_ACCEPT_ENCODING': ''
        }
        
        response = litefile.handler(request)
        
        self.assertIsNotNone(response)
        status, headers, content = response
        self.assertEqual(status, 304)

    def test_handler_etag_match(self):
        """测试 ETag 匹配"""
        from unittest.mock import Mock
        
        litefile = LiteFile(
            path=self.test_file,
            base='/',
            name='test.html',
            text=self.test_content,
            status_code=200
        )
        
        request = Mock()
        request.environ = {
            'HTTP_IF_MODIFIED_SINCE': '',
            'HTTP_IF_NONE_MATCH': litefile.etag,
            'HTTP_ACCEPT_ENCODING': ''
        }
        
        response = litefile.handler(request)
        
        self.assertIsNotNone(response)
        status, headers, content = response
        self.assertEqual(status, 304)


if __name__ == '__main__':
    unittest.main()
