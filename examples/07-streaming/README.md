# 流式响应示例

本示例展示了 Litefs 框架的流式响应功能，包括：

1. **文本流** - 动态生成文本数据，模拟实时数据推送
2. **文件流** - 流式返回大文件，避免一次性加载到内存
3. **进度流** - 使用 Server-Sent Events 实时返回任务进度

## 运行示例

### 方法一：直接运行

```bash
python app.py
```

### 方法二：使用 WSGI 服务器

```bash
# 使用 gunicorn
gunicorn wsgi:application -w 4 -b :8000

# 使用 uWSGI
uwsgi --http :8000 --wsgi-file wsgi.py
```

## 访问端点

- **文本流**: http://localhost:9090/stream/text
- **文件流**: http://localhost:9090/stream/file
- **进度流**: http://localhost:9090/stream/progress

## 技术说明

### 1. 文本流

使用 `Response.stream()` 方法返回一个生成器，该生成器会逐行生成文本数据：

```python
def stream_text(request):
    def generate_text():
        for i in range(10):
            yield f"Line {i+1}\n"
            time.sleep(0.5)  # 模拟延迟
    return Response.stream(generate_text())
```

### 2. 文件流

使用简化的 `Response.file_stream()` 方法，自动处理文件的流式传输：

```python
def stream_file(request):
    file_path = 'test_large_file.txt'
    # 自动处理文件存在检查、MIME 类型检测和流式传输
    return Response.file_stream(file_path)
```

### 3. 进度流

使用简化的 `Response.sse()` 方法，自动设置 Server-Sent Events 所需的响应头：

```python
def stream_progress(request):
    def generate_progress():
        total = 100
        for i in range(total + 1):
            progress = i / total * 100
            yield f"data: {{\"progress\": {progress:.1f}}}\n\n"
            time.sleep(0.1)
    # 自动设置 SSE 响应头
    return Response.sse(generate_progress())
```

## 注意事项

- 流式响应会使用 `Transfer-Encoding: chunked` 编码，适用于不确定长度的响应
- 文件流会自动处理大文件，避免一次性加载到内存
- Server-Sent Events 适用于实时数据推送场景，如进度条、实时通知等
