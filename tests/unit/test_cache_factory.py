#!/usr/bin/env python
# coding: utf-8

"""
缓存工厂测试

覆盖 CacheFactory 按后端类型创建实例、非法后端报错与配置对象驱动的创建。
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from litefs.cache.cache import MemoryCache, TreeCache
from litefs.cache.db import DatabaseCache
from litefs.cache.factory import CacheBackend, CacheFactory


class TestCacheFactoryCreate(unittest.TestCase):
    """create_cache 按类型创建"""

    def test_memory_backend(self):
        """memory 后端返回 MemoryCache"""
        cache = CacheFactory.create_cache('memory', max_size=123)
        self.assertIsInstance(cache, MemoryCache)
        self.assertEqual(cache._max_size, 123)

    def test_backend_case_insensitive(self):
        """后端名大小写不敏感"""
        cache = CacheFactory.create_cache('MEMORY')
        self.assertIsInstance(cache, MemoryCache)

    def test_tree_backend(self):
        """tree 后端返回 TreeCache"""
        cache = CacheFactory.create_cache('tree', clean_period=30, expiration_time=120)
        self.assertIsInstance(cache, TreeCache)
        self.assertEqual(cache.clean_period, 30)

    def test_database_backend(self):
        """database 后端返回 DatabaseCache（内存库）"""
        cache = CacheFactory.create_cache('database', db_path=':memory:')
        self.assertIsInstance(cache, DatabaseCache)

    def test_redis_backend_passes_config(self):
        """redis 后端透传连接配置"""
        with patch('litefs.cache.factory.RedisCache') as mock_redis:
            CacheFactory.create_cache(
                'redis', host='r.example.com', port=6380, db=2,
                password='pw', key_prefix='app:', expiration_time=60,
                unknown_extra='x',
            )
            kwargs = mock_redis.call_args.kwargs
            self.assertEqual(kwargs['host'], 'r.example.com')
            self.assertEqual(kwargs['port'], 6380)
            self.assertEqual(kwargs['db'], 2)
            self.assertEqual(kwargs['password'], 'pw')
            self.assertEqual(kwargs['key_prefix'], 'app:')
            self.assertEqual(kwargs['expiration_time'], 60)

    def test_memcache_backend_passes_config(self):
        """memcache 后端透传连接配置"""
        with patch('litefs.cache.factory.MemcacheCache') as mock_memcache:
            CacheFactory.create_cache(
                'memcache', servers=['s:11211'], key_prefix='m:',
                expiration_time=120,
            )
            kwargs = mock_memcache.call_args.kwargs
            self.assertEqual(kwargs['servers'], ['s:11211'])
            self.assertEqual(kwargs['key_prefix'], 'm:')
            self.assertEqual(kwargs['expiration_time'], 120)

    def test_unknown_backend_raises(self):
        """未知后端抛 ValueError"""
        with self.assertRaises(ValueError):
            CacheFactory.create_cache('unknown-backend')


class TestCacheFactoryFromConfig(unittest.TestCase):
    """create_from_config 配置对象驱动"""

    def test_memory_from_config(self):
        """memory 后端从配置读取 max_size"""
        config = SimpleNamespace(cache_backend='memory', cache_max_size=555)
        cache = CacheFactory.create_from_config(config)
        self.assertIsInstance(cache, MemoryCache)
        self.assertEqual(cache._max_size, 555)

    def test_default_backend_is_memory(self):
        """未指定后端时默认 memory"""
        cache = CacheFactory.create_from_config(SimpleNamespace())
        self.assertIsInstance(cache, MemoryCache)

    def test_tree_from_config(self):
        """tree 后端从配置读取参数"""
        config = SimpleNamespace(
            cache_backend='tree', cache_clean_period=45, cache_expiration_time=180,
        )
        cache = CacheFactory.create_from_config(config)
        self.assertIsInstance(cache, TreeCache)
        self.assertEqual(cache.clean_period, 45)

    def test_database_from_config(self):
        """database 后端从配置读取参数"""
        config = SimpleNamespace(
            cache_backend='database', database_path=':memory:',
            database_cache_table='app_cache', cache_expiration_time=90,
        )
        cache = CacheFactory.create_from_config(config)
        self.assertIsInstance(cache, DatabaseCache)

    def test_redis_from_config(self):
        """redis 后端从配置读取连接参数"""
        config = SimpleNamespace(
            cache_backend='redis', redis_host='cfg.example.com', redis_port=6399,
            redis_db=3, redis_password='secret', redis_key_prefix='cfg:',
            cache_expiration_time=240,
        )
        with patch('litefs.cache.factory.RedisCache') as mock_redis:
            CacheFactory.create_from_config(config)
            kwargs = mock_redis.call_args.kwargs
            self.assertEqual(kwargs['host'], 'cfg.example.com')
            self.assertEqual(kwargs['port'], 6399)
            self.assertEqual(kwargs['db'], 3)
            self.assertEqual(kwargs['password'], 'secret')
            self.assertEqual(kwargs['key_prefix'], 'cfg:')
            self.assertEqual(kwargs['expiration_time'], 240)

    def test_memcache_from_config(self):
        """memcache 后端从配置读取连接参数"""
        config = SimpleNamespace(
            cache_backend='memcache', memcache_servers=['c:11211'],
            memcache_key_prefix='cfg:', cache_expiration_time=300,
        )
        with patch('litefs.cache.factory.MemcacheCache') as mock_memcache:
            CacheFactory.create_from_config(config)
            kwargs = mock_memcache.call_args.kwargs
            self.assertEqual(kwargs['servers'], ['c:11211'])
            self.assertEqual(kwargs['key_prefix'], 'cfg:')


class TestCacheBackendConstants(unittest.TestCase):
    """CacheBackend 常量"""

    def test_backend_type_constants(self):
        """后端类型常量与工厂分支一致"""
        self.assertEqual(CacheBackend.MEMORY, 'memory')
        self.assertEqual(CacheBackend.TREE, 'tree')
        self.assertEqual(CacheBackend.REDIS, 'redis')
        self.assertEqual(CacheBackend.DATABASE, 'database')
        self.assertEqual(CacheBackend.MEMCACHE, 'memcache')


if __name__ == '__main__':
    unittest.main()
