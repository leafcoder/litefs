#!/usr/bin/env python
# coding: utf-8

"""
任务管理系统 REST API

完整的项目管理 API，包含：
- 用户认证 (JWT)
- 项目管理
- 任务管理（状态、优先级、截止日期）
- 成员管理
- 评论系统
- 分页、排序、过滤
- 输入验证
- OpenAPI 文档
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs, Response
from litefs.routing import get, post, put, delete, patch
from litefs.auth import Auth, init_default_roles_and_permissions
from litefs.auth.models import User, Role
from litefs.auth.password import hash_password
from litefs.auth.middleware import login_required, role_required
from litefs.openapi import OpenAPI

# 应用目录
APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 应用配置
# ============================================================================

app = Litefs(
    host='0.0.0.0',
    port=8082,
    debug=True,
    secret_key='task-manager-secret-key-change-in-production'
)

# 添加静态文件支持
app.add_static('/static', os.path.join(APP_DIR, 'static'))

# JWT 认证配置
auth = Auth(app, secret_key='your-secret-key-change-in-production')
openapi = OpenAPI(app, title='任务管理 API', version='1.0.0', description='团队任务管理系统 API')

# ============================================================================
# 初始化数据
# ============================================================================

init_default_roles_and_permissions()

admin_role = Role.get_by_name('admin')
editor_role = Role.get_by_name('editor')
user_role = Role.get_by_name('user')

# 创建默认用户
admin_user = User.create(
    username='admin',
    email='admin@example.com',
    password_hash=hash_password('admin123'),
    roles=[admin_role],
)

editor_user = User.create(
    username='alice',
    email='alice@example.com',
    password_hash=hash_password('alice123'),
    roles=[editor_role],
)

User.create(
    username='bob',
    email='bob@example.com',
    password_hash=hash_password('bob123'),
    roles=[user_role],
)

User.create(
    username='charlie',
    email='charlie@example.com',
    password_hash=hash_password('charlie123'),
    roles=[user_role],
)

# ============================================================================
# 内存数据库
# ============================================================================

class Database:
    """简单的内存数据库"""
    
    def __init__(self):
        self._users: Dict[str, Dict] = {}
        self._projects: Dict[str, Dict] = {}
        self._tasks: Dict[str, Dict] = {}
        self._comments: Dict[str, Dict] = {}
        self._project_members: Dict[str, List[str]] = {}  # project_id -> [user_ids]
        self._task_assignees: Dict[str, List[str]] = {}  # task_id -> [user_ids]
        self._init_sample_data()
    
    def _init_sample_data(self):
        """初始化示例数据"""
        now = datetime.now()
        
        # 项目数据
        projects = [
            {
                'id': 'proj-1',
                'name': '官网重构',
                'slug': 'website-redesign',
                'description': '将公司官网迁移到新平台，提升用户体验和 SEO 效果',
                'owner_id': 'admin',
                'status': 'active',
                'color': '#3498db',
                'created_at': (now - timedelta(days=30)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=2)).isoformat() + 'Z',
            },
            {
                'id': 'proj-2',
                'name': '移动端 App 开发',
                'slug': 'mobile-app',
                'description': '开发 iOS 和 Android 原生应用',
                'owner_id': 'alice',
                'status': 'active',
                'color': '#e74c3c',
                'created_at': (now - timedelta(days=45)).isoformat() + 'Z',
                'updated_at': (now - timedelta(hours=5)).isoformat() + 'Z',
            },
            {
                'id': 'proj-3',
                'name': 'API 性能优化',
                'slug': 'api-optimization',
                'description': '优化后端 API 响应时间，提升整体性能',
                'owner_id': 'admin',
                'status': 'planning',
                'color': '#2ecc71',
                'created_at': (now - timedelta(days=7)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=1)).isoformat() + 'Z',
            },
            {
                'id': 'proj-4',
                'name': '数据迁移项目',
                'slug': 'data-migration',
                'description': '将旧系统数据迁移到新数据库',
                'owner_id': 'alice',
                'status': 'completed',
                'color': '#9b59b6',
                'created_at': (now - timedelta(days=90)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=15)).isoformat() + 'Z',
            },
        ]
        
        for proj in projects:
            self._projects[proj['id']] = proj
        
        # 项目成员
        self._project_members = {
            'proj-1': ['admin', 'alice', 'bob'],
            'proj-2': ['alice', 'charlie'],
            'proj-3': ['admin', 'bob', 'charlie'],
            'proj-4': ['alice'],
        }
        
        # 任务数据
        tasks = [
            # proj-1 的任务
            {
                'id': 'task-1',
                'project_id': 'proj-1',
                'title': '设计新首页布局',
                'description': '根据新品牌形象设计首页，要求简洁大气',
                'status': 'done',
                'priority': 'high',
                'assignees': ['alice'],
                'due_date': (now + timedelta(days=-5)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=20)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=5)).isoformat() + 'Z',
                'completed_at': (now - timedelta(days=5)).isoformat() + 'Z',
                'tags': ['design'],
                'estimated_hours': 8,
                'actual_hours': 10,
            },
            {
                'id': 'task-2',
                'project_id': 'proj-1',
                'title': '开发首页前端组件',
                'description': '使用 React 实现首页各个模块的组件',
                'status': 'in_progress',
                'priority': 'high',
                'assignees': ['bob'],
                'due_date': (now + timedelta(days=7)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=15)).isoformat() + 'Z',
                'updated_at': (now - timedelta(hours=2)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['frontend', 'react'],
                'estimated_hours': 24,
                'actual_hours': 12,
            },
            {
                'id': 'task-3',
                'project_id': 'proj-1',
                'title': 'SEO 优化',
                'description': '优化页面标题、描述和关键词，提升搜索引擎排名',
                'status': 'todo',
                'priority': 'medium',
                'assignees': [],
                'due_date': (now + timedelta(days=14)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=10)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=10)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['seo'],
                'estimated_hours': 6,
                'actual_hours': 0,
            },
            {
                'id': 'task-4',
                'project_id': 'proj-1',
                'title': '性能测试',
                'description': '使用 Lighthouse 进行性能测试，确保加载时间 < 3s',
                'status': 'todo',
                'priority': 'medium',
                'assignees': ['admin'],
                'due_date': (now + timedelta(days=20)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=5)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=5)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['testing', 'performance'],
                'estimated_hours': 4,
                'actual_hours': 0,
            },
            
            # proj-2 的任务
            {
                'id': 'task-5',
                'project_id': 'proj-2',
                'title': 'iOS 登录界面开发',
                'description': '实现用户登录/注册界面，支持第三方登录',
                'status': 'done',
                'priority': 'high',
                'assignees': ['charlie'],
                'due_date': (now + timedelta(days=-10)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=30)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=10)).isoformat() + 'Z',
                'completed_at': (now - timedelta(days=10)).isoformat() + 'Z',
                'tags': ['ios', 'ui'],
                'estimated_hours': 12,
                'actual_hours': 14,
            },
            {
                'id': 'task-6',
                'project_id': 'proj-2',
                'title': 'Android 登录界面开发',
                'description': '实现 Android 平台的登录界面',
                'status': 'in_progress',
                'priority': 'high',
                'assignees': ['charlie'],
                'due_date': (now + timedelta(days=3)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=25)).isoformat() + 'Z',
                'updated_at': (now - timedelta(hours=6)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['android', 'ui'],
                'estimated_hours': 12,
                'actual_hours': 8,
            },
            {
                'id': 'task-7',
                'project_id': 'proj-2',
                'title': '推送通知服务集成',
                'description': '集成 APNs 和 FCM 推送服务',
                'status': 'todo',
                'priority': 'medium',
                'assignees': ['alice'],
                'due_date': (now + timedelta(days=10)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=15)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=15)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['backend', 'push'],
                'estimated_hours': 8,
                'actual_hours': 0,
            },
            
            # proj-3 的任务
            {
                'id': 'task-8',
                'project_id': 'proj-3',
                'title': '分析 API 性能瓶颈',
                'description': '使用 profiling 工具找出性能瓶颈',
                'status': 'in_progress',
                'priority': 'high',
                'assignees': ['admin'],
                'due_date': (now + timedelta(days=5)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=7)).isoformat() + 'Z',
                'updated_at': (now - timedelta(hours=1)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['analysis'],
                'estimated_hours': 8,
                'actual_hours': 4,
            },
            {
                'id': 'task-9',
                'project_id': 'proj-3',
                'title': '实现 Redis 缓存',
                'description': '对高频访问的数据添加 Redis 缓存',
                'status': 'todo',
                'priority': 'high',
                'assignees': ['bob'],
                'due_date': (now + timedelta(days=12)).isoformat() + 'Z',
                'created_at': (now - timedelta(days=3)).isoformat() + 'Z',
                'updated_at': (now - timedelta(days=3)).isoformat() + 'Z',
                'completed_at': None,
                'tags': ['cache', 'redis'],
                'estimated_hours': 16,
                'actual_hours': 0,
            },
        ]
        
        for task in tasks:
            self._tasks[task['id']] = task
        
        # 任务负责人
        self._task_assignees = {t['id']: t['assignees'] for t in tasks}
        
        # 评论数据
        comments = [
            {
                'id': 'comment-1',
                'task_id': 'task-1',
                'user_id': 'admin',
                'content': '设计稿已经完成了，可以开始开发了',
                'created_at': (now - timedelta(days=18)).isoformat() + 'Z',
            },
            {
                'id': 'comment-2',
                'task_id': 'task-1',
                'user_id': 'alice',
                'content': '收到，我这边开始做前端开发',
                'created_at': (now - timedelta(days=17)).isoformat() + 'Z',
            },
            {
                'id': 'comment-3',
                'task_id': 'task-2',
                'user_id': 'bob',
                'content': '首页组件已经完成了 60%，预计后天可以提测',
                'created_at': (now - timedelta(hours=5)).isoformat() + 'Z',
            },
            {
                'id': 'comment-4',
                'task_id': 'task-6',
                'user_id': 'alice',
                'content': '登录界面的 UI 有点调整，需要重新对接接口',
                'created_at': (now - timedelta(days=2)).isoformat() + 'Z',
            },
            {
                'id': 'comment-5',
                'task_id': 'task-8',
                'user_id': 'admin',
                'content': '初步分析发现 /api/users 和 /api/reports 这两个接口响应较慢',
                'created_at': (now - timedelta(hours=8)).isoformat() + 'Z',
            },
        ]
        
        for comment in comments:
            self._comments[comment['id']] = comment
    
    def generate_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
    
    def generate_slug(self, text: str) -> str:
        import re
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

# 全局数据库实例
db = Database()

# ============================================================================
# 辅助函数
# ============================================================================

def success_response(data: Any = None, message: str = None, meta: Dict = None, status_code: int = 200):
    """统一成功响应格式"""
    response = {'success': True}
    if message:
        response['message'] = message
    if meta:
        response['meta'] = meta
    if data is not None:
        response['data'] = data
    
    # 如果需要返回非 200 状态码，使用 (response, status_code) 格式
    if status_code != 200:
        return response, status_code
    return response

def error_response(message: str, code: str = None, details: Any = None, status_code: int = 400):
    """统一错误响应格式"""
    return {
        'success': False,
        'error': {
            'code': code or 'ERROR',
            'message': message,
            'details': details,
        }
    }, status_code

def paginate(items: List, page: int = 1, per_page: int = 20):
    """分页处理"""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'data': items[start:end],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': (total + per_page - 1) // per_page,
            'has_next': end < total,
            'has_prev': page > 1,
        }
    }

def get_query_param(request, key: str, default=None, type_func=None):
    """获取查询参数"""
    query_string = request.query_string
    if not query_string:
        return default
    
    params = parse_qs(query_string)
    values = params.get(key)
    if values is None:
        return default
    
    value = values[0] if values else default
    
    if type_func:
        try:
            return type_func(value)
        except (ValueError, TypeError):
            return default
    
    return value

def validate_required(data: Dict, fields: List[str]):
    """验证必填字段"""
    missing = [f for f in fields if not data.get(f)]
    if missing:
        raise ValidationError(f"缺少必填字段: {', '.join(missing)}")

class ValidationError(Exception):
    pass

# ============================================================================
# API 路由
# ============================================================================

# ----------------------------------------------------------------------------
# 首页
# ----------------------------------------------------------------------------

@get('/', name='index')
def index(request):
    """前端页面"""
    template_path = os.path.join(APP_DIR, 'templates', 'index.html')
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return Response(html_content, headers=[("Content-Type", "text/html; charset=utf-8")])

@get('/api', name='api_info')
def api_info(request):
    """API 首页"""
    return success_response({
        'name': '任务管理 API',
        'version': '1.0.0',
        'description': '团队任务管理系统 RESTful API',
        'endpoints': {
            '认证': [
                {'method': 'POST', 'path': '/api/auth/login', 'desc': '用户登录'},
                {'method': 'POST', 'path': '/api/auth/register', 'desc': '用户注册'},
                {'method': 'POST', 'path': '/api/auth/refresh', 'desc': '刷新 Token'},
            ],
            '用户': [
                {'method': 'GET', 'path': '/api/users', 'desc': '用户列表'},
                {'method': 'GET', 'path': '/api/users/{id}', 'desc': '用户详情'},
                {'method': 'PUT', 'path': '/api/users/{id}', 'desc': '更新用户'},
            ],
            '项目': [
                {'method': 'GET', 'path': '/api/projects', 'desc': '项目列表'},
                {'method': 'POST', 'path': '/api/projects', 'desc': '创建项目'},
                {'method': 'GET', 'path': '/api/projects/{id}', 'desc': '项目详情'},
                {'method': 'PUT', 'path': '/api/projects/{id}', 'desc': '更新项目'},
                {'method': 'DELETE', 'path': '/api/projects/{id}', 'desc': '删除项目'},
                {'method': 'GET', 'path': '/api/projects/{id}/members', 'desc': '项目成员'},
                {'method': 'POST', 'path': '/api/projects/{id}/members', 'desc': '添加成员'},
            ],
            '任务': [
                {'method': 'GET', 'path': '/api/tasks', 'desc': '任务列表'},
                {'method': 'POST', 'path': '/api/tasks', 'desc': '创建任务'},
                {'method': 'GET', 'path': '/api/tasks/{id}', 'desc': '任务详情'},
                {'method': 'PUT', 'path': '/api/tasks/{id}', 'desc': '更新任务'},
                {'method': 'PATCH', 'path': '/api/tasks/{id}/status', 'desc': '更新状态'},
                {'method': 'PATCH', 'path': '/api/tasks/{id}/assignees', 'desc': '分配负责人'},
                {'method': 'DELETE', 'path': '/api/tasks/{id}', 'desc': '删除任务'},
            ],
            '评论': [
                {'method': 'GET', 'path': '/api/tasks/{id}/comments', 'desc': '任务评论'},
                {'method': 'POST', 'path': '/api/tasks/{id}/comments', 'desc': '添加评论'},
                {'method': 'DELETE', 'path': '/api/comments/{id}', 'desc': '删除评论'},
            ],
            '统计': [
                {'method': 'GET', 'path': '/api/stats/overview', 'desc': '总体概览'},
                {'method': 'GET', 'path': '/api/stats/projects/{id}', 'desc': '项目统计'},
            ],
        },
        'documentation': {
            'swagger_ui': '/docs',
            'openapi_spec': '/openapi.json',
        }
    })

# ----------------------------------------------------------------------------
# 认证相关
# ----------------------------------------------------------------------------

@post('/api/auth/login', name='login')
def login(request):
    """用户登录"""
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['username', 'password'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    username = data['username']
    password = data['password']
    
    # 查找用户
    user = User.get_by_username(username)
    if not user:
        return error_response('用户名或密码错误', code='AUTH_FAILED', status_code=401)
    
    # 验证密码
    from litefs.auth.password import verify_password
    if not verify_password(password, user.password_hash):
        return error_response('用户名或密码错误', code='AUTH_FAILED', status_code=401)
    
    # 生成 Token
    token = auth._jwt.create_access_token({'sub': user.id, 'username': user.username})
    refresh_token = auth._jwt.create_refresh_token({'sub': user.id})
    
    return success_response({
        'access_token': token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'roles': [r.name for r in user.roles],
        }
    }, message='登录成功')

@post('/api/auth/register', name='register')
def register(request):
    """用户注册"""
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['username', 'email', 'password'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    username = data['username']
    email = data['email']
    password = data['password']
    
    # 检查用户名是否存在
    if User.get_by_username(username):
        return error_response('用户名已存在', code='USERNAME_EXISTS')
    
    # 检查邮箱是否存在
    if User.get_by_email(email):
        return error_response('邮箱已被使用', code='EMAIL_EXISTS')
    
    # 创建用户
    user = User.create(
        username=username,
        email=email,
        password_hash=hash_password(password),
        roles=[user_role],
    )
    
    return success_response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
    }, message='注册成功', status_code=201)

@post('/api/auth/refresh', name='refresh_token')
def refresh_token(request):
    """刷新 Token"""
    data = request.json if hasattr(request, 'json') else {}
    refresh_token_str = data.get('refresh_token')
    
    if not refresh_token_str:
        return error_response('缺少 refresh_token', code='MISSING_TOKEN')
    
    # 验证并生成新 Token
    payload = auth._jwt.decode_token(refresh_token_str)
    if not payload or payload.get('type') != 'refresh':
        return error_response('无效的 refresh_token', code='INVALID_TOKEN', status_code=401)
    
    user_id = payload.get('sub')
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', code='USER_NOT_FOUND', status_code=401)
    
    new_token = auth._jwt.create_access_token({'sub': user.id, 'username': user.username})
    
    return success_response({
        'access_token': new_token,
        'token_type': 'Bearer',
    })

@get('/api/auth/me', name='current_user')
@login_required
def get_current_user(request):
    """获取当前用户信息"""
    current_user = request.user
    
    # 获取用户参与的项目数量
    user_projects = sum(1 for members in db._project_members.values() if current_user.username in members)
    
    # 获取用户负责的任务数量
    user_tasks = sum(1 for task in db._tasks.values() if current_user.username in task['assignees'])
    
    return success_response({
        'id': current_user.id,
        'username': current_user.username,
        'email': current_user.email,
        'roles': [r.name for r in current_user.roles],
        'stats': {
            'projects': user_projects,
            'tasks': user_tasks,
        }
    })

# ----------------------------------------------------------------------------
# 用户管理
# ----------------------------------------------------------------------------

@get('/api/users', name='list_users')
@login_required
def list_users(request):
    """获取用户列表"""
    page = get_query_param(request, 'page', 1, int)
    per_page = get_query_param(request, 'per_page', 20, int)
    search = get_query_param(request, 'search', '')
    
    # 获取所有用户 (模拟)
    users = []
    for username in ['admin', 'alice', 'bob', 'charlie']:
        user = User.get_by_username(username)
        if user:
            if not search or search.lower() in username.lower() or search.lower() in user.email.lower():
                users.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'roles': [r.name for r in user.roles],
                })
    
    result = paginate(users, page, per_page)
    return success_response(**result)

@get('/api/users/{user_id}', name='get_user')
@login_required
def get_user(request, user_id):
    """获取用户详情"""
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', code='NOT_FOUND', status_code=404)
    
    # 获取用户参与的项目
    user_projects = []
    for proj_id, members in db._project_members.items():
        if user.username in members:
            proj = db._projects.get(proj_id)
            if proj:
                user_projects.append({
                    'id': proj['id'],
                    'name': proj['name'],
                    'role': 'owner' if proj['owner_id'] == user.username else 'member',
                })
    
    # 获取用户负责的任务
    user_tasks = [t for t in db._tasks.values() if user.username in t['assignees']]
    
    return success_response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'roles': [r.name for r in user.roles],
        'projects': user_projects,
        'tasks': {
            'total': len(user_tasks),
            'todo': sum(1 for t in user_tasks if t['status'] == 'todo'),
            'in_progress': sum(1 for t in user_tasks if t['status'] == 'in_progress'),
            'done': sum(1 for t in user_tasks if t['status'] == 'done'),
        }
    })

@put('/api/users/{user_id}', name='update_user')
@login_required
def update_user(request, user_id):
    """更新用户信息"""
    current_user = request.user
    
    # 只有用户自己或管理员可以更新
    if current_user.id != user_id and 'admin' not in [r.name for r in current_user.roles]:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', code='NOT_FOUND', status_code=404)
    
    data = request.json if hasattr(request, 'json') else {}
    
    # 更新字段
    if 'email' in data:
        user.email = data['email']
    if 'password' in data:
        user.password_hash = hash_password(data['password'])
    
    return success_response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
    }, message='更新成功')

# ----------------------------------------------------------------------------
# 项目管理
# ----------------------------------------------------------------------------

@get('/api/projects', name='list_projects')
@login_required
def list_projects(request):
    """获取项目列表"""
    page = get_query_param(request, 'page', 1, int)
    per_page = get_query_param(request, 'per_page', 20, int)
    status = get_query_param(request, 'status')
    search = get_query_param(request, 'search', '')
    
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    projects = []
    for proj in db._projects.values():
        # 非管理员只能看到自己是成员的项目
        if not is_admin and current_user.username not in db._project_members.get(proj['id'], []):
            continue
        
        # 过滤
        if status and proj['status'] != status:
            continue
        if search:
            if search.lower() not in proj['name'].lower() and search.lower() not in proj['description'].lower():
                continue
        
        # 获取统计数据
        project_tasks = [t for t in db._tasks.values() if t['project_id'] == proj['id']]
        
        projects.append({
            **proj,
            'owner': User.get_by_username(proj['owner_id']).id if proj['owner_id'] else None,
            'member_count': len(db._project_members.get(proj['id'], [])),
            'task_stats': {
                'total': len(project_tasks),
                'todo': sum(1 for t in project_tasks if t['status'] == 'todo'),
                'in_progress': sum(1 for t in project_tasks if t['status'] == 'in_progress'),
                'done': sum(1 for t in project_tasks if t['status'] == 'done'),
            }
        })
    
    # 按更新时间排序
    projects.sort(key=lambda x: x['updated_at'], reverse=True)
    
    result = paginate(projects, page, per_page)
    return success_response(**result)

@post('/api/projects', name='create_project')
@login_required
def create_project(request):
    """创建项目"""
    current_user = request.user
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['name'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    project_id = db.generate_id('proj')
    now = datetime.now().isoformat() + 'Z'
    
    project = {
        'id': project_id,
        'name': data['name'],
        'slug': db.generate_slug(data['name']),
        'description': data.get('description', ''),
        'owner_id': current_user.username,
        'status': data.get('status', 'planning'),
        'color': data.get('color', '#3498db'),
        'created_at': now,
        'updated_at': now,
    }
    
    db._projects[project_id] = project
    db._project_members[project_id] = [current_user.username]
    
    return success_response(project, message='项目创建成功', status_code=201)

@get('/api/projects/{project_id}', name='get_project')
@login_required
def get_project(request, project_id):
    """获取项目详情"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    project = db._projects.get(project_id)
    if not project:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    # 权限检查
    if not is_admin and current_user.username not in db._project_members.get(project_id, []):
        return error_response('无权限访问该项目', code='FORBIDDEN', status_code=403)
    
    # 获取成员信息
    members = []
    for username in db._project_members.get(project_id, []):
        user = User.get_by_username(username)
        if user:
            members.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': 'owner' if project['owner_id'] == username else 'member',
            })
    
    # 获取任务统计
    project_tasks = [t for t in db._tasks.values() if t['project_id'] == project_id]
    
    return success_response({
        **project,
        'owner': {
            'id': User.get_by_username(project['owner_id']).id,
            'username': project['owner_id'],
        } if project['owner_id'] else None,
        'members': members,
        'task_stats': {
            'total': len(project_tasks),
            'todo': sum(1 for t in project_tasks if t['status'] == 'todo'),
            'in_progress': sum(1 for t in project_tasks if t['status'] == 'in_progress'),
            'done': sum(1 for t in project_tasks if t['status'] == 'done'),
            'overdue': sum(1 for t in project_tasks if t['status'] != 'done' and t.get('due_date') and t['due_date'] < datetime.now().isoformat() + 'Z'),
        },
        'recent_tasks': project_tasks[:5],  # 最近的任务
    })

