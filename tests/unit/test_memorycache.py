#!/usr/bin/env python
# -*- coding: utf-8 -*-

import threading
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.cache import MemoryCache


class TestMemoryCache(unittest.TestCase):
    """测试 MemoryCache"""

    def setUp(self):
        """设置测试环境"""
        self.max_size = 100
        self.cache_key = 'test_key'
        self.cache_value = 'test_val'

    def test_init(self):
        """测试初始化"""
        cache = MemoryCache(max_size=self.max_size)
        
        self.assertEqual(cache._max_size, self.max_size)
        self.assertEqual(len(cache), 0)

    def test_put(self):
        """测试 put 方法"""
        cache = MemoryCache(max_size=self.max_size)
        
        for i in range(self.max_size):
            cache.put(f'{self.cache_key}-{i}', self.cache_value)
        
        self.assertEqual(len(cache), self.max_size)

    def test_get(self):
        """测试 get 方法"""
        cache = MemoryCache(max_size=self.max_size)
        
        cache.put(self.cache_key, self.cache_value)
        result = cache.get(self.cache_key)
        
        self.assertEqual(result, self.cache_value)

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = MemoryCache(max_size=self.max_size)
        
        result = cache.get('nonexistent_key')
        
        self.assertIsNone(result)

    def test_delete(self):
        """测试 delete 方法"""
        cache = MemoryCache(max_size=self.max_size)
        size = len(cache)
        
        cache.put(self.cache_key, self.cache_value)
        cache.delete(self.cache_key)
        
        self.assertEqual(len(cache), size)
        self.assertIsNone(cache.get(self.cache_key))

    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        cache = MemoryCache(max_size=self.max_size)
        
        cache.delete('nonexistent_key')
        
        self.assertEqual(len(cache), 0)

    def test_out_of_max_size(self):
        """测试超过最大大小"""
        cache = MemoryCache(max_size=self.max_size)
        
        for i in range(1000):
            cache.put(f'{self.cache_key}-{i}', self.cache_value)
        
        self.assertEqual(len(cache), self.max_size)
        
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
        cache = MemoryCache(max_size=self.max_size)
        
        cache.put(self.cache_key, 'old_value')
        cache.put(self.cache_key, 'new_value')
        
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.get(self.cache_key), 'new_value')

    def test_str_representation(self):
        """测试字符串表示"""
        cache = MemoryCache(max_size=self.max_size)
        cache.put('key1', 'value1')
        
        cache_str = str(cache)
        
        self.assertIn('key1', cache_str)
        self.assertIn('value1', cache_str)

    def test_access_updates_lru(self):
        """测试访问更新 LRU"""
        cache = MemoryCache(max_size=3)
        
        cache.put('key1', 'value1')
        cache.put('key2', 'value2')
        cache.put('key3', 'value3')
        
        cache.get('key1')
        cache.put('key4', 'value4')
        
        self.assertEqual(len(cache), 3)
        self.assertEqual(cache.get('key1'), 'value1')
        self.assertIsNone(cache.get('key2'))
        self.assertEqual(cache.get('key3'), 'value3')
        self.assertEqual(cache.get('key4'), 'value4')


class TestMemoryCacheHardening(unittest.TestCase):
    """v0.11.0 MemoryCache 加固（并发保护 / LRU 顺序）"""

    def test_lru_eviction_order(self):
        """测试 LRU 淘汰顺序：最近访问的键保留，最久未访问的键先逐出"""
        cache = MemoryCache(max_size=3)
        cache.put('k1', 'v1')
        cache.put('k2', 'v2')
        cache.put('k3', 'v3')

        # 访问 k1，使其成为最近使用
        self.assertEqual(cache.get('k1'), 'v1')

        cache.put('k4', 'v4')

        # k2 为最久未访问，应被逐出；k1 因被访问而保留
        self.assertIsNone(cache.get('k2'))
        self.assertEqual(cache.get('k1'), 'v1')
        self.assertEqual(cache.get('k3'), 'v3')
        self.assertEqual(cache.get('k4'), 'v4')

    def test_concurrent_put_get_delete(self):
        """测试多线程并发读写删除不崩溃、数据最终一致"""
        cache = MemoryCache(max_size=1000)
        errors = []
        barrier = threading.Barrier(8)

        def worker(worker_id):
            barrier.wait()
            try:
                for i in range(200):
                    key = f'k{worker_id * 200 + i}'
                    cache.put(key, i)
                    self.assertEqual(cache.get(key), i)
                    if i % 2 == 0:
                        cache.delete(key)
                        self.assertIsNone(cache.get(key))
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(cache), 800)

    def test_concurrent_eviction_no_crash(self):
        """测试并发触发 LRU 淘汰与过期清理不崩溃"""
        cache = MemoryCache(max_size=50)
        errors = []
        barrier = threading.Barrier(8)

        def worker(worker_id):
            barrier.wait()
            try:
                for i in range(300):
                    cache.put(f'k{worker_id}-{i}', i, expiration=0.01)
            except Exception as e:  # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertLessEqual(len(cache), 50)


if __name__ == '__main__':
    unittest.main()
