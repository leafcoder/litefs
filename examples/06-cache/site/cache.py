def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    from litefs.cache import MemoryCache
    
    action = self.get.get('action', 'view')
    message = ''
    
    cache = MemoryCache(max_size=1000)
    
    if action == 'set':
        key = self.get.get('key', 'test_key')
        value = self.get.get('value', 'test_value')
        cache.put(key, value)
        message = f"已设置缓存: {key} = {value}"
    
    elif action == 'get':
        key = self.get.get('key', 'test_key')
        value = cache.get(key)
        if value is not None:
            message = f"获取缓存: {key} = {value}"
        else:
            message = f"缓存不存在: {key}"
    
    elif action == 'delete':
        key = self.get.get('key', 'test_key')
        result = cache.delete(key)
        if result:
            message = f"已删除缓存: {key}"
        else:
            message = f"缓存不存在: {key}"
    
    elif action == 'clear':
        cache.clear()
        message = "已清除所有缓存"
    
    elif action == 'set_multiple':
        cache.put('user:1', {'id': 1, 'name': '张三', 'age': 25})
        cache.put('user:2', {'id': 2, 'name': '李四', 'age': 30})
        cache.put('user:3', {'id': 3, 'name': '王五', 'age': 28})
        message = "已设置多个用户缓存"
    
    elif action == 'set_with_ttl':
        cache.put('temp_data', 'This data will expire', ttl=10)
        message = "已设置带 TTL 的缓存（10秒过期）"
    
    elif action == 'check_stats':
        stats = cache.get_stats()
        message = f"缓存统计: {stats}"
    
    elif action == 'set_large':
        large_data = {'data': list(range(1000))}
        cache.put('large_data', large_data)
        message = "已设置大数据缓存"
    
    cache_data = cache.to_dict()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>缓存管理示例</title>
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
        </style>
    </head>
    <body>
        <h1>缓存管理示例</h1>
        
        <div class="success">
            <strong>{message}</strong>
        </div>
        
        <div class="section">
            <h2>缓存操作</h2>
            
            <h3>基本操作</h3>
            <div class="info">
                <a href="/cache?action=set&key=test_key&value=test_value">
                    <button>设置缓存</button>
                </a>
                <a href="/cache?action=get&key=test_key">
                    <button>获取缓存</button>
                </a>
                <a href="/cache?action=delete&key=test_key">
                    <button class="danger">删除缓存</button>
                </a>
                <a href="/cache?action=clear">
                    <button class="danger">清除所有缓存</button>
                </a>
            </div>
            
            <h3>高级操作</h3>
            <div class="info">
                <a href="/cache?action=set_multiple">
                    <button class="success">设置多个缓存</button>
                </a>
                <a href="/cache?action=set_with_ttl">
                    <button class="success">设置带 TTL 的缓存</button>
                </a>
                <a href="/cache?action=check_stats">
                    <button>查看缓存统计</button>
                </a>
                <a href="/cache?action=set_large">
                    <button>设置大数据缓存</button>
                </a>
            </div>
        </div>
        
        <div class="section">
            <h2>当前缓存数据</h2>
            {cache_table}
        </div>
        
        <div class="section">
            <h2>缓存使用说明</h2>
            <ul>
                <li><strong>设置缓存：</strong>使用 <code>cache.put(key, value, ttl=None)</code></li>
                <li><strong>获取缓存：</strong>使用 <code>cache.get(key)</code></li>
                <li><strong>删除缓存：</strong>使用 <code>cache.delete(key)</code></li>
                <li><strong>清除缓存：</strong>使用 <code>cache.clear()</code></li>
                <li><strong>检查存在：</strong>使用 <code>cache.exists(key)</code></li>
                <li><strong>获取统计：</strong>使用 <code>cache.get_stats()</code></li>
            </ul>
        </div>
        
        <div class="section">
            <h2>缓存类型</h2>
            <ul>
                <li><strong>MemoryCache：</strong>基于内存的缓存，支持 TTL</li>
                <li><strong>TreeCache：</strong>树形结构缓存，支持层级访问</li>
                <li><strong>RedisCache：</strong>基于 Redis 的分布式缓存</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>缓存应用场景</h2>
            <ul>
                <li><strong>数据库查询结果缓存：</strong>减少数据库压力</li>
                <li><strong>API 响应缓存：</strong>提高 API 响应速度</li>
                <li><strong>计算结果缓存：</strong>避免重复计算</li>
                <li><strong>会话数据缓存：</strong>提高会话访问速度</li>
                <li><strong>配置数据缓存：</strong>减少配置读取开销</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
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
    
    return html.format(message=message, cache_table=cache_table)
