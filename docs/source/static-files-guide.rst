静态文件路由指南
==================

Litefs 提供了静态文件路由功能，可以轻松地提供静态资源（如 CSS、JavaScript、图片等）。

功能特性
--------

* 静态文件路由
* 自动 MIME 类型检测
* 安全防护（防止路径遍历攻击）
* 支持子路径访问
* 支持 HEAD 和 GET 方法
* 自动处理 404 和 403 错误

快速开始
--------

基本使用
^^^^^^^^

.. code-block:: python

   from litefs import Litefs

   app = Litefs()

   # 添加静态文件路由
   app.add_static('/static', './static', name='static')

   app.run()

访问静态文件：

* http://localhost:8080/static/css/style.css
* http://localhost:8080/static/js/app.js
* http://localhost:8080/static/images/logo.png

目录结构
^^^^^^^^

推荐的静态文件目录结构：

.. code-block:: text

   project/
   ├── app.py
   └── static/
       ├── css/           # CSS 样式文件
       ├── js/            # JavaScript 文件
       ├── images/        # 图片文件
       ├── fonts/         # 字体文件
       └── assets/        # 其他资源

完整示例
^^^^^^^^

.. code-block:: python

   from litefs import Litefs
   from litefs.routing import get

   app = Litefs(
       host='0.0.0.0',
       port=8080,
       debug=True
   )

   # 添加静态文件路由
   app.add_static('/static', './static', name='static')

   # 主页
   @get('/', name='index')
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
           <script src="/static/js/app.js"></script>
       </body>
       </html>
       '''

   app.run()

参数说明
----------

``add_static`` 方法接受以下参数：

* **prefix**：URL 前缀，如 ``/static``
* **directory**：静态文件目录路径，如 ``./static``
* **name**：路由名称（可选）

.. code-block:: python

   app.add_static('/static', './static', name='static')
   app.add_static('/uploads', './uploads', name='uploads')
   app.add_static('/media', './media', name='media')

安全特性
----------

防止路径遍历攻击
^^^^^^^^^^^^^^^^

静态文件路由会自动阻止路径遍历攻击，例如：

.. code-block:: text

   # 以下请求会被拒绝：
   http://localhost:8080/static/../../../etc/passwd
   http://localhost:8080/static/../secret.txt

文件类型检查
^^^^^^^^^^^^

静态文件路由会自动检测 MIME 类型，确保正确的 Content-Type 响应头：

* ``.css`` → ``text/css``
* ``.js`` → ``application/javascript``
* ``.png`` → ``image/png``
* ``.jpg`` → ``image/jpeg``
* ``.html`` → ``text/html``

错误处理
^^^^^^^^

* **404 Not Found**：文件不存在
* **403 Forbidden**：路径遍历攻击或目录访问

高级用法
----------

多个静态文件目录
^^^^^^^^^^^^^^^^

.. code-block:: python

   from litefs import Litefs

   app = Litefs()

   app.add_static('/static', './static', name='static')
   app.add_static('/uploads', './uploads', name='uploads')
   app.add_static('/media', './media', name='media')

   app.run()

子路径访问
^^^^^^^^^^

静态文件路由支持子路径访问：

.. code-block:: python

   app.add_static('/static', './static')

   # 可以访问：
   # /static/css/style.css
   # /static/js/app.js
   # /static/images/logo.png
   # /static/fonts/fontawesome.woff2
   # /static/assets/data.json

自定义错误处理
^^^^^^^^^^^^^^

如果需要自定义静态文件处理逻辑，可以定义自己的路由：

.. code-block:: python

   from litefs import Litefs
   from litefs.routing import get
   import os

   app = Litefs()

   @get('/custom/{file_path:path}', name='custom_static')
   def custom_static_handler(request, file_path):
       # 自定义静态文件处理逻辑
       # ...
       pass

   app.run()

最佳实践
----------

目录组织
^^^^^^^^

建议将静态文件按类型组织：

.. code-block:: text

   static/
   ├── css/           # CSS 样式文件
   │   ├── style.css
   │   └── theme.css
   ├── js/            # JavaScript 文件
   │   ├── app.js
   │   └── vendor.js
   ├── images/        # 图片文件
   │   ├── logo.png
   │   └── banner.jpg
   ├── fonts/         # 字体文件
   │   └── font.woff2
   └── assets/        # 其他资源
       └── data.json

缓存策略
^^^^^^^^

在生产环境中，建议使用 CDN 或反向代理（如 Nginx）来提供静态文件服务，以提高性能。

安全建议
^^^^^^^^

* 不要将敏感文件放在静态文件目录中
* 确保静态文件目录权限正确
* 使用版本控制管理静态文件
* 定期清理未使用的静态文件

性能优化
----------

使用 CDN
^^^^^^^^

对于大型应用，建议使用 CDN 来分发静态文件：

.. code-block:: html

   <!-- 使用 CDN -->
   <link rel="stylesheet" href="https://cdn.example.com/css/style.css">
   <script src="https://cdn.example.com/js/app.js"></script>

反向代理
^^^^^^^^

使用 Nginx 作为反向代理提供静态文件：

.. code-block:: nginx

   server {
       listen 80;
       server_name example.com;

       location /static/ {
           alias /path/to/static/;
           expires 30d;
           add_header Cache-Control "public, immutable";
       }

       location / {
           proxy_pass http://localhost:8080;
       }
   }

常见问题
----------

Q: 如何访问子目录中的文件？

A: 静态文件路由支持子路径访问，例如 ``/static/css/style.css`` 会访问 ``./static/css/style.css``。

Q: 如何处理文件不存在的情况？

A: 静态文件路由会自动返回 404 错误，如果需要自定义错误页面，可以定义自己的路由处理逻辑。

Q: 如何限制文件访问？

A: 确保静态文件目录权限正确，不要将敏感文件放在静态文件目录中。

Q: 如何支持文件上传？

A: 文件上传需要使用 POST 请求和 ``request.files`` 属性，静态文件路由只支持 GET 和 HEAD 方法。

Q: 如何处理大文件？

A: 对于大文件，建议使用专业的静态文件服务器或 CDN，Litefs 的静态文件路由适合中小型文件。

相关文档
----------

* :doc:`routing-guide` - 路由系统指南
* :doc:`middleware-guide` - 中间件指南
* :doc:`config-management` - 配置管理
* :doc:`wsgi-deployment` - WSGI 部署
