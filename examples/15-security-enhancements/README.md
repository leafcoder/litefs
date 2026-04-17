# Litefs 安全增强功能示例

本示例展示 Litefs 框架的安全增强功能，包括数据库连接池优化、CSRF 保护和安全头部。

## 功能特性

### 1. 数据库连接池优化

**文件**: `src/litefs/database/core.py`

提供高性能的数据库连接管理：

- ✅ **连接健康检查** - 自动检测和移除失效连接
- ✅ **连接回收** - 定期回收长时间使用的连接
- ✅ **连接池监控** - 实时监控连接池状态
- ✅ **事件监听** - 记录连接生命周期事件
- ✅ **智能配置** - SQLite 自动禁用连接池

**配置参数**:
```python
app = Litefs(
    database_url='postgresql://localhost/mydb',
    database_pool_size=10,          # 连接池大小
    database_max_overflow=20,       # 最大溢出连接数
    database_pool_timeout=30,       # 连接超时时间（秒）
    database_pool_recycle=3600      # 连接回收时间（秒）
)
```

**监控连接池**:
```python
# 获取连接池状态
status = app.db.get_pool_status()
print(status)
# 输出: {
#     'pool_size': 10,
#     'checked_in': 8,
#     'checked_out': 2,
#     'overflow': 0,
#     'invalid': 0
# }
```

---

### 2. CSRF 保护

**文件**: `src/litefs/middleware/csrf.py`

提供完整的 CSRF 保护机制：

- ✅ **自动生成 Token** - 为每个会话生成唯一的 CSRF Token
- ✅ **多种验证方式** - 支持 Header、表单、Cookie 验证
- ✅ **Cookie 配置** - 支持安全、HttpOnly、SameSite 配置
- ✅ **豁免方法** - 可配置不需要 CSRF 保护的方法

**使用方法**:
```python
from litefs.middleware import CSRFMiddleware

# 添加 CSRF 中间件
app.add_middleware(CSRFMiddleware,
    secret_key='your-secret-key',
    token_name='csrf_token',
    header_name='X-CSRFToken',
    cookie_secure=True,
    cookie_http_only=True,
    cookie_same_site='Strict'
)
```

**在表单中使用**:
```html
<form method="POST" action="/submit">
    <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
    <!-- 其他表单字段 -->
    <button type="submit">提交</button>
</form>
```

**在 AJAX 中使用**:
```javascript
// 从 Cookie 获取 CSRF Token
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// 发送请求时添加 CSRF Token
fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
});
```

---

### 3. 安全头部

**文件**: `src/litefs/middleware/security.py`

自动添加安全相关的 HTTP 响应头：

- ✅ **X-Frame-Options** - 防止点击劫持
- ✅ **X-Content-Type-Options** - 防止 MIME 类型嗅探
- ✅ **X-XSS-Protection** - 启用 XSS 过滤
- ✅ **Strict-Transport-Security** - 强制使用 HTTPS
- ✅ **Content-Security-Policy** - 内容安全策略
- ✅ **Referrer-Policy** - 控制 Referer 信息
- ✅ **Permissions-Policy** - 控制浏览器功能

**使用方法**:
```python
from litefs.middleware import SecurityMiddleware

# 添加安全头部中间件
app.add_middleware(SecurityMiddleware,
    x_frame_options='DENY',
    x_content_type_options='nosniff',
    x_xss_protection='1; mode=block',
    strict_transport_security='max-age=31536000; includeSubDomains',
    content_security_policy="default-src 'self'; script-src 'self' 'unsafe-inline'",
    referrer_policy='strict-origin-when-cross-origin',
    permissions_policy='geolocation=(), microphone=()'
)
```

**安全头部说明**:

