#!/usr/bin/env python
# coding: utf-8

import unittest
import os
import tempfile
from litefs.cache import DatabaseCache


class TestDatabaseCache(unittest.TestCase):
    """测试 DatabaseCache"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_cache.db")
        self.cache = DatabaseCache(db_path=self.db_path)

    def tearDown(self):
        """测试后清理"""
        self.cache.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_put_and_get(self):
        """测试存储和获取"""
        self.cache.put("key1", "value1")
        self.assertEqual(self.cache.get("key1"), "value1")

    def test_put_with_expiration(self):
        """测试带过期时间的存储"""
        self.cache.put("key1", "value1", expiration=1)
        self.assertEqual(self.cache.get("key1"), "value1")

    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_delete(self):
        """测试删除"""
        self.cache.put("key1", "value1")
        self.cache.delete("key1")
        self.assertIsNone(self.cache.get("key1"))

    def test_exists(self):
        """测试检查键是否存在"""
        self.cache.put("key1", "value1")
        self.assertTrue(self.cache.exists("key1"))
        self.assertFalse(self.cache.exists("nonexistent"))

    def test_expire(self):
        """测试设置过期时间"""
        self.cache.put("key1", "value1")
        self.assertTrue(self.cache.expire("key1", 3600))
        self.assertFalse(self.cache.expire("nonexistent", 3600))

    def test_ttl(self):
        """测试获取剩余过期时间"""
        self.cache.put("key1", "value1", expiration=3600)
        ttl = self.cache.ttl("key1")
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 3600)

    def test_clear(self):
        """测试清空缓存"""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.clear()
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))

    def test_len(self):
        """测试获取缓存大小"""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.assertEqual(len(self.cache), 2)

    def test_get_many(self):
        """测试批量获取"""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.put("key3", "value3")
        
        result = self.cache.get_many(["key1", "key2", "key4"])
        self.assertEqual(result["key1"], "value1")
        self.assertEqual(result["key2"], "value2")
        self.assertNotIn("key4", result)

    def test_set_many(self):
        """测试批量存储"""
        mapping = {"key1": "value1", "key2": "value2", "key3": "value3"}
        self.cache.set_many(mapping)
        
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")

    def test_delete_many(self):
        """测试批量删除"""
        self.cache.put("key1", "value1")
        self.cache.put("key2", "value2")
        self.cache.put("key3", "value3")
        
        self.cache.delete_many(["key1", "key2"])
        
        self.assertIsNone(self.cache.get("key1"))
        self.assertIsNone(self.cache.get("key2"))
        self.assertEqual(self.cache.get("key3"), "value3")

    def test_context_manager(self):
        """测试上下文管理器"""
        with DatabaseCache(db_path=self.db_path) as cache:
            cache.put("key1", "value1")
            self.assertEqual(cache.get("key1"), "value1")

    def test_complex_data_types(self):
        """测试复杂数据类型"""
        import pickle
        
        data = {
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "tuple": (1, 2, 3),
            "set": {1, 2, 3},
        }
        
        self.cache.put("complex", data)
        result = self.cache.get("complex")
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["list"], [1, 2, 3])
            self.assertEqual(result["dict"], {"a": 1, "b": 2})


if __name__ == "__main__":
    unittest.main()