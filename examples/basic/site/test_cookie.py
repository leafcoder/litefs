def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    action = self.get.get('action', 'view')
    
    if action == 'set':
        name = self.get.get('name', 'test_cookie')
        value = self.get.get('value', 'test_value')
        max_age = int(self.get.get('max_age', 3600))
        path = self.get.get('path', '/')
        
        self.set_cookie(name, value, max_age=max_age, path=path)
        message = f"已设置 Cookie: {name} = {value}"
    
    elif action == 'delete':
        name = self.get.get('name', 'test_cookie')
        self.set_cookie(name, '', max_age=-1, path='/')
        message = f"已删除 Cookie: {name}"
    
    elif action == 'set_multiple':
        self.set_cookie('user_name', '张三', max_age=3600, path='/')
        self.set_cookie('user_age', '25', max_age=3600, path='/')
        self.set_cookie('user_role', 'admin', max_age=3600, path='/')
        self.set_cookie('theme', 'dark', max_age=86400, path='/')
        message = "已设置多个 Cookie"
    
    elif action == 'clear_all':
        for cookie_name in ['user_name', 'user_age', 'user_role', 'theme', 'test_cookie', 'visit_count']:
            self.set_cookie(cookie_name, '', max_age=-1, path='/')
        message = "已清除所有 Cookie"
    
    else:
        message = "Cookie 操作示例"
    
    import json
    cookies_dict = {}
    
    # 首先从 self.cookie 中读取客户端发送的 cookie
    for key, morsel in self.cookie.items():
        cookies_dict[key] = {
            'value': morsel.value,
            'expires': morsel.get('expires', ''),
            'max_age': morsel.get('max-age', ''),
            'path': morsel.get('path', ''),
            'domain': morsel.get('domain', ''),
            'secure': morsel.get('secure', False),
            'httponly': morsel.get('httponly', False)
        }
    
    # 然后添加刚刚设置的 cookie（如果有）
    if hasattr(self, '_cookies') and self._cookies:
        for name, cookie in self._cookies.items():
            for cookie_name, morsel in cookie.items():
                if cookie_name not in cookies_dict:
                    cookies_dict[cookie_name] = {
                        'value': morsel.value,
                        'expires': morsel.get('expires', ''),
                        'max_age': morsel.get('max-age', ''),
                        'path': morsel.get('path', ''),
                        'domain': morsel.get('domain', ''),
                        'secure': morsel.get('secure', False),
                        'httponly': morsel.get('httponly', False)
                    }
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Cookie 操作示例</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; }}
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
        <h1>Cookie 操作示例</h1>
        
        <div class="success">
            <strong>{message}</strong>
        </div>
        
        <div class="section">
            <h2>当前 Cookie 状态</h2>
            {cookies_table}
        </div>
        
        <div class="section">
            <h2>Cookie 操作</h2>
            
            <h3>设置单个 Cookie</h3>
            <div class="info">
                <a href="/test_cookie?action=set&name=test_cookie&value=test_value&max_age=3600">
                    <button>设置 test_cookie</button>
                </a>
                <a href="/test_cookie?action=set&name=user_pref&value=dark_mode&max_age=86400">
                    <button>设置 user_pref</button>
                </a>
            </div>
            
            <h3>设置多个 Cookie</h3>
            <div class="info">
                <a href="/test_cookie?action=set_multiple">
                    <button class="success">设置多个用户 Cookie</button>
                </a>
            </div>
            
            <h3>删除 Cookie</h3>
            <div class="warning">
                <a href="/test_cookie?action=delete&name=test_cookie">
                    <button class="danger">删除 test_cookie</button>
                </a>
                <a href="/test_cookie?action=delete&name=user_pref">
                    <button class="danger">删除 user_pref</button>
                </a>
            </div>
            
            <h3>清除所有 Cookie</h3>
            <div class="warning">
                <a href="/test_cookie?action=clear_all">
                    <button class="danger">清除所有 Cookie</button>
                </a>
            </div>
        </div>
        
        <div class="section">
            <h2>Cookie 原始数据</h2>
            <pre>{cookies_json}</pre>
        </div>
        
        <div class="section">
            <h2>Cookie 使用说明</h2>
            <ul>
                <li><strong>设置 Cookie：</strong>使用 <code>self.set_cookie(name, value, **options)</code></li>
                <li><strong>读取 Cookie：</strong>使用 <code>self.cookie</code> 属性获取所有 Cookie</li>
                <li><strong>删除 Cookie：</strong>设置 <code>max_age=-1</code> 来删除 Cookie</li>
                <li><strong>常用选项：</strong>max_age（过期时间秒数）、path（路径）、domain（域名）、secure（HTTPS）、httponly（仅 HTTP）</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    if cookies_dict:
        cookies_table = """
        <table>
            <thead>
                <tr>
                    <th>名称</th>
                    <th>值</th>
                    <th>过期时间</th>
                    <th>路径</th>
                    <th>安全</th>
                    <th>HTTP Only</th>
                </tr>
            </thead>
            <tbody>
        """
        for name, info in cookies_dict.items():
            cookies_table += f"""
                <tr>
                    <td>{name}</td>
                    <td>{info['value']}</td>
                    <td>{info['max_age'] or info['expires']}</td>
                    <td>{info['path']}</td>
                    <td>{info['secure']}</td>
                    <td>{info['httponly']}</td>
                </tr>
            """
        cookies_table += """
            </tbody>
        </table>
        """
    else:
        cookies_table = '<p class="warning">当前没有 Cookie</p>'
    
    cookies_json = json.dumps(cookies_dict, indent=2, ensure_ascii=False)
    
    return html.format(
        message=message,
        cookies_table=cookies_table,
        cookies_json=cookies_json
    )
