#!/usr/bin/env python
# coding: utf-8

"""
认证授权系统单元测试
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestJWT(unittest.TestCase):
    """JWT 测试"""
    
    def test_create_and_decode_token(self):
        """测试创建和解码 Token"""
        from litefs.auth.jwt import JWTManager
        
        manager = JWTManager('test-secret-key')
        
        payload = {'sub': 1, 'username': 'test'}
        token = manager.create_access_token(payload)
        
        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        
        decoded = manager.decode_token(token)
        
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded['sub'], 1)
        self.assertEqual(decoded['username'], 'test')
        self.assertEqual(decoded['type'], 'access')
    
    def test_invalid_token(self):
        """测试无效 Token"""
        from litefs.auth.jwt import JWTManager
        
        manager = JWTManager('test-secret-key')
        
        decoded = manager.decode_token('invalid.token.here')
        self.assertIsNone(decoded)
    
    def test_refresh_token(self):
        """测试 Refresh Token"""
        from litefs.auth.jwt import JWTManager
        
        manager = JWTManager('test-secret-key')
        
        payload = {'sub': 1}
        token = manager.create_refresh_token(payload)
        
        decoded = manager.decode_token(token)
        
        self.assertEqual(decoded['type'], 'refresh')
    
    def test_token_revocation(self):
        """测试 Token 撤销"""
        from litefs.auth.jwt import JWTManager
        
        manager = JWTManager('test-secret-key')
        
        token = manager.create_access_token({'sub': 1})
        
        decoded = manager.decode_token(token)
        self.assertIsNotNone(decoded)
        
        manager.revoke_token(token)
        
        decoded = manager.decode_token(token)
        self.assertIsNone(decoded)


class TestPassword(unittest.TestCase):
    """密码测试"""
    
    def test_hash_and_verify_password(self):
        """测试密码哈希和验证"""
        from litefs.auth.password import hash_password, verify_password
        
        password = 'test-password-123'
        password_hash = hash_password(password)
        
        self.assertIsNotNone(password_hash)
        self.assertNotEqual(password, password_hash)
        
        self.assertTrue(verify_password(password, password_hash))
        self.assertFalse(verify_password('wrong-password', password_hash))
    
    def test_generate_password(self):
        """测试生成密码"""
        from litefs.auth.password import generate_password
        
        password = generate_password(16)
        
        self.assertEqual(len(password), 16)
    
    def test_validate_password_strength(self):
        """测试密码强度验证"""
        from litefs.auth.password import validate_password_strength
        
        valid, errors = validate_password_strength('StrongPass123')
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)
        
        valid, errors = validate_password_strength('weak')
        self.assertFalse(valid)
        self.assertGreater(len(errors), 0)
    
    def test_check_password_breach_with_known_password(self):
        """测试已知泄露密码的检查"""
        from litefs.auth.password import check_password_breach, clear_breach_cache
        from unittest.mock import patch, MagicMock

        clear_breach_cache()

        # Mock HIBP API 响应
        # SHA1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
        # SHA1("123456")  = 7C4A8D09CA3762AF61E59520943DC26494F8941B
        def make_mock_resp(suffix, count):
            resp = MagicMock()
            resp.read.return_value = f"{suffix}:{count}\n".encode('utf-8')
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch('litefs.auth.password.urlopen',
                   return_value=make_mock_resp('1E4C9B93F3F0682250B6CF8331B7EE68FD8', 3730471)):
            is_breached = check_password_breach("password", use_cache=False)
            self.assertTrue(is_breached, "已知泄露密码 'password' 应该被检测到")

        clear_breach_cache()
        with patch('litefs.auth.password.urlopen',
                   return_value=make_mock_resp('D09CA3762AF61E59520943DC26494F8941B', 2582869)):
            is_breached = check_password_breach("123456", use_cache=False)
            self.assertTrue(is_breached, "已知泄露密码 '123456' 应该被检测到")

        clear_breach_cache()
    
    def test_check_password_breach_with_safe_password(self):
        """测试安全密码的检查"""
        from litefs.auth.password import check_password_breach, generate_password, clear_breach_cache
        from unittest.mock import patch, MagicMock

        clear_breach_cache()
        safe_password = generate_password(32)

        # Mock API 返回不包含该密码后缀的响应
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"AAAAAA:1\n"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('litefs.auth.password.urlopen', return_value=mock_resp):
            is_breached = check_password_breach(safe_password, use_cache=False)
            self.assertFalse(is_breached, "随机生成的强密码不应该被检测为泄露")

        clear_breach_cache()
    
    def test_check_password_breach_with_empty_password(self):
        """测试空密码的检查"""
        from litefs.auth.password import check_password_breach
        
        is_breached = check_password_breach("", use_cache=False)
        self.assertFalse(is_breached, "空密码不应该被检测为泄露")
        
        is_breached = check_password_breach(None, use_cache=False)
        self.assertFalse(is_breached, "None 密码不应该被检测为泄露")
    
    def test_check_password_breach_cache(self):
        """测试密码泄露检查缓存"""
        from litefs.auth.password import check_password_breach, clear_breach_cache
        from unittest.mock import patch, MagicMock

        clear_breach_cache()

        # Mock HIBP API 响应
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"1E4C9B93F3F0682250B6CF8331B7EE68FD8:3730471\n"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('litefs.auth.password.urlopen', return_value=mock_resp):
            is_breached1 = check_password_breach("password", use_cache=True)
            is_breached2 = check_password_breach("password", use_cache=True)
            self.assertEqual(is_breached1, is_breached2)
            self.assertTrue(is_breached1)

        clear_breach_cache()
    
    def test_get_breach_count(self):
        """测试获取密码泄露次数"""
        from litefs.auth.password import get_breach_count
        from unittest.mock import patch, MagicMock

        # Mock HIBP API 响应，避免依赖外部网络
        # SHA1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
        # prefix=5BAA6, suffix=1E4C9B93F3F0682250B6CF8331B7EE68FD8
        fake_response = (
            "1E4C9B93F3F0682250B6CF8331B7EE68FD8:3730471\n"
            "A3CDB1E1B4B3B4B3B3B3B3B3B3B3B3B3B3B3B3B3:5\n"
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = fake_response.encode('utf-8')
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch('litefs.auth.password.urlopen', return_value=mock_resp):
            count = get_breach_count("password")
            self.assertGreater(count, 0, "mocked API should return breach count > 0")

        # 测试空密码（不调用 API）
        count = get_breach_count("")
        self.assertEqual(count, 0, "空密码的泄露次数应该是 0")


class TestModels(unittest.TestCase):
    """模型测试"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.auth.models import User, Role, Permission, MemoryUserStore, set_user_store
        self.User = User
        self.Role = Role
        self.Permission = Permission
        Role._registry = {}
        Permission._registry = {}
        # 每个测试使用全新的内存存储
        self._store = MemoryUserStore()
        set_user_store(self._store)
    
    def test_create_user(self):
        """测试创建用户"""
        from litefs.auth.password import hash_password
        
        user = self._store.create(
            username='testuser',
            password_hash=hash_password('password123'),
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.id, 1)
    
    def test_get_user_by_username(self):
        """测试根据用户名获取用户"""
        from litefs.auth.password import hash_password
        
        self._store.create(
            username='testuser',
            password_hash=hash_password('password123'),
        )
        
        user = self._store.get_by_username('testuser')
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'testuser')
    
    def test_create_role_and_permission(self):
        """测试创建角色和权限"""
        perm = self.Permission.create('user:read', '查看用户')
        role = self.Role.create('user', '普通用户', [perm])
        
        self.assertIsNotNone(perm)
        self.assertIsNotNone(role)
        self.assertEqual(perm.name, 'user:read')
        self.assertEqual(role.name, 'user')
        self.assertTrue(role.has_permission('user:read'))
    
    def test_user_roles(self):
        """测试用户角色"""
        from litefs.auth.password import hash_password
        
        perm = self.Permission.create('user:read', '查看用户')
        role = self.Role.create('user', '普通用户', [perm])
        
        user = self._store.create(
            username='testuser',
            password_hash=hash_password('password123'),
            roles=[role],
        )
        
        self.assertTrue(user.has_role('user'))
        self.assertTrue(user.has_permission('user:read'))


