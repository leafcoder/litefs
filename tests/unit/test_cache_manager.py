#!/usr/bin/env python
# coding: utf-8

"""
缓存管理器单元测试

验证 CacheManager 的单例模式和全局缓存功能
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs.cache import (
    CacheManager,
    CacheBackend,
    MemoryCache,
    TreeCache,
    get_global_cache,
)


class TestCacheManager(unittest.TestCase):
    """测试缓存管理器"""

    def setUp(self):
        """每个测试前重置缓存"""
        CacheManager.reset_cache()

    def tearDown(self):
        """每个测试后清理缓存"""
        CacheManager.reset_cache()

    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = CacheManager()
        manager2 = CacheManager()
        self.assertIs(manager1, manager2)

    def test_get_cache_creates_instance(self):
        """测试获取缓存自动创建实例"""
        cache = CacheManager.get_cache(backend=CacheBackend.MEMORY)
        self.assertIsNotNone(cache)
        self.assertIsInstance(cache, MemoryCache)

    def test_get_cache_returns_same_instance(self):
        """测试相同 cache_key 返回同一实例"""
        cache1 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='test_cache'
        )
        cache2 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='test_cache'
        )
        self.assertIs(cache1, cache2)

    def test_get_cache_data_persistence(self):
        """测试缓存数据持久化"""
        cache1 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='data_test'
        )
        cache1.put('key1', 'value1')

        # 重新获取同一缓存，数据应该还在
        cache2 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='data_test'
        )
        self.assertEqual(cache2.get('key1'), 'value1')

    def test_get_session_cache(self):
        """测试获取会话缓存"""
        cache = CacheManager.get_session_cache()
        self.assertIsInstance(cache, MemoryCache)

        # 再次获取应该是同一实例
        cache2 = CacheManager.get_session_cache()
        self.assertIs(cache, cache2)

    def test_get_file_cache(self):
        """测试获取文件缓存"""
        cache = CacheManager.get_file_cache()
        self.assertIsInstance(cache, TreeCache)

        # 再次获取应该是同一实例
        cache2 = CacheManager.get_file_cache()
        self.assertIs(cache, cache2)

    def test_reset_single_cache(self):
        """测试重置单个缓存"""
        cache1 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='reset_test1'
        )
        cache2 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='reset_test2'
        )

        cache1.put('key', 'value')
        cache2.put('key', 'value')

        # 重置单个缓存
        CacheManager.reset_cache('reset_test1')

        # cache1 应该被重置
        self.assertFalse(CacheManager.has_cache('reset_test1'))
        # cache2 应该还在
        self.assertTrue(CacheManager.has_cache('reset_test2'))

    def test_reset_all_caches(self):
        """测试重置所有缓存"""
        CacheManager.get_cache(backend=CacheBackend.MEMORY, cache_key='cache1')
        CacheManager.get_cache(backend=CacheBackend.MEMORY, cache_key='cache2')

        self.assertTrue(CacheManager.has_cache('cache1'))
        self.assertTrue(CacheManager.has_cache('cache2'))

        CacheManager.reset_cache()

        self.assertFalse(CacheManager.has_cache('cache1'))
        self.assertFalse(CacheManager.has_cache('cache2'))

    def test_list_caches(self):
        """测试列出所有缓存"""
        CacheManager.reset_cache()

        CacheManager.get_cache(backend=CacheBackend.MEMORY, cache_key='cache_a')
        CacheManager.get_cache(backend=CacheBackend.MEMORY, cache_key='cache_b')

        caches = CacheManager.list_caches()
        self.assertIn('cache_a', caches)
        self.assertIn('cache_b', caches)

    def test_get_global_cache_convenience(self):
        """测试便捷函数 get_global_cache"""
        cache1 = get_global_cache(backend=CacheBackend.MEMORY)
        cache1.put('global_key', 'global_value')

        cache2 = get_global_cache(backend=CacheBackend.MEMORY)
        self.assertEqual(cache2.get('global_key'), 'global_value')

    def test_different_cache_keys_different_instances(self):
        """测试不同 cache_key 创建不同实例"""
        cache1 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='key1'
        )
        cache2 = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='key2'
        )
        self.assertIsNot(cache1, cache2)

    def test_cache_persists_across_litefs_instances(self):
        """测试缓存在多个 Litefs 实例间共享"""
        from litefs.core import Litefs

        # 重置缓存
        CacheManager.reset_cache()

        # 创建第一个应用实例
        app1 = Litefs(
            host='localhost',
            port=9090,
            webroot='./site',
        )
        app1.caches.put('shared_key', 'shared_value')

        # 创建第二个应用实例
        app2 = Litefs(
            host='localhost',
            port=9091,
            webroot='./site',
        )

        # 第二个实例应该能访问第一个实例写入的数据
        self.assertEqual(app2.caches.get('shared_key'), 'shared_value')

        # 验证是同一缓存实例
        self.assertIs(app1.caches, app2.caches)


if __name__ == '__main__':
    unittest.main()
