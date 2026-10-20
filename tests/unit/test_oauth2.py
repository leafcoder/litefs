#!/usr/bin/env python
# coding: utf-8

"""
OAuth2 认证管理测试

覆盖 litefs.auth.oauth2 模块：OAuth2State、OAuth2 管理器与蓝图工厂。
所有网络请求均通过 mock 替换，不发起真实调用。
"""

import asyncio
import unittest
from unittest.mock import Mock, patch

from litefs.auth.oauth2 import OAuth2, OAuth2State, create_oauth2_blueprint
from litefs.auth.providers import OAuth2Provider, OAuth2UserInfo


class FakeProvider(OAuth2Provider):
    """测试用假提供商"""

    name = "fake"
    authorize_url = "https://fake.example/authorize"
    access_token_url = "https://fake.example/token"
    userinfo_url = "https://fake.example/user"

    def get_access_token(self, code, redirect_uri=None):
        return {"access_token": "tok", "redirect_uri": redirect_uri}

    def get_user_info(self, access_token, openid=None, code=None):
        return OAuth2UserInfo(
            provider=self.name,
            provider_user_id="uid1",
            username="fakeuser",
            email="fake@example.com",
        )


class TestOAuth2State(unittest.TestCase):
    """测试 OAuth2 状态管理"""

    def test_create_and_verify(self):
        """创建的状态可验证且验证后销毁（一次性）"""
        state = OAuth2State()
        token = state.create(provider="github", redirect_uri="http://cb", foo="x")
        data = state.verify(token)
        self.assertEqual(data["provider"], "github")
        self.assertEqual(data["redirect_uri"], "http://cb")
        self.assertEqual(data["foo"], "x")
        # 一次性：再次验证返回 None
        self.assertIsNone(state.verify(token))

    def test_verify_unknown_state(self):
        """未知状态返回 None"""
        self.assertIsNone(OAuth2State().verify("no-such-state"))

    def test_verify_expired(self):
        """过期状态验证失败"""
        state = OAuth2State(ttl=-1)
        token = state.create(provider="github")
        self.assertIsNone(state.verify(token))

    def test_cleanup_removes_expired(self):
        """cleanup 清理过期状态并保留有效状态"""
        state = OAuth2State(ttl=600)
        fresh = state.create(provider="github")
        state._states["old"] = {"provider": "g", "created_at": 0}
        state.cleanup()
        self.assertIn(fresh, state._states)
        self.assertNotIn("old", state._states)


class TestOAuth2Register(unittest.TestCase):
    """测试提供商注册"""

    def test_register_builtin(self):
        """按名称注册内置提供商"""
        oauth = OAuth2()
        oauth.register("github", client_id="c", client_secret="s")
        self.assertIsInstance(oauth.get_provider("github"), OAuth2Provider)

    def test_register_custom_class(self):
        """注册自定义提供商类"""
        oauth = OAuth2()
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        self.assertIsInstance(oauth.get_provider("fake"), FakeProvider)

    def test_register_unknown_raises(self):
        """注册未知提供商抛 ValueError"""
        oauth = OAuth2()
        with self.assertRaises(ValueError):
            oauth.register("nope", client_id="c", client_secret="s")

    def test_get_provider_missing(self):
        """未注册的提供商返回 None"""
        self.assertIsNone(OAuth2().get_provider("github"))

    def test_init_app(self):
        """init_app 保存应用引用"""
        app = Mock()
        oauth = OAuth2(app=app)
        self.assertIs(oauth._app, app)


class TestAuthorizeRedirect(unittest.TestCase):
    """测试授权重定向"""

    def _oauth(self):
        oauth = OAuth2()
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        return oauth

    def test_redirect_to_authorize_url(self):
        """生成指向授权地址的重定向响应"""
        oauth = self._oauth()
        response = oauth.authorize_redirect(Mock(), "fake")
        self.assertEqual(response.status_code, 302)
        location = [v for k, v in response.headers if k == "Location"][0]
        self.assertTrue(location.startswith(FakeProvider.authorize_url))

    def test_unknown_provider_json_400(self):
        """未知提供商返回 400 JSON"""
        response = self._oauth().authorize_redirect(Mock(), "nope")
        self.assertEqual(response.status_code, 400)

    def test_state_recorded(self):
        """重定向时状态被记录，可被 verify"""
        oauth = self._oauth()
        response = oauth.authorize_redirect(Mock(), "fake")
        from urllib.parse import urlparse, parse_qs
        location = [v for k, v in response.headers if k == "Location"][0]
        query = parse_qs(urlparse(location).query)
        state_data = oauth._state.verify(query["state"][0])
        self.assertEqual(state_data["provider"], "fake")


