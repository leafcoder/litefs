def handler(self):
    self.start_response(200, [('Content-Type', 'text/html; charset=utf-8')])
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Litefs 快速入门</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .info { background: #e7f3ff; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .code { background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace; }
            .next { background: #d4edda; padding: 20px; border-radius: 5px; margin: 20px 0; }
            a { color: #007bff; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>🚀 Litefs 快速入门</h1>
        
        <div class="info">
            <h2>欢迎使用 Litefs!</h2>
            <p>Litefs 是一个轻量级、高性能的 Python Web 框架。</p>
        </div>
        
        <div class="code">
            <h3>最简单的示例代码：</h3>
            <pre>
import litefs

app = litefs.Litefs(
    host='0.0.0.0',
    port=8080,
    webroot='./site',
    debug=True
)

app.run()
            </pre>
        </div>
        
        <div class="next">
            <h3>下一步：</h3>
            <ul>
                <li><a href="/hello">查看 Hello World 示例</a></li>
                <li><a href="/json">查看 JSON 响应示例</a></li>
                <li><a href="/info">查看请求信息</a></li>
            </ul>
        </div>
        
        <div class="info">
            <h3>特性：</h3>
            <ul>
                <li>✅ 轻量级，零依赖</li>
                <li>✅ 高性能，支持并发</li>
                <li>✅ 易于使用，快速上手</li>
                <li>✅ 支持中间件、会话、缓存</li>
                <li>✅ 完整的 WSGI 支持</li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    return html
