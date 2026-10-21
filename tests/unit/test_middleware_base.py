#!/usr/bin/env python
# coding: utf-8

"""
中间件基类与管理器测试

覆盖 Middleware 同步/异步默认回退、_has_async_override 检测，
以及 MiddlewareManager 的注册与同步/异步执行路径。
"""

import asyncio
import unittest
from unittest.mock import Mock

from litefs.middleware.base import Middleware, MiddlewareManager


class AsyncRequestMiddleware(Middleware):
    """仅覆盖异步请求处理的中间件"""

    async def async_process_request(self, request_handler):
        return 'async-request-response'


class AsyncResponseMiddleware(Middleware):
    """仅覆盖异步响应处理的中间件"""

    async def async_process_response(self, request_handler, response):
        return response + '-async'


class AsyncExceptionMiddleware(Middleware):
    """仅覆盖异步异常处理的中间件"""

    async def async_process_exception(self, request_handler, exception):
        return 'async-exception-response'


class TestMiddlewareDefaults(unittest.TestCase):
    """Middleware 默认行为"""

    def test_init_stores_app(self):
        """构造时保存 app 引用"""
        app = Mock()
        self.assertIs(Middleware(app).app, app)

    def test_default_process_request_returns_none(self):
        """默认请求处理返回 None"""
        self.assertIsNone(Middleware(Mock()).process_request(Mock()))

    def test_default_process_response_passthrough(self):
        """默认响应处理原样返回"""
        response = {'ok': True}
        self.assertIs(Middleware(Mock()).process_response(Mock(), response), response)

    def test_default_process_exception_returns_none(self):
        """默认异常处理返回 None"""
        self.assertIsNone(Middleware(Mock()).process_exception(Mock(), ValueError()))

    def test_async_defaults_fall_back_to_sync(self):
        """异步默认实现回退到同步方法"""
        middleware = Middleware(Mock())
        handler = Mock()
        response = {'data': 1}

        self.assertIsNone(asyncio.run(middleware.async_process_request(handler)))
        self.assertIs(asyncio.run(middleware.async_process_response(handler, response)), response)
        self.assertIsNone(asyncio.run(middleware.async_process_exception(handler, ValueError())))

    def test_has_async_override_base_class(self):
        """基类自身不算覆盖"""
        self.assertFalse(Middleware(Mock())._has_async_override('async_process_request'))
        self.assertFalse(Middleware(Mock())._has_async_override('async_process_response'))
        self.assertFalse(Middleware(Mock())._has_async_override('async_process_exception'))

    def test_has_async_override_subclass(self):
        """子类覆盖异步方法时检测为 True"""
        self.assertTrue(AsyncRequestMiddleware(Mock())._has_async_override('async_process_request'))
        self.assertTrue(
            AsyncResponseMiddleware(Mock())._has_async_override('async_process_response')
        )
        self.assertTrue(
            AsyncExceptionMiddleware(Mock())._has_async_override('async_process_exception')
        )
        # 未覆盖的方法仍为 False
        async_request = AsyncRequestMiddleware(Mock())
        self.assertFalse(async_request._has_async_override('async_process_response'))


class TestMiddlewareManagerRegistry(unittest.TestCase):
    """MiddlewareManager 注册管理"""

    def test_add_returns_self_for_chaining(self):
        """add 支持链式调用"""
        manager = MiddlewareManager()
        self.assertIs(manager.add(Middleware), manager)

    def test_remove(self):
        """remove 移除指定中间件类"""
        manager = MiddlewareManager()
        manager.add(Middleware).add(AsyncRequestMiddleware)
        manager.remove(Middleware)
        remaining = [cls for cls, _ in manager._middlewares]
        self.assertEqual(remaining, [AsyncRequestMiddleware])

    def test_clear(self):
        """clear 清空所有中间件"""
        manager = MiddlewareManager()
        manager.add(Middleware).add(Middleware)
        manager.clear()
        self.assertEqual(manager._middlewares, [])

    def test_get_middleware_instances_with_kwargs(self):
        """get_middleware_instances 用 kwargs 构造实例"""
        class Configurable(Middleware):
            def __init__(self, app, **kwargs):
                super().__init__(app)
                self.kwargs = kwargs

        manager = MiddlewareManager()
        manager.add(Configurable, token_name='X-Auth')
        instances = manager.get_middleware_instances('app')
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].kwargs, {'token_name': 'X-Auth'})


