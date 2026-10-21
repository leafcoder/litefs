#!/usr/bin/env python
# coding: utf-8

"""
数据库迁移示例

展示 Litefs 基于 Alembic 的数据库版本化迁移能力：

- ``litefs db init`` —— 初始化迁移环境（alembic.ini + migrations/）
- ``litefs db migrate -m "..."`` —— 对比模型与库结构，生成迁移脚本
- ``litefs db upgrade`` —— 应用迁移
- ``litefs db downgrade`` —— 回退迁移
- ``litefs db current`` / ``litefs db history`` —— 查看版本与历史

运行::

    pip install 'litefs[db]'
    python app.py

迁移命令需要在本目录下执行（CLI 会从当前目录的 app.py 读取 database_url）::

    litefs db init
    litefs db migrate -m "初始迁移"
    litefs db upgrade
    litefs db current
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.core import Litefs
from litefs.handlers import Response
from litefs.routing import get, post

# 导入自定义模型：既是 alembic autogenerate 的数据来源，
# 也是运行时建表（create_all）的依据
from models import Base, Category, Product

APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 应用配置
# ============================================================================

app = Litefs(
    host='0.0.0.0',
    port=8084,
    debug=True,
    database_url='sqlite:///app.db',
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))


# ============================================================================
# 建表
#
# 演示场景直接建表；生产环境请使用 `litefs db upgrade` 应用迁移脚本，
# 保证线上库结构与代码版本严格对应。
# ============================================================================

Base.metadata.create_all(bind=app.db.engine)


def _seed_if_empty():
    """首次启动时写入示例数据"""
    session = app.db.get_session()
    try:
        if session.query(Category).count() == 0:
            category = Category(name='默认分类', description='自动创建的示例分类')
            session.add(category)
            session.flush()
            session.add(Product(
                name='Litefs 入门手册',
                price=9900,
                stock=100,
                description='从零开始构建一个生产可用的 Python Web 服务',
                category_id=category.id,
            ))
            session.commit()
    finally:
        session.close()


_seed_if_empty()


# ============================================================================
# 业务路由
# ============================================================================

@get('/', name='index')
def index(request):
    """首页：展示迁移命令与接口列表"""
    return request.render_template('index.html', **{
        'title': 'Litefs 数据库迁移示例',
        'commands': [
            'litefs db init',
            'litefs db migrate -m "初始迁移"',
            'litefs db upgrade',
            'litefs db downgrade',
            'litefs db current',
            'litefs db history',
        ],
        'endpoints': [
            {'path': '/api/products', 'desc': 'GET 商品列表 / POST 创建商品'},
            {'path': '/api/products/{id}', 'desc': 'GET 商品详情'},
            {'path': '/api/categories', 'desc': 'GET 分类列表'},
        ],
    })


@get('/api/products', name='api_product_list')
def api_product_list(request):
    """商品列表"""
    session = app.db.get_session()
    try:
        products = session.query(Product).order_by(Product.id).all()
        data = [{
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'stock': p.stock,
            'category': p.category.name if p.category else None,
        } for p in products]
    finally:
        session.close()

    return Response.json({'total': len(data), 'items': data})


@post('/api/products', name='api_product_create')
def api_product_create(request):
    """创建商品"""
    payload = request.json or {}
    name = (payload.get('name') or '').strip()
    if not name:
        return Response.json({'error': 'name 不能为空'}, status_code=400)

    session = app.db.get_session()
    try:
        product = Product(
            name=name,
            price=int(payload.get('price', 0)),
            stock=int(payload.get('stock', 0)),
            description=payload.get('description'),
            category_id=payload.get('category_id'),
        )
        session.add(product)
        session.commit()
        data = {'id': product.id, 'name': product.name}
    finally:
        session.close()

    return Response.json(data, status_code=201)


@get('/api/products/{id}', name='api_product_detail')
def api_product_detail(request, id):
    """商品详情"""
    session = app.db.get_session()
    try:
        product = session.query(Product).filter_by(id=int(id)).first()
        if product is None:
            return Response.json({'error': '商品不存在'}, status_code=404)
        data = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'stock': product.stock,
            'description': product.description,
            'category': product.category.name if product.category else None,
        }
    finally:
        session.close()

    return Response.json(data)


@get('/api/categories', name='api_category_list')
def api_category_list(request):
    """分类列表"""
    session = app.db.get_session()
    try:
        categories = session.query(Category).order_by(Category.id).all()
        data = [{'id': c.id, 'name': c.name, 'description': c.description} for c in categories]
    finally:
        session.close()

    return Response.json({'total': len(data), 'items': data})


app.register_routes(__name__)


if __name__ == '__main__':
    print('=' * 60)
    print('Litefs 数据库迁移示例')
    print('=' * 60)
    print()
    print('应用地址: http://localhost:8084')
    print('数据库:   sqlite:///app.db')
    print()
    print('迁移命令（在本目录下执行）:')
    print('  litefs db init')
    print('  litefs db migrate -m "初始迁移"')
    print('  litefs db upgrade')
    print('  litefs db current')
    print('=' * 60)

    app.run()
