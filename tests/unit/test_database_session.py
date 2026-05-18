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
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

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

    def test_no_debug_print_in_source(self):
        """测试源码中不包含调试 print 语句（安全修复验证）"""
        import inspect
        from litefs.session.db import DatabaseSession
        source = inspect.getsource(DatabaseSession)
        self.assertNotIn('print(f"调试', source, "DatabaseSession 不应包含调试 print 语句")
        self.assertNotIn("调试：数据库路径", source, "不应泄露数据库路径")
        self.assertNotIn("调试：存储 Session", source, "不应泄露 Session 数据")
        self.assertNotIn("调试：查询 Session", source, "不应泄露查询结果")
        self.assertNotIn("调试：表", source, "不应泄露表结构")

    def test_no_print_output_on_init(self):
        """测试初始化时不产生 print 输出"""
        import io
        import sys
        import tempfile
        tmp_dir = tempfile.mkdtemp()
        try:
            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured
            try:
                store = DatabaseSession(db_path=os.path.join(tmp_dir, "test_no_print.db"))
                store.close()
            finally:
                sys.stdout = old_stdout
            output = captured.getvalue()
            self.assertEqual(output, "", "初始化时不应有任何 print 输出")
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_no_print_output_on_save(self):
        """测试保存 Session 时不产生 print 输出"""
        import io
        import sys
        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            session = self.session_store.create()
            session.data["sensitive"] = "password123"
            self.session_store.save(session)
        finally:
            sys.stdout = old_stdout
        output = captured.getvalue()
        self.assertEqual(output, "", "保存 Session 时不应有任何 print 输出")


class TestDatabaseSessionConnectionPool(unittest.TestCase):
    """测试 DatabaseSession 的连接池功能"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_pool.db")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_pool_parameters(self):
        """测试默认连接池参数"""
        store = DatabaseSession(db_path=self.db_path)
        self.assertEqual(store._pool_size, 5)
        self.assertEqual(store._max_overflow, 10)
        self.assertEqual(store._pool_timeout, 30)
        self.assertEqual(store._pool_recycle, 3600)
        self.assertTrue(store._use_pool)
        store.close()

    def test_custom_pool_parameters(self):
        """测试自定义连接池参数"""
        store = DatabaseSession(
            db_path=self.db_path,
            pool_size=10,
            max_overflow=20,
            pool_timeout=60,
            pool_recycle=1800
        )
        self.assertEqual(store._pool_size, 10)
        self.assertEqual(store._max_overflow, 20)
        self.assertEqual(store._pool_timeout, 60)
        self.assertEqual(store._pool_recycle, 1800)
        store.close()

    def test_pool_disabled(self):
        """测试禁用连接池"""
        store = DatabaseSession(
            db_path=self.db_path,
            use_pool=False
        )
        self.assertFalse(store._use_pool)
        self.assertIsNone(store._engine)
        store.close()

    def test_pool_operations(self):
        """测试连接池基本操作"""
        from litefs.session import Session
        
        store = DatabaseSession(
            db_path=self.db_path,
            pool_size=3,
            max_overflow=5
        )
        
        # 创建并保存 Session
        session = Session()
        session['key'] = 'value'
        store.put(session.id, session)
        
        # 获取 Session
        retrieved = store.get(session.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['key'], 'value')
        
        # 检查 Session 是否存在
        self.assertTrue(store.exists(session.id))
        
        # 删除 Session
        store.delete(session.id)
        self.assertFalse(store.exists(session.id))
        
        store.close()

    def test_pool_concurrent_access(self):
        """测试连接池并发访问"""
        from litefs.session import Session
        import threading
        import time
        
        store = DatabaseSession(
            db_path=self.db_path,
            pool_size=5,
            max_overflow=10
        )
        
        # 创建多个 Session
        sessions = []
        for i in range(10):
            session = Session()
            session['id'] = i
            store.put(session.id, session)
            sessions.append(session)
        
        # 并发获取 Session
        results = []
        errors = []
        
        def get_session(session_id):
            try:
                session = store.get(session_id)
                if session:
                    results.append(session['id'])
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for session in sessions:
            t = threading.Thread(target=get_session, args=(session.id,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证结果
        self.assertEqual(len(errors), 0, f"并发访问出错: {errors}")
        self.assertEqual(len(results), 10)
        
        store.close()

    def test_pool_memory_database(self):
        """测试内存数据库连接池"""
        from litefs.session import Session
        
        # 内存数据库使用 StaticPool
        store = DatabaseSession(db_path=":memory:")
        
        session = Session()
        session['key'] = 'value'
        store.put(session.id, session)
        
        retrieved = store.get(session.id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['key'], 'value')
        
        store.close()


if __name__ == "__main__":
    unittest.main()