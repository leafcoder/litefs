def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>表单处理示例</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .section {{ margin: 30px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            .info {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }}
            input, textarea, select {{ padding: 8px; margin: 5px 0; width: 100%; max-width: 300px; }}
            button {{ padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            pre {{ background: #f5f5f5; padding: 10px; overflow-x: auto; }}
        </style>
    </head>
    <body>
        <h1>表单处理示例</h1>
        
        <div class="section">
            <h2>GET 参数示例</h2>
            <form method="GET" action="/test_form">
                <input type="text" name="username" placeholder="用户名" required>
                <input type="email" name="email" placeholder="邮箱">
                <button type="submit">提交 GET 请求</button>
            </form>
            <div class="info">
                <strong>当前 GET 参数：</strong><br>
                <pre>{get_params}</pre>
            </div>
        </div>
        
        <div class="section">
            <h2>POST 表单示例</h2>
            <form method="POST" action="/test_form">
                <input type="text" name="name" placeholder="姓名" required>
                <input type="number" name="age" placeholder="年龄">
                <select name="gender">
                    <option value="">选择性别</option>
                    <option value="male">男</option>
                    <option value="female">女</option>
                </select>
                <textarea name="message" placeholder="留言内容" rows="3"></textarea>
                <button type="submit">提交 POST 请求</button>
            </form>
            <div class="info">
                <strong>当前 POST 参数：</strong><br>
                <pre>{post_params}</pre>
            </div>
        </div>
        
        <div class="section">
            <h2>文件上传示例</h2>
            <form method="POST" action="/test_form" enctype="multipart/form-data">
                <input type="file" name="file1" multiple>
                <input type="text" name="description" placeholder="文件描述">
                <button type="submit">上传文件</button>
            </form>
            <div class="info">
                <strong>上传的文件：</strong><br>
                <pre>{files_info}</pre>
            </div>
        </div>
        
        <div class="section">
            <h2>原始请求体示例</h2>
            <div class="info">
                <strong>请求体内容：</strong><br>
                <pre>{body_info}</pre>
            </div>
        </div>
    </body>
    </html>
    """
    
    import json
    get_params = json.dumps(dict(self.get), indent=2, ensure_ascii=False)
    post_params = json.dumps(dict(self.post), indent=2, ensure_ascii=False)
    
    files_info = "无上传文件"
    if self.files:
        files_dict = {}
        for key, fp in self.files.items():
            fp.seek(0)
            content = fp.read()
            fp.seek(0)
            files_dict[key] = {
                "size": len(content),
                "type": type(fp).__name__,
                "description": self.post.get('description', 'N/A')
            }
        files_info = json.dumps(files_dict, indent=2, ensure_ascii=False)
    
    body_info = "无请求体内容"
    if self.body:
        try:
            body_str = self.body.decode('utf-8', errors='replace')
            body_info = body_str[:500] + "..." if len(body_str) > 500 else body_str
        except:
            body_info = f"二进制数据，长度: {len(self.body)} 字节"
    
    return html.format(
        get_params=get_params,
        post_params=post_params,
        files_info=files_info,
        body_info=body_info
    )
