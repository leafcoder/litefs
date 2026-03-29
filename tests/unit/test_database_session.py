#!/usr/bin/env python
# coding: utf-8

import unittest
import os
import tempfile
from litefs.session import DatabaseSession, Session


class TestDatabaseSession(unittest.TestCase):
    """测试 DatabaseSession"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_sessions.db")
        self.session_store = DatabaseSession(db_path=self.db_path)

    def tearDown(self):
        """测试后清理"""
        self.session_store.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_create_session(self):
        """测试创建 Session"""
        session = self.session_store.create()
        self.assertIsInstance(session, Session)
        self.assertIsNotNone(session.id)
        self.assertEqual(session.data, {})

    def test_save_and_get_session(self):
        """测试保存和获取 Session"""
        session = self.session_store.create()
        session.data["user_id"] = 123
        session.data["username"] = "test_user"
        
        self.session_store.save(session)
        
        retrieved_session = self.session_store.get(session.id)
        self.assertIsNotNone(retrieved_session)
        if retrieved_session:
            self.assertEqual(retrieved_session.id, session.id)
            self.assertEqual(retrieved_session.data["user_id"], 123)
            self.assertEqual(retrieved_session.data["username"], "test_user")

    def test_get_nonexistent_session(self):
        """测试获取不存在的 Session"""
        session = self.session_store.get("nonexistent_id")
        self.assertIsNone(session)

    def test_delete_session(self):
        """测试删除 Session"""
        session = self.session_store.create()
        session.data["test"] = "value"
        self.session_store.save(session)
        
        self.session_store.delete(session.id)
        
        retrieved_session = self.session_store.get(session.id)
        self.assertIsNone(retrieved_session)

    def test_exists_session(self):
        """测试检查 Session 是否存在"""
        session = self.session_store.create()
        self.session_store.save(session)
        
        self.assertTrue(self.session_store.exists(session.id))
        self.assertFalse(self.session_store.exists("nonexistent_id"))

    def test_expire_session(self):
        """测试设置 Session 过期时间"""
        session = self.session_store.create()
        self.session_store.save(session)
        
        self.assertTrue(self.session_store.expire(session.id, 3600))
        self.assertFalse(self.session_store.expire("nonexistent_id", 3600))

    def test_ttl_session(self):
        """测试获取 Session 剩余过期时间"""
        session = self.session_store.create()
        self.session_store.save(session)
        
        ttl = self.session_store.ttl(session.id)
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 3600)

    def test_clear_sessions(self):
        """测试清空所有 Session"""
        session1 = self.session_store.create()
        session2 = self.session_store.create()
        self.session_store.save(session1)
        self.session_store.save(session2)
        
        self.session_store.clear()
        
        self.assertIsNone(self.session_store.get(session1.id))
        self.assertIsNone(self.session_store.get(session2.id))

    def test_len_sessions(self):
        """测试获取 Session 数量"""
        session1 = self.session_store.create()
        session2 = self.session_store.create()
        self.session_store.save(session1)
        self.session_store.save(session2)
        
        self.assertEqual(len(self.session_store), 2)

    def test_context_manager(self):
        """测试上下文管理器"""
        with DatabaseSession(db_path=self.db_path) as session_store:
            session = session_store.create()
            session.data["test"] = "value"
            session_store.save(session)
            
            retrieved_session = session_store.get(session.id)
            self.assertIsNotNone(retrieved_session)
            if retrieved_session:
                self.assertEqual(retrieved_session.data["test"], "value")

    def test_session_data_persistence(self):
        """测试 Session 数据持久化"""
        session = self.session_store.create()
        session.data["user_id"] = 123
        session.data["cart"] = ["item1", "item2"]
        session.data["preferences"] = {"theme": "dark", "language": "zh"}
        
        self.session_store.save(session)
        
        retrieved_session = self.session_store.get(session.id)
        self.assertIsNotNone(retrieved_session)
        if retrieved_session:
            self.assertEqual(retrieved_session.data["user_id"], 123)
            self.assertEqual(retrieved_session.data["cart"], ["item1", "item2"])
            self.assertEqual(retrieved_session.data["preferences"], {"theme": "dark", "language": "zh"})


if __name__ == "__main__":
    unittest.main()