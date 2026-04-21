# Litefs v0.8.0 升级开发计划

## 项目状态概览

**当前版本**: v0.8.0

**已完成核心功能**:
| 模块 | 状态 | 说明 |
|------|------|------|
| WebSocket 支持 | ✅ 完成 | 实时通信、房间管理、心跳检测 |
| Celery 任务队列 | ✅ 完成 | 异步任务、定时任务、健康检查 |
| JWT 认证系统 | ✅ 完成 | Token 生成/验证、权限装饰器 |
| 缓存系统 | ✅ 完成 | Redis/Memcache/数据库缓存 |
| 数据库支持 | ✅ 完成 | 连接池、ORM 集成 |
| 调试工具 | ✅ 完成 | 请求检查、SQL 日志、性能分析 |
| 中间件 | ✅ 完成 | CORS/CSRF/限流/安全头部/日志 |
| OpenAPI 文档 | ✅ 完成 | Swagger UI 集成 |
| 插件系统 | ✅ 完成 | 生命周期管理、依赖注入 |
| 会话管理 | ✅ 完成 | 多后端存储支持 |

---

## v0.8.0 升级目标

### 核心目标
1. **认证系统增强** - OAuth2、社交登录
2. **可观测性** - Prometheus 指标导出
3. **开发者体验** - 数据库迁移工具
4. **邮件支持** - SMTP 发送、模板邮件

> **架构说明**: HTTPS 支持不在计划内，生产环境建议通过 Nginx/HAProxy 等反向代理处理 SSL 终止，应用服务器专注于业务逻辑。

---

## 详细功能规划

### 1. OAuth2 认证增强 (高优先级)

**目标**: 支持主流 OAuth2 提供商集成

**功能特性**:
- OAuth2 授权码流程
- 支持 GitHub、Google、微信、企业微信
- 统一的用户身份映射
- Token 刷新机制
- 安全的 State 参数验证

**实现方案**:
```python
from litefs.auth import OAuth2, GitHubProvider, GoogleProvider

oauth = OAuth2(app)

oauth.register(
    name='github',
    client_id='your-client-id',
    client_secret='your-client-secret',
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    userinfo_url='https://api.github.com/user'
)

@route('/login/github')
def github_login(request):
    return oauth.authorize_redirect('github', '/callback')

@route('/callback')
def github_callback(request):
    user = oauth.authorize_user('github', request)
    return {'user': user}
```

**工作量**: 5-6 天

**影响范围**:
- `src/litefs/auth/` - 新增 oauth2.py, providers.py

---

### 2. Prometheus 监控指标 (高优先级)

**目标**: 导出 Prometheus 格式的监控指标

**功能特性**:
- 请求计数/延迟/错误率
- 活跃连接数
- 数据库连接池状态
- 缓存命中率
- 自定义指标支持

**实现方案**:
```python
from litefs.middleware import PrometheusMiddleware

app.add_middleware(PrometheusMiddleware, {
    'prefix': 'litefs',
    'exclude_paths': ['/health', '/metrics'],
    'buckets': [0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
})

# GET /metrics
```

**输出示例**:
```
litefs_http_requests_total{method="GET",status="200"} 1234
litefs_http_request_duration_seconds_bucket{le="0.1"} 1000
litefs_db_connections_active 5
litefs_db_connections_idle 15
litefs_cache_hits_total 5000
litefs_cache_misses_total 200
```

**工作量**: 3-4 天

**影响范围**:
- `src/litefs/middleware/` - 新增 prometheus.py

---

### 3. 数据库迁移工具 (中优先级)

**目标**: 集成 Alembic 数据库迁移

**功能特性**:
- 自动生成迁移脚本
- 版本管理
- 回滚支持
- 多环境配置
- CLI 命令集成

**实现方案**:
```python
app = Litefs(
    database_url='postgresql://localhost/mydb',
    migrations_dir='migrations'
)
```

