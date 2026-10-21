#!/usr/bin/env python
# coding: utf-8

"""
用户模型与存储后端测试

覆盖 Permission / Role / User 数据模型、注册表、MemoryUserStore
与全局用户存储切换。
"""

import unittest

from litefs.auth.models import (
    MemoryUserStore,
    Permission,
    Role,
    User,
    get_user_store,
    init_default_roles_and_permissions,
    set_user_store,
)


class TestPermission(unittest.TestCase):
    """Permission 模型与注册表"""

    def test_create_with_default_description(self):
        """创建权限时描述默认为空"""
        perm = Permission.create('test:perm-default')
        self.assertEqual(perm.name, 'test:perm-default')
        self.assertEqual(perm.description, '')

    def test_registry_lookup(self):
        """创建后可通过名称从注册表获取"""
        perm = Permission.create('test:perm-lookup', '测试权限')
        self.assertIs(Permission.get_by_name('test:perm-lookup'), perm)

    def test_get_by_name_missing(self):
        """未注册名称返回 None"""
        self.assertIsNone(Permission.get_by_name('test:perm-not-exists'))


class TestRole(unittest.TestCase):
    """Role 模型"""

    def setUp(self):
        self.read_perm = Permission.create('test:role-read')
        self.write_perm = Permission.create('test:role-write')

    def test_create_with_permissions(self):
        """创建角色可携带权限列表"""
        role = Role.create('test:editor', '编辑', [self.read_perm])
        self.assertEqual(role.name, 'test:editor')
        self.assertEqual(role.permissions, [self.read_perm])
        self.assertIs(Role.get_by_name('test:editor'), role)

    def test_add_permission_no_duplicate(self):
        """重复添加权限不会产生重复项"""
        role = Role.create('test:adder')
        role.add_permission(self.read_perm)
        role.add_permission(self.read_perm)
        self.assertEqual(role.permissions, [self.read_perm])

    def test_remove_permission(self):
        """移除权限"""
        role = Role.create('test:remover', permissions=[self.read_perm])
        role.remove_permission(self.read_perm)
        self.assertEqual(role.permissions, [])
        role.remove_permission(self.read_perm)

    def test_has_permission(self):
        """按名称检查权限"""
        role = Role.create('test:checker', permissions=[self.read_perm])
        self.assertTrue(role.has_permission('test:role-read'))
        self.assertFalse(role.has_permission('test:role-write'))


class TestUser(unittest.TestCase):
    """User 模型"""

    def setUp(self):
        self.admin_role = Role.create('test:admin-role')
        self.user_role = Role.create('test:user-role', permissions=[
            Permission.create('test:user-read'),
        ])

    def test_add_and_remove_role(self):
        """添加与移除角色，重复添加去重"""
        user = User(id=1, username='alice', password_hash='hash')
        user.add_role(self.user_role)
        user.add_role(self.user_role)
        self.assertEqual(user.roles, [self.user_role])
        user.remove_role(self.user_role)
        self.assertEqual(user.roles, [])
        user.remove_role(self.user_role)

    def test_has_role(self):
        """按名称检查角色"""
        user = User(id=1, username='alice', password_hash='hash', roles=[self.admin_role])
        self.assertTrue(user.has_role('test:admin-role'))
        self.assertFalse(user.has_role('test:user-role'))

    def test_has_permission_across_roles(self):
        """跨角色检查权限"""
        user = User(id=1, username='alice', password_hash='hash', roles=[self.user_role])
        self.assertTrue(user.has_permission('test:user-read'))
        self.assertFalse(user.has_permission('test:user-write'))

    def test_defaults(self):
        """默认字段值"""
        user = User(id=2, username='bob', password_hash='hash')
        self.assertIsNone(user.email)
        self.assertTrue(user.is_active)
        self.assertEqual(user.roles, [])


class TestMemoryUserStore(unittest.TestCase):
    """MemoryUserStore 内存存储"""

    def setUp(self):
        self.store = MemoryUserStore()

    def test_create_assigns_incremental_ids(self):
        """创建用户自动分配递增 ID"""
        user1 = self.store.create('alice', 'hash1')
        user2 = self.store.create('bob', 'hash2', email='bob@example.com')
        self.assertEqual(user1.id, 1)
        self.assertEqual(user2.id, 2)
        self.assertEqual(user2.email, 'bob@example.com')

    def test_create_with_roles(self):
        """创建用户可携带角色"""
        role = Role.create('test:store-role')
        user = self.store.create('alice', 'hash', roles=[role])
        self.assertEqual(user.roles, [role])

    def test_get_by_id_and_username(self):
        """按 ID 与用户名查询"""
        user = self.store.create('alice', 'hash')
        self.assertIs(self.store.get_by_id(user.id), user)
        self.assertIs(self.store.get_by_username('alice'), user)
        self.assertIsNone(self.store.get_by_id(999))
        self.assertIsNone(self.store.get_by_username('nobody'))

    def test_delete(self):
        """删除用户同时清理用户名索引"""
        user = self.store.create('alice', 'hash')
        self.assertTrue(self.store.delete(user.id))
        self.assertIsNone(self.store.get_by_id(user.id))
        self.assertIsNone(self.store.get_by_username('alice'))
        self.assertFalse(self.store.delete(user.id))

    def test_list_all(self):
        """list_all 返回全部用户"""
        self.store.create('alice', 'hash')
        self.store.create('bob', 'hash')
        users = self.store.list_all()
        self.assertEqual(len(users), 2)
        self.assertEqual({u.username for u in users}, {'alice', 'bob'})


class TestUserStoreSwitching(unittest.TestCase):
    """全局用户存储切换"""

    def setUp(self):
        self._original = get_user_store()

    def tearDown(self):
        set_user_store(self._original)

    def test_default_store_is_memory(self):
        """默认存储为 MemoryUserStore 单例"""
        self.assertIsInstance(get_user_store(), MemoryUserStore)
        self.assertIs(get_user_store(), get_user_store())

    def test_set_user_store(self):
        """set_user_store 可切换全局存储"""
        custom = MemoryUserStore()
        set_user_store(custom)
        self.assertIs(get_user_store(), custom)


class TestInitDefaultRolesAndPermissions(unittest.TestCase):
    """默认角色与权限初始化"""

    def test_returns_user_and_admin_roles(self):
        """返回 user 与 admin 两个角色，权限挂载正确"""
        user_role, admin_role = init_default_roles_and_permissions()
        self.assertEqual(user_role.name, 'user')
        self.assertTrue(user_role.has_permission('user:read'))
        self.assertEqual(admin_role.name, 'admin')
        self.assertTrue(admin_role.has_permission('admin:manage_users'))
        self.assertIsNotNone(Permission.get_by_name('user:delete'))


if __name__ == '__main__':
    unittest.main()
