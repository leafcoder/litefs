#!/usr/bin/env python
# coding: utf-8

"""
静态文件路由示例

演示如何使用 Litefs 的静态文件路由功能
"""

from litefs import Litefs

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True
)

# 添加静态文件路由
app.add_static('/static', './static', name='static')

# 添加主页路由
@app.add_get('/', name='index')
def index_handler(request):
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Litefs 静态文件示例</title>
        <link rel="stylesheet" href="/static/css/style.css">
    </head>
    <body>
        <h1>Litefs 静态文件示例</h1>
        <p>这是一个演示静态文件路由功能的示例应用。</p>
        
        <h2>功能特性</h2>
        <ul>
            <li>静态文件路由</li>
            <li>自动 MIME 类型检测</li>
            <li>安全防护（防止路径遍历攻击）</li>
            <li>支持子路径访问</li>
        </ul>
        
        <h2>示例链接</h2>
        <ul>
            <li><a href="/static/css/style.css">CSS 文件</a></li>
            <li><a href="/static/js/app.js">JavaScript 文件</a></li>
            <li><a href="/static/images/logo.png">图片文件</a></li>
        </ul>
        
        <script src="/static/js/app.js"></script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print('启动 Litefs 静态文件示例应用...')
    print('访问 http://localhost:8080 查看主页')
    print('访问 http://localhost:8080/static/css/style.css 查看静态文件')
    app.run()
