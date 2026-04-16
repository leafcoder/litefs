# FastAPI 示例

用于与 Litefs ASGI 性能对比的 FastAPI 实现示例。

## 运行示例

```bash
python app.py
```

## 可用端点

- `GET /` - 首页
- `GET /async` - 异步处理示例
- `GET /user/{id}` - 路径参数示例
- `GET /query?name=...&age=...` - 查询参数示例

服务器运行在 `http://127.0.0.1:8001`
