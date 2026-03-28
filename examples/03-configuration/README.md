# 配置管理

Litefs 配置管理的各种方式示例。

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
