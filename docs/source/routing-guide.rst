路由系统指南
==============

Litefs 提供了一个现代、灵活的路由系统，支持多种路由定义方式和功能特性。

功能特性
--------

* 装饰器风格路由定义
* 方法链风格路由定义
* 路径参数支持（如 ``/user/{id}``）
* 多种 HTTP 方法支持（GET, POST, PUT, DELETE 等）
* 路由命名与反向解析
* 优先级路由匹配
* 安全防护（防止路径遍历攻击）

快速开始
--------

装饰器风格
^^^^^^^^^^

.. code-block:: python

   from litefs import Litefs
   from litefs.routing import get, post

   app = Litefs()

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

   app.register_routes(__name__)
   app.run()

方法链风格
^^^^^^^^^^

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

路由注册
^^^^^^^^

.. code-block:: python

   # 注册当前模块的路由
   app.register_routes(__name__)

   # 注册其他模块的路由
   import routes_module
   app.register_routes(routes_module)

   # 注册模块名称字符串
   app.register_routes('myapp.routes')

路径参数
----------

Litefs 支持路径参数，可以在路由路径中使用 ``{param}`` 语法：

.. code-block:: python

   @get('/user/{id}', name='user_detail')
   def user_detail_handler(request, id):
       return f'User ID: {id}'

   @get('/user/{id}/posts/{post_id}', name='user_post')
   def user_post_handler(request, id, post_id):
       return f'User ID: {id}, Post ID: {post_id}'

路径参数默认是字符串类型，需要在处理函数中进行类型转换：

.. code-block:: python

   @get('/user/{id}')
   def user_handler(request, id):
       user_id = int(id)  # 转换为整数
       # 处理逻辑...

HTTP 方法支持
--------------

Litefs 支持以下 HTTP 方法：

* GET
* POST
* PUT
* DELETE
* PATCH
* OPTIONS
* HEAD

.. code-block:: python

   from litefs.routing import get, post, put, delete, patch, options, head

   @get('/resource', name='get_resource')
   def get_resource_handler(request):
       return {'method': 'GET'}

   @post('/resource', name='create_resource')
   def create_resource_handler(request):
       return {'method': 'POST'}

   @put('/resource/{id}', name='update_resource')
   def update_resource_handler(request, id):
       return {'method': 'PUT', 'id': id}

   @delete('/resource/{id}', name='delete_resource')
   def delete_resource_handler(request, id):
       return {'method': 'DELETE', 'id': id}

路由命名与反向解析
--------------------

可以为路由指定名称，然后使用 ``url_for`` 方法生成 URL：

.. code-block:: python

   @get('/user/{id}', name='user_detail')
   def user_detail_handler(request, id):
       return f'User ID: {id}'

   # 反向解析 URL
   url = app.url_for('user_detail', id=123)  # 生成 '/user/123'

请求属性
----------

在路由处理函数中，``request`` 对象提供了以下属性：

* **request.params**：GET 参数（字典）
* **request.data**：POST 参数（字典）
* **request.files**：上传的文件（字典）
* **request.body**：原始请求体（字节）
* **request.environ**：WSGI 环境变量
* **request.request_method**：HTTP 方法
* **request.path**：请求路径
* **request.headers**：请求头
* **request.route_params**：路由路径参数

示例：

.. code-block:: python

   @get('/search', name='search')
   def search_handler(request):
       query = request.params.get('query', '')
       page = int(request.params.get('page', '1'))
       return {'query': query, 'page': page}

   @post('/form', name='form')
   def form_handler(request):
       name = request.data.get('name')
       email = request.data.get('email')
       return {'name': name, 'email': email}

路由匹配
----------

Litefs 路由系统使用正则表达式进行路径匹配，支持：

* 精确匹配（如 ``/hello``）
* 路径参数（如 ``/user/{id}``）
* 优先级排序（更具体的路由优先匹配）
* 加载顺序匹配（按照路由定义的顺序进行匹配）

路由冲突
^^^^^^^^

如果两个路由路径模式冲突，更具体的路由会优先匹配。例如：

* ``/user/{id}`` 会匹配 ``/user/123``
* ``/user/admin`` 会优先匹配精确路径

加载顺序限制
^^^^^^^^^^^^

**重要提示**：Litefs 路由系统是根据路由定义的加载顺序进行匹配的。在注册路由时，建议：

1. **先注册更具体的路由**，再注册更通用的路由
2. **避免路由路径重叠**，如果必须重叠，确保具体的路由先被注册
3. **注意模块导入顺序**，因为不同模块的路由注册顺序会影响匹配结果

例如，以下定义顺序是正确的：

.. code-block:: python

   # 先注册具体路由
   @get('/user/admin', name='admin_user')
   def admin_user_handler(request):
       return 'Admin User'

   # 再注册通用路由
   @get('/user/{id}', name='user_detail')
   def user_detail_handler(request, id):
       return f'User ID: {id}'

