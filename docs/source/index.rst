.. Litefs documentation master file, created by
   sphinx-quickstart on Fri Mar 27 18:34:14 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Litefs 文档
===========

Litefs 是一个轻量级的 Python Web 框架，提供高性能的 HTTP 服务器、现代路由系统、WSGI 支持、中间件系统、缓存管理等功能。

.. toctree::
   :maxdepth: 2
   :caption: 快速开始:
   
   getting-started
   routing-guide
   static-files-guide
   configuration

.. toctree::
   :maxdepth: 2
   :caption: 核心功能:
   
   middleware-guide
   cache-system
   session-management
   auth-system
   websocket
   wsgi-deployment
   asgi-deployment

.. toctree::
   :maxdepth: 2
   :caption: 进阶指南:
   
   static-files-guide

.. toctree::
   :maxdepth: 2
   :caption: 测试文档:
   
   unit-tests
   performance-stress-tests

.. toctree::
   :maxdepth: 2
   :caption: API 文档:
   
   api

.. toctree::
   :maxdepth: 2
   :caption: 其他资源:
   
   improvement-analysis
   bug-fixes
   linux-server-guide
   development
   project-structure
   analysis-report

功能特性
--------

* 高性能 HTTP 服务器（支持 epoll 和 greenlet）
* 现代路由系统（装饰器风格、方法链风格）
* 静态文件路由（支持子路径、MIME 类型检测、安全防护）
* WSGI 1.0 兼容（PEP 3333）
* ASGI 3.0 兼容
* 支持 Gunicorn、uWSGI、Waitress 等 WSGI 服务器
* 支持 Uvicorn、Daphne、Hypercorn 等 ASGI 服务器
* Mako 模板引擎支持
* 会话管理（Memory、Redis、Database、Memcache 后端）
* 多级缓存系统（Memory + Tree cache + Redis）
* 中间件系统（日志、安全、CORS 等）
* 认证授权系统（JWT、角色权限管理）
* WebSocket 支持（实时通信、房间管理）
* 健康检查系统
* 文件监控和热重载
* Python 3.7+ 支持

快速开始
--------

安装
^^^^^^

.. code-block:: bash

   pip install litefs

或从源码安装：

.. code-block:: bash

   git clone https://github.com/leafcoder/litefs.git
   cd litefs
   pip install -r requirements.txt
   python setup.py install

基本使用
^^^^^^^^

使用现代路由系统：

.. code-block:: python

   from litefs import Litefs
   from litefs.routing import get, post

   app = Litefs(
       host='0.0.0.0',
       port=8080,
       debug=True
   )

   @get('/', name='index')
   def index_handler(request):
       return 'Hello, World!'

   @get('/user/{id}', name='user_detail')
   def user_detail_handler(request, id):
       return f'User ID: {id}'

   @post('/login', name='login')
   def login_handler(request):
       username = request.data.get('username')
       password = request.data.get('password')
       return {'status': 'success', 'username': username}

   app.run()

或使用方法链风格：

.. code-block:: python

   from litefs import Litefs

   app = Litefs()

   def index_handler(request):
       return 'Hello, World!'

   def user_detail_handler(request, id):
       return f'User ID: {id}'

   app.add_get('/', index_handler, name='index')
   app.add_get('/user/{id}', user_detail_handler, name='user_detail')

   app.run()

静态文件路由
^^^^^^^^^^^^^

.. code-block:: python

   from litefs import Litefs

   app = Litefs()

   app.add_static('/static', './static', name='static')

   app.run()

访问静态文件：

* http://localhost:8080/static/css/style.css
* http://localhost:8080/static/js/app.js
* http://localhost:8080/static/images/logo.png

详细的说明请参考 :doc:`routing-guide` 和 :doc:`static-files-guide`。

WSGI 部署
^^^^^^^^^^^

创建 ``wsgi.py``：

.. code-block:: python

   from litefs import Litefs
   from litefs.routing import get

   app = Litefs()

   @get('/', name='index')
   def index_handler(request):
       return 'Hello, World!'

   application = app.wsgi()

使用 Gunicorn 部署：

.. code-block:: bash

   gunicorn -w 4 -b :8000 wsgi:application

使用 uWSGI 部署：

.. code-block:: bash

   uwsgi --http :8000 --wsgi-file wsgi.py

使用 Waitress 部署（Windows）：

.. code-block:: bash

   waitress-serve --port=8000 wsgi:application

详细的部署说明请参考 :doc:`wsgi-deployment`。

索引和表格
============

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
