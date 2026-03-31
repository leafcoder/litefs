#!/usr/bin/env python
# coding: utf-8

"""
Session 各后端使用示例

演示如何使用 Litefs 的各种 Session 后端
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.session import (
    DatabaseSession, RedisSession, MemcacheSession,
    SessionFactory, SessionBackend
)

def example_1_database_session_direct():
    """示例 1: 直接使用 Database Session"""
    print("=" * 60)
    print("示例 1: 直接使用 Database Session")
    print("=" * 60)

    try:
        # 创建 Database Session 存储
        session_store = DatabaseSession(
            db_path=":memory:",  # 使用内存数据库
            table_name="sessions",
            expiration_time=3600
        )

        # 创建新 Session
        from litefs.session.session import Session
        import uuid
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        print(f"创建 Session: {session.id}")

        # 设置 Session 数据
        session["user_id"] = 123
        session["username"] = "test_user"
        session["email"] = "test@example.com"
        session["role"] = "admin"
        print("设置 Session 数据: user_id, username, email, role")

        # 保存 Session
        session_store.put(session.id, session)
        print("保存 Session 到数据库")

        # 调试：检查数据库中的数据
        print("调试：检查数据库中的数据")
        conn = session_store._connect()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM sessions WHERE session_id = ?", (session.id,))
        row = cursor.fetchone()
        if row:
            print(f"调试：数据库中存在 Session，data={row['data']}")
        else:
            print("调试：数据库中不存在 Session")

        # 获取 Session
        retrieved_session = session_store.get(session.id)
        if retrieved_session:
            print(f"获取 Session: {retrieved_session.id}")
            print(f"Session 数据: {dict(retrieved_session)}")
        else:
            print("无法获取 Session")

        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")

        # 设置 Session 过期时间
        expire_result = session_store.expire(session.id, 1800)  # 30分钟
        print(f"设置 Session 过期时间: {expire_result}")

        # 获取 Session 剩余过期时间
        ttl = session_store.ttl(session.id)
        print(f"Session 剩余过期时间: {ttl} 秒")

        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")

        # 检查 Session 是否存在
        exists_after_delete = session_store.exists(session.id)
        print(f"删除后 Session 是否存在: {exists_after_delete}")

        # 关闭连接
        session_store.close()
        print("关闭数据库连接")

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_2_redis_session_direct():
    """示例 2: 直接使用 Redis Session"""
    print("=" * 60)
    print("示例 2: 直接使用 Redis Session")
    print("=" * 60)

    try:
        # 创建 Redis Session 存储
        session_store = RedisSession(
            host="localhost",
            port=6379,
            db=0,
            key_prefix="session:",
            expiration_time=3600
        )

        # 创建新 Session
        from litefs.session.session import Session
        import uuid
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        print(f"创建 Session: {session.id}")

        # 设置 Session 数据
        session["user_id"] = 456
        session["username"] = "redis_user"
        session["cart"] = [
            {"id": 1, "name": "商品1", "price": 99.99},
            {"id": 2, "name": "商品2", "price": 199.99}
        ]
        print("设置 Session 数据: user_id, username, cart")

        # 保存 Session
        session_store.put(session.id, session)
        print("保存 Session 到 Redis")

        # 获取 Session
        retrieved_session = session_store.get(session.id)
        if retrieved_session:
            print(f"获取 Session: {retrieved_session.id}")
            print(f"Session 数据: {dict(retrieved_session)}")
        else:
            print("无法获取 Session")

        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")

        # 设置 Session 过期时间
        expire_result = session_store.expire(session.id, 1800)  # 30分钟
        print(f"设置 Session 过期时间: {expire_result}")

        # 获取 Session 剩余过期时间
        ttl = session_store.ttl(session.id)
        print(f"Session 剩余过期时间: {ttl} 秒")

        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")

        # 检查 Session 是否存在
        exists_after_delete = session_store.exists(session.id)
        print(f"删除后 Session 是否存在: {exists_after_delete}")

        # 关闭连接
        session_store.close()
        print("关闭 Redis 连接")

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_3_memcache_session_direct():
    """示例 3: 直接使用 Memcache Session"""
    print("=" * 60)
    print("示例 3: 直接使用 Memcache Session")
    print("=" * 60)

    try:
        # 创建 Memcache Session 存储
        session_store = MemcacheSession(
            servers=["localhost:11211"],
            key_prefix="session:",
            expiration_time=3600
        )

        # 创建新 Session
        from litefs.session.session import Session
        import uuid
        session_id = str(uuid.uuid4())
        session = Session(session_id)
        print(f"创建 Session: {session.id}")

        # 设置 Session 数据
        session["user_id"] = 789
        session["username"] = "memcache_user"
        session["preferences"] = {
            "theme": "dark",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai"
        }
        print("设置 Session 数据: user_id, username, preferences")

        # 保存 Session
        session_store.put(session.id, session)
        print("保存 Session 到 Memcache")

        # 获取 Session
        retrieved_session = session_store.get(session.id)
        if retrieved_session:
            print(f"获取 Session: {retrieved_session.id}")
            print(f"Session 数据: {dict(retrieved_session)}")
        else:
            print("无法获取 Session")

        # 检查 Session 是否存在
        exists = session_store.exists(session.id)
        print(f"Session 是否存在: {exists}")

        # 设置 Session 过期时间
        expire_result = session_store.expire(session.id, 1800)  # 30分钟
        print(f"设置 Session 过期时间: {expire_result}")

        # 获取 Session 剩余过期时间
        ttl = session_store.ttl(session.id)
        print(f"Session 剩余过期时间: {ttl} 秒")

        # 删除 Session
        session_store.delete(session.id)
        print(f"删除 Session: {session.id}")

        # 检查 Session 是否存在
        exists_after_delete = session_store.exists(session.id)
        print(f"删除后 Session 是否存在: {exists_after_delete}")

        # 关闭连接
        session_store.close()
        print("关闭 Memcache 连接")

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_4_session_factory():
    """示例 4: 使用 Session 工厂创建不同后端的 Session"""
    print("=" * 60)
    print("示例 4: 使用 Session 工厂创建不同后端的 Session")
    print("=" * 60)

    try:
        # 使用 Session 工厂创建 Database Session
        print("创建 Database Session...")
        from litefs.session.session import Session
        import uuid
        db_session_store = SessionFactory.create_session(
            backend=SessionBackend.DATABASE,
            db_path=":memory:",
            expiration_time=3600
        )
        session_id = str(uuid.uuid4())
        db_session = Session(session_id)
        db_session["test"] = "database session"
        db_session_store.put(session_id, db_session)
        print(f"Database Session 创建成功: {db_session.id}")
        db_session_store.close()

        # 使用 Session 工厂创建 Redis Session
        print("\n创建 Redis Session...")
        redis_session_store = SessionFactory.create_session(
            backend=SessionBackend.REDIS,
            host="localhost",
            port=6379,
            db=0,
            expiration_time=3600
        )
        session_id = str(uuid.uuid4())
        redis_session = Session(session_id)
        redis_session["test"] = "redis session"
        redis_session_store.put(session_id, redis_session)
        print(f"Redis Session 创建成功: {redis_session.id}")
        redis_session_store.close()

        # 使用 Session 工厂创建 Memcache Session
        print("\n创建 Memcache Session...")
        memcache_session_store = SessionFactory.create_session(
            backend=SessionBackend.MEMCACHE,
            servers=["localhost:11211"],
            expiration_time=3600
        )
        session_id = str(uuid.uuid4())
        memcache_session = Session(session_id)
        memcache_session["test"] = "memcache session"
        memcache_session_store.put(session_id, memcache_session)
        print(f"Memcache Session 创建成功: {memcache_session.id}")
        memcache_session_store.close()

    except Exception as e:
        print(f"错误: {e}")

    print()

def example_5_web_app_session():
    """示例 5: 在 Web 应用中使用 Session"""
    print("=" * 60)
    print("示例 5: 在 Web 应用中使用 Session")
    print("=" * 60)
    print("启动 Web 应用，访问 http://localhost:8085/session-demo")
    print("=" * 60)

    # 创建 Litefs 应用实例
    app = Litefs(
        host='0.0.0.0',
        port=8085,
        webroot='./examples/12-session-backends/site',
        debug=True,
        database_path='data.db',
        session_backend='database',
        session_expiration_time=3600
    )

    # 运行应用
    app.run()


def main():
    """主函数"""
    print("Litefs Session 各后端使用示例")
    print("=" * 60)
    print("本示例演示如何使用不同后端的 Session 存储")
    print("包括直接使用和在 Web 应用中使用")
    print("=" * 60)
    print()

    # 运行示例
    example_1_database_session_direct()
    example_2_redis_session_direct()
    example_3_memcache_session_direct()
    example_4_session_factory()
    example_5_web_app_session()


if __name__ == '__main__':
    main()
