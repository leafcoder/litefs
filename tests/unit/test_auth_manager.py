#!/usr/bin/env python
# coding: utf-8

"""
认证授权管理器测试

覆盖 litefs.auth.Auth：初始化、路由注册、登录/注册/刷新/登出处理器、
用户创建与验证。
"""

import unittest
from unittest.mock import Mock

from litefs.auth import Auth
from litefs.auth.models import MemoryUserStore, set_user_store
from litefs.auth.password import hash_password


class AuthManagerTestCase(unittest.TestCase):
    """公共基类：隔离全局用户存储"""

    def setUp(self):
        self.store = MemoryUserStore()
        set_user_store(self.store)
        self.auth = Auth(secret_key='unit-test-secret')

    def tearDown(self):
        set_user_store(MemoryUserStore())

    @staticmethod
    def make_request(data):
        request = Mock(spec=[])
        request.json = data
        return request


class TestAuthInit(AuthManagerTestCase):
    """Auth 初始化"""

    def test_default_secret_fallback(self):
        """未提供密钥时使用默认占位密钥"""
        auth = Auth()
        self.assertEqual(auth.secret_key, 'change-me-in-production')

    def test_token_configuration_stored(self):
        """token 配置项保存到实例"""
        auth = Auth(
            secret_key='k', algorithm='HS256',
            access_token_expires=600, refresh_token_expires=7200,
            token_location='cookie', token_name='X-Auth', token_prefix='Token',
        )
        self.assertEqual(auth.access_token_expires, 600)
        self.assertEqual(auth.refresh_token_expires, 7200)
        self.assertEqual(auth.token_location, 'cookie')
        self.assertEqual(auth.token_name, 'X-Auth')
        self.assertEqual(auth.token_prefix, 'Token')

    def test_init_app_registers_middleware_and_routes(self):
        """init_app 注册认证中间件与四个认证路由"""
        app = Mock()
        self.auth.init_app(app)
        app.add_middleware.assert_called_once()
        registered = {call.args[0]: call for call in app.add_post.call_args_list}
        self.assertEqual(
            set(registered),
            {'/auth/login', '/auth/register', '/auth/refresh', '/auth/logout'},
        )
        self.assertEqual(registered['/auth/login'].kwargs['name'], 'auth_login')
        self.assertEqual(registered['/auth/refresh'].kwargs['name'], 'auth_refresh')

    def test_constructor_with_app_inits_immediately(self):
        """构造时传入 app 立即完成初始化"""
        app = Mock()
        Auth(secret_key='k', app=app)
        app.add_middleware.assert_called_once()


class TestLoginHandler(AuthManagerTestCase):
    """登录处理器"""

    def _create_user(self):
        self.store.create('alice', hash_password('secret123'))

    def test_missing_credentials_returns_400(self):
        """缺少用户名或密码返回 400"""
        result, status = self.auth.login_handler(self.make_request({'username': 'alice'}))
        self.assertEqual(status, 400)
        self.assertIn('error', result)

        result, status = self.auth.login_handler(self.make_request({}))
        self.assertEqual(status, 400)

    def test_wrong_password_returns_401(self):
        """密码错误返回 401"""
        self._create_user()
        result, status = self.auth.login_handler(
            self.make_request({'username': 'alice', 'password': 'wrong'})
        )
        self.assertEqual(status, 401)

    def test_unknown_user_returns_401(self):
        """用户不存在返回 401"""
        result, status = self.auth.login_handler(
            self.make_request({'username': 'ghost', 'password': 'x'})
        )
        self.assertEqual(status, 401)

    def test_success_returns_tokens(self):
        """登录成功返回访问令牌与刷新令牌"""
        self._create_user()
        result = self.auth.login_handler(
            self.make_request({'username': 'alice', 'password': 'secret123'})
        )
        self.assertIn('access_token', result)
        self.assertEqual(result['token_type'], 'Bearer')
        self.assertEqual(result['expires_in'], self.auth.access_token_expires)

        access_payload = self.auth._jwt.decode_token(result['access_token'])
        refresh_payload = self.auth._jwt.decode_token(result['refresh_token'])
        self.assertEqual(access_payload['username'], 'alice')
        self.assertEqual(access_payload['type'], 'access')
        self.assertEqual(refresh_payload['type'], 'refresh')


