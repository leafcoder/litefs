# Litefs Full Stack Example

一个完整的 Litefs Web 应用示例，展示了 Litefs 的核心功能和最佳实践。

## 功能特性

- **路由处理**：基本的页面路由和处理
- **表单处理**：联系表单提交和验证
- **会话管理**：用户会话和访问历史记录
- **缓存使用**：内存缓存示例
- **中间件集成**：日志、安全、CORS、限流中间件
- **静态文件服务**：CSS 样式和静态资源
- **健康检查**：应用健康状态和就绪检查
- **响应式设计**：适配不同屏幕尺寸

## 目录结构

```
fullstack_example/
├── app.py          # 应用主文件
├── wsgi.py         # WSGI 应用文件
├── site/           # Web 根目录
│   ├── index.py    # 首页
│   ├── about.py    # 关于页面
│   ├── contact.py  # 联系页面
│   ├── dashboard.py # 仪表板页面
│   └── static/     # 静态文件
│       └── css/
│           └── style.css # 样式文件
└── README.md       # 说明文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r ../../requirements.txt
```

### 2. 运行开发服务器

```bash
python app.py
```

应用将在 `http://localhost:8080` 启动。

### 3. 部署到生产环境

使用 Gunicorn：

```bash
pip install gunicorn gevent
gunicorn -w 4 -k gevent -b :8000 wsgi:application
```

使用 uWSGI：

```bash
pip install uwsgi
uwsgi --http :8000 --wsgi-file wsgi.py --processes 4 --threads 2 --master
```

使用 Waitress（Windows 推荐）：

```bash
pip install waitress
waitress-serve --port=8000 wsgi:application
```

## 访问端点

- **首页**：`http://localhost:8080/`
- **关于页面**：`http://localhost:8080/about`
- **联系页面**：`http://localhost:8080/contact`
- **仪表板**：`http://localhost:8080/dashboard`
- **健康检查**：`http://localhost:8080/health`
- **就绪检查**：`http://localhost:8080/health/ready`

## 技术栈

- **后端**：Litefs Web 框架
- **前端**：HTML5, CSS3
- **部署**：支持 Gunicorn、uWSGI、Waitress

## 最佳实践

1. **代码组织**：使用类封装应用逻辑
2. **中间件配置**：合理使用中间件增强应用功能
3. **会话管理**：利用会话存储用户状态
4. **表单处理**：验证用户输入
5. **健康检查**：监控应用状态
6. **静态文件**：合理组织静态资源
7. **部署配置**：使用 WSGI 服务器提高性能

## 扩展建议

- 添加数据库集成
- 实现用户认证系统
- 添加 API 端点
- 集成模板引擎
- 实现文件上传功能
- 添加更多中间件

## 注意事项

- 本示例仅用于演示目的，生产环境中需要添加更多安全措施
- 实际应用中应使用真实的邮件发送服务
- 建议使用 HTTPS 保护生产环境
