#!/usr/bin/env python
# coding: utf-8

"""
缓存使用示例

演示如何使用 Litefs 的各种缓存实例
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.cache import (
    MemoryCache,
    TreeCache,
    RedisCache,
    DatabaseCache,
    MemcacheCache,
    CacheFactory,
    CacheBackend,
    CacheManager,
)


def example_1_basic_memory_cache():
    """示例 1: 基本内存缓存使用"""
    print("=" * 60)
    print("示例 1: 基本内存缓存使用")
    print("=" * 60)

    # 创建内存缓存实例
    cache = MemoryCache(max_size=10000)

    # 设置缓存
    cache.put("user:1", {"id": 1, "name": "张三", "age": 25})
    cache.put("user:2", {"id": 2, "name": "李四", "age": 30})

    # 获取缓存
    user1 = cache.get("user:1")
    print(f"获取用户1: {user1}")

    # 检查缓存大小
    print(f"缓存大小: {len(cache)}")

    # 删除缓存
    cache.delete("user:2")
    print(f"删除后缓存大小: {len(cache)}")

    print()


def example_2_tree_cache_with_expiration():
    """示例 2: 树形缓存（支持自动过期）"""
    print("=" * 60)
    print("示例 2: 树形缓存（支持自动过期）")
    print("=" * 60)

    # 创建树形缓存，设置清理周期和过期时间
    cache = TreeCache(
        clean_period=60,          # 每60秒清理一次过期数据
        expiration_time=3600      # 默认过期时间1小时
    )

    # 设置缓存
    cache.put("session:abc123", {"user_id": 1, "login_time": "2024-01-01"})
    cache.put("session:def456", {"user_id": 2, "login_time": "2024-01-01"})

    # 获取缓存
    session = cache.get("session:abc123")
    print(f"获取会话: {session}")

    # 树形缓存会自动清理过期数据
    print(f"缓存大小: {len(cache)}")

    print()


def example_3_cache_factory():
    """示例 3: 使用缓存工厂创建缓存"""
    print("=" * 60)
    print("示例 3: 使用缓存工厂创建缓存")
    print("=" * 60)

    # 使用工厂创建内存缓存
    memory_cache = CacheFactory.create_cache(
        backend=CacheBackend.MEMORY,
        max_size=5000
    )
    memory_cache.put("key1", "value1")
    print(f"内存缓存: {memory_cache.get('key1')}")

    # 使用工厂创建树形缓存
    tree_cache = CacheFactory.create_cache(
        backend=CacheBackend.TREE,
        clean_period=30,
        expiration_time=1800
    )
    tree_cache.put("key2", "value2")
    print(f"树形缓存: {tree_cache.get('key2')}")

    # 使用工厂创建 Redis 缓存
    try:
        redis_cache = CacheFactory.create_cache(
            backend=CacheBackend.REDIS,
            host="localhost",
            port=6379,
            db=0,
            key_prefix="litefs:",
            expiration_time=3600
        )
        redis_cache.put("key3", "value3")
        print(f"Redis 缓存: {redis_cache.get('key3')}")
        redis_cache.close()
    except Exception as e:
        print(f"Redis 缓存不可用: {e}")

    # 使用工厂创建数据库缓存
    db_cache = CacheFactory.create_cache(
        backend=CacheBackend.DATABASE,
        db_path=":memory:",
        table_name="cache",
        expiration_time=3600
    )
    db_cache.put("key4", "value4")
    print(f"数据库缓存: {db_cache.get('key4')}")
    db_cache.close()

    print()


def example_4_global_cache_manager():
    """示例 4: 全局缓存管理器（确保缓存常驻内存）"""
    print("=" * 60)
    print("示例 4: 全局缓存管理器（确保缓存常驻内存）")
    print("=" * 60)

    # 重置缓存（用于测试）
    CacheManager.reset_cache()

    # 获取全局缓存实例
    cache = CacheManager.get_cache(
        backend=CacheBackend.MEMORY,
        cache_key="my_app_cache",
        max_size=10000
    )

    # 设置数据
    cache.put("app_data", {"version": "1.0.0", "status": "running"})

    # 在不同地方获取同一缓存实例
    cache2 = CacheManager.get_cache(
        backend=CacheBackend.MEMORY,
        cache_key="my_app_cache"
    )

    # 验证是同一实例，数据共享
    print(f"是否为同一实例: {cache is cache2}")
    print(f"共享数据: {cache2.get('app_data')}")

    # 使用便捷函数获取会话缓存
    session_cache = CacheManager.get_session_cache(max_size=1000000)
    session_cache.put("user:123", {"name": "张三"})

    # 使用便捷函数获取文件缓存
    file_cache = CacheManager.get_file_cache()
    file_cache.put("/static/style.css", "body { margin: 0; }")

    print(f"会话缓存: {session_cache.get('user:123')}")
    print(f"文件缓存: {file_cache.get('/static/style.css')}")

    # 列出所有缓存
    print(f"所有缓存: {CacheManager.list_caches()}")

    print()


def example_5_cache_in_litefs_app():
    """示例 5: 在 Litefs 应用中使用缓存"""
    print("=" * 60)
    print("示例 5: 在 Litefs 应用中使用缓存")
    print("=" * 60)

    # 创建 Litefs 应用实例
    app = Litefs(
        host='localhost',
        port=9090,
        webroot='./site',
        debug=True
    )

    # 使用应用内置的缓存
    app.caches.put("config:theme", "dark")
    app.caches.put("config:language", "zh-CN")

    print(f"应用配置: {app.caches.get('config:theme')}")
    print(f"应用语言: {app.caches.get('config:language')}")

    # 使用会话缓存
    app.sessions.put("session:xyz", {"user_id": 1, "username": "admin"})
    print(f"会话数据: {app.sessions.get('session:xyz')}")

    # 使用文件缓存
    app.files.put("/index.html", "<html><body>Hello</body></html>")
    print(f"文件缓存: {app.files.get('/index.html')}")

    print()


def example_6_cache_with_complex_data():
    """示例 6: 缓存复杂数据类型"""
    print("=" * 60)
    print("示例 6: 缓存复杂数据类型")
    print("=" * 60)

    cache = MemoryCache(max_size=10000)

    # 缓存字典
    user_data = {
        "id": 1,
        "name": "张三",
        "profile": {
            "age": 25,
            "city": "北京",
            "hobbies": ["读书", "运动", "编程"]
        }
    }
    cache.put("user:1", user_data)
    print(f"缓存字典: {cache.get('user:1')}")

    # 缓存列表
    products = [
        {"id": 1, "name": "商品1", "price": 100},
        {"id": 2, "name": "商品2", "price": 200},
        {"id": 3, "name": "商品3", "price": 300}
    ]
    cache.put("products", products)
    print(f"缓存列表: {cache.get('products')}")

    # 缓存字符串
    cache.put("html_content", "<html><body>Hello World</body></html>")
    print(f"缓存字符串: {cache.get('html_content')}")

    # 缓存数字
    cache.put("counter", 100)
    print(f"缓存数字: {cache.get('counter')}")

    print()


def example_7_cache_best_practices():
    """示例 7: 缓存最佳实践"""
    print("=" * 60)
    print("示例 7: 缓存最佳实践")
    print("=" * 60)

    cache = MemoryCache(max_size=10000)

    # 1. 使用命名空间组织缓存键
    cache.put("user:profile:1", {"name": "张三"})
    cache.put("user:settings:1", {"theme": "dark"})
    cache.put("product:info:1", {"name": "商品1", "price": 100})

    # 2. 缓存计算结果
    def expensive_calculation(n):
        print(f"执行复杂计算: {n}")
        return sum(range(n))

    # 先检查缓存
    result = cache.get("calc:100")
    if result is None:
        result = expensive_calculation(100)
        cache.put("calc:100", result)
    print(f"缓存计算结果: {result}")

    # 3. 使用缓存避免重复查询
    cache.put("db:query:users", [{"id": 1, "name": "张三"}, {"id": 2, "name": "李四"}])
    users = cache.get("db:query:users")
    print(f"缓存查询结果: {users}")

    # 4. 定期清理缓存
    cache.delete("calc:100")
    print(f"清理后缓存大小: {len(cache)}")

    print()


def example_8_redis_cache_advanced():
    """示例 8: Redis 缓存高级用法"""
    print("=" * 60)
    print("示例 8: Redis 缓存高级用法")
    print("=" * 60)

    try:
        cache = RedisCache(
            host="localhost",
            port=6379,
            db=0,
            key_prefix="litefs:",
            expiration_time=3600
        )

        print("\n【基本操作】")
        # 设置缓存
        cache.put("key1", "value1")
        print(f"  设置缓存: key1 = value1")
        print(f"  获取缓存: {cache.get('key1')}")

        # 更新缓存
        cache.put("key1", "updated_value")
        print(f"  更新缓存: key1 = updated_value")
        print(f"  获取更新后的值: {cache.get('key1')}")

        print("\n【键操作】")
        # 检查键是否存在
        exists = cache.exists("key1")
        print(f"  键 key1 是否存在: {exists}")

        # 删除键
        cache.delete("key1")
        print(f"  删除键 key1")
        print(f"  删除后是否存在: {cache.exists('key1')}")

        print("\n【过期时间管理】")
        # 设置带过期时间的缓存
        cache.put("temp_key", "temp_value")
        print(f"  设置缓存: temp_key = temp_value")

        # 查询剩余过期时间
        ttl = cache.ttl("temp_key")
        print(f"  剩余过期时间: {ttl} 秒")

        # 设置新的过期时间
        cache.expire("temp_key", 7200)
        print(f"  设置过期时间为 7200 秒")
        ttl = cache.ttl("temp_key")
        print(f"  新的剩余过期时间: {ttl} 秒")

        print("\n【批量操作】")
        # 批量设置
        cache.set_many({
            "user:1": '{"id": 1, "name": "张三", "age": 25}',
            "user:2": '{"id": 2, "name": "李四", "age": 30}',
            "user:3": '{"id": 3, "name": "王五", "age": 28}'
        })
        print(f"  批量设置 3 个用户数据")

        # 批量获取
        values = cache.get_many(["user:1", "user:2", "user:3"])
        print(f"  批量获取结果:")
        for key, value in values.items():
            print(f"    {key}: {value}")

        # 批量删除
        cache.delete_many(["user:1", "user:2"])
        print(f"  批量删除 user:1 和 user:2")
        print(f"  user:3 是否还存在: {cache.exists('user:3')}")

        print("\n【复杂数据类型】")
        # 缓存字典
        user_data = {
            "id": 100,
            "name": "管理员",
            "roles": ["admin", "editor"],
            "permissions": {"read": True, "write": True}
        }
        import json
        cache.put("admin:user", json.dumps(user_data))
        retrieved = json.loads(cache.get("admin:user"))
        print(f"  缓存字典数据: {retrieved}")

        # 缓存列表
        products = ["商品1", "商品2", "商品3", "商品4", "商品5"]
        cache.put("product:list", json.dumps(products))
        retrieved_list = json.loads(cache.get("product:list"))
        print(f"  缓存列表数据: {retrieved_list}")

        print("\n【缓存统计】")
        print(f"  当前缓存键数量: {len(cache)}")

        print("\n【清除所有缓存】")
        cache.clear()
        print(f"  清除所有缓存完成")
        print(f"  清除后缓存大小: {len(cache)}")

        cache.close()
        print(f"  Redis 连接已关闭")

    except ImportError as e:
        print(f"  Redis 依赖未安装: {e}")
        print(f"  请运行: pip install redis")
    except Exception as e:
        print(f"  Redis 连接失败: {e}")
        print(f"  请确保 Redis 服务已启动: redis-server")

    print()


def example_9_database_cache():
    """示例 9: 数据库缓存"""
    print("=" * 60)
    print("示例 9: 数据库缓存")
    print("=" * 60)

    try:
        print("\n【内存数据库缓存】")
        # 创建数据库缓存（使用内存数据库）
        cache = DatabaseCache(
            db_path=":memory:",
            table_name="cache",
            expiration_time=3600
        )

        print("  创建内存数据库缓存")

        print("\n【基本操作】")
        # 设置缓存
        cache.put("key1", "value1")
        print(f"  设置缓存: key1 = value1")
        print(f"  获取缓存: {cache.get('key1')}")

        # 更新缓存
        cache.put("key1", "updated_value")
        print(f"  更新缓存: key1 = updated_value")
        print(f"  获取更新后的值: {cache.get('key1')}")

        print("\n【键操作】")
        # 检查键是否存在
        exists = cache.exists("key1")
        print(f"  键 key1 是否存在: {exists}")

        # 删除键
        cache.delete("key1")
        print(f"  删除键 key1")
        print(f"  删除后是否存在: {cache.exists('key1')}")

        print("\n【过期时间管理】")
        # 设置带过期时间的缓存
        cache.put("temp_key", "temp_value")
        print(f"  设置缓存: temp_key = temp_value")

        # 查询剩余过期时间
        ttl = cache.ttl("temp_key")
        print(f"  剩余过期时间: {ttl} 秒")

        # 设置新的过期时间
        cache.expire("temp_key", 7200)
        print(f"  设置过期时间为 7200 秒")
        ttl = cache.ttl("temp_key")
        print(f"  新的剩余过期时间: {ttl} 秒")

        print("\n【批量操作】")
        # 批量设置
        cache.set_many({
            "user:1": '{"id": 1, "name": "张三", "age": 25}',
            "user:2": '{"id": 2, "name": "李四", "age": 30}',
            "user:3": '{"id": 3, "name": "王五", "age": 28}'
        })
        print(f"  批量设置 3 个用户数据")

        # 批量获取
        values = cache.get_many(["user:1", "user:2", "user:3"])
        print(f"  批量获取结果:")
        for key, value in values.items():
            print(f"    {key}: {value}")

        # 批量删除
        cache.delete_many(["user:1", "user:2"])
        print(f"  批量删除 user:1 和 user:2")
        print(f"  user:3 是否还存在: {cache.exists('user:3')}")

        print("\n【复杂数据类型】")
        # 缓存字典
        user_data = {
            "id": 100,
            "name": "管理员",
            "roles": ["admin", "editor"],
            "permissions": {"read": True, "write": True}
        }
        import json
        cache.put("admin:user", json.dumps(user_data))
        retrieved = json.loads(cache.get("admin:user"))
        print(f"  缓存字典数据: {retrieved}")

        # 缓存列表
        products = ["商品1", "商品2", "商品3", "商品4", "商品5"]
        cache.put("product:list", json.dumps(products))
        retrieved_list = json.loads(cache.get("product:list"))
        print(f"  缓存列表数据: {retrieved_list}")

        print("\n【缓存统计】")
        print(f"  当前缓存键数量: {len(cache)}")

        print("\n【清除所有缓存】")
        cache.clear()
        print(f"  清除所有缓存完成")
        print(f"  清除后缓存大小: {len(cache)}")

        cache.close()
        print(f"  数据库连接已关闭")

        print("\n【文件数据库缓存】")
        # 创建文件数据库缓存（持久化存储）
        file_cache = DatabaseCache(
            db_path="/tmp/litefs_cache.db",
            table_name="cache",
            expiration_time=3600
        )
        print(f"  创建文件数据库缓存: /tmp/litefs_cache.db")

        file_cache.put("persistent_key", "persistent_value")
        print(f"  设置持久化缓存: persistent_key = persistent_value")
        print(f"  获取持久化缓存: {file_cache.get('persistent_key')}")

        file_cache.close()
        print(f"  数据库连接已关闭")
        print(f"  数据已持久化到文件，下次启动仍可访问")

    except Exception as e:
        print(f"  数据库缓存错误: {e}")

    print()


def example_10_memcache_cache():
    """示例 10: Memcache 缓存"""
    print("=" * 60)
    print("示例 10: Memcache 缓存")
    print("=" * 60)

    try:
        print("\n【创建 Memcache 缓存】")
        # 创建 Memcache 缓存
        cache = MemcacheCache(
            servers=["localhost:11211"],
            key_prefix="litefs:",
            expiration_time=3600
        )
        print("  连接到 Memcache 服务器: localhost:11211")

        print("\n【基本操作】")
        # 设置缓存
        cache.put("key1", "value1")
        print(f"  设置缓存: key1 = value1")
        print(f"  获取缓存: {cache.get('key1')}")

        # 更新缓存
        cache.put("key1", "updated_value")
        print(f"  更新缓存: key1 = updated_value")
        print(f"  获取更新后的值: {cache.get('key1')}")

        print("\n【键操作】")
        # 检查键是否存在
        exists = cache.exists("key1")
        print(f"  键 key1 是否存在: {exists}")

        # 删除键
        cache.delete("key1")
        print(f"  删除键 key1")
        print(f"  删除后是否存在: {cache.exists('key1')}")

        print("\n【过期时间管理】")
        # 设置带过期时间的缓存
        cache.put("temp_key", "temp_value")
        print(f"  设置缓存: temp_key = temp_value")

        # 查询剩余过期时间
        ttl = cache.ttl("temp_key")
        print(f"  剩余过期时间: {ttl} 秒")

        # 设置新的过期时间
        cache.expire("temp_key", 7200)
        print(f"  设置过期时间为 7200 秒")
        ttl = cache.ttl("temp_key")
        print(f"  新的剩余过期时间: {ttl} 秒")

        print("\n【批量操作】")
        # 批量设置
        cache.set_many({
            "user:1": '{"id": 1, "name": "张三", "age": 25}',
            "user:2": '{"id": 2, "name": "李四", "age": 30}',
            "user:3": '{"id": 3, "name": "王五", "age": 28}'
        })
        print(f"  批量设置 3 个用户数据")

        # 批量获取
        values = cache.get_many(["user:1", "user:2", "user:3"])
        print(f"  批量获取结果:")
        for key, value in values.items():
            print(f"    {key}: {value}")

        # 批量删除
        cache.delete_many(["user:1", "user:2"])
        print(f"  批量删除 user:1 和 user:2")
        print(f"  user:3 是否还存在: {cache.exists('user:3')}")

        print("\n【复杂数据类型】")
        # 缓存字典
        user_data = {
            "id": 100,
            "name": "管理员",
            "roles": ["admin", "editor"],
            "permissions": {"read": True, "write": True}
        }
        import json
        cache.put("admin:user", json.dumps(user_data))
        retrieved = json.loads(cache.get("admin:user"))
        print(f"  缓存字典数据: {retrieved}")

        # 缓存列表
        products = ["商品1", "商品2", "商品3", "商品4", "商品5"]
        cache.put("product:list", json.dumps(products))
        retrieved_list = json.loads(cache.get("product:list"))
        print(f"  缓存列表数据: {retrieved_list}")

        print("\n【缓存统计】")
        print(f"  当前缓存键数量: {len(cache)}")

        print("\n【清除所有缓存】")
        cache.clear()
        print(f"  清除所有缓存完成")
        print(f"  清除后缓存大小: {len(cache)}")

        cache.close()
        print(f"  Memcache 连接已关闭")

    except ImportError as e:
        print(f"  Memcache 依赖未安装: {e}")
        print(f"  请运行: pip install python-memcached")
    except Exception as e:
        print(f"  Memcache 连接失败: {e}")
        print(f"  请确保 Memcache 服务已启动: memcached -d -m 64 -p 11211")

    print()


def example_11_cache_sharing_across_instances():
    """示例 11: 在多个 Litefs 实例间共享缓存"""
    print("=" * 60)
    print("示例 11: 在多个 Litefs 实例间共享缓存")
    print("=" * 60)

    # 重置缓存
    CacheManager.reset_cache()

    # 创建第一个应用实例
    app1 = Litefs(
        host='localhost',
        port=9090,
        webroot='./site',
    )

    # 在第一个实例中设置缓存
    app1.caches.put("shared_key", "shared_value")
    print(f"实例1设置缓存: shared_key = shared_value")

    # 创建第二个应用实例
    app2 = Litefs(
        host='localhost',
        port=9091,
        webroot='./site',
    )

    # 第二个实例可以访问第一个实例设置的缓存
    value = app2.caches.get("shared_key")
    print(f"实例2获取缓存: {value}")

    # 验证是同一缓存实例
    print(f"是否为同一缓存实例: {app1.caches is app2.caches}")

    print()


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Litefs 缓存使用示例" + " " * 28 + "║")
    print("╚" + "═" * 58 + "╝")
    print("\n")

    example_1_basic_memory_cache()
    example_2_tree_cache_with_expiration()
    example_3_cache_factory()
    example_4_global_cache_manager()
    example_5_cache_in_litefs_app()
    example_6_cache_with_complex_data()
    example_7_cache_best_practices()
    example_8_redis_cache_advanced()
    example_9_database_cache()
    example_10_memcache_cache()
    example_11_cache_sharing_across_instances()

    print("=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == '__main__':
    main()