def make_handler(middlewares):
    """构造带 _middlewares 列表的请求处理器 Mock"""
    handler = Mock(spec=[])
    handler._middlewares = middlewares
    return handler


class TestMiddlewareManagerSync(unittest.TestCase):
    """MiddlewareManager 同步执行路径"""

    def test_process_request_short_circuit(self):
        """某个中间件返回非 None 时短路"""
        first, second = Mock(), Mock()
        first.process_request.return_value = 'blocked'
        second.process_request.return_value = None

        result = MiddlewareManager().process_request(make_handler([first, second]))
        self.assertEqual(result, 'blocked')
        second.process_request.assert_not_called()

    def test_process_request_all_pass(self):
        """全部返回 None 时最终返回 None"""
        first, second = Mock(), Mock()
        first.process_request.return_value = None
        second.process_request.return_value = None

        self.assertIsNone(MiddlewareManager().process_request(make_handler([first, second])))

    def test_process_response_reverse_order(self):
        """响应处理按逆序执行"""
        order = []
        first, second = Mock(), Mock()
        first.process_response.side_effect = lambda h, r: order.append('first') or r + '1'
        second.process_response.side_effect = lambda h, r: order.append('second') or r + '2'

        result = MiddlewareManager().process_response(make_handler([first, second]), 'r')
        self.assertEqual(result, 'r21')
        self.assertEqual(order, ['second', 'first'])

    def test_process_exception_short_circuit(self):
        """某个中间件处理异常返回非 None 时短路"""
        first, second = Mock(), Mock()
        first.process_exception.return_value = 'handled'
        second.process_exception.return_value = None

        result = MiddlewareManager().process_exception(make_handler([first, second]), ValueError())
        self.assertEqual(result, 'handled')
        second.process_exception.assert_not_called()

    def test_process_exception_all_pass(self):
        """全部返回 None 时最终返回 None"""
        first = Mock()
        first.process_exception.return_value = None
        self.assertIsNone(
            MiddlewareManager().process_exception(make_handler([first]), ValueError())
        )


class TestMiddlewareManagerAsync(unittest.TestCase):
    """MiddlewareManager 异步执行路径"""

    def test_async_process_request_with_sync_fallback(self):
        """同步中间件通过线程池执行"""
        middleware = Mock()
        middleware._has_async_override.return_value = False
        middleware.process_request.return_value = None

        result = asyncio.run(MiddlewareManager().async_process_request(make_handler([middleware])))
        self.assertIsNone(result)
        middleware.process_request.assert_called_once()

    def test_async_process_request_with_async_override(self):
        """覆盖了异步方法的中间件直接 await"""
        middleware = AsyncRequestMiddleware(Mock())

        result = asyncio.run(MiddlewareManager().async_process_request(make_handler([middleware])))
        self.assertEqual(result, 'async-request-response')

    def test_async_process_response_reverse_order(self):
        """异步响应处理按逆序执行"""
        first, second = Mock(), Mock()
        first._has_async_override.return_value = False
        second._has_async_override.return_value = False
        first.process_response.side_effect = lambda h, r: r + '1'
        second.process_response.side_effect = lambda h, r: r + '2'

        result = asyncio.run(
            MiddlewareManager().async_process_response(make_handler([first, second]), 'r')
        )
        self.assertEqual(result, 'r21')

    def test_async_process_response_with_async_override(self):
        """异步响应覆盖生效"""
        middleware = AsyncResponseMiddleware(Mock())
        result = asyncio.run(
            MiddlewareManager().async_process_response(make_handler([middleware]), 'r')
        )
        self.assertEqual(result, 'r-async')

    def test_async_process_exception_short_circuit(self):
        """异步异常处理短路"""
        handled = Mock()
        handled._has_async_override.return_value = False
        handled.process_exception.return_value = 'handled'

        result = asyncio.run(
            MiddlewareManager().async_process_exception(make_handler([handled]), ValueError())
        )
        self.assertEqual(result, 'handled')

    def test_async_process_exception_with_async_override(self):
        """异步异常覆盖生效"""
        middleware = AsyncExceptionMiddleware(Mock())
        result = asyncio.run(
            MiddlewareManager().async_process_exception(make_handler([middleware]), ValueError())
        )
        self.assertEqual(result, 'async-exception-response')


if __name__ == '__main__':
    unittest.main()
