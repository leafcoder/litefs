# Linux 系统开发服务器使用指南

## 问题解决

### 问题：`No module named litefs.__main__`

**原因**：缺少 `__main__.py` 文件，导致 `python -m litefs` 命令无法工作。

**解决方案**：已创建 `src/litefs/__main__.py` 文件。

## 使用方法

### 方法 1：使用 Makefile（推荐）

```bash
# 确保在项目根目录
cd /path/to/litefs

# 启动开发服务器
make dev-serve

# 或者使用普通模式
make serve
```

### 方法 2：直接使用 Python

```bash
# 设置 PYTHONPATH
export PYTHONPATH=/path/to/litefs/src

# 启动开发服务器
python -m litefs --host localhost --port 9090 --webroot examples/basic/site --debug
```

### 方法 3：开发模式安装

```bash
# 安装到当前环境
pip install -e .

# 然后可以直接使用
litefs --host localhost --port 9090 --webroot examples/basic/site --debug
```

## 服务器配置选项

```bash
python -m litefs --help
```

可用选项：
- `-H, --host HOST`：绑定服务器到指定主机（默认：localhost）
- `-P, --port PORT`：绑定服务器到指定端口（默认：9090）
- `--webroot WEBROOT`：使用指定目录作为 Web 根目录（默认：./site）
- `--debug`：以调试模式启动服务器
- `--not-found NOT_FOUND`：使用指定文件作为 404 页面
- `--default-page DEFAULT_PAGE`：使用指定文件作为默认页面（默认：index.html）
- `--cgi-dir CGI_DIR`：使用指定目录作为 CGI 脚本目录
- `--log LOG`：将日志保存到指定文件
- `--listen LISTEN`：服务器监听队列大小
- `--max-request-size MAX_REQUEST_SIZE`：最大请求体大小（字节，默认：10MB）
- `--max-upload-size MAX_UPLOAD_SIZE`：最大文件上传大小（字节，默认：50MB）

## WSGI 服务器

### 使用 Gunicorn

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务器
gunicorn -w 4 -b localhost:9090 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  examples.wsgi.wsgi_example:application
```

### 使用 uWSGI

```bash
# 安装 uWSGI
pip install uwsgi

# 启动服务器
uwsgi --http localhost:9090 \
  --wsgi-file examples/wsgi/wsgi_example.py \
  --master \
  --processes 4 \
  --enable-threads \
  --threads 2
```

### 使用 Waitress

```bash
# 安装 Waitress
pip install waitress

# 启动服务器
waitress-serve --port=9090 \
  --threads=4 \
  examples.wsgi.wsgi_example:application
```

## 注意事项

### Linux 特定问题

1. **权限问题**：确保对 `webroot` 目录有读取权限
2. **端口占用**：确保指定端口未被占用
3. **防火墙**：如果需要外部访问，确保防火墙允许相应端口

### 文件监控

Litefs 使用 `watchdog` 库进行文件监控，支持：
- 自动重新加载修改的文件
- 实时更新缓存

### 调试模式

调试模式提供：
- 详细的日志输出
- 错误堆栈跟踪
- 开发友好的错误页面

## 故障排除

### 模块找不到

```bash
# 检查 PYTHONPATH
echo $PYTHONPATH

# 手动设置
export PYTHONPATH=/path/to/litefs/src:$PYTHONPATH
```

### 端口被占用

```bash
# 查找占用端口的进程
lsof -i :9090

# 或使用 netstat
netstat -tulpn | grep :9090

# 终止进程
kill -9 <PID>
```

### 权限问题

```bash
# 检查目录权限
ls -la examples/basic/site

# 修改权限
chmod -R 755 examples/basic/site
```

## 性能优化

### 生产环境建议

1. 使用 WSGI 服务器（Gunicorn/uWSGI）而不是开发服务器
2. 配置适当的工作进程数（通常为 CPU 核心数的 2-4 倍）
3. 启用日志轮转
4. 使用反向代理（Nginx）
5. 启用 gzip 压缩

### 开发环境建议

1. 使用调试模式
2. 启用文件监控
3. 使用较小的监听队列
4. 详细的日志输出

## 参考资源

- [Litefs 主文档](../README.md)
- [开发指南](../DEVELOPMENT.md)
- [项目结构](../PROJECT_STRUCTURE.md)