class TestAuthorizeUser(unittest.TestCase):
    """测试授权回调获取用户"""

    def _oauth(self, mapper=None):
        oauth = OAuth2(user_mapper=mapper)
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        return oauth

    def _request_with_code(self, oauth, provider="fake", query=None):
        query = query or {}
        state = oauth._state.create(provider=provider, redirect_uri="http://cb")
        request = Mock()
        request.query = {"code": "abc", "state": state, **query}
        return request

    def test_success(self):
        """完整授权流程返回用户信息"""
        oauth = self._oauth()
        user = oauth.authorize_user(self._request_with_code(oauth))
        self.assertIsInstance(user, OAuth2UserInfo)
        self.assertEqual(user.username, "fakeuser")

    def test_user_mapper_applied(self):
        """user_mapper 应用于用户信息"""
        oauth = self._oauth(mapper=lambda info: {"mapped": info.username})
        user = oauth.authorize_user(self._request_with_code(oauth))
        self.assertEqual(user, {"mapped": "fakeuser"})

    def test_missing_code_returns_none(self):
        """缺少 code 返回 None"""
        oauth = self._oauth()
        request = Mock()
        request.query = {"state": "whatever"}
        self.assertIsNone(oauth.authorize_user(request))

    def test_invalid_state_returns_none(self):
        """无效 state 返回 None"""
        oauth = self._oauth()
        request = Mock()
        request.query = {"code": "abc", "state": "bogus"}
        self.assertIsNone(oauth.authorize_user(request))

    def test_unknown_provider_in_state_returns_none(self):
        """状态指向未注册提供商返回 None"""
        oauth = self._oauth()
        state = oauth._state.create(provider="ghost")
        request = Mock()
        request.query = {"code": "abc", "state": state}
        self.assertIsNone(oauth.authorize_user(request))

    def test_token_error_returns_none(self):
        """token 响应含 error 时返回 None"""
        oauth = self._oauth()
        state = oauth._state.create(provider="fake", redirect_uri="http://cb")
        request = Mock()
        request.query = {"code": "abc", "state": state}
        with patch.object(
            oauth.get_provider("fake"),
            "get_access_token",
            return_value={"error": "bad_code"},
        ):
            self.assertIsNone(oauth.authorize_user(request))

    def test_query_string_fallback(self):
        """无 query 属性时从 query_string 解析"""
        oauth = self._oauth()
        state = oauth._state.create(provider="fake", redirect_uri="http://cb")
        request = Mock(spec=["query_string"])
        request.query_string = f"code=abc&state={state}"
        user = oauth.authorize_user(request)
        self.assertEqual(user.username, "fakeuser")


class TestAuthorizeUserAsync(unittest.TestCase):
    """测试异步授权流程"""

    def test_async_flow_success(self):
        """异步流程：mock _async_request 后返回用户信息"""
        oauth = OAuth2()
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        state = oauth._state.create(provider="fake", redirect_uri="http://cb")
        request = Mock()
        request.query = {"code": "abc", "state": state}

        async def fake_async_request(url, *_args, **_kwargs):
            if "token" in url:
                return {"access_token": "tok"}
            return {"id": "uid1", "login": "fakeuser"}

        provider = oauth.get_provider("fake")
        with patch.object(provider, "_async_request", side_effect=fake_async_request):
            user = asyncio.run(oauth.authorize_user_async(request))
        self.assertIsInstance(user, OAuth2UserInfo)

    def test_async_flow_no_code(self):
        """异步流程缺少 code 返回 None"""
        request = Mock()
        request.query = {}
        result = asyncio.run(OAuth2().authorize_user_async(request))
        self.assertIsNone(result)


class TestBuildTokenRequestData(unittest.TestCase):
    """测试 token 请求数据构造"""

    def test_wechat_params(self):
        oauth = OAuth2()
        oauth.register("wechat", client_id="wx", client_secret="s")
        data = oauth._build_token_request_data(
            oauth.get_provider("wechat"), "code"
        )
        self.assertEqual(data["appid"], "wx")
        self.assertEqual(data["grant_type"], "authorization_code")

    def test_wecom_params(self):
        oauth = OAuth2()
        oauth.register("wecom", client_id="corp", client_secret="s")
        data = oauth._build_token_request_data(
            oauth.get_provider("wecom"), "code"
        )
        self.assertEqual(data["corpid"], "corp")
        self.assertEqual(data["corpsecret"], "s")

    def test_google_params(self):
        oauth = OAuth2()
        oauth.register("google", client_id="g", client_secret="s")
        data = oauth._build_token_request_data(
            oauth.get_provider("google"), "code", "http://cb"
        )
        self.assertEqual(data["grant_type"], "authorization_code")
        self.assertEqual(data["redirect_uri"], "http://cb")

    def test_default_params(self):
        oauth = OAuth2()
        oauth.register("github", client_id="gh", client_secret="s")
        data = oauth._build_token_request_data(
            oauth.get_provider("github"), "code", None
        )
        self.assertEqual(data["client_id"], "gh")
        self.assertNotIn("grant_type", data)


class TestGetAuthorizeUrl(unittest.TestCase):
    """测试 get_authorize_url 方法"""

    def test_url_with_state(self):
        """显式传入 state 时直接使用"""
        oauth = OAuth2()
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        url = oauth.get_authorize_url("fake", state="fixed")
        self.assertIn("state=fixed", url)

    def test_url_generates_state(self):
        """未传 state 时自动生成并登记"""
        oauth = OAuth2()
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        url = oauth.get_authorize_url("fake")
        from urllib.parse import urlparse, parse_qs
        state = parse_qs(urlparse(url).query)["state"][0]
        self.assertIsNotNone(oauth._state.verify(state))

    def test_unknown_provider_raises(self):
        """未知提供商抛 ValueError"""
        with self.assertRaises(ValueError):
            OAuth2().get_authorize_url("nope")

    def test_set_user_mapper(self):
        """set_user_mapper 更新映射函数"""
        oauth = OAuth2()
        mapper = lambda info: info  # noqa: E731
        oauth.set_user_mapper(mapper)
        self.assertIs(oauth._user_mapper, mapper)


class TestCreateBlueprint(unittest.TestCase):
    """测试蓝图工厂"""

    def test_routes_generated_per_provider(self):
        """每个提供商生成 login 与 callback 两条路由"""
        oauth = OAuth2()
        oauth.register(
            "fake", client_id="c", client_secret="s",
            provider_class=FakeProvider,
        )
        routes = create_oauth2_blueprint(oauth)
        self.assertEqual(len(routes), 2)
        for route in routes:
            self.assertTrue(callable(route) or hasattr(route, "path"))

    def test_empty_providers(self):
        """无注册提供商时返回空列表"""
        self.assertEqual(create_oauth2_blueprint(OAuth2()), [])


if __name__ == "__main__":
    unittest.main()
