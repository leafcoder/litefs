# Litefs 示例

本目录包含 Litefs 框架的可运行示例，按功能递进组织。每个示例都是独立目录，
自带 `app.py`、模板与静态资源，可直接 `cd` 进入后运行。

## 示例清单

| 目录 | 主题 | 端口 | 核心内容 |
| --- | --- | --- | --- |
| `01-quickstart/` | 快速入门 | 8081 | 路由（装饰器风格）、中间件、模板渲染、静态文件 |
| `02-rest-api/` | REST API | 8082 | JWT 认证、项目/任务/成员/评论 CRUD、分页排序过滤、OpenAPI 文档 |
| `03-web-app/` | 全栈 Web 应用 | 8083 | 注册登录、OAuth2 社交登录、文章与评论、访问统计、管理后台 |
| `04-realtime/` | 实时通信 | 8084 | WebSocket 连接、房间管理、消息广播、在线用户列表 |
| `05-production/` | 生产部署 | 8085 | 多进程 workers、结构化日志、Redis/内存缓存、健康检查、优雅关闭、Celery |
| `06-prometheus-monitoring/` | 监控指标 | 8083 | Prometheus 中间件、`/metrics` 端点、请求/错误/延迟/缓存/连接池指标 |
| `07-database-migrations/` | 数据库迁移 | 8084 | Alembic 迁移环境、`litefs db` 命令组、模型与迁移脚本管理 |
| `08-mail-service/` | 邮件服务 | 8085 | Mako 双模板渲染、SMTP 客户端（STARTTLS/SSL）、Celery 异步发送、附件 |
| `09-i18n/` | 国际化 | 8086 | 四级语言协商、请求级 locale、模板翻译函数注入、`.po`/`.mo` 编译 |

## 通用约定

- **源码路径**：所有示例的 `app.py` 都会把仓库的 `src/` 加入 `sys.path`，
  因此**无需先 `pip install` 本仓库**，在源码目录直接运行即可。
- **端口**：示例端口互不冲突，可同时运行；但 `06`/`03` 同为 8083、`07`/`04` 同为 8084、
  `08`/`05` 同为 8085，同时启动时需修改对应示例的 `port` 参数。
- **数据存储**：示例数据默认落在内存或本地 SQLite 文件中，重启后重置。

## 运行示例

### 1. 快速入门（8081）

```bash
cd examples/01-quickstart
python app.py
```

访问 http://localhost:8081

路由：`GET /`、`GET /about`、`GET /user/{id}`、`POST /api/data`

### 2. REST API（8082）

```bash
cd examples/02-rest-api
python app.py
```

访问 http://localhost:8082 ，API 文档在 `/api`，OpenAPI 规范在 `/openapi.json`。

默认账号：`admin / admin123`、`john / john123`、`jane / jane123`

### 3. 博客系统（8083）

```bash
cd examples/03-web-app
python app.py
```

访问 http://localhost:8083

包含用户注册登录、OAuth2（GitHub / Google）社交登录、文章与评论、访问统计与后台管理。

### 4. 实时通信（8084）

```bash
cd examples/04-realtime
python app.py
```

访问 http://localhost:8084 ，页面会自动建立 WebSocket 连接，支持房间切换与消息广播。

### 5. 生产部署（8085）

```bash
cd examples/05-production
pip install -r requirements.txt

# 开发模式
python app.py
# 生产模式（多进程）
WORKERS=4 python app.py
# 开启调试工具栏
DEBUG_TOOLBAR=true python app.py
```

该目录同时提供 `Dockerfile`、`docker-compose.yml` 与 `nginx.conf`，
可直接用于容器化与反向代理部署演练。

### 6. Prometheus 监控（8083）

```bash
cd examples/06-prometheus-monitoring
pip install 'litefs[prometheus]'
python app.py
```

```bash
curl http://127.0.0.1:8083/api/items/1
curl http://127.0.0.1:8083/api/cache/demo   # 第一次 miss，第二次 hit
curl http://127.0.0.1:8083/api/error        # 产生 500 错误计数
curl http://127.0.0.1:8083/metrics          # 查看指标
```

> `/metrics` 会暴露内部路径与状态码分布，不要直接暴露到公网。

### 7. 数据库迁移（8084）

```bash
cd examples/07-database-migrations
pip install 'litefs[db]'
python app.py
```

迁移命令需在示例目录内执行（CLI 从当前目录的 `app.py` 读取 `database_url`）：

```bash
litefs db init
litefs db migrate -m "初始迁移"
litefs db upgrade
litefs db current
litefs db history
litefs db downgrade
```

### 8. 邮件服务（8085）

```bash
cd examples/08-mail-service
python app.py
```

默认开启**预览模式**，无需 SMTP 服务器即可体验：

```bash
curl -X POST http://localhost:8085/api/mail/preview \
  -H 'Content-Type: application/json' \
  -d '{"name": "张三", "email": "zhangsan@example.com"}'
```

接入真实 SMTP 服务器：

```bash
export MAIL_ENABLED=1
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=noreply@example.com
export SMTP_PASSWORD=your-password
python app.py
```

### 9. 国际化（8086）

```bash
cd examples/09-i18n
python compile_messages.py     # 先把 .po 编译为 .mo
python app.py
```

```bash
curl http://localhost:8086/                              # 按 Accept-Language 协商
curl "http://localhost:8086/?locale=en"                  # 查询参数优先级最高
curl -H "Accept-Language: en-US,en;q=0.9" http://localhost:8086/
```

`compile_messages.py` 是零依赖的 `.po` → `.mo` 编译器，修改 `locales/zh_CN/LC_MESSAGES/messages.po`
后重新执行即可生效。

## 相关文档

| 主题 | 文档 |
| --- | --- |
| Prometheus 监控 | [prometheus-monitoring.md](../docs/source/prometheus-monitoring.md) |
| 数据库迁移 | [database-migrations.md](../docs/source/database-migrations.md) |
| 邮件服务 | [mail-service.md](../docs/source/mail-service.md) |
| 国际化 | [i18n.md](../docs/source/i18n.md) |
| 性能回归基准 | [performance-regression.md](../docs/source/performance-regression.md) |
| 依赖安全审计 | [dependency-audit.md](../docs/source/dependency-audit.md) |
