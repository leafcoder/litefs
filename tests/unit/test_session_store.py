#!/usr/bin/env python
# coding: utf-8

"""
Session 存储测试

覆盖 litefs.session.session 与 litefs.session.cache_session 模块：
Session 对象、MemorySessionStore、CachedSessionStore。
"""

import unittest
from unittest.mock import MagicMock, Mock

from litefs.session.session import MemorySessionStore, Session
from litefs.session.cache_session import CachedSessionStore


class TestSession(unittest.TestCase):
    """测试 Session 数据对象"""

    def test_auto_generated_id(self):
        """未指定 ID 时自动生成 UUID"""
        session = Session()
        self.assertTrue(session.id)
        self.assertEqual(len(session.id), 36)

    def test_custom_id_and_data(self):
        """可指定 ID，data 为空字典"""
        session = Session(session_id="fixed")
        self.assertEqual(session.id, "fixed")
        self.assertEqual(session.data, {})

    def test_data_dict_behavior(self):
        """Session 继承 UserDict，可按字典操作"""
        session = Session()
        session["user"] = "alice"
        self.assertEqual(session["user"], "alice")
        self.assertEqual(dict(session), {"user": "alice"})

    def test_str(self):
        """str 输出包含 ID"""
        self.assertEqual(str(Session(session_id="s1")), "<Session Id=s1>")

    def test_save_without_store(self):
        """无 store 时 save 返回 False"""
        self.assertFalse(Session().save())

    def test_save_with_store(self):
        """有 store 时 save 写入并返回 True"""
        store = Mock()
        session = Session(session_id="s1", store=store)
        self.assertTrue(session.save())
        store.put.assert_called_once_with("s1", session)


class TestMemorySessionStore(unittest.TestCase):
    """测试内存 Session 存储"""

    def setUp(self):
        self.store = MemorySessionStore()

    def test_put_get(self):
        """put/get 存取 Session"""
        session = Session(session_id="a")
        session["k"] = "v"
        self.store.put("a", session)
        self.assertIs(self.store.get("a"), session)

    def test_get_missing_returns_none(self):
        """获取不存在的 Session 返回 None"""
        self.assertIsNone(self.store.get("ghost"))

    def test_delete_and_exists(self):
        """delete 移除 Session，exists 检查存在性"""
        self.store.put("a", Session())
        self.assertTrue(self.store.exists("a"))
        self.store.delete("a")
        self.assertFalse(self.store.exists("a"))
        # 删除不存在的 ID 不抛异常
        self.store.delete("ghost")

    def test_clear_and_len(self):
        """clear 清空，__len__ 统计数量"""
        self.store.put("a", Session())
        self.store.put("b", Session())
        self.assertEqual(len(self.store), 2)
        self.store.clear()
        self.assertEqual(len(self.store), 0)

    def test_expire_unsupported(self):
        """内存存储不支持过期，expire 恒为 False"""
        self.store.put("a", Session())
        self.assertFalse(self.store.expire("a", 60))

    def test_ttl_semantics(self):
        """ttl：不存在返回 -2，存在但不支持过期返回 -1"""
        self.assertEqual(self.store.ttl("ghost"), -2)
        self.store.put("a", Session())
        self.assertEqual(self.store.ttl("a"), -1)

    def test_eviction_on_max_size(self):
        """达到 max_size 后按 LRU 淘汰最早的 Session"""
        store = MemorySessionStore(max_size=2)
        store.put("first", Session())
        store.put("second", Session())
        store.put("third", Session())
        self.assertIsNone(store.get("first"))
        self.assertIsNotNone(store.get("second"))
        self.assertIsNotNone(store.get("third"))
        self.assertEqual(len(store), 2)

    def test_create_and_save(self):
        """create 创建绑定 store 的 Session，save 写回"""
        session = self.store.create()
        session["x"] = 1
        self.assertIs(session.store, self.store)
        self.store.save(session)
        self.assertIs(self.store.get(session.id), session)


class TestCachedSessionStore(unittest.TestCase):
    """测试带缓存的 Session 存储"""

    def setUp(self):
        self.base = MagicMock()
        self.cache = Mock()
        self.cached = CachedSessionStore(self.base, self.cache)

    def test_put_writes_both_layers(self):
        """put 同时写底层与缓存"""
        session = Session(session_id="a")
        self.cached.put("a", session)
        self.base.put.assert_called_once_with("a", session)
        self.cache.put.assert_called_once_with("session:a", session)

    def test_get_cache_hit(self):
        """缓存命中时不查底层"""
        self.cache.get.return_value = "cached-session"
        self.assertEqual(self.cached.get("a"), "cached-session")
        self.base.get.assert_not_called()

    def test_get_cache_miss_fills_cache(self):
        """缓存未命中时查底层并回填缓存"""
        self.cache.get.return_value = None
        self.base.get.return_value = "base-session"
        self.assertEqual(self.cached.get("a"), "base-session")
        self.cache.put.assert_called_once_with("session:a", "base-session")

    def test_get_missing_everywhere(self):
        """两层都不存在返回 None 且不回填"""
        self.cache.get.return_value = None
        self.base.get.return_value = None
        self.assertIsNone(self.cached.get("ghost"))
        self.cache.put.assert_not_called()

    def test_delete_both_layers(self):
        """delete 同时清理两层"""
        self.cached.delete("a")
        self.base.delete.assert_called_once_with("a")
        self.cache.delete.assert_called_once_with("session:a")

    def test_delegation(self):
        """exists/expire/ttl/clear/len/create 委托底层"""
        self.base.exists.return_value = True
        self.assertTrue(self.cached.exists("a"))
        self.base.expire.return_value = True
        self.assertTrue(self.cached.expire("a", 60))
        self.base.ttl.return_value = 30
        self.assertEqual(self.cached.ttl("a"), 30)
        self.cached.clear()
        self.base.clear.assert_called_once()
        self.base.__len__.return_value = 5
        self.assertEqual(len(self.cached), 5)
        self.base.create.return_value = "new-session"
        self.assertEqual(self.cached.create(), "new-session")

    def test_custom_cache_key_prefix(self):
        """可自定义缓存键前缀"""
        cached = CachedSessionStore(self.base, self.cache, cache_key_prefix="p:")
        cached.put("k", "v")
        self.cache.put.assert_called_once_with("p:k", "v")

    def test_save_uses_put(self):
        """save 复用 put 逻辑"""
        session = Session(session_id="z")
        self.cached.save(session)
        self.base.put.assert_called_once_with("z", session)


if __name__ == "__main__":
    unittest.main()
