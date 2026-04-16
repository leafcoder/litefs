#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合示例 - 展示 Litefs 框架的主要特性

本示例展示了 Litefs 框架的核心功能：
1. 路由系统（装饰器和方法链风格）
2. 中间件系统（日志、安全、CORS）
3. 会话管理
4. 缓存系统
5. 请求验证
6. 静态文件服务
7. 错误处理
8. 健康检查
"""

import sys
import os
import time

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))  # noqa: E402

from litefs import Litefs, Response
from litefs.routing import get, post
from litefs.middleware import (
    LoggingMiddleware,
    SecurityMiddleware,
    CORSMiddleware,
    RateLimitMiddleware,
    HealthCheck
)
from litefs.cache import MemoryCache, TreeCache
from litefs.validators import required, string_type, number_type, email

# ==================== 创建应用 ====================

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    session_backend='memory',
    session_expiration_time=3600,
    cache_backend='tree',
    cache_expiration_time=3600,
    cache_clean_period=60
)

# ==================== 添加中间件 ====================

# 日志中间件
app.add_middleware(LoggingMiddleware)

# 安全中间件
app.add_middleware(SecurityMiddleware)

# CORS 中间件
app.add_middleware(CORSMiddleware)

# 限流中间件
app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=60)

# 健康检查中间件
app.add_middleware(HealthCheck, path='/health', status=200)

# ==================== 静态文件服务 ====================

# 添加静态文件目录
app.add_static('/static', './static', name='static')

# ==================== 缓存示例 ====================

# 创建缓存实例
memory_cache = MemoryCache(max_size=1000)
tree_cache = TreeCache(clean_period=60, expiration_time=3600)


@app.add_get('/cache', name='cache_example')
def cache_example_handler(request):
    """缓存示例"""
    # 使用内存缓存
    memory_cache.put('counter', memory_cache.get('counter', 0) + 1)
    
    # 使用树形缓存
    tree_cache.put('timestamp', time.time())
    
    return Response.json({
        'memory_cache': memory_cache.get('counter'),
        'tree_cache': tree_cache.get('timestamp'),
        'app_cache': app.caches.get('visit_count', 0)
    })


# ==================== 会话示例 ====================

@app.add_get('/session', name='session_example')
def session_example_handler(request):
    """会话示例"""
    # 获取或创建会话
    session = request.session
    
    # 获取访问次数
    visit_count = session.get('visit_count', 0)
    visit_count += 1
    session['visit_count'] = visit_count
    
    # 获取用户名
    username = session.get('username', 'Guest')
    
    return Response.json({
        'visit_count': visit_count,
        'username': username,
        'session_id': session.id
    })


# ==================== 表单验证示例 ====================

@app.add_get('/form', name='form_example')
def form_example_handler(request):
    """表单页面"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>表单验证示例</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
        button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .error { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>表单验证示例</h1>
    <form id="demoForm">
        <div class="form-group">
            <label for="username">用户名 (必填，3-20字符)</label>
            <input type="text" id="username" name="username" required>
        </div>
        <div class="form-group">
            <label for="email">邮箱 (必填，有效邮箱格式)</label>
            <input type="email" id="email" name="email" required>
        </div>
        <div class="form-group">
            <label for="age">年龄 (0-120)</label>
            <input type="number" id="age" name="age" min="0" max="120">
        </div>
        <button type="submit">提交</button>
    </form>
    <div id="result"></div>
    
    <script>
        document.getElementById('demoForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(Object.fromEntries(formData))
            });
            const result = await response.json();
            document.getElementById('result').innerHTML = 
                result.is_valid 
                ? `<p style="color: green;">✓ 验证通过！</p><pre>${JSON.stringify(result, null, 2)}</pre>`
                : `<p style="color: red;">✗ 验证失败：</p><pre>${JSON.stringify(result, null, 2)}</pre>`;
        });
    </script>
