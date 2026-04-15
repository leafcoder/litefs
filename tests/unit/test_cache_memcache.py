#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Memcache 缓存测试
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json


class TestMemcacheCache:
    """Memcache 缓存测试"""
    
    @pytest.fixture
    def mock_memcache_client(self):
        """创建模拟的 Memcache 客户端"""
        client = MagicMock()
        client.stats.return_value = {}
        client.get.return_value = None
        client.set.return_value = True
        client.delete.return_value = True
        return client
    
    @pytest.fixture
    def cache(self, mock_memcache_client):
        """创建 Memcache 缓存实例"""
        from litefs.cache.memcache import MemcacheCache
        
        cache = MemcacheCache(memcache_client=mock_memcache_client)
        # 设置 _use_pymemcache 属性以模拟 pymemcache 行为
        cache._use_pymemcache = True
        return cache
    
    def test_init_with_client(self, mock_memcache_client):
        """测试使用现有客户端初始化"""
        from litefs.cache.memcache import MemcacheCache
        
        cache = MemcacheCache(memcache_client=mock_memcache_client)
        
        assert cache._mc == mock_memcache_client
        assert cache._key_prefix == "litefs:"
        assert cache._expiration_time == 3600
    
    def test_init_with_custom_params(self, mock_memcache_client):
        """测试自定义参数初始化"""
        from litefs.cache.memcache import MemcacheCache
        
        cache = MemcacheCache(
            memcache_client=mock_memcache_client,
            key_prefix="test:",
            expiration_time=7200
        )
        
        assert cache._key_prefix == "test:"
        assert cache._expiration_time == 7200
    
    def test_init_without_client_pymemcache(self):
        """测试不使用现有客户端（pymemcache）"""
        # 这个测试验证在没有 pymemcache 时的行为
        from litefs.cache.memcache import MemcacheCache
        
        # 应该可以创建实例，但使用时会失败
        cache = MemcacheCache(servers=['localhost:11211'])
        assert cache is not None
        # 验证缓存对象已创建（应该有_mc 属性）
        assert hasattr(cache, '_mc')
    
    def test_make_key(self, cache):
        """测试生成带前缀的键"""
        key = cache._make_key('test_key')
        assert key == 'litefs:test_key'
    
    def test_make_key_with_custom_prefix(self):
        """测试使用自定义前缀生成键"""
        from litefs.cache.memcache import MemcacheCache
        
        mock_client = MagicMock()
        mock_client.stats.return_value = {}
        
        cache = MemcacheCache(
            memcache_client=mock_client,
            key_prefix="custom:"
        )
        
        key = cache._make_key('test_key')
        assert key == 'custom:test_key'
    
    def test_put(self, cache, mock_memcache_client):
        """测试存储值"""
        cache.put('test_key', 'test_value')
        
        # 验证 set 被调用
        assert mock_memcache_client.set.called
        call_args = mock_memcache_client.set.call_args
        assert call_args[0][0] == 'litefs:test_key'
        assert json.loads(call_args[0][1]) == 'test_value'
    
    def test_put_with_expiration(self, cache, mock_memcache_client):
        """测试存储值并设置过期时间"""
        cache.put('test_key', 'test_value', expiration=1800)
        
        # 验证 expire 参数被传递
        assert mock_memcache_client.set.called
        call_kwargs = mock_memcache_client.set.call_args[1]
        assert call_kwargs['expire'] == 1800
    
    def test_put_serialization_error(self, cache, mock_memcache_client):
        """测试序列化错误"""
        # 创建一个无法序列化的对象
        class Unserializable:
            pass
        
        with pytest.raises(ValueError, match="无法序列化值"):
            cache.put('test_key', Unserializable())
    
    def test_get(self, cache, mock_memcache_client):
        """测试获取值"""
        # 设置模拟返回值
        mock_memcache_client.get.return_value = json.dumps('test_value')
        
        value = cache.get('test_key')
        assert value == 'test_value'
        
        # 验证 get 被调用
        assert mock_memcache_client.get.called
        assert mock_memcache_client.get.call_args[0][0] == 'litefs:test_key'
    
    def test_get_not_found(self, cache, mock_memcache_client):
        """测试获取不存在的值"""
        mock_memcache_client.get.return_value = None
        
        value = cache.get('nonexistent_key')
        assert value is None
    
    def test_get_deserialization_error(self, cache, mock_memcache_client):
        """测试反序列化错误"""
        # 返回无效的 JSON
        mock_memcache_client.get.return_value = 'invalid json'
        
        value = cache.get('test_key')
        # 应该返回原始字符串
        assert value == 'invalid json'
    
    def test_delete(self, cache, mock_memcache_client):
        """测试删除值"""
        cache.delete('test_key')
        
        # 验证 delete 被调用
        assert mock_memcache_client.delete.called
        assert mock_memcache_client.delete.call_args[0][0] == 'litefs:test_key'
    
    def test_delete_pattern(self, cache):
        """测试删除模式匹配（Memcache 不支持）"""
        result = cache.delete_pattern('test*')
        assert result == 0
    
    def test_exists(self, cache, mock_memcache_client):
        """测试键是否存在"""
        # 键存在
        mock_memcache_client.get.return_value = json.dumps('value')
        assert cache.exists('test_key') == True
        
        # 键不存在
        mock_memcache_client.get.return_value = None
        assert cache.exists('nonexistent_key') == False
    
    def test_expire(self, cache, mock_memcache_client):
        """测试设置过期时间"""
        # 键存在
        mock_memcache_client.get.return_value = json.dumps('value')
        
        result = cache.expire('test_key', 1800)
        assert result == True
        
        # 验证 set 被调用更新过期时间
        assert mock_memcache_client.set.called
    
    def test_expire_not_found(self, cache, mock_memcache_client):
        """测试设置不存在的键的过期时间"""
        mock_memcache_client.get.return_value = None
        
        result = cache.expire('nonexistent_key', 1800)
        assert result == False
    
    def test_ttl(self, cache, mock_memcache_client):
        """测试获取 TTL（Memcache 不支持）"""
        mock_memcache_client.get.return_value = json.dumps('value')
        
        ttl = cache.ttl('test_key')
        assert ttl == -1  # Memcache 不支持 TTL 查询
    
    def test_ttl_not_found(self, cache, mock_memcache_client):
        """测试获取不存在键的 TTL"""
        mock_memcache_client.get.return_value = None
        
        ttl = cache.ttl('nonexistent_key')
        assert ttl == -2
    
    def test_clear(self, cache):
        """测试清空缓存（Memcache 不支持）"""
        # 应该不抛出异常
        cache.clear()
    
    def test_len(self, cache):
        """测试获取缓存长度（Memcache 不支持）"""
        length = len(cache)
        assert length == 0
    
    def test_get_many(self, cache, mock_memcache_client):
        """测试批量获取"""
        # 设置模拟返回值
        mock_memcache_client.get_many.return_value = {
            'litefs:key1': json.dumps('value1'),
            'litefs:key2': json.dumps('value2'),
            'litefs:key3': None
        }
        
        result = cache.get_many(['key1', 'key2', 'key3'])
        
        assert 'key1' in result
        assert result['key1'] == 'value1'
        assert 'key2' in result
        assert result['key2'] == 'value2'
        assert 'key3' not in result
    
    def test_get_many_empty(self, cache):
        """测试批量获取空列表"""
        result = cache.get_many([])
        assert result == {}
    
    def test_set_many(self, cache, mock_memcache_client):
        """测试批量存储"""
        data = {'key1': 'value1', 'key2': 'value2'}
        cache.set_many(data)
        
        # 验证 set_many 或多次 set 被调用
        assert mock_memcache_client.set.called or mock_memcache_client.set_many.called
    
    def test_set_many_empty(self, cache, mock_memcache_client):
        """测试批量存储空字典"""
        cache.set_many({})
        
        # 不应该调用任何方法
        assert not mock_memcache_client.set.called
        assert not mock_memcache_client.set_many.called
    
    def test_incr(self, cache, mock_memcache_client):
        """测试递增（Memcache 不支持）"""
        # MemcacheCache 没有 incr 方法
        # 验证方法不存在
        assert not hasattr(cache, 'incr')
        # 跳过实际测试
        pytest.skip("incr 方法不存在")
    
    def test_decr(self, cache, mock_memcache_client):
        """测试递减（Memcache 不支持）"""
        # MemcacheCache 没有 decr 方法
        # 验证方法不存在
        assert not hasattr(cache, 'decr')
        # 跳过实际测试
        pytest.skip("decr 方法不存在")
    
    def test_repr(self, cache):
        """测试字符串表示"""
        repr_str = repr(cache)
        assert 'MemcacheCache' in repr_str


class TestMemcacheCacheIntegration:
    """Memcache 缓存集成测试"""
    
    @pytest.mark.skip(reason="需要真实的 Memcache 服务器")
    def test_real_memcache_connection(self):
        """测试真实的 Memcache 连接"""
        from litefs.cache.memcache import MemcacheCache
        
        # 这需要真实的 Memcache 服务器
        # cache = MemcacheCache(servers=['localhost:11211'])
        # cache.put('test', 'value')
        # assert cache.get('test') == 'value'
        pass
    
    @pytest.mark.skip(reason="需要真实的 Memcache 服务器")
    def test_real_memcache_expiration(self):
        """测试真实的 Memcache 过期"""
        from litefs.cache.memcache import MemcacheCache
        import time
        
        # cache = MemcacheCache(servers=['localhost:11211'])
        # cache.put('test', 'value', expiration=1)
        # time.sleep(2)
        # assert cache.get('test') is None
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
