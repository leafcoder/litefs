#!/usr/bin/env python
# coding: utf-8

"""
TreeCache 与 MemoryCache 缺失分支测试

覆盖 TreeCache 的 delete/exists/clear/close/auto_clean，
以及 MemoryCache 的 expire/ttl/过期清理与容量淘汰联动。
"""

import time
import unittest

from litefs.cache.cache import MemoryCache, TreeCache


class TestTreeCacheBranches(unittest.TestCase):
    """TreeCache 补充分支"""

    def setUp(self):
        self.cache = TreeCache(clean_period=3600, expiration_time=3600)

    def tearDown(self):
        self.cache.close()

    def test_put_overwrite_updates_timestamp(self):
        """重复写入同一键更新时间戳而非插入"""
        self.cache.put('k', 'v1')
        self.cache.put('k', 'v2')
        self.assertEqual(self.cache.get('k'), 'v2')
        self.assertEqual(len(self.cache), 1)

    def test_delete_with_child_keys(self):
        """delete 同时清理子键（key/% 前缀匹配）"""
        self.cache.put('parent', 1)
        self.cache.put('parent/child', 2)
        self.cache.delete('parent')
        self.assertIsNone(self.cache.get('parent'))
        self.assertIsNone(self.cache.get('parent/child'))

    def test_delete_missing_key(self):
        """删除不存在的键不崩溃"""
        self.cache.delete('missing')
        self.assertEqual(len(self.cache), 0)

    def test_exists(self):
        """exists 检查键存在性"""
        self.cache.put('k', 1)
        self.assertTrue(self.cache.exists('k'))
        self.assertFalse(self.cache.exists('missing'))

    def test_expired_entry_on_get(self):
        """过期条目读取时移除"""
        self.cache.put('k', 1, expiration=-1)
        self.assertIsNone(self.cache.get('k'))
        self.assertNotIn('k', self.cache.data)

    def test_auto_clean_removes_expired(self):
        """auto_clean 批量清理过期条目"""
        cache = TreeCache(clean_period=0, expiration_time=3600)
        self.addCleanup(cache.close)
        cache.put('old', 1, expiration=-1)
        self.cache.put('fresh', 2, expiration=3600)
        self.cache.auto_clean()
        self.assertNotIn('old', self.cache.data)
        self.assertIn('fresh', self.cache.data)

    def test_auto_clean_within_period_noop(self):
        """清理周期内 auto_clean 直接返回"""
        self.cache.put('k', 1)
        self.cache.auto_clean()  # 刚清理过，未到周期
        self.assertIn('k', self.cache.data)

    def test_clear(self):
        """clear 清空内存与 SQLite 记录"""
        self.cache.put('k', 1)
        self.cache.clear()
        self.assertEqual(len(self.cache), 0)
        rows = self.cache.conn.execute('SELECT COUNT(*) FROM cache').fetchone()
        self.assertEqual(rows[0], 0)

    def test_close(self):
        """close 关闭连接，重复关闭不崩溃"""
        self.cache.close()
        self.cache.close()


class TestMemoryCacheBranches(unittest.TestCase):
    """MemoryCache 补充分支"""

    def setUp(self):
        self.cache = MemoryCache()

    def test_str_and_len(self):
        """str 输出内部字典，len 返回条目数"""
        self.cache.put('a', 1)
        self.assertIn("'a'", str(self.cache))
        self.assertEqual(len(self.cache), 1)

    def test_expire_existing_key(self):
        """expire 为存在的键设置过期时间"""
        self.cache.put('a', 1)
        self.assertTrue(self.cache.expire('a', 60))
        self.assertGreater(self.cache.ttl('a'), 0)

    def test_expire_missing_key(self):
        """expire 对不存在的键返回 False"""
        self.assertFalse(self.cache.expire('missing', 60))

    def test_ttl_semantics(self):
        """ttl：无过期时间 -1，键不存在 -2，过期后 -2"""
        self.cache.put('plain', 1)
        self.assertEqual(self.cache.ttl('plain'), -1)
        self.assertEqual(self.cache.ttl('missing'), -2)
        self.cache.put('temp', 1, expiration=-1)
        self.assertEqual(self.cache.ttl('temp'), -2)

    def test_ttl_never_negative(self):
        """已到期的键 ttl 钳制为 0"""
        self.cache.put('a', 1, expiration=1)
        # 未过期但剩余不足 1 秒，int() 截断为 0
        self.cache._expiry['a'] = time.time() + 0.5
        self.assertEqual(self.cache.ttl('a'), 0)

    def test_cleanup_before_eviction(self):
        """容量满时先清理过期条目再考虑 LRU 淘汰"""
        cache = MemoryCache(max_size=2)
        cache.put('expired', 1, expiration=-1)
        cache.put('keep', 2)
        cache.put('new', 3)
        self.assertNotIn('expired', cache._cache)
        self.assertIn('keep', cache._cache)
        self.assertIn('new', cache._cache)

    def test_put_without_expiration_removes_ttl(self):
        """无过期时间写入清除旧的过期标记"""
        self.cache.put('a', 1, expiration=60)
        self.cache.put('a', 2)
        self.assertEqual(self.cache.ttl('a'), -1)

    def test_close_noop(self):
        """close 为空操作"""
        self.assertIsNone(self.cache.close())


if __name__ == '__main__':
    unittest.main()
