#!/usr/bin/env python
# coding: utf-8

"""
核心功能综合示例

展示 Litefs 框架的核心功能：
- 统一异常处理体系
- 请求上下文管理
- 表单验证系统
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, post
from litefs.exceptions import (
    NotFound, BadRequest, Unauthorized, Forbidden,
    InternalServerError, abort
)
from litefs.context import g, has_request_context, get_current_request
from litefs.forms import Form, Field, Email, Length, Required


# 自定义错误处理
def handle_404(error, request_handler):
    """自定义 404 错误处理"""
    return {
        'error': 'Not Found',
        'message': 'The requested resource was not found',
        'path': request_handler.path_info,
        'status_code': 404
    }, 404


def handle_500(error, request_handler):
    """自定义 500 错误处理"""
    return {
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred',
        'status_code': 500
    }, 500


# 表单定义
class UserForm(Form):
    """用户表单"""
    
    username = Field(
        label='Username',
        required=True,
        validators=[Length(min_length=3, max_length=20)]
    )
    
    email = Field(
        label='Email',
        required=True,
        validators=[Email()]
    )
    
    age = Field(
        label='Age',
        required=False
    )


app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

# 注册错误处理器
from litefs.exceptions import error_handler
error_handler.register(404)(handle_404)
error_handler.register(500)(handle_500)


@route('/', name='index')
def index(request):
    """
    首页 - 展示功能列表
    """
    return {
        'message': 'Litefs 核心功能示例',
        'features': {
            'exception_handling': {
                'description': '统一异常处理体系',
                'endpoints': {
                    '/error/404': '404 Not Found 示例',
                    '/error/400': '400 Bad Request 示例',
                    '/error/401': '401 Unauthorized 示例',
                    '/error/403': '403 Forbidden 示例',
                    '/error/500': '500 Internal Server Error 示例',
                    '/error/abort': '使用 abort() 函数示例'
                }
            },
            'context_management': {
                'description': '请求上下文管理',
                'endpoints': {
                    '/context/set': '设置上下文数据',
                    '/context/get': '获取上下文数据',
                    '/context/info': '查看上下文信息'
                }
            },
            'form_validation': {
                'description': '表单验证系统',
                'endpoints': {
                    '/form/validate': '表单验证示例（POST）'
                }
            }
        }
    }


# ==================== 异常处理示例 ====================

@route('/error/404', name='error_404')
def error_404(request):
    """404 Not Found 示例"""
    raise NotFound(
        message='Resource not found',
        description='The requested resource does not exist'
    )


@route('/error/400', name='error_400')
def error_400(request):
    """400 Bad Request 示例"""
    raise BadRequest(
        message='Invalid request',
        description='The request could not be understood'
    )


@route('/error/401', name='error_401')
def error_401(request):
    """401 Unauthorized 示例"""
    raise Unauthorized(
        message='Authentication required',
        description='You need to authenticate to access this resource',
        www_authenticate='Bearer'
    )


@route('/error/403', name='error_403')
def error_403(request):
    """403 Forbidden 示例"""
    raise Forbidden(
        message='Access denied',
        description='You do not have permission to access this resource'
    )


@route('/error/500', name='error_500')
def error_500(request):
    """500 Internal Server Error 示例"""
    raise InternalServerError(
        message='Server error',
        description='An unexpected error occurred on the server'
    )


@route('/error/abort', name='error_abort')
def error_abort(request):
    """使用 abort() 函数示例"""
    # 可以使用 abort() 函数快速抛出异常
    abort(403, message='Access forbidden', description='You are not allowed here')


# ==================== 上下文管理示例 ====================

@route('/context/set', name='context_set')
def context_set(request):
    """设置上下文数据"""
    # 使用 g 对象存储数据
    g.user_id = 12345
    g.username = 'john_doe'
    g.role = 'admin'
    g.login_time = '2024-01-15 10:30:00'
    
    return {
        'message': 'Context data set successfully',
        'data': {
            'user_id': g.user_id,
            'username': g.username,
            'role': g.role,
            'login_time': g.login_time
        }
    }


@route('/context/get', name='context_get')
def context_get(request):
    """获取上下文数据"""
    # 检查是否存在上下文
    if not has_request_context():
        return {
            'message': 'No request context available'
        }
    
    # 获取之前设置的数据
    user_id = g.get('user_id', 'Not set')
    username = g.get('username', 'Not set')
    role = g.get('role', 'Not set')
    
    return {
        'message': 'Context data retrieved',
        'data': {
            'user_id': user_id,
            'username': username,
            'role': role,
            'has_user_id': 'user_id' in g
        }
    }


@route('/context/info', name='context_info')
def context_info(request):
    """查看上下文信息"""
    current_request = get_current_request()
    
    return {
        'message': 'Context information',
        'info': {
            'has_context': has_request_context(),
            'request_method': current_request.request_method if current_request else None,
            'request_path': current_request.path_info if current_request else None,
            'context_repr': repr(g)
        }
    }


# ==================== 表单验证示例 ====================

@post('/form/validate', name='form_validate')
def form_validate(request):
    """表单验证示例"""
    # 获取表单数据
    form_data = {
        'username': request.form.get('username'),
        'email': request.form.get('email'),
        'age': request.form.get('age')
    }
    
    # 创建表单实例并验证
    form = UserForm(data=form_data)
    
    if form.validate():
        # 验证成功
        return {
            'status': 'success',
            'message': 'Form validation passed',
            'data': form.data
        }
    else:
        # 验证失败
        return {
            'status': 'error',
            'message': 'Form validation failed',
            'errors': form.errors
        }, 400


@route('/form/example', name='form_example')
def form_example(request):
    """表单示例页面"""
    return {
        'message': 'User Form Example',
        'fields': {
            'username': {
                'label': 'Username',
                'type': 'text',
                'required': True,
                'validators': ['min_length:3', 'max_length:20']
            },
            'email': {
                'label': 'Email',
                'type': 'email',
                'required': True,
                'validators': ['valid_email']
            },
            'age': {
                'label': 'Age',
                'type': 'number',
                'required': False
            }
        },
        'test_command': 'curl -X POST -d "username=john&email=john@example.com&age=25" http://localhost:8080/form/validate'
    }


# ==================== 综合示例 ====================

@post('/user/create', name='user_create')
def user_create(request):
    """
    创建用户 - 综合示例
    
    展示如何结合使用：
    - 表单验证
    - 上下文管理
    - 异常处理
    """
    # 设置上下文数据
    g.operation = 'create_user'
    g.timestamp = '2024-01-15 10:30:00'
    
    # 获取表单数据
    form_data = {
        'username': request.form.get('username'),
        'email': request.form.get('email'),
        'age': request.form.get('age')
    }
    
    # 验证表单
    form = UserForm(data=form_data)
    
    if not form.validate():
        # 验证失败，抛出异常
        raise BadRequest(
            message='Form validation failed',
            description=str(form.errors)
        )
    
    # 模拟创建用户
    user_id = 12345
    
    # 在上下文中存储用户信息
    g.user_id = user_id
    g.username = form.data['username']
    
    return {
        'status': 'success',
        'message': 'User created successfully',
        'data': {
            'user_id': user_id,
            'username': form.data['username'],
            'email': form.data['email'],
            'age': form.data.get('age'),
            'context': {
                'operation': g.operation,
                'timestamp': g.timestamp
            }
        }
    }


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 核心功能综合示例")
    print("=" * 60)
    print()
    print("功能特性：")
    print("  ✓ 统一异常处理体系 - 完整的 HTTP 异常类和错误处理")
    print("  ✓ 请求上下文管理 - 类似 Flask 的 g 对象")
    print("  ✓ 表单验证系统 - 强大的表单验证功能")
    print()
    print("示例端点：")
    print("  http://localhost:8080/                    - 首页")
    print()
    print("  异常处理示例：")
    print("  http://localhost:8080/error/404           - 404 Not Found")
    print("  http://localhost:8080/error/400           - 400 Bad Request")
    print("  http://localhost:8080/error/401           - 401 Unauthorized")
    print("  http://localhost:8080/error/403           - 403 Forbidden")
    print("  http://localhost:8080/error/500           - 500 Internal Server Error")
    print("  http://localhost:8080/error/abort         - abort() 函数示例")
    print()
    print("  上下文管理示例：")
    print("  http://localhost:8080/context/set         - 设置上下文数据")
    print("  http://localhost:8080/context/get         - 获取上下文数据")
    print("  http://localhost:8080/context/info        - 查看上下文信息")
    print()
    print("  表单验证示例：")
    print("  http://localhost:8080/form/example        - 表单示例")
    print("  http://localhost:8080/form/validate       - 表单验证（POST）")
    print()
    print("  综合示例：")
    print("  http://localhost:8080/user/create         - 创建用户（POST）")
    print()
    print("测试命令：")
    print("  # 表单验证测试")
    print("  curl -X POST -d 'username=john&email=john@example.com&age=25' http://localhost:8080/form/validate")
    print()
    print("  # 用户创建测试")
    print("  curl -X POST -d 'username=jane&email=jane@example.com' http://localhost:8080/user/create")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
