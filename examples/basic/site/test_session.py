def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    action = self.get.get('action', 'view')
    message = ''
    
    if action == 'set':
        key = self.get.get('key', 'username')
        value = self.get.get('value', 'guest')
        self.session[key] = value
        message = f"已设置 Session: {key} = {value}"
    
    elif action == 'delete':
        key = self.get.get('key', 'username')
        if key in self.session:
            del self.session[key]
            message = f"已删除 Session: {key}"
        else:
            message = f"Session 中不存在: {key}"
    
    elif action == 'clear':
        self.session.clear()
        message = "已清除所有 Session 数据"
    
    elif action == 'set_user':
        self.session['username'] = '张三'
        self.session['user_id'] = '1001'
        self.session['role'] = 'admin'
        self.session['login_time'] = '2024-01-01 12:00:00'
        message = "已设置用户 Session 信息"
    
    elif action == 'set_cart':
        self.session['cart_items'] = [
            {'id': 1, 'name': '商品A', 'price': 99.99, 'quantity': 2},
            {'id': 2, 'name': '商品B', 'price': 199.99, 'quantity': 1}
        ]
        self.session['cart_total'] = 399.97
        message = "已设置购物车 Session"
    
    elif action == 'set_pref':
        self.session['theme'] = 'dark'
        self.session['language'] = 'zh-CN'
        self.session['timezone'] = 'Asia/Shanghai'
        message = "已设置用户偏好 Session"
    
    elif action == 'increment':
        count_key = self.get.get('key', 'visit_count')
        current_count = self.session.get(count_key, 0)
        self.session[count_key] = current_count + 1
        message = f"{count_key}: {current_count} -> {current_count + 1}"
    
    import json
    import time
    from datetime import datetime
    
    session_data = dict(self.session)
    session_id = self.session.id if hasattr(self.session, 'id') else 'N/A'
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Session 管理示例</title>
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
            .session-id {{ background: #f8f9fa; padding: 15px; border-radius: 5px; font-family: monospace; }}
        </style>
    </head>
    <body>
        <h1>Session 管理示例</h1>
        
        <div class="success">
            <strong>{message}</strong>
        </div>
        
        <div class="section">
            <h2>Session 信息</h2>
            <div class="session-id">
                <strong>Session ID:</strong> {session_id}
            </div>
        </div>
        
        <div class="section">
            <h2>当前 Session 数据</h2>
            {session_table}
        </div>
        
        <div class="section">
            <h2>Session 操作</h2>
            
            <h3>基本操作</h3>
            <div class="info">
                <a href="/test_session?action=set&key=username&value=张三">
                    <button>设置 username</button>
                </a>
                <a href="/test_session?action=set&key=email&value=test@example.com">
                    <button>设置 email</button>
                </a>
                <a href="/test_session?action=delete&key=username">
                    <button class="danger">删除 username</button>
                </a>
                <a href="/test_session?action=clear">
                    <button class="danger">清除所有 Session</button>
                </a>
            </div>
            
            <h3>计数器示例</h3>
            <div class="info">
                <a href="/test_session?action=increment&key=visit_count">
                    <button>访问计数 +1</button>
                </a>
                <a href="/test_session?action=increment&key=click_count">
                    <button>点击计数 +1</button>
                </a>
            </div>
            
            <h3>预设场景</h3>
            <div class="info">
                <a href="/test_session?action=set_user">
                    <button class="success">设置用户登录信息</button>
                </a>
                <a href="/test_session?action=set_cart">
                    <button class="success">设置购物车数据</button>
                </a>
                <a href="/test_session?action=set_pref">
                    <button class="success">设置用户偏好</button>
                </a>
            </div>
        </div>
        
        <div class="section">
            <h2>Session 原始数据</h2>
            <pre>{session_json}</pre>
        </div>
        
        <div class="section">
            <h2>Session 使用说明</h2>
            <ul>
                <li><strong>设置 Session：</strong>使用 <code>self.session[key] = value</code></li>
                <li><strong>读取 Session：</strong>使用 <code>self.session[key]</code> 或 <code>self.session.get(key, default)</code></li>
                <li><strong>删除 Session：</strong>使用 <code>del self.session[key]</code></li>
                <li><strong>清除 Session：</strong>使用 <code>self.session.clear()</code></li>
                <li><strong>Session ID：</strong>使用 <code>self.session.id</code> 获取唯一标识</li>
                <li><strong>遍历 Session：</strong>Session 继承自 UserDict，支持字典操作</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>Session 应用场景</h2>
            <ul>
                <li><strong>用户登录状态：</strong>存储用户 ID、角色、登录时间等</li>
                <li><strong>购物车：</strong>存储购物车商品、数量、总价等</li>
                <li><strong>用户偏好：</strong>存储主题、语言、时区等个性化设置</li>
                <li><strong>访问计数：</strong>记录页面访问次数、用户行为统计</li>
                <li><strong>临时数据：</strong>表单数据、分页状态、筛选条件等</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    if session_data:
        session_table = """
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
        for key, value in session_data.items():
            value_type = type(value).__name__
            if value_type == 'str':
                display_value = value[:100] + '...' if len(value) > 100 else value
            elif value_type == 'list':
                display_value = f"[{len(value)} items]"
            elif value_type == 'dict':
                display_value = f"{{{len(value)} keys}}"
            else:
                display_value = str(value)
            
            session_table += f"""
                <tr>
                    <td><code>{key}</code></td>
                    <td>{display_value}</td>
                    <td>{value_type}</td>
                </tr>
            """
        session_table += """
            </tbody>
        </table>
        """
    else:
        session_table = '<p class="warning">当前 Session 为空</p>'
    
    session_json = json.dumps(session_data, indent=2, ensure_ascii=False, default=str)
    
    return html.format(
        message=message,
        session_id=session_id,
        session_table=session_table,
        session_json=session_json
    )
