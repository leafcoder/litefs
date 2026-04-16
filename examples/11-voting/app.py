#!/usr/bin/env python
# coding: utf-8

"""
投票示例应用

演示如何在 Litefs 中使用 SQLAlchemy 进行数据库操作和投票功能。
"""

import os
import sys
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from litefs import Litefs
from litefs.routing import get, post, route
from litefs.middleware import LoggingMiddleware

from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship, backref

from models import Base, Poll, Option, Vote


app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=False,
    database_url='sqlite:///polls.db'
).add_middleware(LoggingMiddleware)

app.add_static('/static', 'static')


def get_db():
    """
    获取数据库会话
    """
    db = app.db_session()
    try:
        yield db
    finally:
        db.close()


@route('/init', name='init')
def init_database(request):
    """
    初始化数据库表
    """
    app.create_all_tables()
    return '数据库表初始化完成！'


@route('/', name='index')
def index(request):
    """
    首页 - 显示所有投票
    """
    db = app.db_session()
    try:
        polls = db.query(Poll).order_by(Poll.created_at.desc()).all()
        
        return request.render_template('index.html', polls=polls)
    finally:
        db.close()


@route('/poll/create', name='create_poll_form')
def create_poll_form(request):
    """
    创建投票表单
    """
    return request.render_template('create_poll.html')


@post('/poll/create', name='create_poll_post')
def create_poll(request):
    """
    创建投票处理
    """
    db = app.db_session()
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        options = request.form.get('options')
        
        if not title or not options:
            request.session['message'] = '标题和选项不能为空！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', '/poll/create')])
            return ''
        
        poll = Poll(
            title=title,
            description=description or '',
            created_at=datetime.utcnow()
        )
        
        db.add(poll)
        db.commit()
        db.refresh(poll)
        
        for option_text in options:
            if option_text.strip():
                option = Option(
                    poll_id=poll.id,
                    text=option_text.strip(),
                    created_at=datetime.utcnow()
                )
                db.add(option)
        
        db.commit()
        
        request.session['message'] = '投票创建成功！'
        request.session['message_type'] = 'success'
        
    except Exception as e:
        request.session['message'] = f'创建投票失败：{str(e)}'
        request.session['message_type'] = 'error'
        db.rollback()
    finally:
        db.close()
    
    request.start_response(302, [('Location', '/')])
    return ''


@route('/poll/{id}', name='poll_detail')
def poll_detail(request, id):
    """
    投票详情页面
    """
    db = app.db_session()
    try:
        poll = db.query(Poll).filter(Poll.id == id).first()
        
        if not poll:
            request.session['message'] = '投票不存在！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', '/')])
            return ''
        
        return request.render_template('poll_detail.html', poll=poll)
    finally:
        db.close()


@post('/poll/{id}/vote', name='vote')
def vote(request, id):
    """
    投票处理
    """
    db = app.db_session()
    try:
        poll = db.query(Poll).filter(Poll.id == id).first()
        
        if not poll:
            request.session['message'] = '投票不存在！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', '/')])
            return ''
        
        option_id = request.form.get('option_id')
        
        if not option_id:
            request.session['message'] = '请选择一个选项！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', f'/poll/{id}')])
            return ''
        
        option = db.query(Option).filter(Option.id == int(option_id)).first()
        
        if not option:
            request.session['message'] = '选项不存在！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', f'/poll/{id}')])
            return ''
        
        vote = Vote(
            poll_id=poll.id,
            option_id=option.id,
            ip_address=request.environ.get('REMOTE_ADDR', 'unknown'),
            user_agent=request.environ.get('HTTP_USER_AGENT', '')
        )
        
        db.add(vote)
        db.commit()
        
        request.session['message'] = '投票成功！'
        request.session['message_type'] = 'success'
        request.session['poll_id'] = poll.id
        
    except Exception as e:
        request.session['message'] = f'投票失败：{str(e)}'
        request.session['message_type'] = 'error'
        db.rollback()
    finally:
        db.close()
    
    request.start_response(302, [('Location', f'/poll/{id}/result')])
    return ''


@route('/poll/{id}/result', name='poll_result')
def poll_result(request, id):
    """
    投票结果页面
    """
    db = app.db_session()
    try:
        poll = db.query(Poll).filter(Poll.id == id).first()
        
        if not poll:
            request.session['message'] = '投票不存在！'
            request.session['message_type'] = 'error'
            request.start_response(302, [('Location', '/')])
            return ''
        
        options = db.query(Option).filter(Option.poll_id == id).all()
        
        total_votes = db.query(func.count(Vote.id)).filter(Vote.poll_id == id).scalar()
        
        option_votes = []
        for option in options:
            count = db.query(func.count(Vote.id)).filter(Vote.option_id == option.id).scalar()
            percentage = (count / total_votes * 100) if total_votes > 0 else 0
            option_votes.append({
                'option': option,
                'count': count,
                'percentage': percentage
            })
        
        return request.render_template('result.html', poll=poll, option_votes=option_votes, total_votes=total_votes)
    finally:
        db.close()


if __name__ == '__main__':
    # 创建数据库表（使用 models.py 中的 Base）
    from models import Base
    Base.metadata.create_all(bind=app.db.engine)
    
    # 注册路由
    app.register_routes(__name__)
    app.run()