| 头部名称 | 值 | 作用 |
|---------|---|------|
| X-Frame-Options | DENY | 防止页面被嵌入到 iframe 中 |
| X-Content-Type-Options | nosniff | 防止浏览器猜测 MIME 类型 |
| X-XSS-Protection | 1; mode=block | 启用 XSS 过滤器 |
| Strict-Transport-Security | max-age=31536000 | 强制使用 HTTPS |
| Content-Security-Policy | default-src 'self' | 限制资源加载来源 |
| Referrer-Policy | strict-origin-when-cross-origin | 控制 Referer 信息 |
| Permissions-Policy | geolocation=() | 禁用地理位置 API |

---

## 运行示例

```bash
cd examples/15-security-enhancements
python app.py
```

服务器将在 `http://localhost:8080` 启动。

## 示例端点

### 首页
```
GET http://localhost:8080/
```

### 数据库连接池

#### 查看连接池状态
```
GET http://localhost:8080/db/pool-status
```

### CSRF 保护

#### 表单页面
```
GET http://localhost:8080/form
```

#### 表单提交
```
POST http://localhost:8080/form/submit
Content-Type: application/x-www-form-urlencoded

csrf_token=<token>&username=test&password=123
```

### 安全头部

#### 查看安全头部
```
GET http://localhost:8080/headers
```

## 测试命令

### 1. 查看连接池状态
```bash
curl http://localhost:8080/db/pool-status
```

### 2. 查看安全头部
```bash
curl -I http://localhost:8080/headers
```

输出示例：
```
HTTP/1.1 200 OK
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

### 3. 测试 CSRF 保护

#### 获取 CSRF Token
```bash
curl -c cookies.txt http://localhost:8080/form
```

#### 提交表单（带 CSRF Token）
```bash
# 从 cookies.txt 中获取 csrftoken
TOKEN=$(grep csrftoken cookies.txt | awk '{print $NF}')

# 提交表单
curl -b cookies.txt -X POST \
  -H "X-CSRFToken: $TOKEN" \
  -d "username=test&password=123" \
  http://localhost:8080/form/submit
```

## 配置建议

### 生产环境配置

#### 数据库连接池
```python
app = Litefs(
    database_url='postgresql://user:pass@host:5432/db',
    database_pool_size=20,          # 根据并发量调整
    database_max_overflow=10,       # 最大溢出连接数
    database_pool_timeout=30,       # 连接超时
    database_pool_recycle=3600,     # 1小时回收连接
    database_echo=False             # 生产环境关闭 SQL 日志
)
```

#### CSRF 保护
```python
app.add_middleware(CSRFMiddleware,
    secret_key=os.environ.get('CSRF_SECRET_KEY'),  # 从环境变量获取
    cookie_secure=True,            # 生产环境启用
    cookie_http_only=True,
    cookie_same_site='Strict'      # 严格的 SameSite 策略
)
```

#### 安全头部
```python
app.add_middleware(SecurityMiddleware,
    x_frame_options='DENY',
    strict_transport_security='max-age=31536000; includeSubDomains; preload',
    content_security_policy="default-src 'self'; script-src 'self' https://cdn.example.com",
    referrer_policy='strict-origin-when-cross-origin'
)
```

## 最佳实践

### 1. 数据库连接池
- 根据应用并发量调整连接池大小
- 监控连接池状态，及时发现连接泄漏
- 定期回收连接，避免长时间占用
- 生产环境关闭 SQL 日志

### 2. CSRF 保护
- 所有 POST/PUT/DELETE 请求都需要 CSRF Token
- 使用安全的 Cookie 配置
- 不要在 URL 中传递 CSRF Token
- 定期更换 CSRF Secret Key

### 3. 安全头部
- 启用所有推荐的安全头部
- 根据应用需求调整 CSP 策略
- 生产环境强制使用 HTTPS
- 定期检查和更新安全策略

## 性能影响

- **数据库连接池**: 提高并发性能，减少连接创建开销
- **CSRF 保护**: < 1% 性能影响
- **安全头部**: < 0.1% 性能影响

## 相关文档

- [数据库连接池文档](../../docs/database-pool.md)
- [CSRF 保护文档](../../docs/csrf-protection.md)
- [安全头部文档](../../docs/security-headers.md)

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 实现数据库连接池优化
- 实现 CSRF 保护
- 实现安全头部
