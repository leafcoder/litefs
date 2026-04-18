#!/usr/bin/env python
# coding: utf-8

"""
博客系统数据模型

使用内存存储模拟数据库，生产环境应替换为真实数据库
"""

import json
import os
import time
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass, field, asdict


def hash_password(password: str, salt: str = None) -> tuple:
    """密码哈希"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """验证密码"""
    new_hash, _ = hash_password(password, salt)
    return new_hash == hashed


@dataclass
class User:
    """用户模型"""
    id: int
    username: str
    password_hash: str
    password_salt: str
    email: str = ""
    nickname: str = ""
    avatar: str = ""
    bio: str = ""
    created_at: str = ""
    is_admin: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        return cls(**data)


@dataclass
class Post:
    """文章模型"""
    id: int
    title: str
    content: str
    summary: str = ""
    author_id: int = 0
    author_name: str = ""
    category: str = "默认"
    tags: List[str] = field(default_factory=list)
    views: int = 0
    likes: int = 0
    status: str = "published"
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Post':
        return cls(**data)


@dataclass
class Comment:
    """评论模型"""
    id: int
    post_id: int
    user_id: int
    user_name: str
    content: str
    parent_id: int = 0
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PageView:
    """访问统计"""
    id: int
    path: str
    user_id: int = 0
    ip: str = ""
    user_agent: str = ""
    created_at: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


class Database:
    """数据库管理"""
    
    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.users: Dict[int, User] = {}
        self.posts: Dict[int, Post] = {}
        self.comments: Dict[int, Comment] = {}
        self.page_views: List[PageView] = []
        
        self._next_user_id = 1
        self._next_post_id = 1
        self._next_comment_id = 1
        self._next_pv_id = 1
        
        self._load_data()
        self._init_admin()
    
    def _load_data(self):
        """加载数据"""
        users_file = os.path.join(self.data_dir, 'users.json')
        posts_file = os.path.join(self.data_dir, 'posts.json')
        
        if os.path.exists(users_file):
            with open(users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.users = {int(k): User.from_dict(v) for k, v in data.get('users', {}).items()}
                self._next_user_id = data.get('next_user_id', 1)
        
        if os.path.exists(posts_file):
            with open(posts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.posts = {int(k): Post.from_dict(v) for k, v in data.get('posts', {}).items()}
                self._next_post_id = data.get('next_post_id', 1)
    
    def _save_data(self):
        """保存数据"""
        users_file = os.path.join(self.data_dir, 'users.json')
        posts_file = os.path.join(self.data_dir, 'posts.json')
        
        with open(users_file, 'w', encoding='utf-8') as f:
            json.dump({
                'users': {k: v.to_dict() for k, v in self.users.items()},
                'next_user_id': self._next_user_id
            }, f, ensure_ascii=False, indent=2)
        
        with open(posts_file, 'w', encoding='utf-8') as f:
            json.dump({
                'posts': {k: v.to_dict() for k, v in self.posts.items()},
                'next_post_id': self._next_post_id
            }, f, ensure_ascii=False, indent=2)
    
    def _init_admin(self):
        """初始化管理员"""
        if not self.users:
            password_hash, salt = hash_password('admin123')
            admin = User(
                id=1,
                username='admin',
                password_hash=password_hash,
                password_salt=salt,
                email='admin@example.com',
                nickname='管理员',
                is_admin=True,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            self.users[1] = admin
            self._next_user_id = 2
            
            for i, (title, content, category) in enumerate([
                ('欢迎使用 Litefs 博客系统', 'Litefs 是一个轻量级的 Python Web 框架，本博客系统展示了其完整的 Web 开发能力。\n\n## 功能特性\n\n- 用户注册与登录\n- 文章发布与管理\n- 评论系统\n- 访问统计\n\n感谢使用！', '公告'),
                ('Litefs 框架入门指南', '## 安装\n\n```bash\npip install litefs\n```\n\n## 快速开始\n\n```python\nfrom litefs import Litefs\n\napp = Litefs()\n\n@app.route(\'/\')\ndef index(request):\n    return \'Hello World\'\n\napp.run()\n```\n\n更多内容请查看官方文档。', '教程'),
                ('Python Web 开发最佳实践', '## 1. 项目结构\n\n保持项目结构清晰，分离关注点。\n\n## 2. 安全性\n\n- 使用 HTTPS\n- 防止 SQL 注入\n- 防止 XSS 攻击\n- 使用 CSRF 保护\n\n## 3. 性能优化\n\n- 使用缓存\n- 数据库优化\n- 异步处理', '技术'),
            ], 1):
                post = Post(
                    id=i,
                    title=title,
                    content=content,
                    summary=content[:100] + '...',
                    author_id=1,
                    author_name='admin',
                    category=category,
                    views=10 * i,
                    likes=i,
                    created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    updated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
                self.posts[i] = post
            self._next_post_id = 4
            self._save_data()
    
    # 用户操作
    def create_user(self, username: str, password: str, email: str = "", nickname: str = "") -> Optional[User]:
        """创建用户"""
        if self.get_user_by_username(username):
            return None
        
        password_hash, salt = hash_password(password)
        user = User(
            id=self._next_user_id,
            username=username,
            password_hash=password_hash,
            password_salt=salt,
            email=email,
            nickname=nickname or username,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        self.users[user.id] = user
        self._next_user_id += 1
        self._save_data()
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """获取用户"""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """更新用户"""
        user = self.users.get(user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ['id', 'password_hash', 'password_salt']:
                setattr(user, key, value)
        
        self._save_data()
        return user
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """更新密码"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.password_hash, user.password_salt = hash_password(new_password)
        self._save_data()
        return True
    
    def verify_user(self, username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        
        if verify_password(password, user.password_hash, user.password_salt):
            return user
        return None
    
    # 文章操作
    def create_post(self, title: str, content: str, author_id: int, author_name: str, 
                    category: str = "默认", tags: List[str] = None, summary: str = "") -> Post:
        """创建文章"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        post = Post(
            id=self._next_post_id,
            title=title,
            content=content,
            summary=summary or content[:200],
            author_id=author_id,
            author_name=author_name,
            category=category,
            tags=tags or [],
            created_at=now,
            updated_at=now
        )
        self.posts[post.id] = post
        self._next_post_id += 1
        self._save_data()
        return post
    
    def get_post(self, post_id: int) -> Optional[Post]:
        """获取文章"""
        return self.posts.get(post_id)
    
    def get_posts(self, page: int = 1, per_page: int = 10, category: str = None, 
                  author_id: int = None, status: str = "published") -> List[Post]:
        """获取文章列表"""
        posts = list(self.posts.values())
        
        if status:
            posts = [p for p in posts if p.status == status]
        if category:
            posts = [p for p in posts if p.category == category]
        if author_id:
            posts = [p for p in posts if p.author_id == author_id]
        
        posts.sort(key=lambda x: x.created_at, reverse=True)
        
        start = (page - 1) * per_page
        return posts[start:start + per_page]
    
    def update_post(self, post_id: int, **kwargs) -> Optional[Post]:
        """更新文章"""
        post = self.posts.get(post_id)
        if not post:
            return None
        
        for key, value in kwargs.items():
            if hasattr(post, key) and key not in ['id', 'author_id', 'created_at']:
                setattr(post, key, value)
        
        post.updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_data()
        return post
    
    def delete_post(self, post_id: int) -> bool:
        """删除文章"""
        if post_id in self.posts:
            del self.posts[post_id]
            self._save_data()
            return True
        return False
    
    def increment_views(self, post_id: int):
        """增加浏览量"""
        post = self.posts.get(post_id)
        if post:
            post.views += 1
            self._save_data()
    
    # 访问统计
    def record_page_view(self, path: str, user_id: int = 0, ip: str = "", user_agent: str = ""):
        """记录访问"""
        pv = PageView(
            id=self._next_pv_id,
            path=path,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        self.page_views.append(pv)
        self._next_pv_id += 1
    
    def get_stats(self) -> dict:
        """获取统计数据"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_views = len([pv for pv in self.page_views if pv.created_at.startswith(today)])
        
        return {
            'total_users': len(self.users),
            'total_posts': len(self.posts),
            'total_views': len(self.page_views),
            'today_views': today_views,
            'published_posts': len([p for p in self.posts.values() if p.status == 'published'])
        }


db = Database()
