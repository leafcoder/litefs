#!/usr/bin/env python
# coding: utf-8

"""
请求上下文管理测试

覆盖 litefs.context 模块：RequestContextData、RequestContext、G 对象及上下文装饰器。
"""

import threading
import unittest
from unittest.mock import Mock

from litefs.context import (
    G,
    RequestContext,
    RequestContextData,
    RequestContextManager,
    has_request_context,
    get_current_request,
    g,
    with_request_context,
)


class TestRequestContextData(unittest.TestCase):
    """测试请求数据容器"""

    def setUp(self):
        self.request = Mock()
        self.data = RequestContextData(self.request)

    def test_set_and_get(self):
        """set/get 存取数据"""
        self.data.set("user", "alice")
        self.assertEqual(self.data.get("user"), "alice")
        self.assertEqual(self.data.get("missing", "dft"), "dft")

    def test_delete(self):
        """delete 删除已有键，不存在时静默"""
        self.data.set("key", 1)
        self.data.delete("key")
        self.assertNotIn("key", self.data)
        self.data.delete("not-exist")  # 不抛异常

    def test_clear_keys_values_items(self):
        """clear/keys/values/items 行为与 dict 一致"""
        self.data.set("a", 1)
        self.data.set("b", 2)
        self.assertEqual(sorted(self.data.keys()), ["a", "b"])
        self.assertEqual(sorted(self.data.values()), [1, 2])
        self.assertEqual(dict(self.data.items()), {"a": 1, "b": 2})
        self.data.clear()
        self.assertEqual(list(self.data.keys()), [])

    def test_item_protocol(self):
        """支持 [] 读写删除与 in 检查"""
        self.data["x"] = 10
        self.assertIn("x", self.data)
        self.assertEqual(self.data["x"], 10)
        del self.data["x"]
        self.assertNotIn("x", self.data)

    def test_repr_and_created_at(self):
        """__repr__ 包含数据内容，记录创建时间"""
        self.data.set("k", "v")
        self.assertIn("k", repr(self.data))
        self.assertIsNotNone(self.data.created_at)

    def test_request_attached(self):
        """request 对象被保存在容器上"""
        self.assertIs(self.data.request, self.request)


class TestRequestContext(unittest.TestCase):
    """测试请求上下文管理器"""

    def tearDown(self):
        RequestContext.pop()

    def test_push_and_pop(self):
        """push 建立上下文，pop 移除上下文"""
        request = Mock()
        ctx = RequestContext.push(request)
        self.assertTrue(RequestContext.has_context())
        self.assertIs(RequestContext.get_current(), ctx)
        self.assertIs(RequestContext.get_current().request, request)
        RequestContext.pop()
        self.assertFalse(RequestContext.has_context())
        self.assertIsNone(RequestContext.get_current())

    def test_pop_without_context_safe(self):
        """无上下文时 pop 不抛异常"""
        RequestContext.pop()
        self.assertFalse(RequestContext.has_context())

    def test_thread_isolation(self):
        """上下文按线程隔离，线程间互不可见"""
        results = {}

        def worker():
            results["has_context"] = RequestContext.has_context()
            RequestContext.push("worker-request")
            results["request"] = RequestContext.get_current().request
            RequestContext.pop()

        RequestContext.push("main-request")
        t = threading.Thread(target=worker)
        t.start()
        t.join()

        self.assertFalse(results["has_context"])
        self.assertEqual(results["request"], "worker-request")
        self.assertEqual(RequestContext.get_current().request, "main-request")
        RequestContext.pop()


class TestGObject(unittest.TestCase):
    """测试 g 全局上下文对象"""

    def setUp(self):
        RequestContext.push(Mock())

    def tearDown(self):
        RequestContext.pop()

    def test_setattr_getattr(self):
        """属性读写委托给当前上下文"""
        g.user = "alice"
        self.assertEqual(g.user, "alice")
        self.assertEqual(g.get("user"), "alice")

    def test_getattr_missing_returns_none(self):
        """访问未设置的属性返回 None"""
        self.assertIsNone(g.missing_key)

    def test_access_outside_context_raises(self):
        """无上下文时访问属性抛 AttributeError"""
        RequestContext.pop()
        with self.assertRaises(AttributeError) as ctx:
            g.user
        self.assertIn("outside of request context", str(ctx.exception))
        with self.assertRaises(AttributeError):
            g.user = 1
        with self.assertRaises(AttributeError):
            del g.user

    def test_underscore_attribute_bypasses_context(self):
        """下划线属性走普通对象属性，不进入上下文"""
        g._private = 42
        self.assertEqual(g._private, 42)
        self.assertNotIn("_private", RequestContext.get_current())

    def test_delattr_removes_from_context(self):
        """del 属性从上下文中删除"""
        g.token = "abc"
        self.assertIn("token", g)
        del g.token
        self.assertNotIn("token", g)

    def test_contains_outside_context_false(self):
        """无上下文时 in 检查返回 False"""
        RequestContext.pop()
        self.assertNotIn("anything", g)

    def test_get_with_default_outside_context(self):
        """无上下文时 get 返回默认值"""
        RequestContext.pop()
        self.assertEqual(g.get("k", "dft"), "dft")

    def test_pop_value(self):
        """pop 取值并从上下文删除"""
        g.counter = 5
        self.assertEqual(g.pop("counter"), 5)
        self.assertNotIn("counter", g)
        self.assertEqual(g.pop("counter", 0), 0)

    def test_clear(self):
        """clear 清空当前上下文数据"""
        g.a = 1
        g.b = 2
        g.clear()
        self.assertEqual(repr(g), "<g {}>")

    def test_repr(self):
        """repr 反映上下文状态"""
        self.assertEqual(repr(g), "<g {}>")
        g.name = "x"
        self.assertIn("name", repr(g))
        RequestContext.pop()
        self.assertEqual(repr(g), "<g (no context)>")

    def test_global_instance(self):
        """模块级 g 是 G 的实例"""
        self.assertIsInstance(g, G)


class TestContextHelpers(unittest.TestCase):
    """测试上下文辅助函数与装饰器"""

    def tearDown(self):
        RequestContext.pop()

    def test_has_request_context(self):
        """has_request_context 反映上下文状态"""
        self.assertFalse(has_request_context())
        RequestContext.push(Mock())
        self.assertTrue(has_request_context())

    def test_get_current_request(self):
        """get_current_request 返回当前请求对象"""
        self.assertIsNone(get_current_request())
        request = Mock()
        RequestContext.push(request)
        self.assertIs(get_current_request(), request)

    def test_request_context_manager(self):
        """RequestContextManager 进入/退出自动管理上下文"""
        request = Mock()
        with RequestContextManager(request) as ctx:
            self.assertTrue(has_request_context())
            self.assertIs(ctx.request, request)
        self.assertFalse(has_request_context())

    def test_with_request_context_creates_mock_context(self):
        """装饰器在无上下文时创建 Mock 上下文执行"""
        @with_request_context
        def view():
            return has_request_context()

        self.assertFalse(has_request_context())
        self.assertTrue(view())
        self.assertFalse(has_request_context())

    def test_with_request_context_reuses_existing(self):
        """已有上下文时装饰器复用，不覆盖"""
        request = Mock()
        request.mark = "existing"

        @with_request_context
        def view():
            return RequestContext.get_current().request

        RequestContext.push(request)
        self.assertIs(view(), request)
        self.assertIs(RequestContext.get_current().request, request)


if __name__ == "__main__":
    unittest.main()
