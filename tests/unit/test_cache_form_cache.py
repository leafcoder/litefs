#!/usr/bin/env python
# coding: utf-8

"""
表单数据缓存测试

覆盖 FormCache 的 LRU 淘汰、TTL 过期、删除清理与统计信息。
"""

import unittest

from litefs.cache.form_cache import FormCache


class TestFormCache(unittest.TestCase):
    """FormCache 基本行为"""

    def test_set_and_get(self):
        """写入后可读取"""
        cache = FormCache()
        cache.set('a', {'x': 1})
        self.assertEqual(cache.get('a'), {'x': 1})

    def test_get_missing_returns_none(self):
        """获取不存在的键返回 None"""
        self.assertIsNone(FormCache().get('missing'))

    def test_expired_entry_removed(self):
        """过期条目读取时移除并返回 None"""
        cache = FormCache()
        cache.set('a', {'x': 1}, ttl=-1)
        self.assertIsNone(cache.get('a'))
        self.assertNotIn('a', cache)

    def test_set_existing_key_replaces(self):
        """重复写入覆盖旧值"""
        cache = FormCache()
        cache.set('a', {'old': 1})
        cache.set('a', {'new': 2})
        self.assertEqual(cache.get('a'), {'new': 2})
        self.assertEqual(len(cache), 1)

    def test_lru_eviction(self):
        """容量满时淘汰最久未使用的条目"""
        cache = FormCache(max_size=2)
        cache.set('a', 1)
        cache.set('b', 2)
        cache.get('a')  # 访问 a，使 b 成为最久未使用
        cache.set('c', 3)
        self.assertIn('a', cache)
        self.assertNotIn('b', cache)
        self.assertIn('c', cache)

    def test_delete(self):
        """delete 删除存在的键并返回 True"""
        cache = FormCache()
        cache.set('a', 1)
        self.assertTrue(cache.delete('a'))
        self.assertFalse(cache.delete('a'))

    def test_clear(self):
        """clear 清空全部数据"""
        cache = FormCache()
        cache.set('a', 1)
        cache.set('b', 2)
        cache.clear()
        self.assertEqual(len(cache), 0)
        self.assertIsNone(cache.get('a'))

    def test_cleanup_expired(self):
        """cleanup_expired 只清理过期条目并返回数量"""
        cache = FormCache()
        cache.set('expired-1', 1, ttl=-1)
        cache.set('expired-2', 2, ttl=-1)
        cache.set('alive', 3, ttl=300)
        removed = cache.cleanup_expired()
        self.assertEqual(removed, 2)
        self.assertIn('alive', cache)
        self.assertNotIn('expired-1', cache)

    def test_contains(self):
        """in 运算符检查键存在性"""
        cache = FormCache()
        cache.set('a', 1)
        self.assertIn('a', cache)
        self.assertNotIn('b', cache)

    def test_get_stats(self):
        """get_stats 返回容量与配置信息"""
        cache = FormCache(max_size=50, default_ttl=120)
        cache.set('a', 1)
        stats = cache.get_stats()
        self.assertEqual(stats, {'size': 1, 'max_size': 50, 'default_ttl': 120})


if __name__ == '__main__':
    unittest.main()
