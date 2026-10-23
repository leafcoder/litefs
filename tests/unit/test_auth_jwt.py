#!/usr/bin/env python
# coding: utf-8

"""
JWT Token 管理测试

覆盖 TokenBlacklist（内存/缓存后端）与 JWTManager 的创建、解码、撤销流程。
"""

import time
import unittest
from unittest.mock import Mock

from litefs.auth.jwt import JWTManager, TokenBlacklist, create_token, decode_token

SECRET = 'unit-test-secret'


class TestTokenBlacklist(unittest.TestCase):
    """Token 黑名单（内存后端）"""

    def setUp(self):
        self.blacklist = TokenBlacklist()

    def test_add_and_check(self):
        """加入黑名单后检测为已撤销"""
        self.blacklist.add('token-a', expires_in=60)
        self.assertTrue(self.blacklist.is_blacklisted('token-a'))
        self.assertFalse(self.blacklist.is_blacklisted('token-b'))

    def test_expired_entry_not_blacklisted(self):
        """过期条目自动失效并清理"""
        self.blacklist.add('token-a', expires_in=-1)
        self.assertFalse(self.blacklist.is_blacklisted('token-a'))
        self.assertNotIn(self.blacklist._hash_token('token-a'), self.blacklist._memory_store)

    def test_cleanup_removes_only_expired(self):
        """cleanup 仅清理过期条目"""
        self.blacklist.add('expired', expires_in=-1)
        self.blacklist.add('alive', expires_in=60)
        self.blacklist.cleanup()
        self.assertNotIn(self.blacklist._hash_token('expired'), self.blacklist._memory_store)
        self.assertIn(self.blacklist._hash_token('alive'), self.blacklist._memory_store)

    def test_clear(self):
        """clear 清空内存后端"""
        self.blacklist.add('token-a')
        self.blacklist.clear()
        self.assertEqual(len(self.blacklist), 0)

    def test_len_counts_entries(self):
        """len 返回有效条目数量"""
        self.blacklist.add('token-a', expires_in=60)
        self.blacklist.add('token-b', expires_in=60)
        self.assertEqual(len(self.blacklist), 2)

    def test_hash_stores_digest_not_raw_token(self):
        """内存中仅保存哈希，不保存原始 token"""
        self.blacklist.add('my-secret-token')
        self.assertNotIn('my-secret-token', self.blacklist._memory_store)
        self.assertIn(self.blacklist._hash_token('my-secret-token'), self.blacklist._memory_store)


class TestTokenBlacklistWithBackend(unittest.TestCase):
    """Token 黑名单（缓存后端）"""

    def setUp(self):
        self.backend = Mock()
        self.blacklist = TokenBlacklist(backend=self.backend)

    def test_add_uses_backend_put_with_ttl(self):
        """add 调用后端 put 并传入 TTL"""
        self.blacklist.add('token-a', expires_in=120)
        key = f"jwt:blacklist:{self.blacklist._hash_token('token-a')}"
        self.backend.put.assert_called_once()
        args, kwargs = self.backend.put.call_args
        self.assertEqual(args[0], key)
        self.assertEqual(kwargs.get('expiration'), 120)

    def test_is_blacklisted_reads_backend(self):
        """is_blacklisted 读取后端 get 结果"""
        key = f"jwt:blacklist:{self.blacklist._hash_token('token-a')}"
        self.backend.get.return_value = None
        self.assertFalse(self.blacklist.is_blacklisted('token-a'))
        self.backend.get.assert_called_once_with(key)

        self.backend.get.return_value = True
        self.assertTrue(self.blacklist.is_blacklisted('token-a'))

    def test_cleanup_and_clear_are_noop(self):
        """缓存后端下 cleanup/clear 为空操作，len 返回 0"""
        self.blacklist.cleanup()
        self.blacklist.clear()
        self.assertEqual(len(self.blacklist), 0)
        self.backend.get.assert_not_called()


