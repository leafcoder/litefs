#!/usr/bin/env python
# coding: utf-8

"""
OAuth2 提供商测试

覆盖 litefs.auth.providers 模块：UserInfo、各提供商实现与 PKCE 工具。
所有 HTTP 请求均通过 mock 替换，不发起真实网络调用。
"""

import base64
import hashlib
import unittest
from unittest.mock import patch

from litefs.auth.providers import (
    GitHubProvider,
    GoogleProvider,
    OAuth2Provider,
    OAuth2UserInfo,
    PROVIDERS,
    WeChatProvider,
    WeComProvider,
    get_provider,
)


class TestOAuth2UserInfo(unittest.TestCase):
    """测试用户信息对象"""

    def test_to_dict(self):
        """to_dict 输出标准字段且不含 raw_data"""
        info = OAuth2UserInfo(
            provider="github",
            provider_user_id="1",
            username="alice",
            email="a@example.com",
        )
        data = info.to_dict()
        self.assertEqual(data["provider"], "github")
        self.assertEqual(data["username"], "alice")
        self.assertEqual(data["email"], "a@example.com")
        self.assertNotIn("raw_data", data)

    def test_defaults(self):
        """可选字段默认为 None"""
        info = OAuth2UserInfo(provider="x", provider_user_id="1", username="u")
        self.assertIsNone(info.email)
        self.assertIsNone(info.name)
        self.assertIsNone(info.avatar_url)
        self.assertIsNone(info.raw_data)


class TestProviderRegistry(unittest.TestCase):
    """测试提供商注册表"""

    def test_get_provider_all(self):
        """注册表覆盖四家提供商"""
        self.assertIs(get_provider("github"), GitHubProvider)
        self.assertIs(get_provider("google"), GoogleProvider)
        self.assertIs(get_provider("wechat"), WeChatProvider)
        self.assertIs(get_provider("wecom"), WeComProvider)

    def test_get_provider_case_insensitive(self):
        """提供商名称大小写不敏感"""
        self.assertIs(get_provider("GITHUB"), GitHubProvider)

    def test_get_provider_unknown(self):
        """未知提供商返回 None"""
        self.assertIsNone(get_provider("nope"))

    def test_providers_mapping_complete(self):
        """PROVIDERS 映射与注册表一致"""
        self.assertEqual(
            set(PROVIDERS.keys()), {"github", "google", "wechat", "wecom"}
        )


class _MinimalProvider(OAuth2Provider):
    """最小具体实现，用于测试基类逻辑"""

    name = "minimal"
    authorize_url = "https://minimal.example/authorize"

    def get_access_token(self, code, redirect_uri=None):
        return {}

    def get_user_info(self, access_token):
        return None


class TestProviderBase(unittest.TestCase):
    """测试提供商基类"""

    def _make(self):
        return _MinimalProvider(
            client_id="cid", client_secret="cs", redirect_uri="http://cb"
        )

    def test_init_defaults(self):
        """构造参数正确保存"""
        p = self._make()
        self.assertEqual(p.client_id, "cid")
        self.assertEqual(p.client_secret, "cs")
        self.assertEqual(p.redirect_uri, "http://cb")
        self.assertEqual(p.extra_params, {})

    def test_scope_fallback_to_class_default(self):
        """未显式传 scope 时使用类默认值"""
        p = GitHubProvider(client_id="c", client_secret="s")
        self.assertEqual(p.scope, "user:email")

    def test_get_authorize_url(self):
        """授权 URL 包含标准参数与 scope"""
        p = GitHubProvider(client_id="cid", client_secret="s",
                           redirect_uri="http://cb")
        url = p.get_authorize_url(state="st123")
        self.assertTrue(url.startswith(GitHubProvider.authorize_url))
        self.assertIn("client_id=cid", url)
        self.assertIn("redirect_uri=http%3A%2F%2Fcb", url)
        self.assertIn("response_type=code", url)
        self.assertIn("state=st123", url)
        self.assertIn("scope=user%3Aemail", url)

    def test_get_authorize_url_override_redirect(self):
        """authorize_url 支持覆盖 redirect_uri"""
        p = self._make()
        url = p.get_authorize_url(state="s", redirect_uri="http://other")
        self.assertIn("redirect_uri=http%3A%2F%2Fother", url)

    def test_generate_state_random(self):
        """generate_state 每次生成不同随机串"""
        p = self._make()
        self.assertNotEqual(p.generate_state(), p.generate_state())

    def test_pkce_s256(self):
        """PKCE S256 挑战为 base64url(sha256(verifier)) 去掉填充"""
        p = self._make()
        verifier = p.generate_pkce_verifier()
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        self.assertEqual(p.generate_pkce_challenge(verifier), expected)

    def test_pkce_plain(self):
        """PKCE plain 方法原样返回 verifier"""
        p = self._make()
        self.assertEqual(p.generate_pkce_challenge("v", method="plain"), "v")

    def test_request_error_handling(self):
        """_request 网络异常返回 error 字典"""
        p = self._make()
        with patch("urllib.request.urlopen", side_effect=OSError("boom")):
            result = p._request("http://invalid.local")
        self.assertIn("error", result)