class TestRegisterHandler(AuthManagerTestCase):
    """注册处理器"""

    def test_missing_fields_returns_400(self):
        """缺少必填字段返回 400"""
        _, status = self.auth.register_handler(self.make_request({'username': 'alice'}))
        self.assertEqual(status, 400)

    def test_duplicate_username_returns_400(self):
        """用户名已存在返回 400"""
        self.store.create('alice', 'hash')
        _, status = self.auth.register_handler(
            self.make_request({'username': 'alice', 'password': 'secret123'})
        )
        self.assertEqual(status, 400)

    def test_success_creates_user(self):
        """注册成功创建用户并返回 201"""
        result, status = self.auth.register_handler(self.make_request({
            'username': 'alice', 'password': 'secret123', 'email': 'a@b.com',
        }))
        self.assertEqual(status, 201)
        user = self.store.get_by_username('alice')
        self.assertIsNotNone(user)
        self.assertEqual(result['user_id'], user.id)
        self.assertNotEqual(user.password_hash, 'secret123')


class TestRefreshHandler(AuthManagerTestCase):
    """Token 刷新处理器"""

    def test_missing_token_returns_400(self):
        """缺少 refresh_token 返回 400"""
        _, status = self.auth.refresh_handler(self.make_request({}))
        self.assertEqual(status, 400)

    def test_invalid_token_returns_401(self):
        """无效 refresh_token 返回 401"""
        _, status = self.auth.refresh_handler(self.make_request({'refresh_token': 'bad'}))
        self.assertEqual(status, 401)

    def test_access_token_rejected(self):
        """access token 不能用于刷新"""
        token = self.auth._jwt.create_access_token({'sub': 1})
        _, status = self.auth.refresh_handler(self.make_request({'refresh_token': token}))
        self.assertEqual(status, 401)

    def test_unknown_user_returns_401(self):
        """用户不存在返回 401"""
        token = self.auth._jwt.create_refresh_token({'sub': 9999})
        _, status = self.auth.refresh_handler(self.make_request({'refresh_token': token}))
        self.assertEqual(status, 401)

    def test_success_returns_new_access_token(self):
        """刷新成功返回新的访问令牌"""
        user = self.store.create('alice', 'hash')
        token = self.auth._jwt.create_refresh_token({'sub': user.id})
        result = self.auth.refresh_handler(self.make_request({'refresh_token': token}))
        self.assertIn('access_token', result)
        self.assertEqual(result['token_type'], 'Bearer')
        payload = self.auth._jwt.decode_token(result['access_token'])
        self.assertEqual(payload['username'], 'alice')


class TestLogoutAndUserHelpers(AuthManagerTestCase):
    """登出与用户辅助方法"""

    def test_logout_returns_message(self):
        """登出返回成功消息"""
        result = self.auth.logout_handler(self.make_request({}))
        self.assertIn('message', result)

    def test_create_user_hashes_password(self):
        """create_user 存储哈希后的密码"""
        user = self.auth.create_user('alice', 'secret123', email='a@b.com')
        self.assertEqual(user.username, 'alice')
        self.assertNotEqual(user.password_hash, 'secret123')
        self.assertIs(self.store.get_by_username('alice'), user)

    def test_authenticate_success_and_failure(self):
        """authenticate 验证成功返回用户，失败返回 None"""
        self.auth.create_user('alice', 'secret123')
        self.assertIsNotNone(self.auth.authenticate('alice', 'secret123'))
        self.assertIsNone(self.auth.authenticate('alice', 'wrong'))
        self.assertIsNone(self.auth.authenticate('ghost', 'x'))


if __name__ == '__main__':
    unittest.main()
