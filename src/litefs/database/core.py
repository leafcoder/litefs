#!/usr/bin/env python
# coding: utf-8

"""
数据库核心模块，提供数据库连接和会话管理
"""

import os
from typing import Dict, Optional, Type, Union

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from ..config import Config
from ..utils import log_error, log_info


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
        创建数据库引擎

        Returns:
            数据库引擎实例
        """
        # 获取数据库配置
        pool_size = getattr(self.config, 'database_pool_size', 5)
        max_overflow = getattr(self.config, 'database_max_overflow', 10)
        pool_timeout = getattr(self.config, 'database_pool_timeout', 30)
        echo = getattr(self.config, 'database_echo', False)

        # 创建引擎
        engine = create_engine(
            self.database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            echo=echo
        )

        return engine

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
