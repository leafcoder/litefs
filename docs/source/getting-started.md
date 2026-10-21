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
from litefs.core import Litefs
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

### 响应处理

Litefs 会根据返回值类型自动设置 `Content-Type` 响应头：

| 返回值类型 | Content-Type |
|-----------|--------------|
| `dict` / `list` / `tuple` | `application/json; charset=utf-8` |
| HTML 字符串（以 `<` 开头） | `text/html; charset=utf-8` |
| `bytes` | `application/octet-stream` |
| 其他类型 | `text/html; charset=utf-8`（默认） |

示例：

```python
@get('/api/user')
def get_user(request):
    # 自动设置 Content-Type: application/json
    return {'id': 1, 'name': 'Alice'}

@get('/page')
def get_page(request):
    # 自动设置 Content-Type: text/html
    return '<html><body>Hello</body></html>'

@get('/download')
def download(request):
    # 自动设置 Content-Type: application/octet-stream
    return b'\x00\x01\x02\x03'
```

也可以手动设置响应头：

```python
@get('/custom')
def custom_response(request):
    request.start_response(200, [('Content-Type', 'text/plain; charset=utf-8')])
    return 'Custom content type'
```

### 使用方法链风格

```python
from litefs.core import Litefs

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

### 示例目录

- `01-quickstart/` - 快速入门示例（路由、中间件、模板、静态文件）
- `02-rest-api/` - REST API 示例（JWT 认证、CRUD、OpenAPI 文档）
- `03-web-app/` - 博客系统示例（注册登录、OAuth2、文章评论、统计）
- `04-realtime/` - 实时通信示例（WebSocket、房间管理、消息广播）
- `05-production/` - 生产部署示例（多进程、日志、缓存、健康检查）
- `06-prometheus-monitoring/` - Prometheus 监控示例
- `07-database-migrations/` - 数据库迁移示例（Alembic）
- `08-mail-service/` - 邮件服务示例
- `09-i18n/` - 国际化示例

完整说明见 [examples/README.md](https://github.com/leafcoder/litefs/tree/main/examples)。

运行方式：

```bash
cd examples/01-quickstart
python app.py
```

## WSGI 部署

创建 `wsgi.py`：

```python
from litefs.core import Litefs

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
