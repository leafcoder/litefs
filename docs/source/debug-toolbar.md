# 开发调试工具

## 概述

Litefs 提供完整的开发调试工具，帮助开发者快速定位问题：

- **请求/响应检查器**：查看请求头、参数、Cookie、Session 等
- **SQL 查询日志**：记录所有 SQL 查询、执行时间、慢查询分析
- **性能分析器**：请求耗时分析、内存使用、瓶颈定位
- **错误追踪面板**：异常堆栈、错误上下文、错误日志聚合

## 启用方式

```bash
# 方式一：环境变量
export LITEFS_DEBUG=1
python app.py

# 方式二：命令行
LITEFS_DEBUG=1 python app.py
```

## 输出示例

```
═══════════════════════════════════════════════════════════════════
🔍 Litefs Debug - Request #1
═══════════════════════════════════════════════════════════════════

📌 Request
┌─────────────────────────────────────────────────────────────────┐
│ GET /api/users?id=1                                             │
│ Host: localhost:8080                                            │
│ User-Agent: Mozilla/5.0...                                      │
│ Cookie: session_id=abc123                                       │
└─────────────────────────────────────────────────────────────────┘

⏱️ Performance
┌─────────────────────────────────────────────────────────────────┐
│ Total:     45.23ms                                              │
│ Routing:   0.12ms                                               │
│ Handler:   42.50ms                                              │
│ DB:        38.10ms (3 queries)                                  │
│ Template:  0.00ms                                               │
└─────────────────────────────────────────────────────────────────┘

💾 SQL Queries (3)
┌─────────────────────────────────────────────────────────────────┐
│ [1] 12.50ms  SELECT * FROM users WHERE id = 1                   │
│ [2] 15.30ms  SELECT * FROM orders WHERE user_id = 1             │
│ [3] 10.30ms  SELECT * FROM products WHERE id IN (1, 2, 3)       │
│                                                                 │
│ ⚠️  Slow Query: [2] took 15.30ms                                │
└─────────────────────────────────────────────────────────────────┘

📤 Response
┌─────────────────────────────────────────────────────────────────┐
│ Status: 200 OK                                                  │
│ Content-Type: application/json                                  │
│ Size: 1.2KB                                                     │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
```

## 手动追踪

### SQL 查询追踪

```python
from litefs.debug import track_sql

@app.route('/users')
def get_users(request):
    with track_sql('SELECT * FROM users WHERE status = ?', ('active',)):
        # 执行数据库查询
        users = db.query(...)
    
    return {'users': users}
```

### 性能追踪

```python
from litefs.debug import track_performance

@app.route('/report')
def generate_report(request):
    with track_performance('template'):
        # 模板渲染
        html = render_template('report.html', data=data)
    
    return html
```

### 获取当前调试信息

```python
from litefs.debug import get_current_debug

@app.route('/api/data')
def handler(request):
    debug = get_current_debug()
    if debug:
        debug.add_sql_query('SELECT * FROM data', (), 5.0)
    
    return {'data': []}
```

## API 参考

### 环境变量

| 变量 | 值 | 说明 |
|------|-----|------|
| `LITEFS_DEBUG` | `1` | 启用调试工具 |

### 函数

| 函数 | 说明 |
|------|------|
| `is_debug_enabled()` | 检查是否启用调试模式 |
| `get_current_debug()` | 获取当前请求的调试信息 |
| `track_sql(sql, params)` | 追踪 SQL 查询 |
| `track_performance(name)` | 追踪性能指标 |

### RequestDebug 对象

| 属性/方法 | 说明 |
|-----------|------|
| `request_id` | 请求 ID |
| `method` | 请求方法 |
| `path` | 请求路径 |
| `query_string` | 查询字符串 |
| `headers` | 请求头 |
| `cookies` | Cookie |
| `session` | Session |
| `sql_queries` | SQL 查询列表 |
| `errors` | 错误列表 |
| `total_time` | 总耗时（毫秒） |
| `db_time` | 数据库耗时 |
| `add_sql_query(sql, params, duration)` | 添加 SQL 查询 |
| `add_error(error, context)` | 添加错误 |

## 注意事项

1. **生产环境禁用**：调试工具仅用于开发环境，生产环境请确保 `LITEFS_DEBUG` 未设置
2. **性能影响**：调试工具会增加少量性能开销，不建议在生产环境使用
3. **敏感信息**：调试输出会遮蔽 Cookie、Authorization 等敏感信息

## 完整示例

```python
import os
os.environ['LITEFS_DEBUG'] = '1'

from litefs.core import Litefs
from litefs.debug import track_sql

app = Litefs()

@app.route('/api/users')
def get_users(request):
    with track_sql('SELECT * FROM users WHERE status = ?', ('active',)):
        users = [...]  # 数据库查询
    
    return {'users': users}

if __name__ == '__main__':
    app.run()
```
