#!/usr/bin/env python
# coding: utf-8

"""
各类缓存后端 Web 示例

演示在 Web 页面中使用 Memory、Tree、Redis、Database、Memcache 缓存后端
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from litefs import Litefs
from litefs.cache import (
    MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache,
    CacheFactory, CacheBackend
)


def handler(self):
    """缓存后端主页"""
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    action = self.get.get('action', 'view')
    backend = self.get.get('backend', 'memory')
    
    message = ''
    cache_data = {}
    cache_info = {}
    
    # 根据选择的缓存类型创建缓存实例
    try:
        if backend == 'memory':
            cache = MemoryCache(max_size=10000)
            cache_info = {
                'name': 'Memory Cache',
                'description': '基于内存的缓存，最快的读写速度',
                'features': ['极快速度', '线程安全', '支持容量限制', '进程重启数据丢失']
            }
        elif backend == 'tree':
            cache = TreeCache(clean_period=60, expiration_time=3600)
            cache_info = {
                'name': 'Tree Cache',
                'description': '树形结构缓存，支持自动清理过期数据',
                'features': ['自动过期清理', '支持层级访问', '定期清理机制']
            }
        elif backend == 'redis':
            cache = RedisCache(
                host='localhost',
                port=6379,
                db=0,
                key_prefix='litefs:',
                expiration_time=3600
            )
            cache_info = {
                'name': 'Redis Cache',
                'description': '基于 Redis 的分布式缓存',
                'features': ['高性能读写', '支持分布式', '自动过期', '数据持久化']
            }
        elif backend == 'database':
            cache = DatabaseCache(
                db_path=':memory:',
                table_name='cache',
                expiration_time=3600
            )
            cache_info = {
                'name': 'Database Cache',
                'description': '基于 SQLite 的持久化缓存',
                'features': ['持久化存储', '自动过期清理', '支持复杂类型', '线程安全']
            }
        elif backend == 'memcache':
            cache = MemcacheCache(
                servers=['localhost:11211'],
                key_prefix='litefs:',
                expiration_time=3600
            )
            cache_info = {
                'name': 'Memcache Cache',
                'description': '基于 Memcache 的分布式缓存',
                'features': ['极高性能', '支持分布式', '内存存储', '访问速度快']
            }
        else:
            message = f'不支持的缓存类型: {backend}'
            cache = MemoryCache(max_size=10000)
            cache_info = {
                'name': 'Memory Cache',
                'description': '基于内存的缓存',
                'features': ['极快速度', '线程安全']
            }
        
        # 执行缓存操作
        if action == 'set':
            key = self.get.get('key', 'test_key')
            value = self.get.get('value', 'test_value')
            cache.put(key, value)
            message = f'已设置缓存: {key} = {value}'
        
        elif action == 'get':
            key = self.get.get('key', 'test_key')
            value = cache.get(key)
            if value is not None:
                message = f'获取缓存: {key} = {value}'
            else:
                message = f'缓存不存在: {key}'
        
        elif action == 'delete':
            key = self.get.get('key', 'test_key')
            cache.delete(key)
            message = f'已删除缓存: {key}'
        
        elif action == 'set_multiple':
            cache.put('user:1', {'id': 1, 'name': '张三', 'age': 25})
            cache.put('user:2', {'id': 2, 'name': '李四', 'age': 30})
            cache.put('user:3', {'id': 3, 'name': '王五', 'age': 28})
            message = '已设置多个用户缓存'
        
        elif action == 'set_with_ttl':
            if hasattr(cache, 'put'):
                try:
                    import inspect
                    sig = inspect.signature(cache.put)
                    if 'expiration' in sig.parameters or 'ttl' in sig.parameters:
                        cache.put('temp_data', 'This data will expire in 30 seconds', expiration=30)
                        message = '已设置带 TTL 的缓存（30秒过期）'
                    else:
                        cache.put('temp_data', 'This data will expire in 30 seconds')
                        message = '已设置缓存（当前缓存类型不支持 TTL）'
                except:
                    cache.put('temp_data', 'This data will expire in 30 seconds')
                    message = '已设置缓存'
            else:
                message = '缓存不支持设置操作'
        
        elif action == 'set_large':
            large_data = {'data': list(range(1000)), 'timestamp': '2024-01-01'}
            cache.put('large_data', large_data)
            message = '已设置大数据缓存'
        
        elif action == 'check_stats':
            cache_size = len(cache)
            message = f'缓存统计: 共有 {cache_size} 个键'
        
        elif action == 'batch_get':
            if hasattr(cache, 'get_many'):
                keys = ['product:1', 'product:2', 'product:3']
                values = cache.get_many(keys)
                message = f'批量获取: {values}'
            else:
                message = '当前缓存类型不支持批量获取'
        
        elif action == 'batch_set':
            if hasattr(cache, 'set_many'):
                import json
                cache.set_many({
                    'product:1': json.dumps({'name': '商品1', 'price': 100}),
                    'product:2': json.dumps({'name': '商品2', 'price': 200}),
                    'product:3': json.dumps({'name': '商品3', 'price': 300})
                })
                message = '已批量设置商品缓存'
            else:
                message = '当前缓存类型不支持批量设置'
        
        elif action == 'batch_delete':
            if hasattr(cache, 'delete_many'):
                cache.delete_many(['product:1', 'product:2', 'product:3'])
                message = '已批量删除商品缓存'
            else:
                message = '当前缓存类型不支持批量删除'
        
        elif action == 'check_exists':
            if hasattr(cache, 'exists'):
                key = self.get.get('key', 'test_key')
                exists = cache.exists(key)
                message = f'键 {key} 是否存在: {exists}'
            else:
                message = '当前缓存类型不支持检查存在'
        
        elif action == 'set_expire':
            if hasattr(cache, 'expire'):
                key = self.get.get('key', 'test_key')
                cache.expire(key, 7200)
                message = f'已设置 {key} 的过期时间为 7200 秒'
            else:
                message = '当前缓存类型不支持设置过期时间'
        
        elif action == 'check_ttl':
            if hasattr(cache, 'ttl'):
                key = self.get.get('key', 'test_key')
                ttl = cache.ttl(key)
                message = f'键 {key} 的剩余过期时间: {ttl} 秒'
            else:
                message = '当前缓存类型不支持查询 TTL'
        
        elif action == 'clear':
            if hasattr(cache, 'clear'):
                cache.clear()
                message = '已清除所有缓存'
            else:
                message = '当前缓存类型不支持清除操作'
        
        # 获取缓存数据用于显示
        test_keys = ['test_key', 'user:1', 'user:2', 'user:3', 'temp_data', 'large_data']
        for key in test_keys:
            value = cache.get(key)
            if value is not None:
                cache_data[key] = value
        
        # 关闭缓存连接（如果需要）
        if hasattr(cache, 'close'):
            cache.close()
            
    except Exception as e:
        message = f'缓存操作失败: {str(e)}'
        cache_info = {
            'name': 'Error',
            'description': '缓存初始化失败',
            'features': []
        }
        cache_data = {}
    
    # 生成缓存数据表格
    if cache_data:
        cache_table = """
            <table>
                <thead>
                    <tr>
                        <th>键</th>
                        <th>值</th>
                        <th>类型</th>
                    </tr>
                </thead>
                <tbody>
        """
        for key, value in cache_data.items():
            value_type = type(value).__name__
            if value_type == 'str':
                display_value = value[:100] + '...' if len(value) > 100 else value
            elif value_type == 'list':
                display_value = f'[{len(value)} items]'
            elif value_type == 'dict':
                display_value = f'{{{len(value)} keys}}'
            else:
                display_value = str(value)
            
            cache_table += f"""
                <tr>
                    <td><code>{key}</code></td>
                    <td>{display_value}</td>
                    <td>{value_type}</td>
                </tr>
            """
        cache_table += """
                </tbody>
            </table>
        """
    else:
        cache_table = '<p class="warning">当前缓存为空</p>'
    
    # 生成缓存类型选择器
    backend_selector = """
        <div class="backend-selector">
            <h3>选择缓存类型</h3>
            <div class="backend-buttons">
                <a href="/cache-backends-web?backend=memory">
                    <button class="backend-btn memory-btn">Memory Cache</button>
                </a>
                <a href="/cache-backends-web?backend=tree">
                    <button class="backend-btn tree-btn">Tree Cache</button>
                </a>
                <a href="/cache-backends-web?backend=redis">
                    <button class="backend-btn redis-btn">Redis Cache</button>
                </a>
                <a href="/cache-backends-web?backend=database">
                    <button class="backend-btn database-btn">Database Cache</button>
                </a>
                <a href="/cache-backends-web?backend=memcache">
                    <button class="backend-btn memcache-btn">Memcache Cache</button>
                </a>
            </div>
        </div>
    """
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>缓存后端管理</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }}
            .header h1 {{
                margin: 0;
                font-size: 2em;
            }}
            .backend-selector {{
                background: white;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .backend-buttons {{
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
                margin-top: 15px;
            }}
            .backend-btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s;
                flex: 1;
                min-width: 150px;
            }}
            .memory-btn {{ background: #4CAF50; color: white; }}
            .tree-btn {{ background: #2196F3; color: white; }}
            .redis-btn {{ background: #F44336; color: white; }}
            .database-btn {{ background: #FF9800; color: white; }}
            .memcache-btn {{ background: #9C27B0; color: white; }}
            .backend-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            .section {{
                background: white;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .info {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                border-left: 4px solid #2196F3;
            }}
            .success {{
                background: #e8f5e9;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                color: #2e7d32;
                border-left: 4px solid #4CAF50;
            }}
            .warning {{
                background: #fff3e0;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                color: #e65100;
                border-left: 4px solid #FF9800;
            }}
            .error {{
                background: #ffebee;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                color: #c62828;
                border-left: 4px solid #F44336;
            }}
            button {{
                padding: 10px 20px;
                background: #007bff;
                color: white;
                border: none;
                cursor: pointer;
                margin: 5px;
                border-radius: 5px;
                transition: all 0.3s;
            }}
            button:hover {{
                background: #0056b3;
                transform: translateY(-1px);
            }}
            button.danger {{ background: #dc3545; }}
            button.danger:hover {{ background: #c82333; }}
            button.success {{ background: #28a745; }}
            button.success:hover {{ background: #218838; }}
            button.warning {{ background: #ffc107; color: #212529; }}
            button.warning:hover {{ background: #e0a800; }}
            button.info {{ background: #17a2b8; }}
            button.info:hover {{ background: #138496; }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
                background: white;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background: #f8f9fa;
                font-weight: bold;
                color: #333;
            }}
            tr:hover {{
                background: #f5f5f5;
            }}
            pre {{
                background: #f5f5f5;
                padding: 15px;
                overflow-x: auto;
                border-radius: 5px;
                border: 1px solid #ddd;
            }}
            code {{
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
            .feature-list {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 10px;
                margin: 15px 0;
            }}
            .feature-item {{
                background: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                border-left: 3px solid #007bff;
            }}
            .operation-group {{
                margin: 20px 0;
            }}
            .operation-group h3 {{
                color: #333;
                border-bottom: 2px solid #007bff;
                padding-bottom: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 缓存后端管理系统</h1>
            <p>演示如何在 Web 应用中使用不同类型的缓存后端</p>
        </div>
        
        {backend_selector}
        
        <div class="section">
            <h2>当前缓存: {cache_name}</h2>
            <p><strong>描述：</strong>{cache_description}</p>
            <h3>特性</h3>
            <div class="feature-list">
                {feature_items}
            </div>
        </div>
        
        {message_div}
        
        <div class="section">
            <h2>缓存操作</h2>
            
            <div class="operation-group">
                <h3>基本操作</h3>
                <div class="info">
                    <a href="/cache-backends-web?backend={backend}&action=set&key=test_key&value=test_value">
                        <button class="success">设置缓存</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=get&key=test_key">
                        <button class="info">获取缓存</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=delete&key=test_key">
                        <button class="danger">删除缓存</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=clear">
                        <button class="danger">清除所有缓存</button>
                    </a>
                </div>
            </div>
            
            <div class="operation-group">
                <h3>批量操作</h3>
                <div class="info">
                    <a href="/cache-backends-web?backend={backend}&action=set_multiple">
                        <button class="success">设置多个缓存</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=batch_get">
                        <button class="info">批量获取</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=batch_set">
                        <button class="success">批量设置</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=batch_delete">
                        <button class="danger">批量删除</button>
                    </a>
                </div>
            </div>
            
            <div class="operation-group">
                <h3>高级操作</h3>
                <div class="info">
                    <a href="/cache-backends-web?backend={backend}&action=set_with_ttl">
                        <button class="warning">设置带 TTL 的缓存</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=set_large">
                        <button class="info">设置大数据缓存</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=check_exists&key=test_key">
                        <button class="info">检查键是否存在</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=set_expire&key=test_key">
                        <button class="warning">设置过期时间</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=check_ttl&key=test_key">
                        <button class="info">检查 TTL</button>
                    </a>
                    <a href="/cache-backends-web?backend={backend}&action=check_stats">
                        <button class="info">查看统计</button>
                    </a>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>当前缓存数据</h2>
            {cache_table}
        </div>
        
        <div class="section">
            <h2>API 使用示例</h2>
            <pre><code>
# 创建缓存实例
from litefs.cache import {cache_class}

cache = {cache_class}({cache_params})

# 基本操作
cache.put('key', 'value')
value = cache.get('key')
cache.delete('key')

# 批量操作（支持的缓存类型）
cache.set_many({{'key1': 'value1', 'key2': 'value2'}})
values = cache.get_many(['key1', 'key2'])
cache.delete_many(['key1', 'key2'])

# 高级操作（支持的缓存类型）
cache.exists('key')
cache.expire('key', 3600)
ttl = cache.ttl('key')
cache.clear()
            </code></pre>
        </div>
        
        <div class="section">
            <h2>缓存应用场景</h2>
            <ul>
                <li><strong>数据库查询结果缓存：</strong>减少数据库压力，提高查询速度</li>
                <li><strong>API 响应缓存：</strong>缓存 API 响应，减少重复计算</li>
                <li><strong>页面渲染缓存：</strong>缓存渲染后的页面，减少渲染时间</li>
                <li><strong>会话数据缓存：</strong>缓存会话数据，提高访问速度</li>
                <li><strong>配置数据缓存：</strong>缓存配置信息，减少 I/O 操作</li>
                <li><strong>计算结果缓存：</strong>缓存复杂计算结果，避免重复计算</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>性能对比</h2>
            <table>
                <thead>
                    <tr>
                        <th>缓存类型</th>
                        <th>读取速度</th>
                        <th>写入速度</th>
                        <th>持久化</th>
                        <th>分布式</th>
                        <th>适用场景</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Memory Cache</strong></td>
                        <td>极快</td>
                        <td>极快</td>
                        <td>否</td>
                        <td>否</td>
                        <td>单机应用、临时数据</td>
                    </tr>
                    <tr>
                        <td><strong>Tree Cache</strong></td>
                        <td>快</td>
                        <td>快</td>
                        <td>否</td>
                        <td>否</td>
                        <td>需要自动清理过期数据</td>
                    </tr>
                    <tr>
                        <td><strong>Redis Cache</strong></td>
                        <td>快</td>
                        <td>快</td>
                        <td>可选</td>
                        <td>是</td>
                        <td>分布式应用、高性能需求</td>
                    </tr>
                    <tr>
                        <td><strong>Database Cache</strong></td>
                        <td>中</td>
                        <td>中</td>
                        <td>是</td>
                        <td>否</td>
                        <td>需要持久化存储</td>
                    </tr>
                    <tr>
                        <td><strong>Memcache Cache</strong></td>
                        <td>极快</td>
                        <td>极快</td>
                        <td>否</td>
                        <td>是</td>
                        <td>高性能、临时数据</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    # 根据消息类型设置不同的样式
    if message:
        if '失败' in message or '错误' in message:
            message_div = f'<div class="error"><strong>{message}</strong></div>'
        elif '删除' in message or '清除' in message:
            message_div = f'<div class="warning"><strong>{message}</strong></div>'
        else:
            message_div = f'<div class="success"><strong>{message}</strong></div>'
    else:
        message_div = ''
    
    # 生成特性列表
    feature_items = ''.join([f'<div class="feature-item">{feature}</div>' for feature in cache_info.get('features', [])])
    
    # 根据缓存类型设置 API 示例
    cache_examples = {
        'memory': ('MemoryCache', 'max_size=10000'),
        'tree': ('TreeCache', 'clean_period=60, expiration_time=3600'),
        'redis': ('RedisCache', 'host="localhost", port=6379, db=0, key_prefix="litefs:"'),
        'database': ('DatabaseCache', 'db_path=":memory:", table_name="cache", expiration_time=3600'),
        'memcache': ('MemcacheCache', 'servers=["localhost:11211"], key_prefix="litefs:"')
    }
    cache_class, cache_params = cache_examples.get(backend, ('MemoryCache', 'max_size=10000'))
    
    return html.format(
        backend_selector=backend_selector,
        cache_name=cache_info.get('name', ''),
        cache_description=cache_info.get('description', ''),
        feature_items=feature_items,
        message_div=message_div,
        backend=backend,
        cache_table=cache_table,
        cache_class=cache_class,
        cache_params=cache_params
    )