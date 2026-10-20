#!/usr/bin/env python
# coding: utf-8

"""
认证中间件与权限装饰器测试

覆盖 auth.middleware（AuthMiddleware / login_required / role_required）
与 auth.decorators（permission_required / current_user / admin_required /
owner_or_admin_required）。
"""

import unittest
from unittest.mock import Mock

from litefs.auth.decorators import (
    admin_required,
    current_user,
    owner_or_admin_required,
    permission_required,
)
from litefs.auth.jwt import JWTManager
from litefs.auth.middleware import AuthMiddleware, login_required, role_required
from litefs.auth.models import MemoryUserStore, Permission, Role, User, set_user_store
from litefs.exceptions import Forbidden, Unauthorized

SECRET = 'unit-test-secret'


def make_request(**attrs):
    """构造仅声明指定属性的请求 Mock"""
    request = Mock(spec=[])
    for key, value in attrs.items():
        setattr(request, key, value)
    return request


def make_user(user_id=42, roles=None):
    return User(id=user_id, username='alice', password_hash='hash', roles=roles or [])


class AuthMiddlewareTestCase(unittest.TestCase):
    """公共基类：准备 JWT 管理器与用户存储"""

    def setUp(self):
        self.jwt = JWTManager(secret_key=SECRET)
        self.store = MemoryUserStore()
        self.user = self.store.create('alice', 'hash')
        set_user_store(self.store)

    def tearDown(self):
        set_user_store(MemoryUserStore())


class TestAuthMiddlewareTokenExtraction(AuthMiddlewareTestCase):
    """Token 提取（header / cookie / query）"""

    def test_extract_from_header_with_prefix(self):
        """header 模式下剥离 Bearer 前缀"""
        middleware = AuthMiddleware(jwt_manager=self.jwt)
        request = make_request(_environ={'HTTP_AUTHORIZATION': 'Bearer abc.def.ghi'})
        self.assertEqual(middleware._extract_token(request), 'abc.def.ghi')

    def test_extract_from_header_without_prefix(self):
        """header 模式下无前缀时返回原始值"""
        middleware = AuthMiddleware(jwt_manager=self.jwt)
        request = make_request(_environ={'HTTP_AUTHORIZATION': 'raw-token'})
        self.assertEqual(middleware._extract_token(request), 'raw-token')

    def test_extract_from_header_missing(self):
        """header 缺失时返回 None"""
        middleware = AuthMiddleware(jwt_manager=self.jwt)
        request = make_request(_environ={})
        self.assertIsNone(middleware._extract_token(request))

    def test_extract_from_cookie(self):
        """cookie 模式按 token_name 读取"""
        middleware = AuthMiddleware(jwt_manager=self.jwt, token_location='cookie')
        request = make_request(cookies={'Authorization': 'cookie-token'})
        self.assertEqual(middleware._extract_token(request), 'cookie-token')

    def test_extract_from_query(self):
        """query 模式按 token_name 读取"""
        middleware = AuthMiddleware(jwt_manager=self.jwt, token_location='query')
        request = make_request(query={'Authorization': 'query-token'})
        self.assertEqual(middleware._extract_token(request), 'query-token')

    def test_extract_unknown_location(self):
        """未知 token_location 返回 None"""
        middleware = AuthMiddleware(jwt_manager=self.jwt, token_location='body')
        request = make_request()
        self.assertIsNone(middleware._extract_token(request))


class TestAuthMiddlewareProcessRequest(AuthMiddlewareTestCase):
    """process_request 认证流程"""

    def _middleware(self):
        return AuthMiddleware(jwt_manager=self.jwt)

    def test_exempt_path_skips_auth(self):
        """豁免路径直接放行，不提取 token"""
        middleware = AuthMiddleware(jwt_manager=self.jwt, exempt_paths=['/public'])
        request = make_request(path='/public/data')
        self.assertIsNone(middleware.process_request(request))

    def test_no_token_passes_through(self):
        """无 token 时放行"""
        request = make_request(_environ={})
        self.assertIsNone(self._middleware().process_request(request))

    def test_no_jwt_manager_passes_through(self):
        """未配置 jwt_manager 时放行"""
        middleware = AuthMiddleware()
        request = make_request(_environ={'HTTP_AUTHORIZATION': 'Bearer tok'})
        self.assertIsNone(middleware.process_request(request))

    def test_invalid_token_passes_through(self):
        """非法 token 解码失败时放行"""
        request = make_request(_environ={'HTTP_AUTHORIZATION': 'Bearer broken'})
        self.assertIsNone(self._middleware().process_request(request))

    def test_payload_without_sub(self):
        """载荷缺少 sub 时放行"""
        token = self.jwt.create_access_token({'username': 'alice'})
        request = make_request(_environ={'HTTP_AUTHORIZATION': f'Bearer {token}'})
        self.assertIsNone(self._middleware().process_request(request))

    def test_valid_token_injects_user(self):
        """合法 token 注入 request.user 与 request.user_id"""
        token = self.jwt.create_access_token({'sub': self.user.id})
        request = make_request(_environ={'HTTP_AUTHORIZATION': f'Bearer {token}'})
        self.assertIsNone(self._middleware().process_request(request))
        self.assertIs(request.user, self.user)
        self.assertEqual(request.user_id, self.user.id)

    def test_unknown_user_not_injected(self):
        """用户不存在时不注入"""
        token = self.jwt.create_access_token({'sub': 9999})
        request = make_request(_environ={'HTTP_AUTHORIZATION': f'Bearer {token}'})
        self.assertIsNone(self._middleware().process_request(request))
        self.assertFalse(hasattr(request, 'user'))

    def test_process_response_passthrough(self):
        """process_response 原样返回响应"""
        response = {'ok': True}
        self.assertIs(self._middleware().process_response(make_request(), response), response)