</body>
</html>
'''


@app.add_post('/validate', name='validate_form')
def validate_form_handler(request):
    """表单验证"""
    # 定义验证规则
    query_rules = {}
    post_rules = {
        'username': [required(), string_type(min_length=3, max_length=20)],
        'email': [required(), email()],
        'age': [number_type(min_value=0, max_value=120)],
    }
    
    # 验证数据
    is_valid, errors = request.validate_all(query_rules, post_rules)
    
    if is_valid:
        return Response.json({
            'is_valid': True,
            'data': {
                'username': request.post.get('username'),
                'email': request.post.get('email'),
                'age': request.post.get('age')
            }
        })
    else:
        return Response.json({
            'is_valid': False,
            'errors': errors
        }, status=400)


# ==================== 路由示例 ====================

@app.add_get('/', name='index')
def index_handler(request):
    """首页"""
    return Response.json({
        'message': 'Litefs 综合示例',
        'version': '1.0.0',
        'features': [
            '路由系统',
            '中间件系统',
            '会话管理',
            '缓存系统',
            '请求验证',
            '静态文件服务',
            '错误处理',
            '健康检查'
        ]
    })


@app.add_get('/user/{id}', name='user_detail')
def user_detail_handler(request, id):
    """用户详情"""
    return Response.json({
        'user_id': id,
        'message': f'用户 ID: {id}'
    })


@app.add_get('/users', name='user_list')
def user_list_handler(request):
    """用户列表（支持分页）"""
    page = int(request.params.get('page', 1))
    limit = int(request.params.get('limit', 10))
    
    users = [
        {'id': 1, 'username': 'admin', 'email': 'admin@example.com'},
        {'id': 2, 'username': 'john', 'email': 'john@example.com'},
        {'id': 3, 'username': 'jane', 'email': 'jane@example.com'},
    ]
    
    total = len(users)
    start = (page - 1) * limit
    end = start + limit
    users = users[start:end]
    
    return Response.json({
        'users': users,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'pages': (total + limit - 1) // limit
        }
    })


@app.add_post('/user', name='create_user')
def create_user_handler(request):
    """创建用户"""
    username = request.data.get('username', '')
    email = request.data.get('email', '')
    
    return Response.json({
        'message': '用户创建成功',
        'user': {
            'username': username,
            'email': email
        }
    }, status=201)


@app.add_put('/user/{id}', name='update_user')
def update_user_handler(request, id):
    """更新用户"""
    return Response.json({
        'message': '用户更新成功',
        'user_id': id
    })


@app.add_delete('/user/{id}', name='delete_user')
def delete_user_handler(request, id):
    """删除用户"""
    return Response.json({
        'message': '用户删除成功',
        'user_id': id
    })


# ==================== 运行服务器 ====================

if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 综合示例")
    print("=" * 60)
    print("访问地址: http://localhost:8080")
    print("=" * 60)
    print("可用路由:")
    print("  GET  /              - 首页")
    print("  GET  /cache         - 缓存示例")
    print("  GET  /session       - 会话示例")
    print("  GET  /form          - 表单验证示例")
    print("  POST /validate      - 表单验证")
    print("  GET  /user/{id}     - 用户详情")
    print("  GET  /users         - 用户列表")
    print("  POST /user          - 创建用户")
    print("  PUT  /user/{id}     - 更新用户")
    print("  DELETE /user/{id}   - 删除用户")
    print("  GET  /health        - 健康检查")
    print("  GET  /static/*      - 静态文件")
    print("=" * 60)
    print("中间件:")
    print("  - LoggingMiddleware  (日志)")
    print("  - SecurityMiddleware (安全)")
    print("  - CORSMiddleware     (CORS)")
    print("  - RateLimitMiddleware(限流)")
    print("  - HealthCheck        (健康检查)")
    print("=" * 60)
    print("错误处理:")
    print("  - 自动处理 404 和 500 错误")
    print("  - 支持自定义错误页面（通过配置 error_pages_dir）")
    print("=" * 60)
    
    app.run()
