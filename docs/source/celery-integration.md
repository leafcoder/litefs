# Celery 任务队列集成

Litefs 提供了与 Celery 的无缝集成，简化异步任务处理。

## 安装

```bash
pip install celery redis
```

## 快速开始

### 1. 初始化 Celery

```python
from litefs import Litefs
from litefs.tasks import Celery

app = Litefs(
    host='0.0.0.0',
    port=8080,
    celery_broker='redis://localhost:6379/0',
    celery_backend='redis://localhost:6379/1',
)

celery = Celery(app)
```

### 2. 定义任务

```python
@celery.task
def send_email(to, subject, body):
    # 发送邮件
    return {'status': 'sent', 'to': to}
```

### 3. 异步执行

```python
# 提交任务
task_id = send_email.delay('user@example.com', 'Hello', 'World')

# 查询状态
status = celery.get_task_status(task_id)

# 获取结果
result = celery.get_task_result(task_id)
```

## 任务选项

### 基本选项

```python
@celery.task(
    name='custom_task',        # 任务名称
    queue='high_priority',     # 队列名称
    max_retries=3,             # 最大重试次数
    default_retry_delay=60,    # 重试延迟（秒）
    time_limit=300,            # 硬时间限制
    soft_time_limit=270,       # 软时间限制
)
def process_data(data):
    return {'processed': data}
```

### 绑定任务

```python
@celery.task(bind=True)
def process_file(self, filepath):
    try:
        # 处理文件
        return {'status': 'success'}
    except Exception as exc:
        raise self.retry(exc=exc)
```

## 定时任务

```python
from celery.schedules import crontab

@celery.task
def cleanup_sessions():
    # 清理会话
    pass

# 每 30 分钟执行
celery.schedule(
    name='cleanup-every-30-minutes',
    task=cleanup_sessions,
    schedule=30 * 60,
)

# 每天凌晨 2 点执行
celery.schedule(
    name='daily-report',
    task=send_daily_report,
    schedule=crontab(hour=2, minute=0),
)
```

## API 参考

### Celery 类

| 方法 | 说明 |
|------|------|
| `task(func, **options)` | 任务装饰器 |
| `schedule(name, task, schedule, args, kwargs)` | 配置定时任务 |
| `get_task(task_id)` | 获取任务结果对象 |
| `get_task_status(task_id)` | 获取任务状态 |
| `get_task_result(task_id, timeout)` | 获取任务结果 |
| `revoke_task(task_id, terminate)` | 撤销任务 |
| `get_active_tasks()` | 获取活跃任务列表 |
| `get_registered_tasks()` | 获取已注册任务列表 |
| `get_queue_length(queue)` | 获取队列长度 |
| `health_check()` | 健康检查 |

### 配置选项

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `celery_broker` | `None` | Broker URL |
| `celery_backend` | `None` | Result Backend URL |
| `celery_config` | `None` | 额外配置字典 |

## 启动 Worker

```bash
# 启动 Worker
celery -A app.celery worker --loglevel=info

# 启动 Beat（定时任务）
celery -A app.celery beat --loglevel=info

# 同时启动 Worker 和 Beat
celery -A app.celery worker --beat --loglevel=info
```

## 完整示例

参见 [examples/16-celery-tasks/app.py](../examples/16-celery-tasks/app.py)
