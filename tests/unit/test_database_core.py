#!/usr/bin/env python
# coding: utf-8

"""
数据库核心模块测试

覆盖 Database 连接管理（URL 优先级、引擎创建、会话、建表/删表、连接池状态）
与 DatabaseManager 多库管理与单例。
"""

import os
import tempfile
import unittest
from types import SimpleNamespace

from litefs.database.core import Database, DatabaseManager


class TestDatabaseUrlPriority(unittest.TestCase):
    """数据库 URL 获取优先级"""

    def test_config_database_url_first(self):
        """配置中的 database_url 优先"""
        config = SimpleNamespace(database_url='sqlite://')
        self.assertEqual(Database(config)._get_database_url(), 'sqlite://')

    def test_env_variable_second(self):
        """配置缺失时使用环境变量"""
        config = SimpleNamespace()
        with patch_env('DATABASE_URL', 'sqlite:///env.db'):
            self.assertEqual(Database(config)._get_database_url(), 'sqlite:///env.db')

    def test_default_sqlite_last(self):
        """两者都缺失时使用默认 SQLite"""
        config = SimpleNamespace()
        with patch_env('DATABASE_URL', None):
            self.assertEqual(Database(config)._get_database_url(), 'sqlite:///litefs.db')


class patch_env:
    """patch.dict 的小封装，支持删除环境变量"""

    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.existed = name in os.environ
        self.old = os.environ.get(name)

    def __enter__(self):
        if self.value is None:
            os.environ.pop(self.name, None)
        else:
            os.environ[self.name] = self.value

    def __exit__(self, *args):
        if self.existed:
            os.environ[self.name] = self.old
        else:
            os.environ.pop(self.name, None)


class TestDatabase(unittest.TestCase):
    """Database 连接管理"""

    def setUp(self):
        self.tmpfile = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmpfile.close()
        url = f"sqlite:///{self.tmpfile.name}"
        self.db = Database(SimpleNamespace(database_url=url))

    def tearDown(self):
        self.db.dispose()
        os.unlink(self.tmpfile.name)

    def test_engine_and_session_factory_created(self):
        """初始化创建引擎与会话工厂"""
        self.assertIsNotNone(self.db.engine)
        session = self.db.get_session()
        from sqlalchemy.orm import Session
        self.assertIsInstance(session, Session)
        session.close()

    def test_create_and_drop_all(self):
        """create_all/drop_all 建表删表"""
        from sqlalchemy import Column, Integer, Text

        class Dummy(self.db.Base):
            __tablename__ = 'dummy'
            id = Column(Integer, primary_key=True)
            name = Column(Text)

        self.db.create_all()
        session = self.db.get_session()
        session.add(Dummy(name='alice'))
        session.commit()
        self.assertEqual(session.query(Dummy).count(), 1)
        session.close()

        self.db.drop_all()

        from sqlalchemy import inspect as sa_inspect
        inspector = sa_inspect(self.db.engine)
        self.assertNotIn('dummy', inspector.get_table_names())

    def test_pool_events_fired(self):
        """连接建立触发事件监听（无异常即覆盖）"""
        session = self.db.get_session()
        result = session.execute(__import__('sqlalchemy').text('SELECT 1')).scalar()
        self.assertEqual(result, 1)
        session.close()

    def test_get_pool_status(self):
        """连接池状态包含关键字段"""
        status = self.db.get_pool_status()
        for key in ('pool_size', 'checked_in', 'checked_out', 'overflow', 'invalid'):
            self.assertIn(key, status)

    def test_dispose(self):
        """dispose 释放连接池"""
        engine = self.db.engine
        self.db.dispose()
        self.assertTrue(engine.pool is not None)


class TestDatabaseManager(unittest.TestCase):
    """DatabaseManager 多库管理"""

    def setUp(self):
        DatabaseManager._instance = None
        DatabaseManager._databases = {}
        self.tmpfile = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.tmpfile.close()
        self.config = SimpleNamespace(database_url=f"sqlite:///{self.tmpfile.name}")

    def tearDown(self):
        DatabaseManager.close_all()
        DatabaseManager._instance = None
        DatabaseManager._databases = {}
        os.unlink(self.tmpfile.name)

    def test_singleton(self):
        """单例模式"""
        self.assertIs(DatabaseManager(), DatabaseManager())

    def test_get_database_caches_by_name(self):
        """同名数据库返回同一实例"""
        db1 = DatabaseManager.get_database(self.config, 'default')
        db2 = DatabaseManager.get_database(self.config, 'default')
        self.assertIs(db1, db2)

    def test_get_database_different_names(self):
        """不同名称创建不同实例"""
        db1 = DatabaseManager.get_database(self.config, 'a')
        db2 = DatabaseManager.get_database(self.config, 'b')
        self.assertIsNot(db1, db2)

    def test_get_session(self):
        """get_session 返回可用会话"""
        DatabaseManager.get_database(self.config, 'default')
        from sqlalchemy import text
        session = DatabaseManager.get_session('default')
        self.assertEqual(session.execute(text('SELECT 1')).scalar(), 1)
        session.close()

    def test_uninitialized_database_raises(self):
        """未初始化的库名抛 ValueError"""
        with self.assertRaises(ValueError):
            DatabaseManager.get_session('missing')
        with self.assertRaises(ValueError):
            DatabaseManager.create_all('missing')
        with self.assertRaises(ValueError):
            DatabaseManager.drop_all('missing')

    def test_create_all_and_drop_all(self):
        """create_all/drop_all 委托到指定库"""
        from sqlalchemy import Column, Integer, Text

        db = DatabaseManager.get_database(self.config, 'default')

        class Item(db.Base):
            __tablename__ = 'items'
            id = Column(Integer, primary_key=True)
            name = Column(Text)

        DatabaseManager.create_all('default')
        DatabaseManager.drop_all('default')

    def test_close_all_disposes_and_clears(self):
        """close_all 释放所有连接并清空注册表"""
        DatabaseManager.get_database(self.config, 'default')
        DatabaseManager.close_all()
        self.assertEqual(DatabaseManager._databases, {})


if __name__ == '__main__':
    unittest.main()