class TestLoginAndRoleRequired(unittest.TestCase):
    """login_required 与 role_required 装饰器"""

    def test_login_required_without_user(self):
        """未登录返回 401 错误字典"""
        @login_required
        def handler(request):
            return {'ok': True}

        result = handler(make_request())
        self.assertEqual(result, ({'error': '需要登录'}, 401))

    def test_login_required_with_user(self):
        """已登录时正常调用处理函数"""
        @login_required
        def handler(request):
            return {'ok': True}

        request = make_request(user=make_user())
        self.assertEqual(handler(request), {'ok': True})

    def test_role_required_without_user(self):
        """未登录返回 401"""
        @role_required('admin')
        def handler(request):
            return {'ok': True}

        self.assertEqual(handler(make_request()), ({'error': '需要登录'}, 401))

    def test_role_required_with_matching_role(self):
        """拥有目标角色时放行"""
        @role_required('admin')
        def handler(request):
            return {'ok': True}

        request = make_request(user=make_user(roles=[Role(name='admin')]))
        self.assertEqual(handler(request), {'ok': True})

    def test_role_required_with_role_object_name(self):
        """角色对象通过 name 属性匹配"""
        @role_required('editor')
        def handler(request):
            return {'ok': True}

        request = make_request(user=make_user(roles=[Role(name='editor')]))
        self.assertEqual(handler(request), {'ok': True})

    def test_role_required_insufficient(self):
        """角色不匹配返回 403"""
        @role_required('admin')
        def handler(request):
            return {'ok': True}

        request = make_request(user=make_user(roles=[Role(name='user')]))
        self.assertEqual(handler(request), ({'error': '权限不足'}, 403))


class TestPermissionRequired(unittest.TestCase):
    """permission_required 权限装饰器"""

    def test_without_user_raises_unauthorized(self):
        """未登录抛出 Unauthorized"""
        @permission_required('user:read')
        def handler(request):
            return 'data'

        with self.assertRaises(Unauthorized) as ctx:
            handler(make_request())
        self.assertEqual(ctx.exception.message, 'Authentication required')

    def test_missing_permission_raises_forbidden(self):
        """缺少权限抛出 Forbidden"""
        @permission_required('user:read', 'user:write')
        def handler(request):
            return 'data'

        role = Role(name='reader', permissions=[Permission(name='user:read')])
        with self.assertRaises(Forbidden) as ctx:
            handler(make_request(user=make_user(roles=[role])))
        self.assertEqual(ctx.exception.message, 'Insufficient permissions')

    def test_all_permissions_pass(self):
        """权限齐全时正常调用"""
        @permission_required('user:read', 'user:write')
        def handler(request):
            return 'data'

        role = Role(name='editor', permissions=[
            Permission(name='user:read'), Permission(name='user:write'),
        ])
        self.assertEqual(handler(make_request(user=make_user(roles=[role]))), 'data')

    def test_plain_string_permissions(self):
        """权限为纯字符串时按 str 收集"""
        @permission_required('raw-perm')
        def handler(request):
            return 'data'

        role = Role(name='stringy', permissions=['raw-perm'])
        self.assertEqual(handler(make_request(user=make_user(roles=[role]))), 'data')


class TestCurrentUser(unittest.TestCase):
    """current_user 装饰器"""

    def test_passes_user_as_first_argument(self):
        """将 user 作为第一个参数传入"""
        @current_user
        def handler(user, request, extra=None):
            return user, extra

        user = make_user()
        got_user, extra = handler(make_request(user=user), extra='x')
        self.assertIs(got_user, user)
        self.assertEqual(extra, 'x')

    def test_missing_user_passes_none(self):
        """无 user 时传入 None"""
        @current_user
        def handler(user, request):
            return user

        self.assertIsNone(handler(make_request()))


class TestAdminRequired(unittest.TestCase):
    """admin_required 装饰器"""

    def test_admin_role_passes(self):
        """admin 角色放行"""
        @admin_required
        def handler(request):
            return 'admin-data'

        request = make_request(user=make_user(roles=[Role(name='admin')]))
        self.assertEqual(handler(request), 'admin-data')

    def test_non_admin_gets_403(self):
        """非 admin 角色返回 403 字典"""
        @admin_required
        def handler(request):
            return 'admin-data'

        request = make_request(user=make_user(roles=[Role(name='user')]))
        self.assertEqual(handler(request), ({'error': '权限不足'}, 403))


class TestOwnerOrAdminRequired(unittest.TestCase):
    """owner_or_admin_required 装饰器"""

    def _handler(self):
        calls = []

        @owner_or_admin_required(lambda request, *args, **kwargs: '42')
        def handler(request):
            calls.append(request)
            return 'resource'

        return handler, calls

    def test_without_user_raises_unauthorized(self):
        """未登录抛出 Unauthorized"""
        handler, _ = self._handler()
        with self.assertRaises(Unauthorized):
            handler(make_request())

    def test_admin_bypasses_owner_check(self):
        """admin 角色无需匹配所有者"""
        handler, calls = self._handler()
        request = make_request(user=make_user(user_id=1, roles=[Role(name='admin')]))
        self.assertEqual(handler(request), 'resource')

    def test_owner_passes(self):
        """所有者本人放行"""
        handler, calls = self._handler()
        request = make_request(user=make_user(user_id=42))
        self.assertEqual(handler(request), 'resource')

    def test_other_user_raises_forbidden(self):
        """非所有者非管理员抛出 Forbidden"""
        handler, _ = self._handler()
        request = make_request(user=make_user(user_id=7))
        with self.assertRaises(Forbidden):
            handler(request)


if __name__ == '__main__':
    unittest.main()
