#!/usr/bin/env python
# coding: utf-8

"""
投票应用数据库模型

定义了投票系统的核心数据结构。
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Poll(Base):
    """
    投票主题模型
    """
    __tablename__ = 'polls'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment='投票标题')
    description = Column(Text, comment='投票描述')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), comment='更新时间')
    
    options = relationship('Option', backref='poll', cascade='all, delete-orphan')
    votes = relationship('Vote', backref='poll', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Poll {self.title}>'
    
    @property
    def total_votes(self):
        """获取总投票数"""
        return sum(option.vote_count for option in self.options)


class Option(Base):
    """
    投票选项模型
    """
    __tablename__ = 'options'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False, comment='所属投票ID')
    text = Column(String(200), nullable=False, comment='选项文本')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    
    votes = relationship('Vote', backref='option', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Option {self.text}>'
    
    @property
    def vote_count(self):
        """获取选项投票数"""
        return len(self.votes)


class Vote(Base):
    """
    投票记录模型
    """
    __tablename__ = 'votes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    poll_id = Column(Integer, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False, comment='所属投票ID')
    option_id = Column(Integer, ForeignKey('options.id', ondelete='CASCADE'), nullable=False, comment='所选选项ID')
    ip_address = Column(String(45), comment='投票者IP地址')
    user_agent = Column(String(500), comment='用户代理')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='投票时间')
    
    def __repr__(self):
        return f'<Vote {self.id}>'