class TestGitHubProvider(unittest.TestCase):
    """测试 GitHub 提供商"""

    def test_get_user_info_success(self):
        """获取用户信息并选取主邮箱"""
        p = GitHubProvider(client_id="c", client_secret="s")
        user_data = {"id": 42, "login": "alice", "name": "Alice",
                     "email": None, "avatar_url": "http://av"}
        emails = [
            {"email": "sec@example.com", "primary": False, "verified": True},
            {"email": "main@example.com", "primary": True, "verified": True},
        ]
        with patch.object(p, "_request", side_effect=[user_data, emails]):
            info = p.get_user_info("token")
        self.assertEqual(info.provider, "github")
        self.assertEqual(info.provider_user_id, "42")
        self.assertEqual(info.username, "alice")
        self.assertEqual(info.email, "main@example.com")

    def test_get_user_info_error(self):
        """用户接口报错时返回 None"""
        p = GitHubProvider(client_id="c", client_secret="s")
        with patch.object(p, "_request", return_value={"error": "HTTP 401"}):
            self.assertIsNone(p.get_user_info("token"))

    def test_get_user_info_emails_not_list(self):
        """邮箱接口返回非列表时回退到用户主 email"""
        p = GitHubProvider(client_id="c", client_secret="s")
        user_data = {"id": 1, "login": "bob", "email": "bob@example.com"}
        with patch.object(p, "_request", side_effect=[user_data, {"error": "x"}]):
            info = p.get_user_info("token")
        self.assertEqual(info.email, "bob@example.com")

    def test_get_access_token(self):
        """get_access_token 转发 token 接口响应"""
        p = GitHubProvider(client_id="c", client_secret="s")
        with patch.object(
            p, "_request", return_value={"access_token": "t"}
        ) as mocked:
            result = p.get_access_token(code="abc")
        self.assertEqual(result, {"access_token": "t"})
        self.assertEqual(mocked.call_args.kwargs["method"], "POST")


class TestGoogleProvider(unittest.TestCase):
    """测试 Google 提供商"""

    def test_get_user_info_success(self):
        """从 sub/email 构造用户信息"""
        p = GoogleProvider(client_id="c", client_secret="s")
        user_data = {"sub": "9", "email": "u@gmail.com", "name": "U",
                     "picture": "http://pic"}
        with patch.object(p, "_request", return_value=user_data):
            info = p.get_user_info("token")
        self.assertEqual(info.provider, "google")
        self.assertEqual(info.provider_user_id, "9")
        self.assertEqual(info.username, "u")

    def test_get_user_info_error(self):
        """用户接口报错时返回 None"""
        p = GoogleProvider(client_id="c", client_secret="s")
        with patch.object(p, "_request", return_value={"error": "x"}):
            self.assertIsNone(p.get_user_info("token"))

    def test_get_access_token_includes_grant_type(self):
        """Google token 请求包含 grant_type"""
        p = GoogleProvider(client_id="c", client_secret="s")
        with patch.object(p, "_request", return_value={}) as mocked:
            p.get_access_token(code="c")
        self.assertEqual(
            mocked.call_args.kwargs["data"]["grant_type"], "authorization_code"
        )


class TestWeChatProvider(unittest.TestCase):
    """测试微信提供商"""

    def test_authorize_url_suffix(self):
        """微信授权 URL 以 #wechat_redirect 结尾"""
        p = WeChatProvider(client_id="wx", client_secret="s",
                           redirect_uri="http://cb")
        url = p.get_authorize_url(state="s")
        self.assertTrue(url.endswith("#wechat_redirect"))
        self.assertIn("appid=wx", url)
        self.assertIn("scope=snsapi_login", url)

    def test_get_user_info_requires_openid(self):
        """缺少 openid 时返回 None"""
        p = WeChatProvider(client_id="wx", client_secret="s")
        self.assertIsNone(p.get_user_info("token", openid=None))

    def test_get_user_info_success(self):
        """获取微信用户信息"""
        p = WeChatProvider(client_id="wx", client_secret="s")
        data = {"openid": "o1", "unionid": "u1", "nickname": "昵称",
                "headimgurl": "http://av"}
        with patch.object(p, "_request", return_value=data):
            info = p.get_user_info("token", openid="o1")
        self.assertEqual(info.provider, "wechat")
        self.assertEqual(info.provider_user_id, "u1")
        self.assertEqual(info.username, "昵称")

    def test_get_user_info_errcode(self):
        """响应包含 errcode 时返回 None"""
        p = WeChatProvider(client_id="wx", client_secret="s")
        with patch.object(p, "_request", return_value={"errcode": 40029}):
            self.assertIsNone(p.get_user_info("token", openid="o1"))


class TestWeComProvider(unittest.TestCase):
    """测试企业微信提供商"""

    def test_init_with_agent_id(self):
        """支持 agent_id 参数"""
        p = WeComProvider(client_id="corp", client_secret="s", agent_id="100")
        self.assertEqual(p.agent_id, "100")

    def test_authorize_url_includes_agentid(self):
        """授权 URL 包含 agentid"""
        p = WeComProvider(client_id="corp", client_secret="s", agent_id="100")
        url = p.get_authorize_url(state="s")
        self.assertIn("agentid=100", url)
        self.assertIn("appid=corp", url)

    def test_get_user_info_requires_code(self):
        """缺少 code 时返回 None"""
        p = WeComProvider(client_id="corp", client_secret="s")
        self.assertIsNone(p.get_user_info("token", code=None))

    def test_get_user_info_errcode_nonzero(self):
        """errcode 非 0 时返回 None"""
        p = WeComProvider(client_id="corp", client_secret="s")
        with patch.object(p, "_request", return_value={"errcode": 60020}):
            self.assertIsNone(p.get_user_info("token", code="c"))

    def test_get_user_info_success(self):
        """获取企业微信用户信息"""
        p = WeComProvider(client_id="corp", client_secret="s")
        data = {"errcode": 0, "UserId": "Zhang"}
        with patch.object(p, "_request", return_value=data):
            info = p.get_user_info("token", code="c")
        self.assertEqual(info.provider, "wecom")
        self.assertEqual(info.username, "Zhang")


if __name__ == "__main__":
    unittest.main()