class TestDecorators(unittest.TestCase):
    """装饰器测试"""
    
    def test_login_required(self):
        """测试登录验证装饰器"""
        from litefs.auth.middleware import login_required
        
        class MockRequest:
            pass
        
        @login_required
        def protected_view(request):
            return {'success': True}
        
        request = MockRequest()
        result = protected_view(request)
        
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[1], 401)
        
        request.user = type('User', (), {'username': 'test'})()
        result = protected_view(request)
        
        self.assertEqual(result, {'success': True})
    
    def test_role_required(self):
        """测试角色验证装饰器"""
        from litefs.auth.middleware import role_required
        
        class MockRole:
            name = 'admin'
        
        class MockUser:
            roles = [MockRole()]
        
        class MockRequest:
            pass
        
        @role_required('admin')
        def admin_view(request):
            return {'success': True}
        
        request = MockRequest()
        result = admin_view(request)
        
        self.assertEqual(result[1], 401)
        
        request.user = MockUser()
        result = admin_view(request)
        
        self.assertEqual(result, {'success': True})


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestJWT))
    suite.addTests(loader.loadTestsFromTestCase(TestPassword))
    suite.addTests(loader.loadTestsFromTestCase(TestModels))
    suite.addTests(loader.loadTestsFromTestCase(TestDecorators))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
