#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RedisSession 纯 Mock 单元测试

不依赖真实 Redis 服务，覆盖注入客户端、连接检测、setex/set 分支、
SCAN 迭代删除、损坏数据清理与上下文管理等分支。
"""

import sys
from unittest.mock import MagicMock

import pytest

from litefs.session.redis import RedisSession
from litefs.session.session import Session


@pytest.fixture
def client():
    """模拟 Redis 客户端（内置简单键值存储）"""
    redis = MagicMock()
    redis._store = {}
    redis.ping.return_value = True
    redis.exists.side_effect = lambda k: 1 if k in redis._store else 0
    redis.get.side_effect = lambda k: redis._store.get(k)
    redis.delete.side_effect = lambda *ks: sum(redis._store.pop(k, None) is not None for k in ks)
    redis.expire.return_value = True
    redis.ttl.side_effect = lambda k: -2 if k not in redis._store else 100
    redis.scan.side_effect = lambda cursor=0, match=None, count=100: (
        0,
        [k for k in redis._store if _fnmatch(k, match or '*')],
    )
    redis.set.side_effect = _make_setter(redis)
    redis.setex.side_effect = _make_setter(redis)
    return redis


def _make_setter(redis):
    """构造写入回调：setex(key, ttl, value) / set(key, value)"""

    def _set(key, *args):
        redis._store[key] = args[-1]

    return _set


def _fnmatch(key, pattern):
    """简化版通配符匹配（仅支持尾部 *）"""
    if pattern.endswith('*'):
        return key.startswith(pattern[:-1])
    return key == pattern


@pytest.fixture
def store(client):
    """注入模拟客户端的 RedisSession"""
    return RedisSession(redis_client=client, key_prefix='t:s:')


class TestInit:
    """初始化测试"""

    def test_injected_client_skips_connection_params(self, client):
        """注入客户端时忽略连接参数"""
        session = RedisSession(redis_client=client, host='elsewhere', port=1)
        assert session._redis is client

    def test_ping_failure_raises_connection_error(self):
        """ping 失败转换为 ConnectionError"""
        client = MagicMock()
        client.ping.side_effect = OSError('refused')
        with pytest.raises(ConnectionError, match='无法连接到 Redis'):
            RedisSession(redis_client=client)

    def test_import_error_without_redis_lib(self, monkeypatch):
        """redis-py 不可用时抛出带安装指引的 ImportError"""
        monkeypatch.setitem(sys.modules, 'redis', None)
        with pytest.raises(ImportError, match='pip install redis'):
            RedisSession(host='localhost')

    def test_password_included_in_connection_params(self, monkeypatch):
        """密码参数传入连接参数"""
        captured = {}

        fake_redis = MagicMock()
        monkeypatch.setitem(sys.modules, 'redis', fake_redis)
        fake_redis.Redis.side_effect = lambda **kw: captured.update(kw) or MagicMock()

        RedisSession(host='h', port=1234, db=2, password='secret')
        assert captured['password'] == 'secret'
        assert captured['host'] == 'h'
        assert captured['port'] == 1234
        assert captured['db'] == 2
        assert captured['decode_responses'] is True

    def test_no_password_omits_key(self, monkeypatch):
        """未提供密码时连接参数不含 password 键"""
        captured = {}

        fake_redis = MagicMock()
        monkeypatch.setitem(sys.modules, 'redis', fake_redis)
        fake_redis.Redis.side_effect = lambda **kw: captured.update(kw) or MagicMock()

        RedisSession()
        assert 'password' not in captured


class TestPutGet:
    """存取测试"""

    def test_put_with_positive_ttl_uses_setex(self, client, store):
        """过期时间 >0 时使用 setex"""
        session = Session('p1')
        session['k'] = 'v'
        store.put('p1', session)
        client.setex.assert_called_once()
        assert client.set.called is False

    def test_put_with_zero_ttl_uses_set(self, client):
        """过期时间 <=0 时使用 set（永不过期）"""
        store = RedisSession(redis_client=client, expiration_time=0)
        store.put('p0', Session('p0'))
        client.set.assert_called_once()
        assert client.setex.called is False

    def test_put_serialization_error(self, store):
        """不可序列化数据抛 ValueError"""
        session = Session('bad')
        session['obj'] = object()
        with pytest.raises(ValueError, match='无法序列化'):
            store.put('bad', session)

    def test_get_missing_returns_none(self, store):
        """键不存在返回 None"""
        assert store.get('missing') is None

    def test_get_roundtrip(self, store):
        """存取往返保持数据一致"""
        session = Session('rt')
        session['user'] = '王五'
        session['n'] = 7
        store.put('rt', session)
        loaded = store.get('rt')
        assert loaded['user'] == '王五'
        assert loaded['n'] == 7

    def test_get_corrupted_data_deletes(self, client, store):
        """损坏数据被删除并返回 None"""
        client._store['t:s:corrupt'] = '{bad-json'
        assert store.get('corrupt') is None
        assert 't:s:corrupt' not in client._store


class TestScanOperations:
    """SCAN 相关操作测试"""

    def test_scan_keys_iterates(self, store):
        """_scan_keys 返回匹配键"""
        store.put('s1', Session('s1'))
        store.put('s2', Session('s2'))
        keys = store._scan_keys('t:s:*')
        assert set(keys) == {'t:s:s1', 't:s:s2'}

    def test_delete_pattern_removes_matching(self, client, store):
        """delete_pattern 删除匹配键并返回数量"""
        store.put('d1', Session('d1'))
        store.put('d2', Session('d2'))
        count = store.delete_pattern('d*')
        assert count == 2
        assert store.exists('d1') is False

    def test_delete_pattern_no_match_returns_zero(self, store):
        """无匹配键时返回 0"""
        assert store.delete_pattern('nope*') == 0

    def test_clear_removes_prefixed_keys(self, client, store):
        """clear 删除全部带前缀键"""
        store.put('c1', Session('c1'))
        store.put('c2', Session('c2'))
        store.clear()
        assert len(client._store) == 0

    def test_len_counts_prefixed_keys(self, store):
        """__len__ 统计带前缀键数量"""
        assert len(store) == 0
        store.put('l1', Session('l1'))
        store.put('l2', Session('l2'))
        assert len(store) == 2


class TestMiscOperations:
    """辅助方法测试"""

    def test_exists(self, store):
        """exists 反映键存在性"""
        assert store.exists('e1') is False
        store.put('e1', Session('e1'))
        assert store.exists('e1') is True

    def test_expire_delegates(self, client, store):
        """expire 委托给客户端 expire"""
        store.put('x1', Session('x1'))
        assert store.expire('x1', 60) is True
        client.expire.assert_called_once_with('t:s:x1', 60)

    def test_ttl_delegates(self, store):
        """ttl 委托给客户端 ttl"""
        assert store.ttl('nope') == -2
        store.put('t1', Session('t1'))
        assert store.ttl('t1') == 100

    def test_close_swallows_errors(self, client):
        """close 吞掉客户端异常"""
        client.close.side_effect = OSError('already closed')
        store = RedisSession(redis_client=client)
        store.close()

    def test_context_manager_closes(self, client):
        """上下文管理器退出时自动 close"""
        with RedisSession(redis_client=client) as store:
            assert store is not None
        client.close.assert_called_once()

    def test_create_returns_bound_session(self, store):
        """create 返回绑定存储的 Session"""
        session = store.create()
        assert isinstance(session, Session)
        assert session.store is store

    def test_save_delegates_to_put(self, store):
        """save 按 Session.id 调用 put"""
        session = Session('sv')
        session['k'] = 'v'
        store.save(session)
        assert store.get('sv')['k'] == 'v'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