class TestJWTManager(unittest.TestCase):
    """JWTManager 签发与解码"""

    def setUp(self):
        self.manager = JWTManager(secret_key=SECRET)

    def test_create_and_decode_roundtrip(self):
        """签发的 token 可正确解码"""
        token = self.manager.create_token({'sub': 'u1', 'username': 'alice'})
        payload = self.manager.decode_token(token)
        self.assertEqual(payload['sub'], 'u1')
        self.assertEqual(payload['username'], 'alice')
        self.assertIn('iat', payload)

    def test_create_token_with_expiry(self):
        """带过期时间时写入 exp 字段"""
        token = self.manager.create_token({'sub': 'u1'}, expires_in=120)
        payload = self.manager.decode_token(token)
        self.assertIn('exp', payload)
        self.assertGreater(payload['exp'], int(time.time()))

    def test_decode_invalid_structure(self):
        """段数不为 3 的 token 解码返回 None"""
        self.assertIsNone(self.manager.decode_token('not-a-jwt'))
        self.assertIsNone(self.manager.decode_token('a.b.c.d'))

    def test_decode_tampered_signature(self):
        """签名被篡改时解码返回 None"""
        token = self.manager.create_token({'sub': 'u1'})
        bad_token = token[:-2] + ('aa' if token[-2:] != 'aa' else 'bb')
        self.assertIsNone(self.manager.decode_token(bad_token))

    def test_decode_wrong_secret(self):
        """密钥不匹配时解码返回 None"""
        token = self.manager.create_token({'sub': 'u1'})
        other = JWTManager(secret_key='another-secret')
        self.assertIsNone(other.decode_token(token))

    def test_decode_expired_token(self):
        """已过期 token 解码返回 None"""
        token = self.manager.create_token({'sub': 'u1'}, expires_in=-1)
        self.assertIsNone(self.manager.decode_token(token))

    def test_decode_malformed_payload(self):
        """载荷非法 base64 时解码返回 None 而非抛异常"""
        import hashlib
        import hmac as hmac_module
        message = 'a.%%%'
        signature = hmac_module.new(
            SECRET.encode('utf-8'), message.encode('utf-8'), hashlib.sha256
        ).digest()
        import base64
        sig = base64.urlsafe_b64encode(signature).rstrip(b'=').decode('utf-8')
        self.assertIsNone(self.manager.decode_token(f'a.%%%.{sig}'))

    def test_access_and_refresh_token_types(self):
        """access/refresh token 携带 type 字段"""
        access = self.manager.create_access_token({'sub': 'u1'})
        refresh = self.manager.create_refresh_token({'sub': 'u1'})
        self.assertEqual(self.manager.decode_token(access)['type'], 'access')
        self.assertEqual(self.manager.decode_token(refresh)['type'], 'refresh')

    def test_revoke_token_blocks_decode(self):
        """撤销后的 token 无法解码"""
        token = self.manager.create_access_token({'sub': 'u1'})
        self.manager.revoke_token(token)
        self.assertTrue(self.manager.is_token_revoked(token))
        self.assertIsNone(self.manager.decode_token(token))

    def test_revoke_token_without_exp_uses_default_ttl(self):
        """撤销无 exp 的 token 时使用默认 TTL"""
        token = self.manager.create_token({'sub': 'u1'})
        payload = self.manager.decode_token(token)
        self.assertNotIn('exp', payload)
        self.manager.revoke_token(token)
        self.assertTrue(self.manager.is_token_revoked(token))

    def test_revoke_malformed_token(self):
        """撤销畸形 token 不崩溃且进入黑名单"""
        self.manager.revoke_token('garbage')
        self.assertTrue(self.manager.is_token_revoked('garbage'))

    def test_cleanup_blacklist(self):
        """cleanup_blacklist 委托给黑名单对象并清理过期条目"""
        token = self.manager.create_token({'sub': 'u1'})
        # 直接构造已过期的黑名单条目（revoke_token 的 TTL 下限为 3600，不会产生过期条目）
        self.manager._blacklist.add(token, expires_in=-1)
        self.manager.cleanup_blacklist()
        self.assertEqual(len(self.manager._blacklist), 0)


class TestJWTConvenienceFunctions(unittest.TestCase):
    """模块级便捷函数"""

    def test_create_and_decode(self):
        """create_token/decode_token 与管理器行为一致"""
        token = create_token({'sub': 'u1'}, secret_key=SECRET, expires_in=60)
        payload = decode_token(token, secret_key=SECRET)
        self.assertEqual(payload['sub'], 'u1')

    def test_decode_with_wrong_secret(self):
        """便捷解码校验密钥"""
        token = create_token({'sub': 'u1'}, secret_key=SECRET, expires_in=60)
        self.assertIsNone(decode_token(token, secret_key='wrong'))


