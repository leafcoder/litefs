#!/usr/bin/env python
# coding: utf-8

"""
数据库核心模块，提供数据库连接和会话管理
"""

import os
import time
from typing import Dict, Optional, Type, Union

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, Session, sessionmaker

from ..config import Config
from ..utils import log_error, log_info, log_debug


class Database:
    """
    数据库连接管理类
    """

    def __init__(self, config: Config):
        """
        初始化数据库连接

        Args:
            config: 配置对象
        """
        self.config = config
        self.database_url = self._get_database_url()
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.Base = declarative_base()

    def _get_database_url(self) -> str:
        """
        获取数据库连接 URL

        优先级：
        1. 配置中的 database_url
        2. 环境变量 DATABASE_URL
        3. 默认值 sqlite:///litefs.db

        Returns:
            数据库连接 URL
        """
        # 优先从配置中获取 database_url
        if hasattr(self.config, 'database_url') and self.config.database_url:
            return self.config.database_url

        # 从环境变量获取
        if os.environ.get('DATABASE_URL'):
            return os.environ.get('DATABASE_URL')

        # 默认使用 SQLite
        return 'sqlite:///litefs.db'

    def _create_engine(self):
        """
        创建数据库引擎（优化版）
        
        包含连接池优化：
        - 连接健康检查（pool_pre_ping）
        - 连接回收（pool_recycle）
        - 连接池监控
        - 连接泄漏检测
        
        Returns:
            数据库引擎实例
        """
        # 获取数据库配置
        pool_size = getattr(self.config, 'database_pool_size', 10)
        max_overflow = getattr(self.config, 'database_max_overflow', 20)
        pool_timeout = getattr(self.config, 'database_pool_timeout', 30)
        pool_recycle = getattr(self.config, 'database_pool_recycle', 3600)
        echo = getattr(self.config, 'database_echo', False)
        
        # 判断是否为 SQLite（SQLite 不支持连接池）
        is_sqlite = self.database_url.startswith('sqlite')
        
        # 创建引擎配置
        engine_kwargs = {
            'echo': echo,
        }
        
        # 非 SQLite 数据库启用连接池
        if not is_sqlite:
            engine_kwargs.update({
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'pool_timeout': pool_timeout,
                'pool_recycle': pool_recycle,
                'pool_pre_ping': True,  # 启用连接健康检查
            })
        
        # 创建引擎
        engine = create_engine(self.database_url, **engine_kwargs)
        
        # 添加连接池事件监听
        self._setup_pool_events(engine)
        
        return engine
    
    def _setup_pool_events(self, engine):
        """
        设置连接池事件监听
        
        Args:
            engine: 数据库引擎
        """
        from sqlalchemy import event
        
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """连接创建时触发"""
            connection_record.info['connected_at'] = time.time()
            log_info(None, f"Database connection created: {id(dbapi_connection)}")
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接从池中取出时触发"""
            log_debug(None, f"Database connection checked out: {id(dbapi_connection)}")
        
        @event.listens_for(engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """连接归还到池中时触发"""
            log_debug(None, f"Database connection checked in: {id(dbapi_connection)}")
        
        @event.listens_for(engine, "close")
        def on_close(dbapi_connection, connection_record):
            """连接关闭时触发"""
            log_info(None, f"Database connection closed: {id(dbapi_connection)}")

    def get_session(self) -> Session:
        """
        获取数据库会话

        Returns:
            数据库会话实例
        """
        return self.SessionLocal()

    def create_all(self):
        """
        创建所有数据表
        """
        self.Base.metadata.create_all(bind=self.engine)

    def drop_all(self):
        """
        删除所有数据表
        """
        self.Base.metadata.drop_all(bind=self.engine)
    
    def get_pool_status(self) -> dict:
        """
        获取连接池状态
        
        Returns:
            连接池状态信息字典
        """
        pool = self.engine.pool
        
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalid': pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0
        }
    
    def dispose(self):
        """
        释放连接池资源
        """
        self.engine.dispose()
        log_info(None, "Database connection pool disposed")


class DatabaseManager:
    """
    数据库管理器，用于管理多个数据库连接
    """

    _instance = None
    _databases: Dict[str, Database] = {}

    def __new__(cls):
        """
        单例模式
        """
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_database(cls, config: Config, name: str = 'default') -> Database:
        """
        获取数据库实例

        Args:
            config: 配置对象
            name: 数据库名称

        Returns:
            数据库实例
        """
        if name not in cls._databases:
            cls._databases[name] = Database(config)
        return cls._databases[name]

    @classmethod
    def get_session(cls, name: str = 'default') -> Session:
        """
        获取数据库会话

        Args:
            name: 数据库名称

        Returns:
            数据库会话实例
        """
        if name not in cls._databases:
            raise ValueError(f"Database {name} not initialized")
        return cls._databases[name].get_session()

    @classmethod
    def create_all(cls, name: str = 'default'):
        """
        创建所有数据表

        Args:
            name: 数据库名称
        """
        if name not in cls._databases:
            raise ValueError(f"Database {name} not initialized")
        cls._databases[name].create_all()

    @classmethod
    def drop_all(cls, name: str = 'default'):
        """
        删除所有数据表

        Args:
            name: 数据库名称
        """
        if name not in cls._databases:
            raise ValueError(f"Database {name} not initialized")
        cls._databases[name].drop_all()

    @classmethod
    def close_all(cls):
        """
        关闭所有数据库连接
        """
        for name, db in cls._databases.items():
            try:
                db.engine.dispose()
                log_info(None, f"Database {name} connection closed")
            except Exception as e:
                log_error(None, f"Error closing database {name}: {e}")
        cls._databases.clear()
