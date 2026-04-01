# 静态文件路由示例

本示例演示了如何使用 Litefs 的静态文件路由功能。

## 功能特性

- ✅ 静态文件路由
- ✅ 自动 MIME 类型检测
- ✅ 安全防护（防止路径遍历攻击）
- ✅ 支持子路径访问
- ✅ 支持 HEAD 和 GET 方法

## 目录结构

```
15-static-files/
├── static_files_example.py  # 主程序
├── static/                  # 静态文件目录
│   ├── css/
│   │   └── style.css       # CSS 样式文件
│   ├── js/
│   │   └── app.js          # JavaScript 文件
│   └── images/
│       └── logo.png        # 图片文件（示例）
└── README.md               # 本文件
```

## 快速开始

### 1. 运行示例

```bash
python static_files_example.py
```

### 2. 访问应用

- **主页**：http://localhost:8080/
- **CSS 文件**：http://localhost:8080/static/css/style.css
- **JavaScript 文件**：http://localhost:8080/static/js/app.js
- **图片文件**：http://localhost:8080/static/images/logo.png

## 代码说明

### 添加静态文件路由

```python
from litefs import Litefs

app = Litefs()

# 添加静态文件路由
app.add_static('/static', './static', name='static')
```

**参数说明**：
- `prefix`：URL 前缀，如 `/static`
- `directory`：静态文件目录路径，如 `./static`
- `name`：路由名称（可选）

### 访问静态文件

静态文件路由支持子路径访问：

```python
# 添加静态文件路由
app.add_static('/static', './static')

# 可以访问：
# /static/css/style.css
# /static/js/app.js
# /static/images/logo.png
```

## 安全特性

### 1. 防止路径遍历攻击

静态文件路由会自动阻止路径遍历攻击，例如：

```python
# 以下请求会被拒绝：
# http://localhost:8080/static/../../../etc/passwd
# http://localhost:8080/static/../secret.txt
```

### 2. 文件类型检查

静态文件路由会自动检测 MIME 类型，确保正确的 Content-Type 响应头：

- `.css` → `text/css`
- `.js` → `application/javascript`
- `.png` → `image/png`
- `.jpg` → `image/jpeg`
- `.html` → `text/html`

### 3. 错误处理

- **404 Not Found**：文件不存在
- **403 Forbidden**：路径遍历攻击或目录访问

## 最佳实践

### 1. 目录组织

建议将静态文件按类型组织：

```
static/
├── css/           # CSS 样式文件
├── js/            # JavaScript 文件
├── images/        # 图片文件
├── fonts/         # 字体文件
└── assets/        # 其他资源
```

### 2. 缓存策略

在生产环境中，建议使用 CDN 或反向代理（如 Nginx）来提供静态文件服务，以提高性能。

### 3. 安全建议

- 不要将敏感文件放在静态文件目录中
- 确保静态文件目录权限正确
- 使用版本控制管理静态文件
- 定期清理未使用的静态文件

## 高级用法

### 多个静态文件目录

```python
app.add_static('/static', './static', name='static')
app.add_static('/uploads', './uploads', name='uploads')
app.add_static('/media', './media', name='media')
```

### 自定义错误处理

```python
@app.add_get('/static/{file_path:path}', name='static_custom')
def static_custom_handler(request, file_path):
    # 自定义静态文件处理逻辑
    # ...
    pass
```

## 注意事项

1. **路径参数**：静态文件路由使用 `{file_path:path}` 参数，支持多级路径
2. **性能**：对于大量静态文件，建议使用专业的静态文件服务器
3. **权限**：确保静态文件目录具有正确的读取权限
4. **大小限制**：Litefs 没有内置的文件大小限制，但建议限制大文件访问

## 总结

Litefs 的静态文件路由功能提供了一种简单、安全的方式来提供静态资源。通过使用 `add_static` 方法，可以轻松地将静态文件目录映射到 URL 路径，并享受自动 MIME 类型检测和安全防护等特性。

对于生产环境，建议结合 CDN 或反向代理使用，以获得更好的性能和可靠性。
