#!/usr/bin/env python
# coding: utf-8

"""
Session 工厂与管理器测试

覆盖 litefs.session.factory 与 litefs.session.manager 模块。
"""

import unittest
from unittest.mock import Mock

from litefs.session.factory import SessionBackend, SessionFactory
from litefs.session.manager import SessionManager, get_global_session_cache
from litefs.session.session import MemorySessionStore
from litefs.session.db import DatabaseSession


class TestSessionBackend(unittest.TestCase):
    """测试后端类型常量"""

    def test_constants(self):
        """后端常量定义"""
        self.assertEqual(SessionBackend.MEMORY, "memory")
        self.assertEqual(SessionBackend.DATABASE, "database")
        self.assertEqual(SessionBackend.REDIS, "redis")
        self.assertEqual(SessionBackend.MEMCACHE, "memcache")


class TestSessionFactory(unittest.TestCase):
    """测试 Session 工厂"""

    def test_create_memory_default(self):
        """默认创建内存存储"""
        store = SessionFactory.create_session()
        self.assertIsInstance(store, MemorySessionStore)

    def test_create_memory_with_max_size(self):
        """内存存储支持 max_size 参数"""
        store = SessionFactory.create_session("memory", max_size=10)
        self.assertEqual(store._max_size, 10)

    def test_create_database(self):
        """创建数据库存储（内存库）"""
        store = SessionFactory.create_session(
            "database", db_path=":memory:", table_name="t"
        )
        self.assertIsInstance(store, DatabaseSession)

    def test_backend_case_insensitive(self):
        """后端名称大小写不敏感"""
        store = SessionFactory.create_session("MEMORY")
        self.assertIsInstance(store, MemorySessionStore)

    def test_unknown_backend_raises(self):
        """未知后端抛 ValueError"""
        with self.assertRaises(ValueError) as ctx:
            SessionFactory.create_session("unknown")
        self.assertIn("不支持的 Session 后端", str(ctx.exception))

    def test_create_redis_with_client(self):
        """redis 后端接受外部客户端实例，不发起真实连接"""
        from litefs.session.redis import RedisSession
        store = SessionFactory.create_session(
            "redis", redis_client=Mock(), key_prefix="p:"
        )
        self.assertIsInstance(store, RedisSession)
        self.assertEqual(store._key_prefix, "p:")

    def test_create_memcache_with_client(self):
        """memcache 后端接受外部客户端实例"""
        from litefs.session.memcache import MemcacheSession
        store = SessionFactory.create_session(
            "memcache", memcache_client=Mock(), key_prefix="p:"
        )
        self.assertIsInstance(store, MemcacheSession)
        self.assertEqual(store._key_prefix, "p:")


class _Config:
    """模拟配置对象"""

    def __init__(self, backend, **attrs):
        self.session_backend = backend
        for k, v in attrs.items():
            setattr(self, k, v)


class TestCreateFromConfig(unittest.TestCase):
    """测试从配置创建 Session"""

    def test_memory_config(self):
        """memory 配置读取 max_size"""
        store = SessionFactory.create_from_config(
            _Config("memory", session_max_size=7)
        )
        self.assertIsInstance(store, MemorySessionStore)
        self.assertEqual(store._max_size, 7)

    def test_database_config(self):
        """database 配置读取路径与表名"""
        store = SessionFactory.create_from_config(
            _Config("database", database_path=":memory:",
                    database_session_table="st")
        )
        self.assertIsInstance(store, DatabaseSession)

    def test_redis_config(self):
        """redis 配置参数被正确提取并传给 RedisSession"""
        from unittest.mock import patch
        config = _Config(
            "redis", redis_host="rh", redis_port=1234, redis_db=3,
            redis_password="pw", redis_session_key_prefix="rp:",
            session_expiration_time=7200,
        )
        with patch("litefs.session.factory.RedisSession") as redis_cls:
            SessionFactory.create_from_config(config)
        redis_cls.assert_called_once_with(
            redis_client=None, host="rh", port=1234, db=3,
            password="pw", key_prefix="rp:", expiration_time=7200,
        )

    def test_missing_backend_defaults_memory(self):
        """配置缺失时默认 memory 后端"""

        class Empty:
            pass

        store = SessionFactory.create_from_config(Empty())
        self.assertIsInstance(store, MemorySessionStore)


class TestSessionManager(unittest.TestCase):
    """测试全局 Session 管理器"""

    def setUp(self):
        SessionManager.reset_session_cache()

    def tearDown(self):
        SessionManager.reset_session_cache()

    def test_singleton(self):
        """SessionManager 为单例"""
        self.assertIs(SessionManager(), SessionManager())

    def test_get_session_cache_singleton_per_key(self):
        """同一 cache_key 返回同一实例"""
        s1 = SessionManager.get_session_cache("memory")
        s2 = SessionManager.get_session_cache("memory")
        self.assertIs(s1, s2)
        self.assertTrue(SessionManager.has_session_cache("default"))

    def test_separate_keys_separate_instances(self):
        """不同 cache_key 返回不同实例"""
        a = SessionManager.get_session_cache("memory", cache_key="a")
        b = SessionManager.get_session_cache("memory", cache_key="b")
        self.assertIsNot(a, b)
        self.assertEqual(
            set(SessionManager.list_session_caches()), {"a", "b"}
        )

    def test_reset_single_key(self):
        """按 key 重置单个缓存实例"""
        SessionManager.get_session_cache("memory", cache_key="keep")
        SessionManager.get_session_cache("memory", cache_key="drop")
        SessionManager.reset_session_cache(cache_key="drop")
        self.assertTrue(SessionManager.has_session_cache("keep"))
        self.assertFalse(SessionManager.has_session_cache("drop"))

    def test_get_with_backend_kwargs(self):
        """get_session_cache 透传后端参数"""
        store = SessionManager.get_session_cache(
            "memory", cache_key="m", max_size=42
        )
        self.assertEqual(store._max_size, 42)

    def test_convenience_function(self):
        """便捷函数复用管理器单例"""
        s1 = get_global_session_cache("memory")
        s2 = SessionManager.get_session_cache("memory")
        self.assertIs(s1, s2)


if __name__ == "__main__":
    unittest.main()
