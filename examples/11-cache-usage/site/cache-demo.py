#!/usr/bin/env python
# coding: utf-8

"""
缓存使用 Web 示例

演示在 Web 应用中使用各种缓存
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from litefs import Litefs
from litefs.cache import (
    CacheManager, CacheBackend, CacheFactory,
    MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache
)
import json


def handler(self):
    """缓存演示主页"""
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])

    action = self.get.get('action', 'view')

    message = ''
    message_type = 'info'

    # 获取缓存类型
    cache_type = self.get.get('cache_type', 'memory')
    
    # 根据选择的缓存类型创建缓存实例
    try:
        if cache_type == 'memory':
            cache = CacheManager.get_cache(
                backend=CacheBackend.MEMORY,
                cache_key='web_memory_cache',
                max_size=10000
            )
            cache_info = {
                'name': '内存缓存 (MemoryCache)',
                'description': '基于内存的高速缓存，适合单机应用'
            }
        elif cache_type == 'tree':
            cache = CacheManager.get_cache(
                backend=CacheBackend.TREE,
                cache_key='web_tree_cache',
                max_size=10000
            )
            cache_info = {
                'name': '树结构缓存 (TreeCache)',
                'description': '基于树结构的内存缓存，支持更复杂的数据结构'
            }
        elif cache_type == 'redis':
            cache = CacheManager.get_cache(
                backend=CacheBackend.REDIS,
                cache_key='web_redis_cache',
                host='localhost',
                port=6379,
                db=0
            )
            cache_info = {
                'name': 'Redis缓存 (RedisCache)',
                'description': '基于Redis的分布式缓存，适合多实例应用'
            }
        elif cache_type == 'database':
            cache = CacheManager.get_cache(
                backend=CacheBackend.DATABASE,
                cache_key='web_database_cache',
                storage='memory'
            )
            cache_info = {
                'name': '数据库缓存 (DatabaseCache)',
                'description': '基于数据库的持久化缓存，支持数据持久化'
            }
        elif cache_type == 'memcache':
            cache = CacheManager.get_cache(
                backend=CacheBackend.MEMCACHE,
                cache_key='web_memcache_cache',
                servers=['localhost:11211']
            )
            cache_info = {
                'name': 'Memcache缓存 (MemcacheCache)',
                'description': '基于Memcached的分布式缓存，适合高并发场景'
            }
        else:
            cache = CacheManager.get_cache(
                backend=CacheBackend.MEMORY,
                cache_key='web_demo_cache',
                max_size=10000
            )
            cache_info = {
                'name': '内存缓存 (MemoryCache)',
                'description': '基于内存的高速缓存，适合单机应用'
            }
    except Exception as e:
        cache = CacheManager.get_cache(
            backend=CacheBackend.MEMORY,
            cache_key='web_demo_cache',
            max_size=10000
        )
        cache_info = {
            'name': '内存缓存 (MemoryCache)',
            'description': '基于内存的高速缓存，适合单机应用'
        }
        message = f'⚠️ 缓存类型初始化失败: {str(e)}，已切换到内存缓存'
        message_type = 'warning'
    
    print(id(cache))

    # 执行操作
    if action == 'set':
        key = self.get.get('key', 'demo_key')
        value = self.get.get('value', 'demo_value')
        cache.put(key, value)
        message = f'✓ 已设置缓存: {key} = {value}'
        message_type = 'success'

    elif action == 'get':
        key = self.get.get('key', 'demo_key')
        value = cache.get(key)
        if value is not None:
            message = f'✓ 获取缓存: {key} = {value}'
            message_type = 'success'
        else:
            message = f'✗ 缓存不存在: {key}'
            message_type = 'warning'

    elif action == 'delete':
        key = self.get.get('key', 'demo_key')
        cache.delete(key)
        message = f'✓ 已删除缓存: {key}'
        message_type = 'success'

    elif action == 'clear':
        cache.clear()
        message = '✓ 已清除所有缓存'
        message_type = 'success'

    elif action == 'set_user':
        user_id = self.get.get('user_id', '1')
        user_data = {
            'id': int(user_id),
            'name': f'用户{user_id}',
            'email': f'user{user_id}@example.com',
            'age': 20 + int(user_id)
        }
        cache.put(f'user:{user_id}', user_data)
        message = f'✓ 已设置用户数据: {user_data}'
        message_type = 'success'

    elif action == 'get_user':
        user_id = self.get.get('user_id', '1')
        user_data = cache.get(f'user:{user_id}')
        if user_data:
            message = f'✓ 获取用户数据: {user_data}'
            message_type = 'success'
        else:
            message = f'✗ 用户数据不存在: user:{user_id}'
            message_type = 'warning'

    elif action == 'set_products':
        products = [
            {'id': 1, 'name': '商品1', 'price': 99.99, 'stock': 100},
            {'id': 2, 'name': '商品2', 'price': 199.99, 'stock': 50},
            {'id': 3, 'name': '商品3', 'price': 299.99, 'stock': 30},
            {'id': 4, 'name': '商品4', 'price': 399.99, 'stock': 20},
            {'id': 5, 'name': '商品5', 'price': 499.99, 'stock': 10}
        ]
        cache.put('products', products)
        message = f'✓ 已设置 {len(products)} 个商品'
        message_type = 'success'

    elif action == 'get_products':
        products = cache.get('products')
        if products:
            message = f'✓ 获取到 {len(products)} 个商品'
            message_type = 'success'
        else:
            message = '✗ 商品列表不存在'
            message_type = 'warning'

    elif action == 'set_config':
        configs = {
            'theme': 'dark',
            'language': 'zh-CN',
            'timezone': 'Asia/Shanghai',
            'page_size': 20
        }
        cache.put('config', configs)
        message = f'✓ 已设置系统配置'
        message_type = 'success'

    elif action == 'get_config':
        config = cache.get('config')
        if config:
            message = f'✓ 获取系统配置: {config}'
            message_type = 'success'
        else:
            message = '✗ 系统配置不存在'
            message_type = 'warning'

    # 获取所有缓存数据
    cache_data = []
    test_keys = ['demo_key', 'user:1', 'user:2', 'user:3', 'products', 'config']
    for key in test_keys:
        value = cache.get(key)
        if value is not None:
            cache_data.append({'key': key, 'value': value, 'type': type(value).__name__})

    # 生成消息样式
    message_styles = {
        'success': 'background: #d4edda; color: #155724; border-left: 4px solid #28a745;',
        'warning': 'background: #fff3cd; color: #856404; border-left: 4px solid #ffc107;',
        'error': 'background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545;',
        'info': 'background: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8;'
    }

    # 生成缓存数据表格
    if cache_data:
        cache_table = """
            <table>
                <thead>
                    <tr>
                        <th>键</th>
                        <th>值</th>
                        <th>类型</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
        """
        for item in cache_data:
            value_str = str(item['value'])
            if len(value_str) > 100:
                value_str = value_str[:100] + '...'

            cache_table += f"""
                <tr>
                    <td><code>{item['key']}</code></td>
                    <td>{value_str}</td>
                    <td><span class="badge">{item['type']}</span></td>
                    <td>
                        <a href="/cache-demo?action=delete&key={item['key']}&cache_type={cache_type}" 
                           onclick="return confirm('确定要删除吗？')">
                           <button class="btn-danger">删除</button>
                        </a>
                    </td>
                </tr>
            """
        cache_table += """
                </tbody>
            </table>
        """
    else:
        cache_table = '<p class="empty-cache">当前缓存为空</p>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>缓存使用示例</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }}
            .header h1 {{
                font-size: 2.5em;
                margin-bottom: 10px;
            }}
            .header p {{
                opacity: 0.9;
                font-size: 1.1em;
            }}
            .content {{
                padding: 40px;
            }}
            .section {{
                margin-bottom: 40px;
            }}
            .section h2 {{
                color: #333;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid #667eea;
            }}
            .message {{
                padding: 15px 20px;
                margin: 20px 0;
                border-radius: 8px;
                font-weight: 500;
            }}
            .btn-group {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-bottom: 20px;
            }}
            button {{
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s;
                font-size: 14px;
            }}
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .btn-primary {{
                background: #667eea;
                color: white;
            }}
            .btn-primary:hover {{
                background: #5568d3;
            }}
            .btn-success {{
                background: #28a745;
                color: white;
            }}
            .btn-success:hover {{
                background: #218838;
            }}
            .btn-warning {{
                background: #ffc107;
                color: #212529;
            }}
            .btn-warning:hover {{
                background: #e0a800;
            }}
            .btn-danger {{
                background: #dc3545;
                color: white;
            }}
            .btn-danger:hover {{
                background: #c82333;
            }}
            .btn-info {{
                background: #17a2b8;
                color: white;
            }}
            .btn-info:hover {{
                background: #138496;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            th {{
                background: #667eea;
                color: white;
                padding: 15px;
                text-align: left;
                font-weight: 600;
            }}
            td {{
                padding: 15px;
                border-bottom: 1px solid #e0e0e0;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            tr:last-child td {{
                border-bottom: none;
            }}
            code {{
                background: #f4f4f4;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                color: #e83e8c;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                background: #667eea;
                color: white;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
            }}
            .empty-cache {{
                text-align: center;
                padding: 40px;
                color: #999;
                font-style: italic;
            }}
            .info-box {{
                background: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #2196F3;
            }}
            .info-box h3 {{
                color: #1976D2;
                margin-bottom: 10px;
            }}
            .info-box ul {{
                margin-left: 20px;
                color: #555;
            }}
            .info-box li {{
                margin: 8px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 缓存使用示例</h1>
                <p>演示如何在 Web 应用中使用 Litefs 缓存</p>
            </div>

            <div class="content">
                {f'<div class="message" style="{message_styles[message_type]}">{message}</div>' if message else ''}

                <div class="section">
                    <h2>缓存类型选择</h2>
                    <div class="btn-group">
                        <a href="/cache-demo?cache_type=memory">
                            <button class="btn-primary">内存缓存</button>
                        </a>
                        <a href="/cache-demo?cache_type=tree">
                            <button class="btn-primary">树结构缓存</button>
                        </a>
                        <a href="/cache-demo?cache_type=redis">
                            <button class="btn-primary">Redis缓存</button>
                        </a>
                        <a href="/cache-demo?cache_type=database">
                            <button class="btn-primary">数据库缓存</button>
                        </a>
                        <a href="/cache-demo?cache_type=memcache">
                            <button class="btn-primary">Memcache缓存</button>
                        </a>
                    </div>
                    <div class="info-box" style="margin-top: 20px;">
                        <h3>当前缓存</h3>
                        <p><strong>类型：</strong>{cache_info['name']}</p>
                        <p><strong>描述：</strong>{cache_info['description']}</p>
                    </div>
                </div>

                <div class="section">
                    <h2>基本操作</h2>
                    <div class="btn-group">
                        <a href="/cache-demo?action=set&key=demo_key&value=demo_value&cache_type={cache_type}">
                            <button class="btn-success">设置缓存</button>
                        </a>
                        <a href="/cache-demo?action=get&key=demo_key&cache_type={cache_type}">
                            <button class="btn-info">获取缓存</button>
                        </a>
                        <a href="/cache-demo?action=delete&key=demo_key&cache_type={cache_type}">
                            <button class="btn-danger">删除缓存</button>
                        </a>
                        <a href="/cache-demo?action=clear&cache_type={cache_type}" onclick="return confirm('确定要清除所有缓存吗？')">
                            <button class="btn-danger">清除所有</button>
                        </a>
                    </div>
                </div>

                <div class="section">
                    <h2>用户数据缓存</h2>
                    <div class="btn-group">
                        <a href="/cache-demo?action=set_user&user_id=1&cache_type={cache_type}">
                            <button class="btn-success">设置用户1</button>
                        </a>
                        <a href="/cache-demo?action=set_user&user_id=2&cache_type={cache_type}">
                            <button class="btn-success">设置用户2</button>
                        </a>
                        <a href="/cache-demo?action=set_user&user_id=3&cache_type={cache_type}">
                            <button class="btn-success">设置用户3</button>
                        </a>
                        <a href="/cache-demo?action=get_user&user_id=1&cache_type={cache_type}">
                            <button class="btn-info">获取用户1</button>
                        </a>
                    </div>
                </div>

                <div class="section">
                    <h2>商品列表缓存</h2>
                    <div class="btn-group">
                        <a href="/cache-demo?action=set_products&cache_type={cache_type}">
                            <button class="btn-success">设置商品列表</button>
                        </a>
                        <a href="/cache-demo?action=get_products&cache_type={cache_type}">
                            <button class="btn-info">获取商品列表</button>
                        </a>
                    </div>
                </div>

                <div class="section">
                    <h2>系统配置缓存</h2>
                    <div class="btn-group">
                        <a href="/cache-demo?action=set_config&cache_type={cache_type}">
                            <button class="btn-success">设置配置</button>
                        </a>
                        <a href="/cache-demo?action=get_config&cache_type={cache_type}">
                            <button class="btn-info">获取配置</button>
                        </a>
                    </div>
                </div>

                <div class="section">
                    <h2>当前缓存数据</h2>
                    {cache_table}
                </div>

                <div class="section">
                    <div class="info-box">
                        <h3>💡 缓存使用说明</h3>
                        <ul>
                            <li><strong>基本操作：</strong>设置、获取、删除单个键值对</li>
                            <li><strong>用户数据：</strong>缓存用户信息，减少数据库查询</li>
                            <li><strong>商品列表：</strong>缓存商品数据，提升页面加载速度</li>
                            <li><strong>系统配置：</strong>缓存配置信息，避免重复读取配置文件</li>
                            <li><strong>全局共享：</strong>使用 CacheManager 确保缓存在多个实例间共享</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html
