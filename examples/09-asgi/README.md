# ASGI 示例

展示如何使用 Litefs 的 ASGI 功能，包括：

1. 基本路由
2. 异步处理函数
3. JSON 响应
4. 路径参数
5. 查询参数

## 运行示例

```bash
python app.py
```

## 可用端点

- `GET /` - 首页
- `GET /async` - 异步处理示例
- `GET /user/{id}` - 路径参数示例
- `GET /query?name=...&age=...` - 查询参数示例
- `POST /api/data` - POST 请求示例
- `GET /stream` - 流式响应示例

服务器运行在 `http://127.0.0.1:8000`
