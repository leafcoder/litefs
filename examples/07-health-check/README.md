# 健康检查

Litefs 健康检查示例，包括与新路由系统的集成。

## 示例文件

- `health_check_example.py` - 健康检查示例主程序

## 运行示例

```bash
python health_check_example.py
```

访问以下端点查看健康检查：
- http://localhost:9090/health - 健康检查
- http://localhost:9090/health/ready - 就绪检查

## 健康检查配置

### 添加健康检查

```python
from litefs.middleware import HealthCheck

app.add_middleware(HealthCheck, path='/health', ready_path='/health/ready')

def check_database():
    """检查数据库连接"""
    return True

app.add_health_check('database', check_database)
```

### 添加就绪检查

```python
def check_migrations():
    """检查数据库迁移"""
    return True

app.add_ready_check('migrations', check_migrations)
```

## 健康检查示例

### 1. 数据库检查

```python
def check_database():
    try:
        with db.connect() as conn:
            conn.execute('SELECT 1')
        return True
    except Exception as e:
        print(f"Database check failed: {e}")
        return False
```

### 2. 缓存检查

```python
def check_cache():
    try:
        cache.put('health_check', 'ok')
        value = cache.get('health_check')
        return value == 'ok'
    except Exception as e:
        print(f"Cache check failed: {e}")
        return False
```

### 3. 磁盘空间检查

```python
def check_disk_space():
    import shutil
    total, used, free = shutil.disk_usage('.')
    return free > 1024 * 1024 * 1024  # 至少 1GB 可用空间
```

### 4. 外部 API 检查

```python
def check_external_api():
    try:
        response = requests.get('https://api.example.com/health', timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"External API check failed: {e}")
        return False
```

### 5. 消息队列检查

```python
def check_message_queue():
    try:
        queue = get_queue_connection()
        queue.connect()
        return True
    except Exception as e:
        print(f"Message queue check failed: {e}")
        return False
```

## 健康检查响应

### 健康检查响应

```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "cache": "healthy",
    "disk_space": "healthy"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 就绪检查响应

```json
{
  "status": "ready",
  "checks": {
    "database": "ready",
    "migrations": "ready"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 不健康响应

```json
{
  "status": "unhealthy",
  "checks": {
    "database": "unhealthy",
    "cache": "healthy",
    "disk_space": "healthy"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 生产环境部署

### Kubernetes 配置

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Nginx 健康检查

```nginx
upstream backend {
    server 127.0.0.1:8080;
    check interval=3000 rise=2 fall=3 timeout=1000 type=http;
    check_http_send "GET /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx http_3xx;
}
```

## 最佳实践

1. 健康检查应该快速响应（< 1秒）
2. 只检查关键依赖，避免过度检查
3. 区分健康检查和就绪检查
4. 提供详细的检查信息用于调试
5. 在容器编排系统中正确配置探针

## 与新路由系统集成

使用新的路由系统定义自定义健康检查端点：

```python
from litefs import Litefs
from litefs.routing import get
from litefs.middleware import HealthCheck

app = Litefs()

# 添加默认健康检查中间件
app.add_middleware(HealthCheck, path='/health', ready_path='/health/ready')

# 定义自定义健康检查路由
@get('/health/custom')
def custom_health_check(self):
    # 执行自定义健康检查逻辑
    checks = {
        'app_status': 'healthy',
        'custom_service': 'healthy',
        'version': '1.0.0'
    }
    
    # 返回 JSON 响应
    self.start_response(200, [('Content-Type', 'application/json')])
    import json
    return json.dumps({
        'status': 'healthy',
        'checks': checks,
        'timestamp': self.request_time.isoformat()
    })

# 注册路由
app.register_routes(custom_health_check)

app.run()
```

### 访问端点

- **默认健康检查**：http://localhost:9090/health
- **默认就绪检查**：http://localhost:9090/health/ready
- **自定义健康检查**：http://localhost:9090/health/custom
