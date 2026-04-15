# 快速开始

## 安装

```bash
pip install litefs
```

或从源码安装：

```bash
git clone https://github.com/leafcoder/litefs.git
cd litefs
pip install -r requirements.txt
python setup.py install
```

## 基本示例

### 使用装饰器风格

```python
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

app.register_routes(__name__)
app.run()
```

### 使用方法链风格

```python
from litefs import Litefs

app = Litefs()

def index_handler(request):
    return 'Hello, World!'

def user_detail_handler(request, id):
    return f'User ID: {id}'

app.add_get('/', index_handler, name='index')
app.add_get('/user/{id}', user_detail_handler, name='user_detail')

app.run()
```

## 推荐示例

Litefs 提供了丰富的示例代码，位于 [examples/](https://github.com/leafcoder/litefs/tree/main/examples) 目录：

### 经典示例目录

- `01-hello-world/` - 快速入门示例
- `02-routing/` - 路由系统示例
- `03-blog/` - 博客应用示例
- `04-api-service/` - API 服务示例
- `05-fullstack/` - 完整应用示例
- `06-sqlalchemy/` - SQLAlchemy 集成示例
- `07-streaming/` - 流式响应示例
- `08-comprehensive/` - **综合示例**（推荐新手）

运行方式：

```bash
cd examples/01-hello-world
python app.py
```

### 独立示例文件

- `asgi_example.py` - ASGI 示例

## WSGI 部署

创建 `wsgi.py`：

```python
from litefs import Litefs

app = Litefs()

@get('/', name='index')
def index_handler(request):
    return 'Hello, World!'

application = app.wsgi()
```

使用 Gunicorn：

```bash
gunicorn -w 4 -b :8000 wsgi:application
```

## 下一步

- [路由系统](routing-guide) - 学习路由定义
- [中间件](middleware-guide) - 使用中间件
- [配置管理](configuration) - 配置应用
- [WSGI 部署](wsgi-deployment) - 生产部署
