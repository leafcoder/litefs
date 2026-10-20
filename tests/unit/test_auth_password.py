#!/usr/bin/env python
# coding: utf-8

"""
密码工具测试

覆盖 litefs.auth.password 模块：哈希/验证、强度校验、泄露检查。
网络请求均通过 mock 替换，不发起真实调用。
"""

import asyncio
import hashlib
import unittest
from unittest.mock import Mock, patch
from urllib.error import URLError

from litefs.auth.password import (
    check_password_breach,
    check_password_breach_async,
    clear_breach_cache,
    generate_password,
    get_breach_count,
    hash_password,
    validate_password_strength,
    verify_password,
)
import litefs.auth.password as password_mod


def sha1_upper(text: str) -> str:
    """计算 SHA-1 大写十六进制"""
    return hashlib.sha1(text.encode()).hexdigest().upper()


class TestHashAndVerify(unittest.TestCase):
    """测试密码哈希与验证"""

    def test_hash_returns_value(self):
        """hash_password 返回非空哈希"""
        hashed = hash_password("secret", rounds=4)
        self.assertTrue(hashed)

    def test_verify_correct_password(self):
        """正确密码验证通过"""
        hashed = hash_password("secret", rounds=4)
        self.assertTrue(verify_password("secret", hashed))

    def test_verify_wrong_password(self):
        """错误密码验证失败"""
        hashed = hash_password("secret", rounds=4)
        self.assertFalse(verify_password("wrong", hashed))

    def test_verify_empty_inputs(self):
        """空密码或空哈希返回 False"""
        self.assertFalse(verify_password("", "hash"))
        self.assertFalse(verify_password("pw", ""))
        self.assertFalse(verify_password(None, None))

    def test_verify_malformed_hash(self):
        """非法哈希格式返回 False"""
        self.assertFalse(verify_password("pw", "not-a-valid-hash"))
        self.assertFalse(verify_password("pw", "pbkdf2$only-salt"))

    def test_verify_bcrypt_exception_returns_false(self):
        """bcrypt 校验异常时返回 False"""
        fake_bcrypt = Mock()
        fake_bcrypt.checkpw.side_effect = ValueError("bad hash")
        with patch.dict("sys.modules", {"bcrypt": fake_bcrypt}), \
             patch.object(password_mod, "HAS_BCRYPT", True):
            self.assertFalse(verify_password("pw", "$2b$12$invalid"))

    def test_pbkdf2_roundtrip(self):
        """pbkdf2 格式哈希可验证"""
        # 直接构造 pbkdf2 哈希
        salt = "a1b2c3d4"
        digest = hashlib.pbkdf2_hmac(
            "sha256", b"mypw", salt.encode(), 100000
        ).hex()
        stored = f"pbkdf2${salt}${digest}"
        self.assertTrue(verify_password("mypw", stored))
        self.assertFalse(verify_password("other", stored))


class TestGeneratePassword(unittest.TestCase):
    """测试随机密码生成"""

    def test_length(self):
        """生成指定长度密码"""
        self.assertEqual(len(generate_password(20)), 20)

    def test_random(self):
        """两次生成结果不同"""
        self.assertNotEqual(generate_password(32), generate_password(32))


class TestValidateStrength(unittest.TestCase):
    """测试密码强度校验"""

    def test_strong_password_passes(self):
        """强密码通过"""
        ok, errors = validate_password_strength("Str0ng!Pass")
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_too_short(self):
        """过短密码报长度错误"""
        ok, errors = validate_password_strength("Ab1")
        self.assertFalse(ok)
        self.assertTrue(any("8 个字符" in e for e in errors))

    def test_missing_lowercase(self):
        """缺少小写字母报错"""
        _, errors = validate_password_strength("ABC123XYZ")
        self.assertTrue(any("小写字母" in e for e in errors))

    def test_missing_uppercase(self):
        """缺少大写字母报错"""
        _, errors = validate_password_strength("abc123xyz")
        self.assertTrue(any("大写字母" in e for e in errors))

    def test_missing_digit(self):
        """缺少数字报错"""
        _, errors = validate_password_strength("Abcdefgh")
        self.assertTrue(any("数字" in e for e in errors))

    def test_common_password_rejected(self):
        """常见弱密码被拒绝"""
        ok, errors = validate_password_strength("password")
        self.assertFalse(ok)
        self.assertTrue(any("过于常见" in e for e in errors))

    def test_too_long(self):
        """超长密码报错"""
        ok, errors = validate_password_strength("Ab1" + "x" * 130)
        self.assertFalse(ok)
        self.assertTrue(any("128" in e for e in errors))


