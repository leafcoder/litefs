.. Litefs documentation master file, created by
   sphinx-quickstart on Fri Mar 27 18:34:14 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Litefs documentation
====================

Litefs 是一个轻量级的 Python Web 框架，提供高性能的 HTTP 服务器、WSGI 支持、中间件系统、缓存管理等功能。

.. toctree::
   :maxdepth: 2
   :caption: 文档:
   
   api
   config-management
   health-check
   middleware-guide
   wsgi-deployment
   wsgi-implementation
   unit-tests
   performance-stress-tests
   improvement-analysis
   bug-fixes
   linux-server-guide
   development
   project-structure
   todo

功能特性
--------

* 高性能 HTTP 服务器（支持 epoll 和 greenlet）
* WSGI 1.0 兼容（PEP 3333）
* 支持 Gunicorn、uWSGI、Waitress 等 WSGI 服务器
* 静态文件服务（支持 gzip/deflate 压缩）
* Mako 模板引擎支持
* CGI 脚本执行（.pl、.py、.php）
* 会话管理
* 多级缓存系统（Memory + Tree cache）
* 文件监控和热重载
* Python 2.6-3.14 支持

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

独立服务器：

.. code-block:: python

   import litefs
   litefs.test_server()

或从命令行：

.. code-block:: bash

   litefs --host localhost --port 9090 --webroot ./site

WSGI 部署
^^^^^^^^^^^

创建 ``wsgi_example.py``：

.. code-block:: python

   import litefs
   app = litefs.Litefs(webroot='./site')
   application = app.wsgi()

使用 Gunicorn 部署：

.. code-block:: bash

   gunicorn -w 4 -b :8000 wsgi_example:application

使用 uWSGI 部署：

.. code-block:: bash

   uwsgi --http :8000 --wsgi-file wsgi_example.py

使用 Waitress 部署（Windows）：

.. code-block:: bash

   waitress-serve --port=8000 wsgi_example:application

详细的部署说明请参考 :doc:`wsgi-deployment`。

索引和表格
============

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