@put('/api/projects/{project_id}', name='update_project')
@login_required
def update_project(request, project_id):
    """更新项目"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    project = db._projects.get(project_id)
    if not project:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    # 只有所有者或管理员可以更新
    if project['owner_id'] != current_user.username and not is_admin:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    data = request.json if hasattr(request, 'json') else {}
    
    # 可更新字段
    updatable = ['name', 'description', 'status', 'color']
    for field in updatable:
        if field in data:
            project[field] = data[field]
    
    if 'name' in data:
        project['slug'] = db.generate_slug(data['name'])
    
    project['updated_at'] = datetime.now().isoformat() + 'Z'
    
    return success_response(project, message='项目更新成功')

@delete('/api/projects/{project_id}', name='delete_project')
@role_required('admin')
def delete_project(request, project_id):
    """删除项目（仅管理员）"""
    if project_id not in db._projects:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    # 删除项目关联的任务和评论
    task_ids = [tid for tid, t in db._tasks.items() if t['project_id'] == project_id]
    for tid in task_ids:
        # 删除任务的评论
        for cid in list(db._comments.keys()):
            if db._comments[cid]['task_id'] == tid:
                del db._comments[cid]
        del db._tasks[tid]
    
    # 删除项目成员关系
    if project_id in db._project_members:
        del db._project_members[project_id]
    
    # 删除项目
    del db._projects[project_id]
    
    return success_response(None, message='项目已删除')

@get('/api/projects/{project_id}/members', name='project_members')
@login_required
def get_project_members(request, project_id):
    """获取项目成员"""
    current_user = request.user
    project = db._projects.get(project_id)
    
    if not project:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    members = []
    for username in db._project_members.get(project_id, []):
        user = User.get_by_username(username)
        if user:
            # 统计该成员在此项目中的任务
            user_tasks = [t for t in db._tasks.values() 
                         if t['project_id'] == project_id and username in t['assignees']]
            
            members.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': 'owner' if project['owner_id'] == username else 'member',
                'task_count': len(user_tasks),
                'completed_count': sum(1 for t in user_tasks if t['status'] == 'done'),
            })
    
    return success_response({'members': members, 'total': len(members)})

@post('/api/projects/{project_id}/members', name='add_member')
@login_required
def add_member(request, project_id):
    """添加项目成员"""
    current_user = request.user
    project = db._projects.get(project_id)
    
    if not project:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    # 只有所有者或管理员可以添加成员
    is_admin = 'admin' in [r.name for r in current_user.roles]
    if project['owner_id'] != current_user.username and not is_admin:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['username'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    username = data['username']
    
    # 检查用户是否存在
    user = User.get_by_username(username)
    if not user:
        return error_response('用户不存在', code='USER_NOT_FOUND', status_code=404)
    
    # 检查是否已是成员
    if username in db._project_members.get(project_id, []):
        return error_response('该用户已是项目成员', code='ALREADY_MEMBER')
    
    db._project_members.setdefault(project_id, []).append(username)
    
    return success_response({
        'username': username,
        'added_at': datetime.now().isoformat() + 'Z',
    }, message='成员添加成功', status_code=201)

@delete('/api/projects/{project_id}/members/{username}', name='remove_member')
@login_required
def remove_member(request, project_id, username):
    """移除项目成员"""
    current_user = request.user
    project = db._projects.get(project_id)
    
    if not project:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    # 只有所有者或管理员可以移除成员
    is_admin = 'admin' in [r.name for r in current_user.roles]
    if project['owner_id'] != current_user.username and not is_admin:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    if username not in db._project_members.get(project_id, []):
        return error_response('该用户不是项目成员', code='NOT_MEMBER')
    
    # 不能移除所有者
    if username == project['owner_id']:
        return error_response('不能移除项目所有者', code='CANNOT_REMOVE_OWNER')
    
    db._project_members[project_id].remove(username)
    
    return success_response(None, message='成员已移除')

# ----------------------------------------------------------------------------
# 任务管理
# ----------------------------------------------------------------------------

@get('/api/tasks', name='list_tasks')
@login_required
def list_tasks(request):
    """获取任务列表"""
    page = get_query_param(request, 'page', 1, int)
    per_page = get_query_param(request, 'per_page', 20, int)
    
    # 筛选参数
    project_id = get_query_param(request, 'project_id')
    status = get_query_param(request, 'status')
    priority = get_query_param(request, 'priority')
    assignee = get_query_param(request, 'assignee')
    tag = get_query_param(request, 'tag')
    search = get_query_param(request, 'search', '')
    sort = get_query_param(request, 'sort', '-created_at')  # 默认按创建时间倒序
    
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    tasks = []
    for task in db._tasks.values():
        # 非管理员只能看到自己是成员的项目中的任务
        if not is_admin:
            members = db._project_members.get(task['project_id'], [])
            if current_user.username not in members:
                continue
        
        # 筛选
        if project_id and task['project_id'] != project_id:
            continue
        if status and task['status'] != status:
            continue
        if priority and task['priority'] != priority:
            continue
        if assignee:
            assignee_list = assignee.split(',')
            task_assignees = task.get('assignees', [])
            if not any(a in assignee_list for a in task_assignees):
                continue
        if tag and tag not in task.get('tags', []):
            continue
        if search:
            if search.lower() not in task['title'].lower() and search.lower() not in task['description'].lower():
                continue
        
        # 获取项目信息
        project = db._projects.get(task['project_id'], {})
        
        # 获取评论数
        comment_count = sum(1 for c in db._comments.values() if c['task_id'] == task['id'])
        
        # 获取负责人信息
        assignees = []
        for username in task['assignees']:
            user = User.get_by_username(username)
            if user:
                assignees.append({
                    'id': user.id,
                    'username': user.username,
                })
        
        tasks.append({
            **task,
            'project_name': project.get('name', ''),
            'project_color': project.get('color', '#3498db'),
            'assignees': assignees,
            'comment_count': comment_count,
            'is_overdue': task['status'] != 'done' and task.get('due_date') and task['due_date'] < datetime.now().isoformat() + 'Z',
        })
    
    # 排序
    reverse = sort.startswith('-')
    sort_key = sort.lstrip('-')
    sort_mapping = {
        'created_at': 'created_at',
        'updated_at': 'updated_at',
        'due_date': 'due_date',
        'priority': 'priority',
        'status': 'status',
    }
    if sort_key in sort_mapping:
        tasks.sort(key=lambda x: x.get(sort_mapping[sort_key], ''), reverse=reverse)
    
    result = paginate(tasks, page, per_page)
    return success_response(**result)

@post('/api/tasks', name='create_task')
@login_required
def create_task(request):
    """创建任务"""
    current_user = request.user
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['title', 'project_id'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    project_id = data['project_id']
    project = db._projects.get(project_id)
    
    if not project:
        return error_response('项目不存在', code='PROJECT_NOT_FOUND', status_code=404)
    
    # 权限检查
    is_admin = 'admin' in [r.name for r in current_user.roles]
    if not is_admin and current_user.username not in db._project_members.get(project_id, []):
        return error_response('无权限在该项目中创建任务', code='FORBIDDEN', status_code=403)
    
    task_id = db.generate_id('task')
    now = datetime.now().isoformat() + 'Z'
    
    # 处理截止日期
    due_date = data.get('due_date')
    if due_date:
        # 验证日期格式
        try:
            datetime.fromisoformat(due_date.replace('Z', '+00:00'))
        except ValueError:
            return error_response('日期格式不正确', code='INVALID_DATE')
    
    task = {
        'id': task_id,
        'project_id': project_id,
        'title': data['title'],
        'description': data.get('description', ''),
        'status': data.get('status', 'todo'),
        'priority': data.get('priority', 'medium'),
        'assignees': data.get('assignees', []),
        'due_date': due_date,
        'created_at': now,
        'updated_at': now,
        'completed_at': None,
        'tags': data.get('tags', []),
        'estimated_hours': data.get('estimated_hours', 0),
        'actual_hours': 0,
    }
    
    db._tasks[task_id] = task
    db._task_assignees[task_id] = task['assignees']
    
    return success_response(task, message='任务创建成功', status_code=201)

@get('/api/tasks/{task_id}', name='get_task')
@login_required
def get_task(request, task_id):
    """获取任务详情"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    # 权限检查
    if not is_admin and current_user.username not in db._project_members.get(task['project_id'], []):
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    # 获取项目信息
    project = db._projects.get(task['project_id'], {})
    
    # 获取负责人信息
    assignees = []
    for username in task['assignees']:
        user = User.get_by_username(username)
        if user:
            assignees.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
            })
    
    # 获取评论
    comments = []
    for comment in db._comments.values():
        if comment['task_id'] == task_id:
            user = User.get_by_username(comment['user_id'])
            if user:
                comments.append({
                    **comment,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                    }
                })
    
    # 按时间排序
    comments.sort(key=lambda x: x['created_at'])
    
    return success_response({
        **task,
        'project': {
            'id': project['id'],
            'name': project['name'],
            'color': project.get('color', '#3498db'),
        },
        'assignees': assignees,
        'comments': comments,
        'comment_count': len(comments),
        'is_overdue': task['status'] != 'done' and task.get('due_date') and task['due_date'] < datetime.now().isoformat() + 'Z',
    })

