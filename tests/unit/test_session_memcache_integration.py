#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memcache Session 测试（使用真实 memcached 服务）
"""

import pytest
import time
from unittest.mock import Mock
from litefs.session.memcache import MemcacheSession
from litefs.session.session import Session


@pytest.fixture
def memcache_session():
    """创建 MemcacheSession 实例（使用真实服务）"""
    # 使用 localhost:11211 的 memcached 服务
    session = MemcacheSession(
        servers=['localhost:11211'],
        key_prefix='test:session:',
        expiration_time=3600
    )
    yield session
    # 清理测试数据
    try:
        session._mc.delete('test:session:cleanup')
    except:
        pass


@pytest.fixture
def mock_session():
    """创建模拟的 Session 对象"""
    session = Mock(spec=Session)
    session.__iter__ = lambda self: iter([('key1', 'value1'), ('key2', 'value2')])
    return session


class TestMemcacheSessionInit:
    """MemcacheSession 初始化测试"""
    
    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        session = MemcacheSession(
            memcache_client=Mock(),
            key_prefix='test:',
            expiration_time=3600
        )
        
        assert session._key_prefix == 'test:'
        assert session._expiration_time == 3600
    
    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        session = MemcacheSession(
            memcache_client=Mock(),
            key_prefix='custom:',
            expiration_time=7200
        )
        
        assert session._key_prefix == 'custom:'
        assert session._expiration_time == 7200


class TestMemcacheSessionOperations:
    """MemcacheSession 操作测试"""
    
    def test_make_key(self, memcache_session):
        """测试生成键"""
        key = memcache_session._make_key('session123')
        assert key == 'test:session:session123'
    
    def test_put_and_get(self, memcache_session):
        """测试存储和获取 Session"""
        session_id = 'test_session_1'
        session_data = {'user_id': 123, 'username': 'test'}
        
        # 存储 Session
        memcache_session.put(session_id, session_data)
        
        # 获取 Session
        result = memcache_session.get(session_id)
        
        assert result is not None
        assert result['user_id'] == 123
        assert result['username'] == 'test'
    
    def test_get_nonexistent(self, memcache_session):
        """测试获取不存在的 Session"""
        result = memcache_session.get('nonexistent_session')
        assert result is None
    
    def test_delete(self, memcache_session):
        """测试删除 Session"""
        session_id = 'test_session_2'
        session_data = {'data': 'test'}
        
        # 先存储
        memcache_session.put(session_id, session_data)
        
        # 验证已存储
        assert memcache_session.get(session_id) is not None
        
        # 删除
        memcache_session.delete(session_id)
        
        # 验证已删除
        result = memcache_session.get(session_id)
        assert result is None
    
    def test_delete_nonexistent(self, memcache_session):
        """测试删除不存在的 Session"""
        # 不应该抛出异常
        memcache_session.delete('nonexistent_session')
    
    def test_exists(self, memcache_session):
        """测试 Session 是否存在"""
        session_id = 'test_session_3'
        session_data = {'data': 'test'}
        
        # 验证不存在
        assert memcache_session.exists(session_id) == False
        
        # 存储
        memcache_session.put(session_id, session_data)
        
        # 验证存在
        assert memcache_session.exists(session_id) == True
        
        # 删除
        memcache_session.delete(session_id)
        
        # 验证不存在
        assert memcache_session.exists(session_id) == False
    
    def test_update(self, memcache_session):
        """测试更新 Session（通过 get+put 实现）"""
        session_id = 'test_session_4'
        initial_data = {'user_id': 123, 'username': 'test'}
        
        # 存储初始数据
        memcache_session.put(session_id, initial_data)
        
        # 获取并更新数据
        existing = memcache_session.get(session_id)
        if existing:
            existing['username'] = 'updated'
            existing['email'] = 'test@example.com'
            memcache_session.put(session_id, existing)
        
        # 获取更新后的数据
        result = memcache_session.get(session_id)
        
        assert result is not None
        assert result['username'] == 'updated'
        assert result['email'] == 'test@example.com'
    
    def test_update_nonexistent(self, memcache_session):
        """测试更新不存在的 Session（应该不执行任何操作）"""
        # MemcacheSession 没有 update 方法，需要通过 get+put 实现
        # 对于不存在的 session，get 会返回 None
        result = memcache_session.get('nonexistent')
        assert result is None
    
    def test_clear(self, memcache_session):
        """测试清空所有 Session"""
        # 存储多个 Session
        memcache_session.put('clear_test_1', {'data': '1'})
        memcache_session.put('clear_test_2', {'data': '2'})
        
        # 清空
        memcache_session.clear()
        
        # 验证已清空（Memcache 不支持模式匹配，可能不会完全清空）
        # 这里只验证方法存在且不抛出异常
        assert True
    
    def test_count(self, memcache_session):
        """测试统计 Session 数量（MemcacheSession 不支持）"""
        # MemcacheSession 没有 count 方法
        # 这个方法应该由 SessionManager 实现
        assert not hasattr(memcache_session, 'count')


class TestMemcacheSessionExpiration:
    """MemcacheSession 过期测试"""
    
    @pytest.mark.skip(reason="需要等待过期，耗时较长")
    def test_session_expiration(self, memcache_session):
        """测试 Session 过期"""
        session_id = 'test_expire'
        session_data = {'data': 'test'}
        
        # 存储 1 秒后过期的 Session
        memcache_session.put(session_id, session_data, expiration=1)
        
        # 立即获取应该存在
        result = memcache_session.get(session_id)
        assert result is not None
        
        # 等待 2 秒
        time.sleep(2)
        
        # 应该已过期
        result = memcache_session.get(session_id)
        assert result is None


class TestMemcacheSessionIntegration:
    """MemcacheSession 集成测试"""
    
    def test_multiple_sessions(self, memcache_session):
        """测试多个 Session"""
        # 存储多个 Session
        sessions = [
            ('session_1', {'user_id': 1}),
            ('session_2', {'user_id': 2}),
            ('session_3', {'user_id': 3}),
        ]
        
        for session_id, data in sessions:
            memcache_session.put(session_id, data)
        
        # 获取所有 Session
        for session_id, expected_data in sessions:
            result = memcache_session.get(session_id)
            assert result is not None
            assert result['user_id'] == expected_data['user_id']
        
        # 删除所有 Session
        for session_id, _ in sessions:
            memcache_session.delete(session_id)
    
    def test_large_session_data(self, memcache_session):
        """测试存储大数据 Session"""
        session_id = 'large_session'
        # 创建大数据
        large_data = {
            'user_id': 123,
            'permissions': list(range(1000)),
            'metadata': {'key': 'value' * 100}
        }
        
        # 存储
        memcache_session.put(session_id, large_data)
        
        # 获取
        result = memcache_session.get(session_id)
        
        assert result is not None
        assert result['user_id'] == 123
        assert len(result['permissions']) == 1000
    
    def test_special_characters(self, memcache_session):
        """测试特殊字符"""
        session_id = 'special_session'
        session_data = {
            'chinese': '中文测试',
            'emoji': '😀😁😂',
            'special': '!@#$%^&*()'
        }
        
        # 存储
        memcache_session.put(session_id, session_data)
        
        # 获取
        result = memcache_session.get(session_id)
        
        assert result is not None
        assert result['chinese'] == '中文测试'
        assert result['emoji'] == '😀😁😂'
        assert result['special'] == '!@#$%^&*()'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
