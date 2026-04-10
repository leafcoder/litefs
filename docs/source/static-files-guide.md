# 静态文件路由

## 功能特性

* 静态文件路由
* 自动 MIME 类型检测
* 安全防护（防止路径遍历攻击）
* 支持子路径访问
* 支持 HEAD 和 GET 方法
* 自动处理 404 和 403 错误

## 快速开始

```python
from litefs import Litefs

app = Litefs()

# 添加静态文件路由
app.add_static('/static', './static', name='static')

app.run()
```

## 目录结构

推荐的静态文件目录结构：

```
project/
├── app.py
└── static/
    ├── css/           # CSS 样式文件
    ├── js/            # JavaScript 文件
    ├── images/        # 图片文件
    ├── fonts/         # 字体文件
    └── assets/        # 其他资源
```

## 安全特性

* **防止路径遍历攻击**：自动阻止 ``../../../etc/passwd`` 等恶意请求
* **文件类型检查**：自动检测 MIME 类型
* **错误处理**：自动返回 404 和 403 错误

## 高级用法

### 多个静态文件目录

```python
app.add_static('/static', './static', name='static')
app.add_static('/uploads', './uploads', name='uploads')
app.add_static('/media', './media', name='media')
```

### 子路径访问

```
/static/css/style.css
/static/js/app.js
/static/images/logo.png
```

## 最佳实践

* **目录组织**：按类型组织静态文件
* **缓存策略**：使用 CDN 或反向代理
* **安全建议**：不要将敏感文件放在静态文件目录中

## 性能优化

### 使用 CDN

```html
<link rel="stylesheet" href="https://cdn.example.com/css/style.css">
<script src="https://cdn.example.com/js/app.js"></script>
```

### 反向代理

```nginx
location /static/ {
    alias /path/to/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## 相关文档

* :doc:`routing-guide` - 路由系统指南
* :doc:`middleware-guide` - 中间件指南
* :doc:`configuration` - 配置管理
* :doc:`wsgi-deployment` - WSGI 部署