class TestCheckPasswordBreach(unittest.TestCase):
    """测试密码泄露检查"""

    def setUp(self):
        clear_breach_cache()

    def tearDown(self):
        clear_breach_cache()

    def _fake_response(self, body: bytes):
        response = Mock()
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def test_empty_password(self):
        """空密码直接返回 False"""
        self.assertFalse(check_password_breach(""))

    def test_breached(self):
        """命中泄露列表返回 True"""
        full = sha1_upper("password123")
        suffix = full[5:]
        body = f"AAAABBBBCCCCDDDD00001:5\n{suffix}:12345\n".encode()
        with patch(
            "litefs.auth.password.urlopen",
            return_value=self._fake_response(body),
        ):
            self.assertTrue(check_password_breach("password123"))

    def test_not_breached(self):
        """未命中泄露列表返回 False"""
        body = b"AAAABBBBCCCCDDDD00001:5\n"
        with patch(
            "litefs.auth.password.urlopen",
            return_value=self._fake_response(body),
        ):
            self.assertFalse(check_password_breach("totally-safe-pw-42"))

    def test_result_cached(self):
        """结果按前缀缓存，第二次调用不发请求"""
        full = sha1_upper("cached-password-1")
        suffix = full[5:]
        body = f"{suffix}:7\n".encode()
        with patch(
            "litefs.auth.password.urlopen",
            return_value=self._fake_response(body),
        ) as mocked:
            self.assertTrue(check_password_breach("cached-password-1"))
            self.assertTrue(check_password_breach("cached-password-1"))
        self.assertEqual(mocked.call_count, 1)

    def test_network_error_falls_back_to_local(self):
        """网络错误时回退到本地常见哈希表"""
        # 'password' 的 SHA-1 在本地降级表中；URLError 触发降级分支
        with patch(
            "litefs.auth.password.urlopen",
            side_effect=URLError("down"),
        ):
            with self.assertWarns(UserWarning):
                self.assertTrue(check_password_breach("password"))
        clear_breach_cache()

    def test_unexpected_error_returns_false(self):
        """其他异常返回 False"""
        with patch(
            "litefs.auth.password.urlopen", side_effect=RuntimeError("x")
        ):
            self.assertFalse(check_password_breach("whatever-pw"))

    def test_get_breach_count(self):
        """get_breach_count 解析泄露次数"""
        full = sha1_upper("counted-password-1")
        suffix = full[5:]
        body = f"{suffix}:42\n".encode()
        with patch(
            "litefs.auth.password.urlopen",
            return_value=self._fake_response(body),
        ):
            self.assertEqual(get_breach_count("counted-password-1"), 42)

    def test_get_breach_count_zero_and_empty(self):
        """未泄露为 0，空密码为 0"""
        self.assertEqual(get_breach_count(""), 0)
        body = b"AAAAA:1\n"
        with patch(
            "litefs.auth.password.urlopen",
            return_value=self._fake_response(body),
        ):
            self.assertEqual(get_breach_count("safe-counted-pw-1"), 0)

    def test_get_breach_count_error(self):
        """get_breach_count 网络错误返回 -1"""
        with patch(
            "litefs.auth.password.urlopen", side_effect=URLError("down")
        ):
            with self.assertWarns(UserWarning):
                self.assertEqual(get_breach_count("some-password"), -1)


class TestAsyncBreachCheck(unittest.TestCase):
    """测试异步泄露检查"""

    def test_async_fallback_without_aiohttp(self):
        """无 aiohttp 时回退同步实现"""
        with patch.object(password_mod, "HAS_AIOHTTP", False):
            with patch(
                "litefs.auth.password.check_password_breach",
                return_value=True,
            ) as sync_check:
                result = asyncio.run(check_password_breach_async("pw"))
        self.assertTrue(result)
        sync_check.assert_called_once()

    def test_async_empty_password(self):
        """异步空密码透传给同步实现并返回 False"""
        with patch.object(password_mod, "HAS_AIOHTTP", False), \
             patch(
                 "litefs.auth.password.check_password_breach",
                 return_value=False,
             ) as sync_check:
            self.assertFalse(asyncio.run(check_password_breach_async("")))
        sync_check.assert_called_once()


if __name__ == "__main__":
    unittest.main()