如果顺序颠倒，``/user/admin`` 会被 ``/user/{id}`` 匹配，因为它先被注册。

最佳实践
----------

路由组织
^^^^^^^^

* **模块化**：将路由按功能模块组织到不同文件中
* **命名规范**：使用清晰、一致的路由命名
* **路径设计**：使用 RESTful 风格的路径设计

示例：

.. code-block:: python

   # routes/users.py
   from litefs.routing import get, post, put, delete

   @get('/users', name='list_users')
   def list_users_handler(request):
       return {'users': []}

   @get('/users/{id}', name='get_user')
   def get_user_handler(request, id):
       return {'user_id': id}

   @post('/users', name='create_user')
   def create_user_handler(request):
       return {'status': 'created'}

   @put('/users/{id}', name='update_user')
   def update_user_handler(request, id):
       return {'user_id': id, 'status': 'updated'}

   @delete('/users/{id}', name='delete_user')
   def delete_user_handler(request, id):
       return {'user_id': id, 'status': 'deleted'}

性能优化
^^^^^^^^

* **路由顺序**：将常用路由放在前面
* **路径复杂度**：避免过于复杂的路径模式
* **缓存**：路由系统内部使用缓存提高匹配速度

错误处理
----------

.. code-block:: python

   from litefs.exceptions import RouteNotFound

   try:
       route_match = app.router.match(path, method)
   except RouteNotFound:
       # 处理路由未找到的情况
       pass

完整示例
----------

.. code-block:: python

   from litefs import Litefs
   from litefs.routing import get, post, put, delete

   app = Litefs(
       host='0.0.0.0',
       port=8080,
       debug=True
   )

   # 主页
   @get('/', name='index')
   def index_handler(request):
       return '''
       <!DOCTYPE html>
       <html>
       <head>
           <meta charset="utf-8">
           <title>Litefs 示例</title>
       </head>
       <body>
           <h1>Litefs 路由系统示例</h1>
           <p>这是一个演示路由系统功能的示例应用。</p>
       </body>
       </html>
       '''

   # 用户相关路由
   @get('/users', name='list_users')
   def list_users_handler(request):
       return {'users': [
           {'id': 1, 'name': 'Alice'},
           {'id': 2, 'name': 'Bob'},
           {'id': 3, 'name': 'Charlie'}
       ]}

   @get('/users/{id}', name='get_user')
   def get_user_handler(request, id):
       return {'user_id': id, 'name': f'User {id}'}

   @post('/users', name='create_user')
   def create_user_handler(request):
       name = request.data.get('name')
       return {'status': 'created', 'name': name}

   @put('/users/{id}', name='update_user')
   def update_user_handler(request, id):
       name = request.data.get('name')
       return {'user_id': id, 'name': name, 'status': 'updated'}

   @delete('/users/{id}', name='delete_user')
   def delete_user_handler(request, id):
       return {'user_id': id, 'status': 'deleted'}

   # 注册路由
   app.register_routes(__name__)

   # 运行应用
   if __name__ == '__main__':
       print('启动 Litefs 路由系统示例应用...')
       print('访问 http://localhost:8080 查看主页')
       app.run()

测试示例
----------

.. code-block:: python

   import requests

   # 测试 GET 路由
   response = requests.get('http://localhost:8080/')
   print(response.text)

   # 测试路径参数
   response = requests.get('http://localhost:8080/users/123')
   print(response.json())

   # 测试 POST 路由
   response = requests.post('http://localhost:8080/users', json={'name': 'Alice'})
   print(response.json())

   # 测试 PUT 路由
   response = requests.put('http://localhost:8080/users/123', json={'name': 'Bob'})
   print(response.json())

   # 测试 DELETE 路由
   response = requests.delete('http://localhost:8080/users/123')
   print(response.json())

常见问题
----------

Q: 路由冲突怎么办？

A: 如果两个路由路径模式冲突，更具体的路由会优先匹配。例如，``/user/admin`` 会优先于 ``/user/{id}`` 匹配。

Q: 如何处理路径参数类型？

A: 路径参数默认是字符串类型，需要在处理函数中进行类型转换。例如，``user_id = int(id)``。

Q: 路由注册失败怎么办？

A: 确保：
* 路由装饰器正确导入
* 路由处理函数正确定义
* ``register_routes`` 方法被调用
* 模块名称或对象正确传递

Q: 如何组织大型应用的路由？

A: 建议将路由按功能模块组织到不同文件中，然后使用 ``app.register_routes()`` 注册每个模块的路由。

相关文档
----------

* :doc:`static-files-guide` - 静态文件路由指南
* :doc:`middleware-guide` - 中间件指南
* :doc:`config-management` - 配置管理
* :doc:`wsgi-deployment` - WSGI 部署
