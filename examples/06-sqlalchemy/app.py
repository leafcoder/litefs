#!/usr/bin/env python
# coding: utf-8

"""
SQLAlchemy 示例应用

演示如何在 Litefs 中使用 SQLAlchemy 进行数据库操作。
"""

import os
import sys
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.routing import get, post
from litefs.middleware import LoggingMiddleware
from models import Base, Post

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 创建应用实例
app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
).add_middleware(LoggingMiddleware)

# 配置 SQLAlchemy
DATABASE_URL = 'sqlite:///blog.db'
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 依赖项：获取数据库会话
def get_db():
    """
    获取数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 首页 - 显示所有文章
@get('/', name='index')
def index(request):
    """
    首页视图，显示所有文章
    """
    db = next(get_db())
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    
    return request.render_template('index.html',
        posts=posts,
        message=request.session.get('message'),
        message_type=request.session.get('message_type')
    )

# 创建文章页面
@get('/create', name='create')
def create(request):
    """
    创建文章页面
    """
    return request.render_template('create.html')

# 创建文章
@post('/create', name='create_post')
def create_post(request):
    """
    创建文章处理函数
    """
    # 直接创建数据库会话，不使用 yield 机制
    db = SessionLocal()
    try:
        # 获取表单数据
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            raise ValueError('标题和内容不能为空')
        
        # 创建文章
        post = Post(title=title, content=content)
        db.add(post)
        db.commit()
        db.refresh(post)
        
        # 设置成功消息
        request.session['message'] = '文章创建成功！'
        request.session['message_type'] = 'success'
        
    except Exception as e:
        # 设置错误消息
        request.session['message'] = f'创建文章失败：{str(e)}'
        request.session['message_type'] = 'error'
        # 发生错误时回滚事务
        db.rollback()
    finally:
        # 关闭数据库会话
        db.close()
    
    # 重定向到首页
    request.start_response(302, [('Location', '/')])
    return ''

# 查看文章
@get('/view/{id}', name='view')
def view(request, id):
    """
    查看文章详情
    """
    try:
        db = next(get_db())
        post = db.query(Post).filter(Post.id == id).first()
        
        if not post:
            request.session['message'] = '文章不存在！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', '/')])
            return ''
        
        return request.render_template('view.html', post=post)
        
    except Exception as e:
        request.session['message'] = f'查看文章失败：{str(e)}'
        request.session['message_type'] = 'error'
        request.start_response(302, [('Location', '/')])
        return ''

# 编辑文章页面
@get('/edit/{id}', name='edit')
def edit(request, id):
    """
    编辑文章页面
    """
    try:
        db = next(get_db())
        post = db.query(Post).filter(Post.id == id).first()
        
        if not post:
            request.session['message'] = '文章不存在！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', '/')])
            return ''
        
        return request.render_template('edit.html', post=post)
        
    except Exception as e:
        request.session['message'] = f'编辑文章失败：{str(e)}'
        request.session['message_type'] = 'error'
        request.start_response(302, [('Location', '/')])
        return ''

# 更新文章
@post('/edit/{id}', name='update')
def update(request, id):
    """
    更新文章处理函数
    """
    try:
        # 获取表单数据
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            raise ValueError('标题和内容不能为空')
        
        # 更新文章
        db = next(get_db())
        post = db.query(Post).filter(Post.id == id).first()
        
        if not post:
            raise ValueError('文章不存在')
        
        post.title = title
        post.content = content
        post.updated_at = datetime.utcnow()
        
        db.commit()
        
        # 设置成功消息
        request.session['message'] = '文章更新成功！'
        request.session['message_type'] = 'success'
        
    except Exception as e:
        # 设置错误消息
        request.session['message'] = f'更新文章失败：{str(e)}'
        request.session['message_type'] = 'error'
    
    # 重定向到首页
    request.start_response(302, [('Location', '/')])
    return ''

# 删除文章
@get('/delete/{id}', name='delete')
def delete(request, id):
    """
    删除文章
    """
    try:
        db = next(get_db())
        post = db.query(Post).filter(Post.id == id).first()
        
        if not post:
            raise ValueError('文章不存在')
        
        db.delete(post)
        db.commit()
        
        # 设置成功消息
        request.session['message'] = '文章删除成功！'
        request.session['message_type'] = 'success'
        
    except Exception as e:
        # 设置错误消息
        request.session['message'] = f'删除文章失败：{str(e)}'
        request.session['message_type'] = 'error'
    
    # 重定向到首页
    request.start_response(302, [('Location', '/')])
    return ''

if __name__ == '__main__':
    # 注册路由
    app.register_routes(__name__)
    app.run()