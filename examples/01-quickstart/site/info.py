def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>请求信息</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
            a {{ color: #007bff; }}
        </style>
    </head>
    <body>
        <h1>请求信息</h1>
        <p><a href="/">返回首页</a></p>
        
        <h2>基本信息</h2>
        <table>
            <tr><th>方法</th><td>{self.method}</td></tr>
            <tr><th>路径</th><td>{self.path_info}</td></tr>
            <tr><th>查询字符串</th><td>{self.query_string or '无'}</td></tr>
            <tr><th>协议</th><td>{self.environ.get('SERVER_PROTOCOL', 'HTTP/1.1')}</td></tr>
        </table>
        
        <h2>请求头</h2>
        <table>
    """
    
    for key, value in self.environ.items():
        if key.startswith('HTTP_'):
            header_name = key[5:].replace('_', '-').title()
            html += f"<tr><th>{header_name}</th><td>{value}</td></tr>"
    
    html += """
        </table>
        
        <h2>GET 参数</h2>
        <table>
    """
    
    if self.get:
        for key, value in self.get.items():
            html += f"<tr><th>{key}</th><td>{value}</td></tr>"
    else:
        html += "<tr><td colspan='2'>无 GET 参数</td></tr>"
    
    html += """
        </table>
        
        <h2>POST 参数</h2>
        <table>
    """
    
    if self.post:
        for key, value in self.post.items():
            html += f"<tr><th>{key}</th><td>{value}</td></tr>"
    else:
        html += "<tr><td colspan='2'>无 POST 参数</td></tr>"
    
    html += """
        </table>
    </body>
    </html>
    """
    
    return html
