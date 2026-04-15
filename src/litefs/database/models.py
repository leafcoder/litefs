#!/usr/bin/env python
# coding: utf-8

"""
数据库模型模块，提供基础模型类
"""

from sqlalchemy import Column, DateTime, func
from sqlalchemy.orm import declarative_base


# 创建基础模型类
Base = declarative_base()


class TimestampMixin:
    """
    时间戳混入类，提供创建时间和更新时间字段
    """
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
