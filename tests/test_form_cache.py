#!/usr/bin/env python
# coding: utf-8

"""
表单缓存测试
"""

import unittest
import time


class TestFormCache(unittest.TestCase):
    """测试表单缓存"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.cache import FormCache
        
        self.cache = FormCache(max_size=100, default_ttl=60)
    
    def test_set_and_get(self):
        """测试设置和获取"""
        key = "test_key"
        value = {"name": "test", "value": 123}
        
        self.cache.set(key, value)
        result = self.cache.get(key)
        
        self.assertEqual(result, value)
    
    def test_get_nonexistent(self):
        """测试获取不存在的键"""
        result = self.cache.get("nonexistent_key")
        self.assertIsNone(result)
    
    def test_expiration(self):
        """测试过期"""
        key = "test_key"
        value = {"name": "test"}
        
        self.cache.set(key, value, ttl=1)
        time.sleep(1.1)
        
        result = self.cache.get(key)
        self.assertIsNone(result)
    
    def test_max_size(self):
        """测试最大容量"""
        for i in range(110):
            self.cache.set(f"key_{i}", {"index": i})
        
        # 应该只保留最近的 100 个
        self.assertEqual(len(self.cache), 100)
        
        # 最早的键应该被移除
        result = self.cache.get("key_0")
        self.assertIsNone(result)
        
        # 最近的键应该存在
        result = self.cache.get("key_109")
        self.assertIsNotNone(result)
    
    def test_delete(self):
        """测试删除"""
        key = "test_key"
        value = {"name": "test"}
        
        self.cache.set(key, value)
        result = self.cache.delete(key)
        
        self.assertTrue(result)
        self.assertIsNone(self.cache.get(key))
    
    def test_delete_nonexistent(self):
        """测试删除不存在的键"""
        result = self.cache.delete("nonexistent_key")
        self.assertFalse(result)
    
    def test_clear(self):
        """测试清空"""
        for i in range(10):
            self.cache.set(f"key_{i}", {"index": i})
        
        self.cache.clear()
        
        self.assertEqual(len(self.cache), 0)
        
        for i in range(10):
            result = self.cache.get(f"key_{i}")
            self.assertIsNone(result)
    
    def test_contains(self):
        """测试包含"""
        key = "test_key"
        value = {"name": "test"}
        
        self.cache.set(key, value)
        
        self.assertIn(key, self.cache)
        self.assertNotIn("nonexistent_key", self.cache)
    
    def test_len(self):
        """测试长度"""
        for i in range(10):
            self.cache.set(f"key_{i}", {"index": i})
        
        self.assertEqual(len(self.cache), 10)
    
    def test_cleanup_expired(self):
        """测试清理过期项"""
        for i in range(5):
            self.cache.set(f"key_{i}", {"index": i}, ttl=1)
        
        time.sleep(1.1)
        
        cleaned = self.cache.cleanup_expired()
        
        self.assertEqual(cleaned, 5)
        self.assertEqual(len(self.cache), 0)
    
    def test_stats(self):
        """测试统计信息"""
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["max_size"], 100)
        self.assertEqual(stats["default_ttl"], 60)
        self.assertEqual(stats["size"], 0)
        
        self.cache.set("test_key", {"name": "test"})
        stats = self.cache.get_stats()
        
        self.assertEqual(stats["size"], 1)


class TestParseFormWithCache(unittest.TestCase):
    """测试带缓存的表单解析"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.handlers.request import parse_form
        
        self.parse_form = parse_form
    
    def test_basic_parsing(self):
        """测试基本解析"""
        query_string = "name=test&value=123"
        result = self.parse_form(query_string)
        
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["value"], "123")
    
    def test_array_parsing(self):
        """测试数组解析"""
        query_string = "items[]=a&items[]=b&items[]=c"
        result = self.parse_form(query_string)
        
        self.assertEqual(result["items"], ["a", "b", "c"])
    
    def test_dict_parsing(self):
        """测试字典解析"""
        query_string = "user[name]=John&user[age]=30"
        result = self.parse_form(query_string)
        
        self.assertEqual(result["user"]["name"], "John")
        self.assertEqual(result["user"]["age"], "30")
    
    def test_empty_value(self):
        """测试空值"""
        query_string = "key="
        result = self.parse_form(query_string)
        
        self.assertEqual(result["key"], "")
    
    def test_special_characters(self):
        """测试特殊字符"""
        query_string = "name=hello%20world&msg=hello+world"
        result = self.parse_form(query_string)
        
        self.assertEqual(result["name"], "hello world")
        self.assertEqual(result["msg"], "hello world")  # unquote_plus 会将 + 解码为空格
    
    def test_cached_parsing(self):
        """测试缓存解析"""
        query_string = "name=test&value=123"
        
        # 第一次解析
        result1 = self.parse_form(query_string)
        
        # 第二次解析应该从缓存获取
        result2 = self.parse_form(query_string)
        
        self.assertEqual(result1, result2)
    
    def test_different_query_strings(self):
        """测试不同的查询字符串"""
        query_string1 = "name=test&value=123"
        query_string2 = "name=test&value=456"
        
        result1 = self.parse_form(query_string1)
        result2 = self.parse_form(query_string2)
        
        self.assertNotEqual(result1, result2)
        self.assertEqual(result1["value"], "123")
        self.assertEqual(result2["value"], "456")
    
    def test_bytes_input(self):
        """测试字节输入"""
        query_string = b"name=test&value=123"
        result = self.parse_form(query_string)
        
        self.assertEqual(result["name"], "test")
        self.assertEqual(result["value"], "123")


if __name__ == '__main__':
    unittest.main()
