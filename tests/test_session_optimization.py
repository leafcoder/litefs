#!/usr/bin/env python
# coding: utf-8

"""
Session 优化测试
"""

import unittest
import time
import tempfile
import os


class TestCachedSessionStore(unittest.TestCase):
    """测试带缓存的 Session 存储"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.session import DatabaseSession, CachedSessionStore
        from litefs.cache import MemoryCache
        
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        
        # 创建底层存储
        self.store = DatabaseSession(db_path=self.db_path)
        
        # 创建缓存
        self.cache = MemoryCache()
        
        # 创建带缓存的存储
        self.cached_store = CachedSessionStore(self.store, self.cache)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_from_cache(self):
        """测试从缓存获取 Session"""
        from litefs.session import Session
        
        # 创建并保存 Session
        session = Session()
        session['key'] = 'value'
        self.cached_store.put(session.id, session)
        
        # 第一次获取（会写入缓存）
        result1 = self.cached_store.get(session.id)
        self.assertIsNotNone(result1)
        self.assertEqual(result1['key'], 'value')
        
        # 第二次获取（从缓存获取）
        result2 = self.cached_store.get(session.id)
        self.assertIsNotNone(result2)
        self.assertEqual(result2['key'], 'value')
    
    def test_get_from_store(self):
        """测试从底层存储获取 Session（缓存未命中）"""
        from litefs.session import Session
        
        # 创建并保存 Session
        session = Session()
        session['key'] = 'value'
        self.store.put(session.id, session)  # 直接存储到底层
        
        # 从带缓存的存储获取
        result = self.cached_store.get(session.id)
        self.assertIsNotNone(result)
        self.assertEqual(result['key'], 'value')
    
    def test_delete(self):
        """测试删除 Session"""
        from litefs.session import Session
        
        # 创建并保存 Session
        session = Session()
        session['key'] = 'value'
        self.cached_store.put(session.id, session)
        
        # 删除 Session
        self.cached_store.delete(session.id)
        
        # 确认已删除
        result = self.cached_store.get(session.id)
        self.assertIsNone(result)
    
    def test_performance(self):
        """测试性能提升"""
        from litefs.session import Session
        
        # 创建并保存 Session
        session = Session()
        session['key'] = 'value'
        self.cached_store.put(session.id, session)
        
        # 测试多次获取的性能
        start = time.time()
        for _ in range(100):
            self.cached_store.get(session.id)
        end = time.time()
        
        # 应该很快（主要从缓存获取）
        self.assertLess(end - start, 0.1, "多次获取应该很快")
    
    def test_cache_miss_then_hit(self):
        """测试缓存未命中后命中"""
        from litefs.session import Session
        
        # 创建并保存 Session（只保存到底层）
        session = Session()
        session['key'] = 'value'
        self.store.put(session.id, session)
        
        # 第一次获取（缓存未命中，从底层获取并写入缓存）
        result1 = self.cached_store.get(session.id)
        self.assertIsNotNone(result1)
        self.assertEqual(result1['key'], 'value')
        
        # 第二次获取（缓存命中）
        result2 = self.cached_store.get(session.id)
        self.assertIsNotNone(result2)
        self.assertEqual(result2['key'], 'value')


class TestDatabaseSessionOptimization(unittest.TestCase):
    """测试 DatabaseSession 优化"""
    
    def setUp(self):
        """测试前准备"""
        from litefs.session import DatabaseSession
        
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test.db')
        
        # 创建 DatabaseSession
        self.store = DatabaseSession(db_path=self.db_path)
    
    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_performance(self):
        """测试 DatabaseSession 查询性能"""
        from litefs.session import Session
        
        # 创建并保存 Session
        session = Session()
        session['key'] = 'value'
        self.store.put(session.id, session)
        
        # 测试多次查询的性能
        start = time.time()
        for _ in range(100):
            self.store.get(session.id)
        end = time.time()
        
        # 应该在合理时间内完成
        self.assertLess(end - start, 1.0, "数据库查询应该很快")
    
    def test_index_optimization(self):
        """测试索引优化"""
        from litefs.session import Session
        
        # 创建多个 Session
        sessions = []
        for i in range(100):
            session = Session()
            session['key'] = f'value_{i}'
            sessions.append(session)
            self.store.put(session.id, session)
        
        # 测试随机查询性能
        import random
        start = time.time()
        for _ in range(100):
            session_id = random.choice(sessions).id
            self.store.get(session_id)
        end = time.time()
        
        # 应该很快（有索引）
        self.assertLess(end - start, 1.0, "索引优化后查询应该很快")


if __name__ == '__main__':
    unittest.main()
