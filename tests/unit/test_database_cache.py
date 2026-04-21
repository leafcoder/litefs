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
        data = {
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "nested": {"inner": {"deep": [4, 5, 6]}},
        }
        
        self.cache.put("complex", data)
        result = self.cache.get("complex")
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["list"], [1, 2, 3])
            self.assertEqual(result["dict"], {"a": 1, "b": 2})
            self.assertEqual(result["nested"]["inner"]["deep"], [4, 5, 6])

    def test_no_pickle_in_source(self):
        """测试源码中不包含 pickle（安全修复验证）"""
        import inspect
        from litefs.cache.db import DatabaseCache
        source = inspect.getsource(DatabaseCache)
        # pickle.dumps 和 pickle.loads 不应出现（注释中的说明除外）
        self.assertNotIn("pickle.dumps", source, "DatabaseCache 不应使用 pickle.dumps")
        self.assertNotIn("pickle.loads", source, "DatabaseCache 不应使用 pickle.loads")

    def test_json_serialization_used(self):
        """测试使用 JSON 序列化（替代 pickle）"""
        import inspect
        from litefs.cache.db import DatabaseCache
        source = inspect.getsource(DatabaseCache)
        self.assertIn("json.dumps", source, "DatabaseCache 应使用 json.dumps 序列化")
        self.assertIn("json.loads", source, "DatabaseCache 应使用 json.loads 反序列化")

    def test_serialize_deserialize_dict(self):
        """测试字典的序列化/反序列化"""
        data = {"key": "value", "number": 42, "nested": {"a": 1}}
        serialized = self.cache._serialize(data)
        self.assertIsInstance(serialized, str)
        deserialized = self.cache._deserialize(serialized)
        self.assertEqual(deserialized, data)

    def test_serialize_deserialize_list(self):
        """测试列表的序列化/反序列化"""
        data = [1, "two", 3.0, {"four": 4}]
        serialized = self.cache._serialize(data)
        deserialized = self.cache._deserialize(serialized)
        self.assertEqual(deserialized, data)

    def test_deserialize_corrupt_data_returns_error(self):
        """测试损坏数据反序列化抛出 ValueError"""
        with self.assertRaises(ValueError):
            self.cache._deserialize("not_valid_base64!!!")

    def test_get_corrupt_data_returns_none(self):
        """测试获取损坏缓存数据返回 None 而非崩溃"""
        # 直接写入损坏数据到数据库
        self.cache._cursor.execute(
            f"INSERT OR REPLACE INTO {self.cache._table_name} "
            "(key, value, timestamp, expiration) VALUES (?, ?, ?, ?)",
            ("corrupt_key", "not_valid_base64!!!", 0, 9999999999)
        )
        self.cache._conn.commit()
        # get() 应返回 None 而非抛出异常
        result = self.cache.get("corrupt_key")
        self.assertIsNone(result)

    def test_unicode_values(self):
        """测试 Unicode 字符串的序列化/反序列化"""
        data = {"chinese": "中文测试", "emoji": "🎉", "japanese": "こんにちは"}
        self.cache.put("unicode", data)
        result = self.cache.get("unicode")
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result["chinese"], "中文测试")
            self.assertEqual(result["emoji"], "🎉")
            self.assertEqual(result["japanese"], "こんにちは")

    def test_value_column_is_text(self):
        """测试 value 列类型为 TEXT（非 BLOB，适配 JSON 序列化）"""
        self.cache._cursor.execute(
            f"PRAGMA table_info({self.cache._table_name})"
        )
        columns = {row[1]: row[2] for row in self.cache._cursor.fetchall()}
        self.assertEqual(columns.get("value"), "TEXT", "value 列应为 TEXT 类型")

    def test_get_many_with_corrupt_data(self):
        """测试批量获取时损坏数据被跳过"""
        self.cache.put("good_key", {"status": "ok"})
        # 写入损坏数据
        self.cache._cursor.execute(
            f"INSERT OR REPLACE INTO {self.cache._table_name} "
            "(key, value, timestamp, expiration) VALUES (?, ?, ?, ?)",
            ("bad_key", "not_valid_base64!!!", 0, 9999999999)
        )
        self.cache._conn.commit()
        result = self.cache.get_many(["good_key", "bad_key"])
        self.assertIn("good_key", result)
        self.assertNotIn("bad_key", result)


if __name__ == "__main__":
    unittest.main()