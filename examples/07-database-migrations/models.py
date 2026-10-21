#!/usr/bin/env python
# coding: utf-8

"""
数据库迁移示例 —— 数据模型

模型统一挂载在 ``litefs.database.models.Base`` 上，
这是 Alembic ``autogenerate`` 使用的 ``target_metadata``，
因此只要本模块被导入，迁移脚本就能感知到表结构变化。

注意：本文件必须位于项目根目录（与 app.py 同级），
``litefs db init`` 才会自动把它填入 ``migrations/env.py`` 的导入位置。
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from litefs.database.models import Base, TimestampMixin


class Category(Base, TimestampMixin):
    """商品分类"""

    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True, comment='分类名称')
    description = Column(String(255), nullable=True, comment='分类描述')

    products = relationship('Product', back_populates='category', lazy='selectin')


class Product(Base, TimestampMixin):
    """商品"""

    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, comment='商品名称')
    price = Column(Integer, nullable=False, default=0, comment='价格（分）')
    stock = Column(Integer, nullable=False, default=0, comment='库存数量')
    description = Column(Text, nullable=True, comment='商品描述')
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True, comment='所属分类')

    category = relationship('Category', back_populates='products', lazy='selectin')


__all__ = ['Base', 'Category', 'Product']
