#!/usr/bin/env python
# coding: utf-8

"""
Database 和 Memcache 缓存后端示例

演示如何使用 Database 和 Memcache 缓存后端
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from litefs import Litefs
from litefs.cache import DatabaseCache, MemcacheCache, CacheFactory, CacheBackend
from litefs.session import DatabaseSession, MemcacheSession, SessionFactory, SessionBackend


def example_database_cache():
    """演示 Database Cache"""
    print("\n=== Database Cache 示例 ===\n")
    
    # 创建 Database Cache
    cache = DatabaseCache(
        db_path=":memory:",
        table_name="cache",
        expiration_time=3600
    )
    
    # 存储数据
    cache.put("user:1", {"name": "张三", "age": 30})
    cache.put("user:2", {"name": "李四", "age": 25})
    cache.put("config:theme", "dark", expiration=7200)
    
    print("存储数据:")
    print("  user:1 -> {'name': '张三', 'age': 30}")
    print("  user:2 -> {'name': '李四', 'age': 25}")
    print("  config:theme -> 'dark' (7200秒过期)")
    
    # 获取数据
    user1 = cache.get("user:1")
    print(f"\n获取 user:1: {user1}")
    
    # 批量获取
    users = cache.get_many(["user:1", "user:2"])
    print(f"批量获取用户: {users}")
    
    # 检查键是否存在
    exists = cache.exists("user:1")
    print(f"user:1 是否存在: {exists}")
    
    # 获取 TTL
    ttl = cache.ttl("user:1")
    print(f"user:1 剩余过期时间: {ttl} 秒")
    
    # 设置过期时间
    cache.expire("user:1", 1800)
    print("设置 user:1 过期时间为 1800 秒")
    
    # 批量存储
    cache.set_many({
        "product:1": {"name": "商品1", "price": 100},
        "product:2": {"name": "商品2", "price": 200}
    })
    print("\n批量存储商品数据")
    
    # 获取缓存大小
    size = len(cache)
    print(f"缓存大小: {size}")
    
    # 模式匹配删除
    cache.delete_pattern("product:%")
    print("删除所有 product:* 键")
    
    # 关闭连接
    cache.close()
    print("\nDatabase Cache 示例完成\n")


def example_memcache_cache():
    """演示 Memcache Cache"""
    print("\n=== Memcache Cache 示例 ===\n")
    
    try:
        # 创建 Memcache Cache
        cache = MemcacheCache(
            servers=["localhost:11211"],
            key_prefix="litefs:",
            expiration_time=3600
        )
        
        # 存储数据
        cache.put("user:1", {"name": "张三", "age": 30})
        cache.put("user:2", {"name": "李四", "age": 25})
        
        print("存储数据:")
        print("  user:1 -> {'name': '张三', 'age': 30}")
        print("  user:2 -> {'name': '李四', 'age': 25}")
        
        # 获取数据
        user1 = cache.get("user:1")
        print(f"\n获取 user:1: {user1}")
        
        # 批量获取
        users = cache.get_many(["user:1", "user:2"])
        print(f"批量获取用户: {users}")
        
        # 检查键是否存在
        exists = cache.exists("user:1")
        print(f"user:1 是否存在: {exists}")
        
        # 批量存储
        cache.set_many({
            "product:1": {"name": "商品1", "price": 100},
            "product:2": {"name": "商品2", "price": 200}
        })
        print("\n批量存储商品数据")
        
        # 批量删除
        cache.delete_many(["user:1", "user:2"])
        print("删除 user:1 和 user:2")
        
        # 关闭连接
        cache.close()
        print("\nMemcache Cache 示例完成\n")
        
    except Exception as e:
        print(f"Memcache 连接失败: {e}")
        print("请确保 Memcache 服务器已启动并安装了 pymemcache 或 python-memcached")


def example_database_session():
    """演示 Database Session"""
    print("\n=== Database Session 示例 ===\n")
    
    # 创建 Database Session
    session_store = DatabaseSession(
        db_path=":memory:",
        table_name="sessions",
        session_timeout=3600
    )
    
    # 创建 Session
    session = session_store.create()
    print(f"创建 Session: {session.id}")
    
    # 设置 Session 数据
    session.data["user_id"] = 123
    session.data["username"] = "张三"
    session.data["cart"] = ["商品1", "商品2"]
    session.data["preferences"] = {"theme": "dark", "language": "zh"}
    
    print("设置 Session 数据:")
    print(f"  user_id: {session.data['user_id']}")
    print(f"  username: {session.data['username']}")
    print(f"  cart: {session.data['cart']}")
    print(f"  preferences: {session.data['preferences']}")
    
    # 保存 Session
    session_store.save(session)
    print("\n保存 Session")
    
    # 获取 Session
    retrieved_session = session_store.get(session.id)
    print(f"获取 Session: {retrieved_session.id}")
    print(f"Session 数据: {retrieved_session.data}")
    
    # 检查 Session 是否存在
    exists = session_store.exists(session.id)
    print(f"Session 是否存在: {exists}")
    
    # 获取 TTL
    ttl = session_store.ttl(session.id)
    print(f"Session 剩余过期时间: {ttl} 秒")
    
    # 设置过期时间
    session_store.expire(session.id, 1800)
    print("设置 Session 过期时间为 1800 秒")
    
    # 获取 Session 数量
    count = len(session_store)
    print(f"Session 数量: {count}")
    
    # 删除 Session
    session_store.delete(session.id)
    print(f"删除 Session: {session.id}")
    
    # 关闭连接
    session_store.close()
    print("\nDatabase Session 示例完成\n")


def example_memcache_session():
    """演示 Memcache Session"""
    print("\n=== Memcache Session 示例 ===\n")
    
    try:
        # 创建 Memcache Session
        session_store = MemcacheSession(
            servers=["localhost:11211"],
            key_prefix="session:",
            session_timeout=3600
        )
        
        # 创建 Session
        session = session_store.create()
        print(f"创建 Session: {session.id}")
        
        # 设置 Session 数据
        session.data["user_id"] = 123
        session.data["username"] = "张三"
        session.data["cart"] = ["商品1", "商品2"]
        
        print("设置 Session 数据:")
        print(f"  user_id: {session.data['user_id']}")
        print(f"  username: {session.data['username']}")
        print(f"  cart: {session.data['cart']}")
        
        # 保存 Session
        session_store.save(session)
        print("\n保存 Session")
        
        # 获取 Session
        retrieved_session = session_store.get(session.id)
        print(f"获取 Session: {retrieved_session.id}")
        print(f"Session 数据: {retrieved_session.data}")
        
        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")
        
        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")
        
        # 关闭连接
        session_store.close()
        print("\nMemcache Session 示例完成\n")
        
    except Exception as e:
        print(f"Memcache 连接失败: {e}")
        print("请确保 Memcache 服务器已启动并安装了 pymemcache 或 python-memcached")


def example_cache_factory():
    """演示 Cache Factory"""
    print("\n=== Cache Factory 示例 ===\n")
    
    # 使用工厂创建 Database Cache
    cache1 = CacheFactory.create_cache(
        backend=CacheBackend.DATABASE,
        db_path=":memory:",
        table_name="cache",
        expiration_time=3600
    )
    
    cache1.put("test", "value")
    print(f"Database Cache: {cache1.get('test')}")
    if hasattr(cache1, 'close'):
        cache1.close()
    
    # 使用工厂创建 Memcache Cache
    try:
        cache2 = CacheFactory.create_cache(
            backend=CacheBackend.MEMCACHE,
            servers=["localhost:11211"],
            key_prefix="litefs:",
            expiration_time=3600
        )
        
        cache2.put("test", "value")
        print(f"Memcache Cache: {cache2.get('test')}")
        if hasattr(cache2, 'close'):
            cache2.close()
    except Exception as e:
        print(f"Memcache Cache 创建失败: {e}")
    
    print("\nCache Factory 示例完成\n")


def example_session_factory():
    """演示 Session Factory"""
    print("\n=== Session Factory 示例 ===\n")
    
    # 使用工厂创建 Database Session
    session_store1 = SessionFactory.create_session(
        backend=SessionBackend.DATABASE,
        db_path=":memory:",
        table_name="sessions",
        session_timeout=3600
    )
    
    session1 = session_store1.create()
    session1.data["user"] = "张三"
    session_store1.save(session1)
    
    retrieved1 = session_store1.get(session1.id)
    if retrieved1:
        print(f"Database Session: {retrieved1.data}")
    session_store1.close()
    
    # 使用工厂创建 Memcache Session
    try:
        session_store2 = SessionFactory.create_session(
            backend=SessionBackend.MEMCACHE,
            servers=["localhost:11211"],
            key_prefix="session:",
            session_timeout=3600
        )
        
        session2 = session_store2.create()
        session2.data["user"] = "李四"
        session_store2.save(session2)
        
        retrieved2 = session_store2.get(session2.id)
        if retrieved2:
            print(f"Memcache Session: {retrieved2.data}")
        session_store2.close()
    except Exception as e:
        print(f"Memcache Session 创建失败: {e}")
    
    print("\nSession Factory 示例完成\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Database 和 Memcache 缓存/Session 后端示例")
    print("=" * 60)
    
    # 运行所有示例
    example_database_cache()
    example_memcache_cache()
    example_database_session()
    example_memcache_session()
    example_cache_factory()
    example_session_factory()
    
    print("=" * 60)
    print("所有示例运行完成")
    print("=" * 60)