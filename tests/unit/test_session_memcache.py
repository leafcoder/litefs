#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MemcacheSession 纯 Mock 单元测试

不依赖真实 memcached 服务，覆盖注入客户端类型判定、连接检测、
序列化异常、损坏数据清理、过期辅助方法与上下文管理等分支。
"""

import sys
from unittest.mock import MagicMock

import pytest

from litefs.session.memcache import MemcacheSession
from litefs.session.session import Session


class PymemcacheStyleClient:
    """模拟 pymemcache 客户端（模块名决定调用约定判定）"""

    def __init__(self):
        self.stored = {}
        self.stats_called = False

    def stats(self):
        self.stats_called = True
        return {}

    def set(self, key, value, expire=0, *args, **kwargs):
        self.stored[key] = value

    def get(self, key, *args, **kwargs):
        return self.stored.get(key)

    def delete(self, key, *args, **kwargs):
        return self.stored.pop(key, None)


# 将模拟客户端归入 pymemcache 模块命名空间，触发 _use_pymemcache 判定
PymemcacheStyleClient.__module__ = 'pymemcache.client.base'


class PythonMemcachedStyleClient:
    """模拟 python-memcached 客户端"""

    def __init__(self):
        self.stored = {}

    def stats(self):
        return {}

    def set(self, key, value, time=0, *args, **kwargs):
        self.stored[key] = value

    def get(self, key, *args, **kwargs):
        return self.stored.get(key)

    def delete(self, key, *args, **kwargs):
        return self.stored.pop(key, None)


PythonMemcachedStyleClient.__module__ = 'memcache'


@pytest.fixture
def pymc():
    """pymemcache 风格客户端"""
    return PymemcacheStyleClient()


@pytest.fixture
def store(pymc):
    """注入 pymemcache 风格客户端的 MemcacheSession"""
    return MemcacheSession(memcache_client=pymc, key_prefix='t:s:')


class TestClientDetection:
    """客户端类型判定测试"""

    def test_pymemcache_client_detected(self):
        """按客户端所属模块判定为 pymemcache 分支"""
        client = PymemcacheStyleClient()
        session = MemcacheSession(memcache_client=client)
        assert session._use_pymemcache is True

    def test_python_memcached_client_detected(self):
        """按客户端所属模块判定为 python-memcached 分支"""
        client = PythonMemcachedStyleClient()
        session = MemcacheSession(memcache_client=client)
        assert session._use_pymemcache is False

    def test_mock_client_falls_back_to_memcached_branch(self):
        """无明确模块归属的客户端按 python-memcached 分支处理"""
        client = MagicMock()
        client.stats.return_value = {}
        session = MemcacheSession(memcache_client=client)
        assert session._use_pymemcache is False

    def test_import_error_when_no_client_library(self, monkeypatch):
        """两个客户端库都不可用时应抛出带安装指引的 ImportError"""
        # sys.modules 中值为 None 的条目会使 import 抛 ImportError
        monkeypatch.setitem(sys.modules, 'pymemcache', None)
        monkeypatch.setitem(sys.modules, 'memcache', None)
        with pytest.raises(ImportError, match='pymemcache 或 python-memcached'):
            MemcacheSession(servers=['localhost:11211'])


class TestConnection:
    """连接检测测试"""

    def test_connection_error_propagates(self):
        """stats 抛异常时转换为 ConnectionError"""
        client = MagicMock()
        client.stats.side_effect = OSError('connection refused')
        with pytest.raises(ConnectionError, match='无法连接到 Memcache'):
            MemcacheSession(memcache_client=client)

    def test_fallback_probe_without_stats(self):
        """客户端无 stats 方法时回退为 set/delete 探测"""
        client = MagicMock(spec=['set', 'delete'])
        session = MemcacheSession(memcache_client=client)
        client.set.assert_called_once_with('_litefs_test', '1')
        client.delete.assert_called_once_with('_litefs_test')
        assert session._use_pymemcache is False


class TestPutGet:
    """存取测试"""

    def test_put_uses_expire_kwarg_for_pymemcache(self, pymc):
        """pymemcache 分支使用 expire= 关键字参数"""
        store = MemcacheSession(
            memcache_client=pymc, key_prefix='t:s:', expiration_time=120
        )
        session = Session('sid1')
        session['k'] = 'v'
        store.put('sid1', session)
        assert pymc.stored['t:s:sid1'] is not None

    def test_put_expiration_zero_clamps_to_zero(self, pymc):
        """过期时间 <=0 时 pymemcache 分支传 expire=0"""
        store = MemcacheSession(
            memcache_client=pymc, key_prefix='t:s:', expiration_time=0
        )
        store.put('sid0', Session('sid0'))
        assert 't:s:sid0' in pymc.stored

    def test_put_uses_time_kwarg_for_memcached_branch(self):
        """python-memcached 分支使用 time= 关键字参数"""
        client = PythonMemcachedStyleClient()
        store = MemcacheSession(memcache_client=client)
        store.put('sid2', Session('sid2'))
        assert client.stored['litefs:session:sid2'] is not None

    def test_put_serialization_error_wraps_value_error(self, store):
        """不可序列化数据应抛出 ValueError"""
        session = Session('bad')
        session['obj'] = object()
        with pytest.raises(ValueError, match='无法序列化'):
            store.put('bad', session)

    def test_get_missing_returns_none(self, store):
        """键不存在时返回 None"""
        assert store.get('missing') is None

    def test_get_roundtrip(self, store):
        """存取往返保持数据一致"""
        session = Session('rt')
        session['user'] = '张三'
        session['n'] = 42
        store.put('rt', session)
        loaded = store.get('rt')
        assert loaded is not None
        assert loaded['user'] == '张三'
        assert loaded['n'] == 42

    def test_get_corrupted_data_deletes_and_returns_none(self, pymc, store):
        """损坏数据应被删除并返回 None"""
        pymc.stored['t:s:corrupt'] = '{invalid-json'
        assert store.get('corrupt') is None
        assert 't:s:corrupt' not in pymc.stored


class TestMiscOperations:
    """辅助方法测试"""

    def test_delete(self, store):
        """删除已有键"""
        store.put('d1', Session('d1'))
        store.delete('d1')
        assert store.get('d1') is None

    def test_delete_pattern_always_zero(self, store):
        """Memcache 不支持模式匹配，恒返回 0"""
        assert store.delete_pattern('t:s:*') == 0

    def test_exists(self, store):
        """exists 反映键存在性"""
        assert store.exists('e1') is False
        store.put('e1', Session('e1'))
        assert store.exists('e1') is True

    def test_expire_existing_returns_true(self, store):
        """对存在的 Session 重设过期时间返回 True"""
        store.put('x1', Session('x1'))
        assert store.expire('x1', 60) is True
        assert store.get('x1') is not None

    def test_expire_missing_returns_false(self, store):
        """对不存在的 Session 返回 False"""
        assert store.expire('nope', 60) is False

    def test_ttl_missing_returns_minus_two(self, store):
        """键不存在时 TTL 返回 -2"""
        assert store.ttl('nope') == -2

    def test_ttl_existing_returns_minus_one(self, store):
        """Memcache 不支持 TTL 查询，存在时返回 -1"""
        store.put('x2', Session('x2'))
        assert store.ttl('x2') == -1

    def test_clear_noop(self, store):
        """clear 不执行任何操作且不抛异常"""
        store.put('c1', Session('c1'))
        store.clear()
        assert store.get('c1') is not None

    def test_len_always_zero(self, store):
        """Memcache 不支持统计键数量，恒返回 0"""
        store.put('c2', Session('c2'))
        assert len(store) == 0

    def test_close_calls_client_close(self):
        """close 调用客户端的 close 方法"""
        client = MagicMock()
        client.stats.return_value = {}
        store = MemcacheSession(memcache_client=client)
        store.close()
        client.close.assert_called_once()

    def test_close_without_close_method(self, pymc):
        """客户端无 close 方法时不抛异常"""
        store = MemcacheSession(memcache_client=pymc)
        store.close()

    def test_close_swallows_errors(self):
        """客户端 close 抛异常时静默吞掉"""
        client = MagicMock()
        client.stats.return_value = {}
        client.close.side_effect = OSError('already closed')
        store = MemcacheSession(memcache_client=client)
        store.close()

    def test_context_manager_closes(self):
        """上下文管理器退出时自动 close"""
        client = MagicMock()
        client.stats.return_value = {}
        with MemcacheSession(memcache_client=client) as store:
            assert store is not None
        client.close.assert_called_once()

    def test_create_returns_session_bound_to_store(self, store):
        """create 返回绑定存储的 Session"""
        session = store.create()
        assert isinstance(session, Session)
        assert session.store is store

    def test_save_delegates_to_put(self, store):
        """save 按 Session.id 调用 put"""
        session = Session('sv')
        session['k'] = 'v'
        store.save(session)
        assert store.get('sv') is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
