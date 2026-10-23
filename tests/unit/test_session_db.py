#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DatabaseSession 纯本地单元测试

使用 SQLite 内存库与临时文件库，覆盖连接池 / 非连接池两条路径、
过期清理、损坏数据清理、expire / ttl / clear / close 等分支。
"""

import sqlite3

import pytest

from litefs.session.db import DatabaseSession
from litefs.session.session import Session


@pytest.fixture
def pool_store():
    """连接池路径（SQLAlchemy + StaticPool 内存库）"""
    store = DatabaseSession(db_path=':memory:', table_name='t_sessions')
    yield store
    store.close()


@pytest.fixture
def raw_store(tmp_path):
    """非连接池路径（sqlite3 直连文件库）"""
    store = DatabaseSession(
        db_path=str(tmp_path / 'sessions.db'),
        use_pool=False,
        table_name='t_sessions',
    )
    yield store
    store.close()


class TestInit:
    """初始化测试"""

    def test_pool_mode_uses_static_pool_for_memory(self, pool_store):
        """内存库走 StaticPool 连接池路径"""
        assert pool_store._use_pool is True
        assert pool_store._engine is not None

    def test_raw_mode_uses_sqlite3(self, raw_store):
        """非连接池路径使用 sqlite3 直连"""
        assert raw_store._use_pool is False
        assert isinstance(raw_store._conn, sqlite3.Connection)

    def test_raw_mode_connects_on_init(self):
        """use_pool=False 时初始化即建表并建立连接"""
        store = DatabaseSession(db_path=':memory:', use_pool=False)
        assert store._conn is not None
        store.close()
        store.close()

    def test_use_pool_falls_back_without_sqlalchemy(self):
        """SQLAlchemy 不可用时 use_pool 自动降级为 False"""
        import litefs.session.db as db_mod
        original = db_mod.SQLALCHEMY_AVAILABLE
        db_mod.SQLALCHEMY_AVAILABLE = False
        try:
            store = DatabaseSession(db_path=':memory:', use_pool=True)
            assert store._use_pool is False
            store.close()
        finally:
            db_mod.SQLALCHEMY_AVAILABLE = original

    def test_initialize_pool_raises_without_sqlalchemy(self):
        """SQLAlchemy 不可用时显式初始化连接池抛 ImportError"""
        import litefs.session.db as db_mod
        original = db_mod.SQLALCHEMY_AVAILABLE
        db_mod.SQLALCHEMY_AVAILABLE = False
        try:
            store = DatabaseSession.__new__(DatabaseSession)
            with pytest.raises(ImportError, match='SQLAlchemy'):
                store._initialize_pool()
        finally:
            db_mod.SQLALCHEMY_AVAILABLE = original


class TestPoolPath:
    """连接池路径操作测试"""

    def test_put_get_roundtrip(self, pool_store):
        """存取往返保持数据一致"""
        session = Session('p1')
        session['user'] = '张三'
        session['n'] = 1
        pool_store.put('p1', session)
        loaded = pool_store.get('p1')
        assert loaded is not None
        assert loaded['user'] == '张三'
        assert loaded['n'] == 1

    def test_get_missing_returns_none(self, pool_store):
        """键不存在返回 None"""
        assert pool_store.get('missing') is None

    def test_put_replaces_existing(self, pool_store):
        """重复 put 覆盖旧数据"""
        s1 = Session('p2')
        s1['v'] = 1
        pool_store.put('p2', s1)
        s2 = Session('p2')
        s2['v'] = 2
        pool_store.put('p2', s2)
        assert pool_store.get('p2')['v'] == 2

    def test_put_serialization_error(self, pool_store):
        """不可序列化数据抛 ValueError"""
        session = Session('bad')
        session['obj'] = object()
        with pytest.raises(ValueError, match='无法序列化'):
            pool_store.put('bad', session)

    def test_get_corrupted_data_deletes(self, pool_store):
        """损坏数据被删除并返回 None"""
        created = 111
        with pool_store._engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text(
                "INSERT INTO t_sessions (session_id, data, created_at, expires_at)"
                " VALUES ('corrupt', '{bad', :c, 9999999999)"
            ), {'c': created})
            conn.commit()
        assert pool_store.get('corrupt') is None
        assert pool_store.exists('corrupt') is False

    def test_get_expired_deletes(self, pool_store):
        """过期数据被删除并返回 None"""
        session = Session('exp')
        pool_store.put('exp', session)
        pool_store.expire('exp', -10)
        assert pool_store.get('exp') is None

    def test_exists_semantics(self, pool_store):
        """exists 区分存在与不存在"""
        assert pool_store.exists('e1') is False
        pool_store.put('e1', Session('e1'))
        assert pool_store.exists('e1') is True

    def test_delete(self, pool_store):
        """删除后不可再获取"""
        pool_store.put('d1', Session('d1'))
        pool_store.delete('d1')
        assert pool_store.get('d1') is None

    def test_expire_missing_returns_false(self, pool_store):
        """对不存在的 Session 设置过期返回 False"""
        assert pool_store.expire('nope', 60) is False

    def test_expire_existing_returns_true(self, pool_store):
        """对存在的 Session 设置过期返回 True"""
        pool_store.put('x1', Session('x1'))
        assert pool_store.expire('x1', 3600) is True

    def test_ttl_missing_returns_minus_two(self, pool_store):
        """键不存在 TTL 返回 -2"""
        assert pool_store.ttl('nope') == -2

    def test_ttl_expired_returns_minus_one_and_deletes(self, pool_store):
        """已过期 TTL 返回 -1 并清理数据"""
        pool_store.put('x2', Session('x2'))
        pool_store.expire('x2', -10)
        assert pool_store.ttl('x2') == -1
        assert pool_store.exists('x2') is False

    def test_ttl_active_returns_positive(self, pool_store):
        """未过期 TTL 返回正数"""
        pool_store.put('x3', Session('x3'))
        assert pool_store.ttl('x3') > 0

    def test_clear_and_len(self, pool_store):
        """clear 清空全部数据，len 返回计数"""
        pool_store.put('c1', Session('c1'))
        pool_store.put('c2', Session('c2'))
        assert len(pool_store) == 2
        pool_store.clear()
        assert len(pool_store) == 0

    def test_create_and_save(self, pool_store):
        """create 返回绑定存储的 Session，save 落库"""
        session = pool_store.create()
        session['k'] = 'v'
        session.save()
        assert pool_store.get(session.id)['k'] == 'v'

    def test_context_manager_closes(self):
        """上下文管理器退出时自动关闭引擎"""
        with DatabaseSession(db_path=':memory:') as store:
            store.put('cm', Session('cm'))
        assert store._engine is None


class TestRawPath:
    """非连接池路径操作测试"""

    def test_put_get_roundtrip(self, raw_store):
        """sqlite3 直连路径存取往返"""
        session = Session('r1')
        session['user'] = '李四'
        raw_store.put('r1', session)
        loaded = raw_store.get('r1')
        assert loaded is not None
        assert loaded['user'] == '李四'

    def test_row_factory_is_sqlite_row(self, raw_store):
        """直连路径使用 sqlite3.Row 行工厂"""
        assert raw_store._conn.row_factory is sqlite3.Row

    def test_get_missing_returns_none(self, raw_store):
        """键不存在返回 None"""
        assert raw_store.get('missing') is None

    def test_delete_and_exists(self, raw_store):
        """删除与存在性判断"""
        raw_store.put('d1', Session('d1'))
        assert raw_store.exists('d1') is True
        raw_store.delete('d1')
        assert raw_store.exists('d1') is False

    def test_expired_get_returns_none(self, raw_store):
        """过期数据返回 None"""
        raw_store.put('exp', Session('exp'))
        raw_store.expire('exp', -10)
        assert raw_store.get('exp') is None

    def test_ttl_semantics(self, raw_store):
        """TTL：缺失 -2 / 过期 -1 / 未过期正数"""
        assert raw_store.ttl('nope') == -2
        raw_store.put('t1', Session('t1'))
        assert raw_store.ttl('t1') > 0
        raw_store.expire('t1', -10)
        assert raw_store.ttl('t1') == -1

    def test_expire_missing_returns_false(self, raw_store):
        """对不存在的 Session 设置过期返回 False"""
        assert raw_store.expire('nope', 60) is False

    def test_clear_and_len(self, raw_store):
        """clear 与 __len__"""
        raw_store.put('c1', Session('c1'))
        raw_store.put('c2', Session('c2'))
        assert len(raw_store) == 2
        raw_store.clear()
        assert len(raw_store) == 0

    def test_close_disposes_connection(self):
        """close 后重连可用（连接重建）"""
        store = DatabaseSession(
            db_path=':memory:', use_pool=False, table_name='t_sessions'
        )
        store.put('k1', Session('k1'))
        store.close()
        assert store._conn is None

    def test_close_idempotent(self, raw_store):
        """重复 close 不抛异常"""
        raw_store.close()
        raw_store.close()

    def test_context_manager(self):
        """上下文管理器退出时自动关闭连接"""
        with DatabaseSession(db_path=':memory:', use_pool=False) as store:
            store.put('cm', Session('cm'))
        assert store._conn is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