@put('/api/tasks/{task_id}', name='update_task')
@login_required
def update_task(request, task_id):
    """更新任务"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    # 权限检查：项目成员或负责人可以更新
    if not is_admin and current_user.username not in db._project_members.get(task['project_id'], []) and current_user.username not in task['assignees']:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    data = request.json if hasattr(request, 'json') else {}
    
    # 可更新字段
    updatable = ['title', 'description', 'status', 'priority', 'due_date', 'tags', 'estimated_hours', 'actual_hours']
    for field in updatable:
        if field in data:
            task[field] = data[field]
    
    # 处理负责人更新
    if 'assignees' in data:
        task['assignees'] = data['assignees']
        db._task_assignees[task_id] = data['assignees']
    
    # 处理状态变更
    if 'status' in data:
        if data['status'] == 'done' and not task['completed_at']:
            task['completed_at'] = datetime.now().isoformat() + 'Z'
        elif data['status'] != 'done':
            task['completed_at'] = None
    
    task['updated_at'] = datetime.now().isoformat() + 'Z'
    
    return success_response(task, message='任务更新成功')

@patch('/api/tasks/{task_id}/status', name='update_task_status')
@login_required
def update_task_status(request, task_id):
    """快速更新任务状态"""
    current_user = request.user
    
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['status'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    status = data['status']
    valid_statuses = ['todo', 'in_progress', 'done', 'cancelled']
    if status not in valid_statuses:
        return error_response(f'无效的状态，可选值: {", ".join(valid_statuses)}', code='INVALID_STATUS')
    
    task['status'] = status
    task['updated_at'] = datetime.now().isoformat() + 'Z'
    
    if status == 'done' and not task['completed_at']:
        task['completed_at'] = datetime.now().isoformat() + 'Z'
    elif status != 'done':
        task['completed_at'] = None
    
    return success_response({'status': task['status']}, message='状态更新成功')

@patch('/api/tasks/{task_id}/assignees', name='update_task_assignees')
@login_required
def update_task_assignees(request, task_id):
    """更新任务负责人"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    # 只有项目所有者、管理员或当前负责人可以分配
    project = db._projects.get(task['project_id'], {})
    if not is_admin and current_user.username not in project.get('owner_id', '') and current_user.username not in task['assignees']:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    data = request.json if hasattr(request, 'json') else {}
    new_assignees = data.get('assignees', [])
    
    # 验证用户存在
    for username in new_assignees:
        user = User.get_by_username(username)
        if not user:
            return error_response(f'用户不存在: {username}', code='USER_NOT_FOUND')
        
        # 验证用户在项目中
        if username not in db._project_members.get(task['project_id'], []):
            return error_response(f'用户 {username} 不是项目成员', code='NOT_PROJECT_MEMBER')
    
    task['assignees'] = new_assignees
    task['updated_at'] = datetime.now().isoformat() + 'Z'
    db._task_assignees[task_id] = new_assignees
    
    return success_response({'assignees': new_assignees}, message='负责人更新成功')

