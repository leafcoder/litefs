#!/usr/bin/env python
# coding: utf-8

"""
缓存后端 Web 示例测试

测试各类缓存后端在 Web 界面中的功能
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

import unittest
import json
from litefs.cache import (
    MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache
)


class TestCacheBackendsWeb(unittest.TestCase):
    """测试缓存后端 Web 示例"""

    def setUp(self):
        """设置测试环境"""
        self.test_data = {
            'test_key': 'test_value',
            'user:1': json.dumps({'id': 1, 'name': '张三', 'age': 25}),
            'user:2': json.dumps({'id': 2, 'name': '李四', 'age': 30}),
            'user:3': json.dumps({'id': 3, 'name': '王五', 'age': 28}),
        }

    def test_memory_cache(self):
        """测试 Memory Cache"""
        cache = MemoryCache(max_size=10000)
        
        cache.put('test_key', 'test_value')
        self.assertEqual(cache.get('test_key'), 'test_value')
        
        cache.put('user:1', json.dumps({'id': 1, 'name': '张三', 'age': 25}))
        self.assertIsNotNone(cache.get('user:1'))
        
        if hasattr(cache, 'exists'):
            self.assertTrue(cache.exists('test_key'))
            cache.delete('test_key')
            self.assertFalse(cache.exists('test_key'))
        else:
            cache.delete('test_key')
            self.assertIsNone(cache.get('test_key'))
        
        cache_size = len(cache)
        self.assertGreaterEqual(cache_size, 0)

    def test_tree_cache(self):
        """测试 Tree Cache"""
        cache = TreeCache(clean_period=60, expiration_time=3600)
        
        cache.put('test_key', 'test_value')
        self.assertEqual(cache.get('test_key'), 'test_value')
        
        cache.put('user:1:name', '张三')
        self.assertEqual(cache.get('user:1:name'), '张三')
        
        cache.delete('test_key')
        self.assertIsNone(cache.get('test_key'))

    def test_database_cache(self):
        """测试 Database Cache"""
        cache = DatabaseCache(
            db_path=':memory:',
            table_name='cache',
            expiration_time=3600
        )
        
        cache.put('test_key', 'test_value')
        self.assertEqual(cache.get('test_key'), 'test_value')
        
        cache.put('user:1', json.dumps({'id': 1, 'name': '张三', 'age': 25}))
        self.assertIsNotNone(cache.get('user:1'))
        
        cache.delete('test_key')
        self.assertIsNone(cache.get('test_key'))
        
        cache.close()

    def test_redis_cache(self):
        """测试 Redis Cache"""
        try:
            cache = RedisCache(
                host='localhost',
                port=6379,
                db=0,
                key_prefix='test_litefs:',
                expiration_time=3600
            )
            
            cache.put('test_key', 'test_value')
            self.assertEqual(cache.get('test_key'), 'test_value')
            
            cache.put('user:1', json.dumps({'id': 1, 'name': '张三', 'age': 25}))
            self.assertIsNotNone(cache.get('user:1'))
            
            self.assertTrue(cache.exists('test_key'))
            cache.delete('test_key')
            self.assertFalse(cache.exists('test_key'))
            
            cache.put('temp_data', 'This data will expire', expiration=30)
            ttl = cache.ttl('temp_data')
            self.assertGreater(ttl, 0)
            
            cache.set_many({
                'product:1': json.dumps({'name': '商品1', 'price': 100}),
                'product:2': json.dumps({'name': '商品2', 'price': 200}),
            })
            
            values = cache.get_many(['product:1', 'product:2'])
            self.assertEqual(len(values), 2)
            
            cache.delete_many(['product:1', 'product:2'])
            
            cache.close()
            
        except (ImportError, ConnectionError) as e:
            self.skipTest(f"Redis 不可用: {e}")

    def test_memcache_cache(self):
        """测试 Memcache Cache"""
        try:
            cache = MemcacheCache(
                servers=['localhost:11211'],
                key_prefix='test_litefs:',
                expiration_time=3600
            )
            
            cache.put('test_key', 'test_value')
            self.assertEqual(cache.get('test_key'), 'test_value')
            
            cache.put('user:1', json.dumps({'id': 1, 'name': '张三', 'age': 25}))
            self.assertIsNotNone(cache.get('user:1'))
            
            cache.delete('test_key')
            self.assertIsNone(cache.get('test_key'))
            
            cache.close()
            
        except (ImportError, ConnectionError) as e:
            self.skipTest(f"Memcache 不可用: {e}")

    def test_cache_operations(self):
        """测试缓存操作"""
        cache = MemoryCache(max_size=10000)
        
        cache.put('test_key', 'test_value')
        self.assertEqual(cache.get('test_key'), 'test_value')
        
        cache.put('user:1', json.dumps({'id': 1, 'name': '张三', 'age': 25}))
        cache.put('user:2', json.dumps({'id': 2, 'name': '李四', 'age': 30}))
        cache.put('user:3', json.dumps({'id': 3, 'name': '王五', 'age': 28}))
        
        self.assertIsNotNone(cache.get('user:1'))
        self.assertIsNotNone(cache.get('user:2'))
        self.assertIsNotNone(cache.get('user:3'))
        
        large_data = {'data': list(range(1000)), 'timestamp': '2024-01-01'}
        cache.put('large_data', large_data)
        self.assertIsNotNone(cache.get('large_data'))
        
        if hasattr(cache, 'clear'):
            cache.clear()
            self.assertIsNone(cache.get('test_key'))
        else:
            cache.delete('test_key')
            cache.delete('user:1')
            cache.delete('user:2')
            cache.delete('user:3')
            cache.delete('large_data')

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        cache = MemoryCache(max_size=10000)
        
        user_data = {'id': 1, 'name': '张三', 'age': 25}
        cache.put('user:1', json.dumps(user_data))
        
        retrieved = cache.get('user:1')
        self.assertIsNotNone(retrieved)
        
        if retrieved is not None:
            parsed_user = json.loads(retrieved)
            self.assertEqual(parsed_user['id'], 1)
            self.assertEqual(parsed_user['name'], '张三')
            self.assertEqual(parsed_user['age'], 25)

    def test_cache_ttl_operations(self):
        """测试缓存 TTL 操作"""
        try:
            cache = RedisCache(
                host='localhost',
                port=6379,
                db=0,
                key_prefix='test_litefs:',
                expiration_time=3600
            )
            
            cache.put('temp_data', 'This data will expire', expiration=30)
            ttl = cache.ttl('temp_data')
            self.assertGreater(ttl, 0)
            self.assertLessEqual(ttl, 30)
            
            cache.expire('temp_data', 60)
            new_ttl = cache.ttl('temp_data')
            self.assertGreater(new_ttl, 30)
            
            cache.close()
            
        except (ImportError, ConnectionError) as e:
            self.skipTest(f"Redis 不可用: {e}")


if __name__ == '__main__':
    unittest.main()
