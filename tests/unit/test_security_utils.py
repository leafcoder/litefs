#!/usr/bin/env python
# coding: utf-8

"""
安全工具函数测试

覆盖 secure_path_join 路径遍历防护、CSRF 令牌生成与校验。
"""

import os
import unittest

from litefs.security import generate_csrf_token, secure_path_join, validate_csrf_token


class TestSecurePathJoin(unittest.TestCase):
    """secure_path_join 路径拼接防护"""

    def test_normal_relative_path(self):
        """正常相对路径拼接成功"""
        result = secure_path_join('/var/www', 'static/app.js')
        self.assertEqual(result, os.path.join('/var/www', 'static/app.js'))

    def test_traversal_rejected(self):
        """.. 路径遍历被拒绝"""
        self.assertIsNone(secure_path_join('/var/www', '../etc/passwd'))

    def test_deep_traversal_rejected(self):
        """多层遍历被拒绝"""
        self.assertIsNone(secure_path_join('/var/www', 'a/../../etc/passwd'))

    def test_self_reference_allowed(self):
        """./ 自引用拼接成功"""
        result = secure_path_join('/var/www', './index.html')
        self.assertEqual(result, os.path.join('/var/www', 'index.html'))

    def test_stays_within_base_allowed(self):
        """子目录内遍历后仍回到 base 下则允许"""
        result = secure_path_join('/var/www', 'a/../index.html')
        self.assertEqual(result, os.path.join('/var/www', 'index.html'))


class TestCsrfToken(unittest.TestCase):
    """CSRF 令牌生成与校验"""

    def test_generate_token_length_and_uniqueness(self):
        """令牌为 64 位十六进制且不重复"""
        token_a = generate_csrf_token()
        token_b = generate_csrf_token()
        self.assertEqual(len(token_a), 64)
        self.assertNotEqual(token_a, token_b)
        int(token_a, 16)  # 十六进制合法

    def test_validate_matching_tokens(self):
        """相同令牌校验通过"""
        token = generate_csrf_token()
        self.assertTrue(validate_csrf_token(token, token))

    def test_validate_mismatched_tokens(self):
        """不同令牌校验失败"""
        self.assertFalse(validate_csrf_token('a' * 64, 'b' * 64))

    def test_validate_empty_tokens(self):
        """空令牌校验失败"""
        self.assertFalse(validate_csrf_token('', 'token'))
        self.assertFalse(validate_csrf_token('token', ''))
        self.assertFalse(validate_csrf_token(None, 'token'))


if __name__ == '__main__':
    unittest.main()