@delete('/api/tasks/{task_id}', name='delete_task')
@login_required
def delete_task(request, task_id):
    """删除任务"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    project = db._projects.get(task['project_id'], {})
    
    # 只有项目所有者、管理员或任务负责人可以删除
    can_delete = (
        is_admin or 
        project.get('owner_id') == current_user.username or
        current_user.username in task['assignees']
    )
    
    if not can_delete:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    # 删除关联的评论
    for cid in list(db._comments.keys()):
        if db._comments[cid]['task_id'] == task_id:
            del db._comments[cid]
    
    # 删除任务
    del db._tasks[task_id]
    if task_id in db._task_assignees:
        del db._task_assignees[task_id]
    
    return success_response(None, message='任务已删除')

# ----------------------------------------------------------------------------
# 评论管理
# ----------------------------------------------------------------------------

@get('/api/tasks/{task_id}/comments', name='task_comments')
@login_required
def get_task_comments(request, task_id):
    """获取任务评论"""
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    comments = []
    for comment in db._comments.values():
        if comment['task_id'] == task_id:
            user = User.get_by_username(comment['user_id'])
            if user:
                comments.append({
                    **comment,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                    }
                })
    
    comments.sort(key=lambda x: x['created_at'])
    
    return success_response({'comments': comments, 'total': len(comments)})

@post('/api/tasks/{task_id}/comments', name='add_comment')
@login_required
def add_comment(request, task_id):
    """添加评论"""
    current_user = request.user
    
    task = db._tasks.get(task_id)
    if not task:
        return error_response('任务不存在', code='NOT_FOUND', status_code=404)
    
    data = request.json if hasattr(request, 'json') else {}
    
    try:
        validate_required(data, ['content'])
    except ValidationError as e:
        return error_response(str(e), code='VALIDATION_ERROR')
    
    comment_id = db.generate_id('comment')
    now = datetime.now().isoformat() + 'Z'
    
    comment = {
        'id': comment_id,
        'task_id': task_id,
        'user_id': current_user.username,
        'content': data['content'],
        'created_at': now,
    }
    
    db._comments[comment_id] = comment
    
    return success_response({
        **comment,
        'user': {
            'id': current_user.id,
            'username': current_user.username,
        }
    }, message='评论添加成功', status_code=201)

@delete('/api/comments/{comment_id}', name='delete_comment')
@login_required
def delete_comment(request, comment_id):
    """删除评论"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    comment = db._comments.get(comment_id)
    if not comment:
        return error_response('评论不存在', code='NOT_FOUND', status_code=404)
    
    # 只有评论作者或管理员可以删除
    if comment['user_id'] != current_user.username and not is_admin:
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    del db._comments[comment_id]
    
    return success_response(None, message='评论已删除')

