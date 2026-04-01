#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json

from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs
from litefs.routing import get
from litefs.cache import MemoryCache, TreeCache, RedisCache, DatabaseCache, MemcacheCache


# 定义缓存后端管理的路由处理函数
@get('/cache-backends-web', name='cache_backends_web')
def cache_backends_web_handler(request):
    action = request.params.get('action', 'view')
    backend = request.params.get('backend', 'memory')
    message = ''
    
    # 根据后端类型创建缓存实例
    if backend == 'memory':
        cache = MemoryCache(max_size=1000)
    elif backend == 'tree':
        cache = TreeCache()
    elif backend == 'redis':
        try:
            cache = RedisCache()
        except Exception as e:
            return f"Redis 连接失败: {e}"
    elif backend == 'database':
        cache = DatabaseCache()
    elif backend == 'memcache':
        try:
            cache = MemcacheCache()
        except Exception as e:
            return f"Memcache 连接失败: {e}"
    else:
        cache = MemoryCache(max_size=1000)
    
    # 处理缓存操作
    if action == 'set':
        key = request.params.get('key', 'test_key')
        value = request.params.get('value', 'test_value')
        cache.put(key, value)
        message = f"已设置 {backend} 缓存: {key} = {value}"
    elif action == 'get':
        key = request.params.get('key', 'test_key')
        value = cache.get(key)
        if value is not None:
            message = f"获取 {backend} 缓存: {key} = {value}"
        else:
            message = f"{backend} 缓存不存在: {key}"
    elif action == 'delete':
        key = request.params.get('key', 'test_key')
        result = cache.delete(key)
        if result:
            message = f"已删除 {backend} 缓存: {key}"
        else:
            message = f"{backend} 缓存不存在: {key}"
    elif action == 'clear':
        cache.clear()
        message = f"已清除所有 {backend} 缓存"
    
    # 获取缓存数据
    try:
        if hasattr(cache, 'to_dict'):
            cache_data = cache.to_dict()
        else:
            cache_data = {}
    except Exception:
        cache_data = {}
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>缓存后端 Web 示例</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 50px auto; padding: 20px; }}
            .section {{ margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            .success {{ background: #d4edda; padding: 15px; border-radius: 5px; margin: 10px 0; color: #155724; }}
            .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; color: #856404; }}
            button {{ padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; margin: 5px; }}
            button:hover {{ background: #0056b3; }}
            button.danger {{ background: #dc3545; }}
            button.danger:hover {{ background: #c82333; }}
            button.success {{ background: #28a745; }}
            button.success:hover {{ background: #218838; }}
            pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; border-radius: 3px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            select {{ padding: 8px; margin: 5px; }}
        </style>
    </head>
    <body>
        <h1>缓存后端 Web 示例</h1>
        
        <div class="success">
            <strong>{message}</strong>
        </div>
        
        <div class="section">
            <h2>缓存后端选择</h2>
            <div class="info">
                <form action="/cache-backends-web" method="get">
                    <select name="backend" onchange="this.form.submit()">
                        <option value="memory" {memory_selected}>Memory Cache</option>
                        <option value="tree" {tree_selected}>Tree Cache</option>
                        <option value="redis" {redis_selected}>Redis Cache</option>
                        <option value="database" {database_selected}>Database Cache</option>
                        <option value="memcache" {memcache_selected}>Memcache Cache</option>
                    </select>
                    <input type="hidden" name="action" value="view">
                </form>
            </div>
        </div>
        
        <div class="section">
            <h2>缓存操作</h2>
            <div class="info">
                <a href="/cache-backends-web?action=set&backend={backend}&key=test_key&value=test_value">
                    <button>设置缓存</button>
                </a>
                <a href="/cache-backends-web?action=get&backend={backend}&key=test_key">
                    <button>获取缓存</button>
                </a>
                <a href="/cache-backends-web?action=delete&backend={backend}&key=test_key">
                    <button class="danger">删除缓存</button>
                </a>
                <a href="/cache-backends-web?action=clear&backend={backend}">
                    <button class="danger">清除所有缓存</button>
                </a>
            </div>
        </div>
        
        <div class="section">
            <h2>当前缓存数据</h2>
            {cache_table}
        </div>
        
        <div class="section">
            <h2>缓存后端说明</h2>
            <ul>
                <li><strong>Memory Cache：</strong>基于内存的缓存，支持 TTL</li>
                <li><strong>Tree Cache：</strong>树形结构缓存，支持层级访问</li>
                <li><strong>Redis Cache：</strong>基于 Redis 的分布式缓存</li>
                <li><strong>Database Cache：</strong>基于数据库的持久化缓存</li>
                <li><strong>Memcache Cache：</strong>基于 Memcache 的缓存</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>注意事项</h2>
            <ul>
                <li>Redis 需要本地安装并运行在 localhost:6379</li>
                <li>Memcache 需要本地安装并运行在 localhost:11211</li>
                <li>Database Cache 使用内存数据库，无需额外配置</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    # 生成选中状态
    memory_selected = 'selected' if backend == 'memory' else ''
    tree_selected = 'selected' if backend == 'tree' else ''
    redis_selected = 'selected' if backend == 'redis' else ''
    database_selected = 'selected' if backend == 'database' else ''
    memcache_selected = 'selected' if backend == 'memcache' else ''
    
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
                display_value = f"[{len(value)} items]"
            elif value_type == 'dict':
                display_value = f"{{{len(value)} keys}}"
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
    
    return html.format(
        message=message,
        backend=backend,
        memory_selected=memory_selected,
        tree_selected=tree_selected,
        redis_selected=redis_selected,
        database_selected=database_selected,
        memcache_selected=memcache_selected,
        cache_table=cache_table
    )


def main():
    """缓存后端 Web 示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        debug=True
    )
    
    # 注册路由
    app.register_routes(__name__)
    
    print("=" * 60)
    print("Litefs Cache Backends Web Example")
    print("=" * 60)
    print(f"访问地址: http://localhost:8080/cache-backends-web")
    print("=" * 60)
    print("\n支持的缓存后端:")
    print("  - Memory Cache (内存缓存)")
    print("  - Tree Cache (树形缓存)")
    print("  - Redis Cache (Redis 缓存)")
    print("  - Database Cache (数据库缓存)")
    print("  - Memcache Cache (Memcache 缓存)")
    print("=" * 60)
    print("\n注意:")
    print("  - Redis 需要本地安装并运行在 localhost:6379")
    print("  - Memcache 需要本地安装并运行在 localhost:11211")
    print("  - Database Cache 使用内存数据库，无需额外配置")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