class TestJWTManagerHardening(unittest.TestCase):
    """v0.11.0 JWT 加固（nbf/iat/leeway/alg 白名单/type 区分）"""

    def setUp(self):
        self.manager = JWTManager(SECRET)

    def test_unsupported_algorithm_rejected_at_init(self):
        """测试构造期拒绝不支持的算法（当前实现仅 HMAC-SHA256）"""
        with self.assertRaises(ValueError):
            JWTManager(SECRET, algorithm='HS512')

        with self.assertRaises(ValueError):
            JWTManager(SECRET, algorithm='none')

    def test_tampered_alg_header_rejected(self):
        """测试篡改 header.alg 的 token 被拒绝（防算法混淆）"""
        import hashlib
        import hmac as hmac_mod

        from litefs._json import dumps

        token = self.manager.create_token({'sub': 'alice'})
        _, payload_encoded, _ = token.split('.')

        # 用相同密钥伪造 HS512 算法头的合法签名
        forged_header = self.manager._base64url_encode(
            dumps({'alg': 'HS512', 'typ': 'JWT'})
        )
        message = f"{forged_header}.{payload_encoded}".encode('utf-8')
        signature = hmac_mod.new(
            SECRET.encode('utf-8'), message, hashlib.sha256
        ).digest()
        forged_sig = self.manager._base64url_encode(signature)

        forged_token = f"{forged_header}.{payload_encoded}.{forged_sig}"
        self.assertIsNone(self.manager.decode_token(forged_token))

    def test_nbf_future_token_rejected(self):
        """测试 nbf 在未来（未生效）的 token 被拒绝"""
        token = self.manager.create_token({
            'sub': 'alice', 'nbf': int(time.time()) + 600,
        })
        self.assertIsNone(self.manager.decode_token(token))

    def test_nbf_past_token_accepted(self):
        """测试 nbf 已生效的 token 正常解码"""
        token = self.manager.create_token({
            'sub': 'alice', 'nbf': int(time.time()) - 60,
        })
        payload = self.manager.decode_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['sub'], 'alice')

    def test_iat_future_beyond_leeway_rejected(self):
        """测试 iat 在未来（超出容忍）的 token 被拒绝"""
        token = self.manager.create_token({
            'sub': 'alice', 'iat': int(time.time()) + 600,
        })
        self.assertIsNone(self.manager.decode_token(token))

    def test_leeway_tolerates_recent_expiry(self):
        """测试 leeway 时钟偏移容忍：刚过期 token 在容忍窗口内仍有效"""
        strict = JWTManager(SECRET)
        lenient = JWTManager(SECRET, leeway=30)

        token = strict.create_token({'sub': 'alice'}, expires_in=-20)

        self.assertIsNone(strict.decode_token(token))
        self.assertIsNotNone(lenient.decode_token(token))

    def test_type_enforcement_on_decode(self):
        """测试 decode_token 按 expected_type 强制校验 type claim"""
        access = self.manager.create_access_token({'sub': 'alice'})
        refresh = self.manager.create_refresh_token({'sub': 'alice'})

        # refresh token 不能当作 access token 使用
        self.assertIsNone(self.manager.decode_token(refresh, expected_type='access'))
        # access token 不能当作 refresh token 使用
        self.assertIsNone(self.manager.decode_token(access, expected_type='refresh'))
        # 正确类型可解码
        self.assertIsNotNone(self.manager.decode_token(access, expected_type='access'))
        self.assertIsNotNone(self.manager.decode_token(refresh, expected_type='refresh'))

    def test_decode_without_expected_type_backward_compatible(self):
        """测试不传 expected_type 时保持向后兼容（不校验 type）"""
        access = self.manager.create_access_token({'sub': 'alice'})
        payload = self.manager.decode_token(access)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['type'], 'access')

    def test_token_without_type_claim_rejected_when_expected(self):
        """测试无 type claim 的 token 在指定 expected_type 时被拒绝"""
        token = self.manager.create_token({'sub': 'alice'})
        self.assertIsNone(self.manager.decode_token(token, expected_type='access'))


if __name__ == '__main__':
    unittest.main()
