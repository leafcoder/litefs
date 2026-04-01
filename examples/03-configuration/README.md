# 配置管理

Litefs 配置管理的各种方式示例，包括新的路由系统配置。

## 示例文件

- `configuration_example.py` - 配置管理示例主程序

## 配置方式

### 1. 默认配置

使用 Litefs 默认配置启动应用。

### 2. 代码配置

通过代码直接配置应用参数。

```python
app = Litefs(
    host='0.0.0.0',
    port=8080,
    webroot='./site',
    debug=True
)
```

### 3. YAML 配置文件

使用 YAML 文件配置应用。

```yaml
host: 0.0.0.0
port: 8080
webroot: ./site
debug: true
```

```python
app = Litefs(config_file='litefs.yaml')
```

### 4. JSON 配置文件

使用 JSON 文件配置应用。

```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "webroot": "./site",
  "debug": true
}
```

```python
app = Litefs(config_file='litefs.json')
```

### 5. TOML 配置文件

使用 TOML 文件配置应用。

```toml
host = "0.0.0.0"
port = 8080
webroot = "./site"
debug = true
```

```python
app = Litefs(config_file='litefs.toml')
```

### 6. 环境变量配置

通过环境变量配置应用。

```bash
export LITEFS_HOST=0.0.0.0
export LITEFS_PORT=8080
export LITEFS_DEBUG=true
```

### 7. 混合配置

结合配置文件、环境变量和代码配置。

## 运行示例

```bash
python configuration_example.py
```

## 配置优先级

代码配置 > 环境变量 > 配置文件 > 默认配置

## 配置项说明

- `host` - 监听地址（默认：127.0.0.1）
- `port` - 监听端口（默认：9090）
- `webroot` - Web 根目录（默认：./site）
- `debug` - 调试模式（默认：False）
- `max_request_size` - 最大请求大小（默认：10485760）
- `max_upload_size` - 最大上传大小（默认：52428800）
- `log` - 日志文件路径
- `workers` - 工作进程数（默认：1）
- `timeout` - 请求超时时间（默认：30）

## 新路由系统配置

### 1. 路由定义方式

Litefs 支持两种路由定义方式：

#### 装饰器风格

```python
from litefs.routing import get, post

@get('/hello')
def hello_handler(self):
    return 'Hello, World!'

@post('/submit')
def submit_handler(self):
    return 'Form submitted!'
```

#### 方法链风格

```python
app = Litefs()

@app.add_get('/hello')
def hello_handler(self):
    return 'Hello, World!'

@app.add_post('/submit')
def submit_handler(self):
    return 'Form submitted!'
```

### 2. 路由注册

使用 `register_routes` 方法注册路由：

```python
app = Litefs()

# 注册单个路由函数
app.register_routes(hello_handler)

# 注册模块中的所有路由
app.register_routes('myapp.routes')
```

### 3. 路径参数

支持路径参数：

```python
@get('/user/{id}')
def user_handler(self, id):
    return f'User ID: {id}'
```

### 4. HTTP 方法支持

支持多种 HTTP 方法：

- `get` - GET 方法
- `post` - POST 方法
- `put` - PUT 方法
- `delete` - DELETE 方法
- `patch` - PATCH 方法
- `options` - OPTIONS 方法
- `head` - HEAD 方法
