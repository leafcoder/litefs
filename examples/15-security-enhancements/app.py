#!/usr/bin/env python
# coding: utf-8

"""
安全增强功能综合示例

展示 Litefs 框架的安全增强功能：
- 数据库连接池优化
- CSRF 保护
- 安全头部
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, post
from litefs.middleware import CSRFMiddleware, SecurityMiddleware


app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    database_url='sqlite:///security_example.db',
    database_pool_size=10,
    database_max_overflow=20,
    database_pool_timeout=30,
    database_pool_recycle=3600
)

# 添加安全中间件
app.add_middleware(SecurityMiddleware,
    x_frame_options='DENY',
    x_content_type_options='nosniff',
    x_xss_protection='1; mode=block',
    strict_transport_security='max-age=31536000; includeSubDomains',
    content_security_policy="default-src 'self'",
    referrer_policy='strict-origin-when-cross-origin'
)

# 添加 CSRF 保护中间件
app.add_middleware(CSRFMiddleware,
    secret_key='your-secret-key-here',
    token_name='csrf_token',
    header_name='X-CSRFToken',
    cookie_name='csrftoken',
    cookie_secure=False,
    cookie_http_only=True,
    cookie_same_site='Lax'
)


@route('/', name='index')
def index(request):
    """
    首页 - 展示功能列表
    """
    return {
        'message': 'Litefs 安全增强功能示例',
        'features': {
            'database_pool': {
                'description': '数据库连接池优化',
                'endpoints': {
                    '/db/pool-status': '查看连接池状态'
                }
            },
            'csrf_protection': {
                'description': 'CSRF 保护',
                'endpoints': {
                    '/form': '表单页面（GET）',
                    '/form/submit': '表单提交（POST，需要 CSRF Token）'
                }
            },
            'security_headers': {
                'description': '安全头部',
                'note': '所有响应都会自动添加安全头部'
            }
        }
    }


# ==================== 数据库连接池示例 ====================

@route('/db/pool-status', name='db_pool_status')
def db_pool_status(request):
    """查看数据库连接池状态"""
    pool_status = app.db.get_pool_status()
    
    return {
        'message': '数据库连接池状态',
        'status': pool_status,
        'config': {
            'pool_size': app.config.database_pool_size,
            'max_overflow': app.config.database_max_overflow,
            'pool_timeout': app.config.database_pool_timeout,
            'pool_recycle': app.config.database_pool_recycle
        }
    }


# ==================== CSRF 保护示例 ====================

@route('/form', name='form_page')
def form_page(request):
    """
    表单页面
    
    展示如何使用 CSRF 保护
    """
    # 获取 CSRF Token
    csrf_token = getattr(request, '_csrf_token', 'no-token')
    
    return {
        'message': '表单页面',
        'csrf_token': csrf_token,
        'form_html': f'''
            <form method="POST" action="/form/submit">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <input type="text" name="username" placeholder="用户名">
                <input type="password" name="password" placeholder="密码">
                <button type="submit">提交</button>
            </form>
        ''',
        'note': '表单包含 CSRF Token，提交时会自动验证'
    }


@post('/form/submit', name='form_submit')
def form_submit(request):
    """
    表单提交处理
    
    CSRF 中间件会自动验证 Token
    """
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    return {
        'message': '表单提交成功',
        'data': {
            'username': username,
            'password': '***'  # 不返回密码
        },
        'note': 'CSRF 验证通过，表单数据已接收'
    }


# ==================== 安全头部示例 ====================

@route('/headers', name='security_headers')
def security_headers(request):
    """
    安全头部示例
    
    展示响应中添加的安全头部
    """
    return {
        'message': '安全头部示例',
        'security_headers': {
            'X-Frame-Options': 'DENY - 防止点击劫持',
            'X-Content-Type-Options': 'nosniff - 防止 MIME 类型嗅探',
            'X-XSS-Protection': '1; mode=block - 启用 XSS 过滤',
            'Strict-Transport-Security': 'max-age=31536000 - 强制 HTTPS',
            'Content-Security-Policy': "default-src 'self' - 内容安全策略",
            'Referrer-Policy': 'strict-origin-when-cross-origin - 控制 Referer'
        },
        'note': '查看响应头可以看到所有安全头部'
    }


# 注册路由
app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 安全增强功能综合示例")
    print("=" * 60)
    print()
    print("功能特性：")
    print("  ✓ 数据库连接池优化 - 健康检查、连接回收、监控")
    print("  ✓ CSRF 保护 - 自动生成和验证 CSRF Token")
    print("  ✓ 安全头部 - 自动添加安全相关的 HTTP 头部")
    print()
    print("示例端点：")
    print("  http://localhost:8080/                    - 首页")
    print()
    print("  数据库连接池：")
    print("  http://localhost:8080/db/pool-status      - 连接池状态")
    print()
    print("  CSRF 保护：")
    print("  http://localhost:8080/form                - 表单页面")
    print("  http://localhost:8080/form/submit         - 表单提交（POST）")
    print()
    print("  安全头部：")
    print("  http://localhost:8080/headers             - 安全头部示例")
    print()
    print("测试命令：")
    print("  # 查看连接池状态")
    print("  curl http://localhost:8080/db/pool-status")
    print()
    print("  # 查看安全头部")
    print("  curl -I http://localhost:8080/headers")
    print()
    print("  # 提交表单（需要 CSRF Token）")
    print("  curl -X POST -H 'X-CSRFToken: your-token' \\")
    print("       -d 'username=test&password=123' \\")
    print("       http://localhost:8080/form/submit")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