**CLI 命令**:
```bash
litefs db init          # 初始化迁移
litefs db migrate       # 生成迁移
litefs db upgrade       # 升级数据库
litefs db downgrade     # 回滚数据库
litefs db current       # 当前版本
litefs db history       # 迁移历史
```

**工作量**: 4-5 天

**影响范围**:
- `src/litefs/database/` - 新增 migrations.py
- `src/litefs/cli.py` - 新增 db 子命令

---

### 4. 邮件发送支持 (中优先级)

**目标**: 提供统一的邮件发送接口

**功能特性**:
- SMTP 配置
- 模板邮件
- 异步发送
- 附件支持
- 队列集成（Celery）

**实现方案**:
```python
from litefs.mail import Mail, Message

mail = Mail(app, host='smtp.example.com', port=587)

msg = Message(
    subject='Welcome',
    recipients=['user@example.com'],
    template='welcome.html',
    context={'name': 'User'}
)
mail.send(msg)

# 异步发送（集成 Celery）
mail.send_async(msg)
```

**工作量**: 3-4 天

**影响范围**:
- `src/litefs/` - 新增 mail/ 模块

---

### 5. i18n 国际化 (低优先级)

**目标**: 支持多语言应用

**功能特性**:
- 语言文件管理
- 自动语言检测
- 模板国际化
- 复数形式支持

**实现方案**:
```python
from litefs.i18n import I18n

i18n = I18n(app, locales_dir='locales', default_locale='zh_CN')

@route('/')
def index(request):
    return {'message': i18n.t('welcome')}
```

**工作量**: 4-5 天

**影响范围**:
- `src/litefs/` - 新增 i18n/ 模块

---

## 开发时间表

### 第 1 周
- [ ] OAuth2 认证增强 (5-6 天)
- [ ] 单元测试

### 第 2 周
- [ ] Prometheus 监控指标 (3-4 天)
- [ ] 数据库迁移工具 (开始)

### 第 3 周
- [ ] 数据库迁移工具 (完成)
- [ ] 邮件发送支持
- [ ] 集成测试

### 第 4 周
- [ ] 文档完善
- [ ] 示例更新
- [ ] 发布准备

### 后续版本 (v0.9.0)
- i18n 国际化
- 其他功能扩展

---

## 版本发布计划

### v0.8.0 (目标)
**发布内容**:
1. OAuth2 认证
2. Prometheus 指标
3. 数据库迁移
4. 邮件发送

**发布条件**:
- 所有功能测试通过
- 文档更新完成
- 示例代码验证

---

## 技术债务

### 需要修复的问题
1. 类型注解完善 - 核心模块添加完整类型提示
2. 测试覆盖率提升 - 目标 85%+
3. 性能基准测试 - 建立性能回归测试

### 代码重构
1. 中间件统一接口
2. 配置管理优化
3. 错误处理标准化

---

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| OAuth2 提供商差异 | 中 | 抽象统一接口 |
| Alembic 集成复杂 | 低 | 参考成熟方案 |
| 邮件模板兼容性 | 低 | 使用 Jinja2 |

---

## 资源需求

### 开发环境
- Python 3.9+
- PostgreSQL / MySQL
- Redis

### 测试环境
- 多种 OAuth2 提供商账号
- SMTP 服务器
- Prometheus 服务器

---

## 成功指标

### 功能完整性
- [ ] 至少支持 3 个 OAuth2 提供商
- [ ] Prometheus 指标覆盖核心功能
- [ ] 数据库迁移 CLI 完整
- [ ] 邮件发送功能可用

### 质量指标
- [ ] 测试覆盖率 > 80%
- [ ] 无 P0/P1 级 Bug
- [ ] 文档覆盖率 100%

### 性能指标
- [ ] 指标收集延迟 < 1ms
- [ ] 邮件发送异步处理

---

**规划版本**: v0.8.0  
**规划日期**: 2025-04-18  
**预计完成**: 4 周  
**下次评审**: 每周五
