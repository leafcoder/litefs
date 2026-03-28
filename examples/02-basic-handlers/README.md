# 基础处理器

Litefs 支持多种响应类型的处理器示例。

## 示例文件

- `basic_handlers_example.py` - 基础处理器示例主程序
- `site/` - 示例站点文件
  - `json.py` - JSON 响应
  - `json_complex.py` - 复杂 JSON 响应
  - `json_custom_header.py` - 自定义头的 JSON 响应
  - `json_error.py` - JSON 错误响应
  - `json_html.py` - JSON 和 HTML 混合响应
  - `html.py` - HTML 响应
  - `text.py` - 文本响应
  - `form.py` - 表单处理
  - `error.py` - 错误处理
  - `generator.py` - 生成器响应
  - `mixed.py` - 混合响应
  - `mixed_tuple.py` - 元组混合响应
  - `mixed_tuple_text.py` - 元组文本混合响应

## 运行示例

```bash
python basic_handlers_example.py
```

访问 http://localhost:8080 查看各个处理器示例。

## 处理器类型

### JSON 响应

```python
def handler(self):
    return {"message": "Hello, World!"}
```

### HTML 响应

```python
def handler(self):
    self.start_response(200, [('Content-Type', 'text/html')])
    return '<h1>Hello World</h1>'
```

### 文本响应

```python
def handler(self):
    self.start_response(200, [('Content-Type', 'text/plain')])
    return 'Hello World'
```

### 表单处理

```python
def handler(self):
    if self.method == 'POST':
        name = self.post.get('name', 'Guest')
        return f'Hello, {name}!'
    return '<form method="post"><input name="name"><button>Submit</button></form>'
```

### 错误处理

```python
def handler(self):
    self.start_response(404, [('Content-Type', 'application/json')])
    return {"error": "Not Found"}
```

### 生成器响应

```python
def handler(self):
    def generate():
        for i in range(10):
            yield f'Line {i}\n'
    return generate()
```
