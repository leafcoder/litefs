#!/usr/bin/env python
# coding: utf-8

"""
Redis 缓存功能测试
"""

import unittest

from litefs.cache import CacheBackend, CacheFactory, MemoryCache, TreeCache


class TestCacheFactory(unittest.TestCase):
    """测试缓存工厂"""

    def test_create_memory_cache(self):
        """测试创建内存缓存"""
        cache = CacheFactory.create_cache(CacheBackend.MEMORY)
        self.assertIsInstance(cache, MemoryCache)

    def test_create_tree_cache(self):
        """测试创建树缓存"""
        cache = CacheFactory.create_cache(CacheBackend.TREE)
        self.assertIsInstance(cache, TreeCache)

    def test_create_memory_cache_with_config(self):
        """测试创建带配置的内存缓存"""
        cache = CacheFactory.create_cache(CacheBackend.MEMORY, max_size=5000)
        self.assertIsInstance(cache, MemoryCache)

    def test_create_tree_cache_with_config(self):
        """测试创建带配置的树缓存"""
        cache = CacheFactory.create_cache(
            CacheBackend.TREE,
            clean_period=30,
            expiration_time=1800
        )
        self.assertIsInstance(cache, TreeCache)

    def test_invalid_backend(self):
        """测试无效的缓存后端"""
        with self.assertRaises(ValueError):
            CacheFactory.create_cache("invalid_backend")

    def test_create_from_config_memory(self):
        """测试从配置创建内存缓存"""
        class Config:
            cache_backend = CacheBackend.MEMORY
            cache_max_size = 5000

        cache = CacheFactory.create_from_config(Config())
        self.assertIsInstance(cache, MemoryCache)

    def test_create_from_config_tree(self):
        """测试从配置创建树缓存"""
        class Config:
            cache_backend = CacheBackend.TREE
            cache_clean_period = 30
            cache_expiration_time = 1800

        cache = CacheFactory.create_from_config(Config())
        self.assertIsInstance(cache, TreeCache)

    def test_create_from_config_default(self):
        """测试从配置创建默认缓存"""
        class Config:
            pass

        cache = CacheFactory.create_from_config(Config())
        self.assertIsInstance(cache, MemoryCache)


class TestCacheBackend(unittest.TestCase):
    """测试缓存后端类型"""

    def test_memory_backend(self):
        """测试内存缓存后端"""
        self.assertEqual(CacheBackend.MEMORY, "memory")

    def test_tree_backend(self):
        """测试树缓存后端"""
        self.assertEqual(CacheBackend.TREE, "tree")

    def test_redis_backend(self):
        """测试 Redis 缓存后端"""
        self.assertEqual(CacheBackend.REDIS, "redis")


class TestMemoryCache(unittest.TestCase):
    """测试内存缓存"""

    def test_put_and_get(self):
        """测试存储和获取"""
        cache = MemoryCache(max_size=100)
        cache.put("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = MemoryCache(max_size=100)
        self.assertIsNone(cache.get("nonexistent"))

    def test_delete(self):
        """测试删除"""
        cache = MemoryCache(max_size=100)
        cache.put("key1", "value1")
        cache.delete("key1")
        self.assertIsNone(cache.get("key1"))

    def test_max_size(self):
        """测试最大容量"""
        cache = MemoryCache(max_size=3)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        cache.put("key4", "value4")
        self.assertIsNone(cache.get("key1"))
        self.assertEqual(cache.get("key4"), "value4")

    def test_update_existing_key(self):
        """测试更新已存在的键"""
        cache = MemoryCache(max_size=100)
        cache.put("key1", "value1")
        cache.put("key1", "value2")
        self.assertEqual(cache.get("key1"), "value2")

    def test_len(self):
        """测试获取缓存大小"""
        cache = MemoryCache(max_size=100)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        self.assertEqual(len(cache), 2)


class TestTreeCache(unittest.TestCase):
    """测试树缓存"""

    def test_put_and_get(self):
        """测试存储和获取"""
        cache = TreeCache(expiration_time=3600)
        cache.put("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")

    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = TreeCache(expiration_time=3600)
        self.assertIsNone(cache.get("nonexistent"))

    def test_delete(self):
        """测试删除"""
        cache = TreeCache(expiration_time=3600)
        cache.put("key1", "value1")
        cache.delete("key1")
        self.assertIsNone(cache.get("key1"))

    def test_expiration(self):
        """测试过期"""
        cache = TreeCache(expiration_time=1)
        cache.put("key1", "value1")
        import time
        time.sleep(2)
        self.assertIsNone(cache.get("key1"))

    def test_delete_pattern(self):
        """测试删除匹配模式的键"""
        cache = TreeCache(expiration_time=3600)
        cache.put("user/1", "value1")
        cache.put("user/2", "value2")
        cache.put("post/1", "value3")
        cache.delete("user/1")
        self.assertIsNone(cache.get("user/1"))
        self.assertEqual(cache.get("user/2"), "value2")
        self.assertEqual(cache.get("post/1"), "value3")

    def test_len(self):
        """测试获取缓存大小"""
        cache = TreeCache(expiration_time=3600)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        self.assertEqual(len(cache), 2)


if __name__ == '__main__':
    unittest.main()
