# Litefs 示例

本目录包含 Litefs Web 框架的各种示例，帮助您快速上手和深入学习。

## 目录结构

```
examples/
├── 01-quickstart/              # 快速入门
├── 02-basic-handlers/          # 基础处理器
├── 03-configuration/          # 配置管理
├── 04-middleware/             # 中间件
├── 05-session/                # 会话管理
├── 06-cache/                  # 缓存
├── 07-health-check/           # 健康检查
├── 08-wsgi-deployment/        # WSGI 部署
├── 09-fullstack/              # 完整应用
├── 10-cache-backends-web/     # 缓存后端 Web 管理界面
└── common/                    # 公共资源
    ├── config/                # 配置文件
    └── static/                # 静态资源
```

## 学习路径

### 1. 快速入门

从 [01-quickstart](./01-quickstart/) 开始，了解 Litefs 的基本用法。

```bash
cd 01-quickstart
python quickstart.py
```

### 2. 基础处理器

学习 [02-basic-handlers](./02-basic-handlers/)，掌握各种响应类型的处理器。

### 3. 配置管理

了解 [03-configuration](./03-configuration/)，学习如何配置 Litefs 应用。

### 4. 中间件

探索 [04-middleware](./04-middleware/)，使用中间件增强应用功能。

### 5. 会话管理

学习 [05-session](./05-session/)，管理用户会话状态。

### 6. 缓存

了解 [06-cache](./06-cache/)，使用缓存提高应用性能。

### 7. 健康检查

学习 [07-health-check](./07-health-check/)，实现应用健康监控。

### 8. WSGI 部署

掌握 [08-wsgi-deployment](./08-wsgi-deployment/)，将应用部署到生产环境。

### 9. 完整应用

参考 [09-fullstack](./09-fullstack/)，构建完整的 Web 应用。

### 10. 缓存后端 Web 管理界面

使用 [10-cache-backends-web](./10-cache-backends-web/)，通过 Web 界面管理各种缓存后端。

## 示例说明

### 01-quickstart

最简单的 Litefs 应用示例，包含：
- 基本应用启动
- HTML 响应
- JSON 响应
- 请求信息展示

### 02-basic-handlers

各种响应类型的处理器示例：
- JSON 响应
- HTML 响应
- 文本响应
- 表单处理
- 错误处理
- 生成器响应
- 混合响应

### 03-configuration

配置管理的各种方式：
- 默认配置
- 代码配置
- YAML 配置文件
- JSON 配置文件
- TOML 配置文件
- 环境变量配置
- 混合配置

### 04-middleware

中间件使用示例：
- 日志中间件
- 安全中间件
- CORS 中间件
- 限流中间件
- 健康检查中间件
- 自定义中间件

### 05-session

会话管理示例：
- 设置会话
- 获取会话
- 删除会话
- 清除会话
- 会话应用场景

### 06-cache

缓存管理示例：
- MemoryCache
- TreeCache
- RedisCache
- 缓存操作
- 缓存应用场景

### 07-health-check

健康检查示例：
- 数据库检查
- 缓存检查
- 磁盘空间检查
- 外部 API 检查
- 消息队列检查

### 08-wsgi-deployment

WSGI 部署示例：
- Gunicorn
- uWSGI
- Waitress
- mod_wsgi
- 性能优化
- 负载均衡

### 09-fullstack

完整的 Web 应用示例：
- 路由处理
- 表单处理
- 会话管理
- 缓存使用
- 中间件集成
- 静态文件服务
- 健康检查

### 10-cache-backends-web

缓存后端 Web 管理界面示例：
- 支持 Memory、Tree、Redis、Database、Memcache 缓存
- 可视化缓存操作
- 批量操作支持
- TTL 管理
- 性能对比
- 缓存应用场景

## 运行示例

每个示例目录都包含独立的 Python 文件，可以直接运行：

```bash
cd <example-directory>
python <example-file>.py
```

## 依赖要求

所有示例都需要安装 Litefs：

```bash
pip install -r ../../requirements.txt
```

部分示例可能需要额外的依赖：

```bash
pip install gunicorn gevent  # WSGI 部署
pip install uwsgi           # uWSGI 部署
pip install waitress        # Waitress 部署
pip install redis           # Redis 缓存
pip install python-memcached  # Memcache 缓存
```

## 最佳实践

1. 从简单示例开始，逐步学习复杂功能
2. 阅读每个示例的 README 文档
3. 运行示例并查看效果
4. 修改示例代码进行实验
5. 参考完整应用示例构建自己的应用

## 贡献

欢迎贡献更多示例！请确保：
- 代码符合 PEP 8 规范
- 添加必要的注释和文档
- 示例可以直接运行
- 包含 README 说明文档

## 许可证

与 Litefs 主项目保持一致。
