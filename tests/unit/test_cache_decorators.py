#!/usr/bin/env python
# coding: utf-8

"""
缓存装饰器测试

覆盖 litefs.cache_decorators 模块：MemoryCacheStore、cached、cache_response、
cache_method、cache_property 及辅助函数。
"""

import unittest
from unittest.mock import Mock

from litefs.cache_decorators import (
    MemoryCacheStore,
    cache_method,
    cache_property,
    cache_response,
    cached,
    clear_all_cache,
    get_cache_store,
    _generate_cache_key,
)


class TestMemoryCacheStore(unittest.TestCase):
    """测试内存缓存存储"""

    def test_set_get_delete(self):
        """set/get/delete 基本读写删除"""
        store = MemoryCacheStore()
        store.set("k", "v", ttl=60)
        self.assertEqual(store.get("k"), "v")
        store.delete("k")
        self.assertIsNone(store.get("k"))

    def test_ttl_expiry(self):
        """TTL 过期后返回 None"""
        store = MemoryCacheStore()
        store.set("k", "v", ttl=-1)
        self.assertIsNone(store.get("k"))

    def test_clear(self):
        """clear 清空全部条目"""
        store = MemoryCacheStore()
        store.set("a", 1, ttl=60)
        store.set("b", 2, ttl=60)
        store.clear()
        self.assertIsNone(store.get("a"))
        self.assertEqual(store.get_stats()["total_entries"], 0)

    def test_get_stats(self):
        """get_stats 返回条目数与容量上限"""
        store = MemoryCacheStore(max_size=10)
        store.set("a", 1, ttl=60)
        stats = store.get_stats()
        self.assertEqual(stats, {"total_entries": 1, "max_size": 10})

    def test_global_store_singleton(self):
        """get_cache_store 返回同一全局实例"""
        self.assertIs(get_cache_store(), get_cache_store())


class TestGenerateCacheKey(unittest.TestCase):
    """测试缓存键生成"""

    def test_key_contains_module_func_and_hash(self):
        """键由模块名、函数名与参数哈希组成"""
        def sample(a, b=1):
            return a + b

        key = _generate_cache_key(sample, (1,), {"b": 2})
        self.assertTrue(key.startswith(f"{__name__}:sample:"))

    def test_key_prefix(self):
        """键前缀插入最前"""
        def sample():
            return 1

        key = _generate_cache_key(sample, (), {}, key_prefix="pfx")
        self.assertTrue(key.startswith("pfx:"))

    def test_same_args_same_key(self):
        """相同参数生成相同键"""
        def sample(a):
            return a

        k1 = _generate_cache_key(sample, (1,), {})
        k2 = _generate_cache_key(sample, (1,), {})
        self.assertEqual(k1, k2)

    def test_unserializable_args_fallback(self):
        """不可序列化参数回退到字符串表示"""
        def sample(obj):
            return obj

        key = _generate_cache_key(sample, (object(),), {})
        self.assertTrue(key.startswith(f"{__name__}:sample:"))


class TestCached(unittest.TestCase):
    """测试 cached 装饰器"""

    def setUp(self):
        clear_all_cache()

    def tearDown(self):
        clear_all_cache()

    def test_result_cached(self):
        """第二次调用命中缓存（调用计数不变）"""
        calls = []

        @cached(ttl=60)
        def compute(x):
            calls.append(x)
            return x * 2

        self.assertEqual(compute(3), 6)
        self.assertEqual(compute(3), 6)
        self.assertEqual(calls, [3])

    def test_different_args_different_cache(self):
        """不同参数各自缓存"""
        calls = []

        @cached(ttl=60)
        def compute(x):
            calls.append(x)
            return x * 2

        compute(1)
        compute(2)
        self.assertEqual(calls, [1, 2])

    def test_skip_cache_func(self):
        """skip_cache_func 为 True 时绕过缓存"""
        calls = []

        @cached(ttl=60, skip_cache_func=lambda x: x > 10)
        def compute(x):
            calls.append(x)
            return x

        compute(20)
        compute(20)
        self.assertEqual(calls, [20, 20])

    def test_custom_cache_store(self):
        """可注入自定义缓存存储"""
        store = MemoryCacheStore()
        calls = []

        @cached(ttl=60, cache_store=store)
        def compute(x):
            calls.append(x)
            return x

        compute(1)
        compute(1)
        self.assertEqual(calls, [1])
        self.assertEqual(store.get_stats()["total_entries"], 1)

    def test_cache_clear_control(self):
        """wrapper.cache_clear 删除无参调用的缓存"""
        calls = []

        @cached(ttl=60, key_prefix="kx")
        def compute():
            calls.append("call")
            return 1

        compute()
        compute.cache_clear()
        compute()
        self.assertEqual(calls, ["call", "call"])


class TestCacheResponse(unittest.TestCase):
    """测试 cache_response 装饰器"""

    def setUp(self):
        clear_all_cache()

    def tearDown(self):
        clear_all_cache()

    def _make_handler(self, path="/api/data", method="GET", headers=None):
        environ = {"PATH_INFO": path, "REQUEST_METHOD": method}
        environ.update(headers or {})
        handler = Mock()
        handler.environ = environ
        return handler

    def test_response_cached_by_path_and_method(self):
        """按路径与方法缓存响应"""
        calls = []

        @cache_response(ttl=60)
        def view(handler):
            calls.append(handler.environ["PATH_INFO"])
            return {"data": 1}

        handler = self._make_handler()
        view(handler)
        view(handler)
        self.assertEqual(calls, ["/api/data"])

    def test_vary_on_header(self):
        """vary_on 请求头不同则缓存不同"""
        calls = []

        @cache_response(ttl=60, vary_on=["Accept-Encoding"])
        def view(handler):
            calls.append(handler.environ.get("HTTP_ACCEPT_ENCODING", ""))
            return {"data": 1}

        view(self._make_handler(headers={"HTTP_ACCEPT_ENCODING": "gzip"}))
        view(self._make_handler(headers={"HTTP_ACCEPT_ENCODING": "br"}))
        self.assertEqual(calls, ["gzip", "br"])


class TestCacheMethodAndProperty(unittest.TestCase):
    """测试 cache_method 与 cache_property 装饰器"""

    def setUp(self):
        clear_all_cache()

    def tearDown(self):
        clear_all_cache()

    def test_cache_method(self):
        """方法结果按实例缓存"""
        calls = []

        class Service:
            @cache_method(ttl=60)
            def get_value(self, key):
                calls.append(key)
                return key * 10

        svc = Service()
        self.assertEqual(svc.get_value(2), 20)
        self.assertEqual(svc.get_value(2), 20)
        self.assertEqual(calls, [2])

    def test_cache_method_per_instance(self):
        """不同实例缓存相互独立"""
        calls = []

        class Service:
            @cache_method(ttl=60)
            def get_value(self, key):
                calls.append(key)
                return key

        svc1, svc2 = Service(), Service()  # 保持引用避免 id 复用
        svc1.get_value(1)
        svc2.get_value(1)
        self.assertEqual(calls, [1, 1])

    def test_cache_property(self):
        """属性计算结果被缓存"""
        calls = []

        class Config:
            @cache_property(ttl=60)
            def value(self):
                calls.append("computed")
                return 42

        cfg = Config()
        self.assertEqual(cfg.value, 42)
        self.assertEqual(cfg.value, 42)
        self.assertEqual(calls, ["computed"])


if __name__ == "__main__":
    unittest.main()