# ----------------------------------------------------------------------------
# 统计接口
# ----------------------------------------------------------------------------

@get('/api/stats/overview', name='stats_overview')
@login_required
def stats_overview(request):
    """获取总体统计"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    if is_admin:
        # 管理员可以看到所有数据
        projects = list(db._projects.values())
        tasks = list(db._tasks.values())
    else:
        # 普通用户只看到参与的项目
        user_projects = [pid for pid, members in db._project_members.items() if current_user.username in members]
        projects = [db._projects.get(pid) for pid in user_projects if db._projects.get(pid)]
        tasks = [t for t in db._tasks.values() if t['project_id'] in user_projects]
    
    # 计算统计
    now = datetime.now().isoformat() + 'Z'
    
    stats = {
        'projects': {
            'total': len(projects),
            'active': sum(1 for p in projects if p['status'] == 'active'),
            'planning': sum(1 for p in projects if p['status'] == 'planning'),
            'completed': sum(1 for p in projects if p['status'] == 'completed'),
        },
        'tasks': {
            'total': len(tasks),
            'todo': sum(1 for t in tasks if t['status'] == 'todo'),
            'in_progress': sum(1 for t in tasks if t['status'] == 'in_progress'),
            'done': sum(1 for t in tasks if t['status'] == 'done'),
            'cancelled': sum(1 for t in tasks if t['status'] == 'cancelled'),
            'overdue': sum(1 for t in tasks if t['status'] != 'done' and t.get('due_date') and t['due_date'] < now),
        },
        'completion_rate': round(len([t for t in tasks if t['status'] == 'done']) / len(tasks) * 100, 1) if tasks else 0,
    }
    
    # 按优先级统计
    priority_stats = {}
    for priority in ['low', 'medium', 'high', 'urgent']:
        p_tasks = [t for t in tasks if t['priority'] == priority]
        priority_stats[priority] = {
            'total': len(p_tasks),
            'done': sum(1 for t in p_tasks if t['status'] == 'done'),
        }
    stats['by_priority'] = priority_stats
    
    # 我的任务统计
    my_tasks = [t for t in tasks if current_user.username in t['assignees']]
    stats['my_tasks'] = {
        'total': len(my_tasks),
        'todo': sum(1 for t in my_tasks if t['status'] == 'todo'),
        'in_progress': sum(1 for t in my_tasks if t['status'] == 'in_progress'),
        'done': sum(1 for t in my_tasks if t['status'] == 'done'),
        'overdue': sum(1 for t in my_tasks if t['status'] != 'done' and t.get('due_date') and t['due_date'] < now),
    }
    
    return success_response(stats)

@get('/api/stats/projects/{project_id}', name='project_stats')
@login_required
def project_stats(request, project_id):
    """获取项目统计"""
    current_user = request.user
    is_admin = 'admin' in [r.name for r in current_user.roles]
    
    project = db._projects.get(project_id)
    if not project:
        return error_response('项目不存在', code='NOT_FOUND', status_code=404)
    
    # 权限检查
    if not is_admin and current_user.username not in db._project_members.get(project_id, []):
        return error_response('无权限', code='FORBIDDEN', status_code=403)
    
    tasks = [t for t in db._tasks.values() if t['project_id'] == project_id]
    members = db._project_members.get(project_id, [])
    now = datetime.now().isoformat() + 'Z'
    
    # 按成员统计
    member_stats = []
    for username in members:
        user = User.get_by_username(username)
        if user:
            user_tasks = [t for t in tasks if username in t['assignees']]
            member_stats.append({
                'username': username,
                'total_tasks': len(user_tasks),
                'completed': sum(1 for t in user_tasks if t['status'] == 'done'),
                'in_progress': sum(1 for t in user_tasks if t['status'] == 'in_progress'),
                'overdue': sum(1 for t in user_tasks if t['status'] != 'done' and t.get('due_date') and t['due_date'] < now),
            })
    
    # 按优先级统计
    priority_stats = {}
    for priority in ['low', 'medium', 'high', 'urgent']:
        p_tasks = [t for t in tasks if t['priority'] == priority]
        priority_stats[priority] = {
            'total': len(p_tasks),
            'done': sum(1 for t in p_tasks if t['status'] == 'done'),
            'in_progress': sum(1 for t in p_tasks if t['status'] == 'in_progress'),
        }
    
    # 工作量统计
    total_estimated = sum(t.get('estimated_hours', 0) for t in tasks)
    total_actual = sum(t.get('actual_hours', 0) for t in tasks)
    
    return success_response({
        'project': {
            'id': project['id'],
            'name': project['name'],
            'status': project['status'],
        },
        'summary': {
            'total_tasks': len(tasks),
            'completed': sum(1 for t in tasks if t['status'] == 'done'),
            'in_progress': sum(1 for t in tasks if t['status'] == 'in_progress'),
            'todo': sum(1 for t in tasks if t['status'] == 'todo'),
            'overdue': sum(1 for t in tasks if t['status'] != 'done' and t.get('due_date') and t['due_date'] < now),
            'completion_rate': round(sum(1 for t in tasks if t['status'] == 'done') / len(tasks) * 100, 1) if tasks else 0,
        },
        'by_member': member_stats,
        'by_priority': priority_stats,
        'workload': {
            'estimated_hours': total_estimated,
            'actual_hours': total_actual,
            'completion': round(total_actual / total_estimated * 100, 1) if total_estimated else 0,
        },
    })

# ============================================================================
# 注册路由并启动
# ============================================================================

app.register_routes(__name__)

if __name__ == '__main__':
    print("=" * 70)
    print("任务管理系统 REST API")
    print("=" * 70)
    print()
    print("功能特性:")
    print("  - 用户认证 (JWT)")
    print("  - 项目管理 (CRUD, 成员管理)")
    print("  - 任务管理 (状态, 优先级, 负责人)")
    print("  - 评论系统")
    print("  - 统计分析")
    print("  - 分页、排序、过滤")
    print("  - 权限控制")
    print()
    print("测试账号:")
    print("  - admin / admin123 (管理员)")
    print("  - alice / alice123 (编辑)")
    print("  - bob   / bob123   (用户)")
    print()
    print("API 端点: http://localhost:8082")
    print("Swagger UI: http://localhost:8082/docs")
    print("=" * 70)
    
    app.run()
