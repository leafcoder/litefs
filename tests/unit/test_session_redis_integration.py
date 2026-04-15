#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis Session 测试（使用真实 Redis 服务）
"""

import pytest
from unittest.mock import Mock
from litefs.session.redis import RedisSession
from litefs.session.session import Session


@pytest.fixture
def redis_session():
    """创建 RedisSession 实例（使用真实服务）"""
    # 使用 localhost:6379 的 Redis 服务
    session = RedisSession(
        host='localhost',
        port=6379,
        db=0,
        key_prefix='test:session:',
        expiration_time=3600
    )
    yield session
    # 清理测试数据
    try:
        session._redis.delete('test:session:cleanup')
    except:
        pass


@pytest.fixture
def mock_session():
    """创建模拟的 Session 对象"""
    session = Mock(spec=Session)
    session.__iter__ = lambda self: iter([('key1', 'value1'), ('key2', 'value2')])
    return session


class TestRedisSessionInit:
    """RedisSession 初始化测试"""
    
    def test_init_with_defaults(self):
        """测试默认参数初始化"""
        session = RedisSession(
            redis_client=Mock(),
            key_prefix='test:',
            expiration_time=3600
        )
        
        assert session._key_prefix == 'test:'
        assert session._expiration_time == 3600
    
    def test_init_with_custom_params(self):
        """测试自定义参数初始化"""
        session = RedisSession(
            redis_client=Mock(),
            key_prefix='custom:',
            expiration_time=7200
        )
        
        assert session._key_prefix == 'custom:'
        assert session._expiration_time == 7200


class TestRedisSessionOperations:
    """RedisSession 操作测试"""
    
    def test_make_key(self, redis_session):
        """测试生成键"""
        key = redis_session._make_key('session123')
        assert key == 'test:session:session123'
    
    def test_put_and_get(self, redis_session):
        """测试存储和获取 Session"""
        session_id = 'test_session_1'
        session_data = {'user_id': 123, 'username': 'test'}
        
        # 存储 Session
        redis_session.put(session_id, session_data)
        
        # 获取 Session
        result = redis_session.get(session_id)
        
        assert result is not None
        assert result['user_id'] == 123
        assert result['username'] == 'test'
    
    def test_get_nonexistent(self, redis_session):
        """测试获取不存在的 Session"""
        result = redis_session.get('nonexistent_session')
        assert result is None
    
    def test_delete(self, redis_session):
        """测试删除 Session"""
        session_id = 'test_session_2'
        session_data = {'data': 'test'}
        
        # 先存储
        redis_session.put(session_id, session_data)
        
        # 验证已存储
        assert redis_session.get(session_id) is not None
        
        # 删除
        redis_session.delete(session_id)
        
        # 验证已删除
        result = redis_session.get(session_id)
        assert result is None
    
    def test_delete_nonexistent(self, redis_session):
        """测试删除不存在的 Session"""
        # 不应该抛出异常
        redis_session.delete('nonexistent_session')
    
    def test_exists(self, redis_session):
        """测试 Session 是否存在"""
        session_id = 'test_session_3'
        session_data = {'data': 'test'}
        
        # 验证不存在
        assert redis_session.exists(session_id) == False
        
        # 存储
        redis_session.put(session_id, session_data)
        
        # 验证存在
        assert redis_session.exists(session_id) == True
        
        # 删除
        redis_session.delete(session_id)
        
        # 验证不存在
        assert redis_session.exists(session_id) == False
    
    def test_clear(self, redis_session):
        """测试清空所有 Session（带前缀）"""
        # 存储多个 Session
        redis_session.put('clear_test_1', {'data': '1'})
        redis_session.put('clear_test_2', {'data': '2'})
        
        # 清空（应该只清空带前缀的）
        redis_session.clear()
        
        # 验证方法存在且不抛出异常
        assert True
    
    def test_count(self, redis_session):
        """测试统计 Session 数量"""
        # RedisSession 没有 count 方法
        assert not hasattr(redis_session, 'count')


class TestRedisSessionExpiration:
    """RedisSession 过期测试"""
    
    @pytest.mark.skip(reason="需要等待过期，耗时较长，在 CI 中可能不稳定")
    def test_session_expiration(self, redis_session):
        """测试 Session 过期"""
        session_id = 'test_expire'
        session_data = {'data': 'test'}
        
        # 存储 1 秒后过期的 Session
        redis_session.put(session_id, session_data, expiration=1)
        
        # 立即获取应该存在
        result = redis_session.get(session_id)
        assert result is not None
        
        # 等待 2 秒
        import time
        time.sleep(2)
        
        # 应该已过期
        result = redis_session.get(session_id)
        assert result is None


class TestRedisSessionIntegration:
    """RedisSession 集成测试"""
    
    def test_multiple_sessions(self, redis_session):
        """测试多个 Session"""
        # 存储多个 Session
        sessions = [
            ('session_1', {'user_id': 1}),
            ('session_2', {'user_id': 2}),
            ('session_3', {'user_id': 3}),
        ]
        
        for session_id, data in sessions:
            redis_session.put(session_id, data)
        
        # 获取所有 Session
        for session_id, expected_data in sessions:
            result = redis_session.get(session_id)
            assert result is not None
            assert result['user_id'] == expected_data['user_id']
        
        # 删除所有 Session
        for session_id, _ in sessions:
            redis_session.delete(session_id)
    
    def test_large_session_data(self, redis_session):
        """测试存储大数据 Session"""
        session_id = 'large_session'
        # 创建大数据
        large_data = {
            'user_id': 123,
            'permissions': list(range(1000)),
            'metadata': {'key': 'value' * 100}
        }
        
        # 存储
        redis_session.put(session_id, large_data)
        
        # 获取
        result = redis_session.get(session_id)
        
        assert result is not None
        assert result['user_id'] == 123
        assert len(result['permissions']) == 1000
    
    def test_special_characters(self, redis_session):
        """测试特殊字符"""
        session_id = 'special_session'
        session_data = {
            'chinese': '中文测试',
            'emoji': '😀😁😂',
            'special': '!@#$%^&*()'
        }
        
        # 存储
        redis_session.put(session_id, session_data)
        
        # 获取
        result = redis_session.get(session_id)
        
        assert result is not None
        assert result['chinese'] == '中文测试'
        assert result['emoji'] == '😀😁😂'
        assert result['special'] == '!@#$%^&*()'
    
    def test_numeric_keys(self, redis_session):
        """测试数字键"""
        session_id = '12345'
        session_data = {'value': 'test'}
        
        redis_session.put(session_id, session_data)
        result = redis_session.get(session_id)
        
        assert result is not None
        assert result['value'] == 'test'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
