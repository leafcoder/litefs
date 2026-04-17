#!/usr/bin/env python
# coding: utf-8

"""
Celery 任务队列集成示例

本示例展示如何使用 Litefs 集成的 Celery 任务队列功能：
- 定义异步任务
- 执行异步任务
- 查询任务状态
- 定时任务配置

前置条件：
1. 安装 Celery: pip install celery
2. 安装 Redis: pip install redis
3. 启动 Redis 服务
4. 启动 Celery Worker: celery -A app.celery worker --loglevel=info
5. 启动 Celery Beat (定时任务): celery -A app.celery beat --loglevel=info
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import route, post
from litefs.tasks import Celery, task, crontab

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
    celery_broker='redis://localhost:6379/0',
    celery_backend='redis://localhost:6379/1',
)

celery = Celery(app)


@celery.task
def send_email(to: str, subject: str, body: str):
    """
    发送邮件任务
    
    这是一个简单的异步任务示例。
    """
    print(f"发送邮件到: {to}")
    print(f"主题: {subject}")
    print(f"内容: {body}")
    time.sleep(2)
    return {'status': 'sent', 'to': to, 'subject': subject}


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_file(self, filepath: str):
    """
    处理文件任务（支持重试）
    
    这是一个绑定任务示例，可以访问任务实例 self。
    """
    try:
        print(f"处理文件: {filepath}")
        time.sleep(3)
        
        return {'status': 'processed', 'filepath': filepath}
    except Exception as exc:
        print(f"处理失败，准备重试: {exc}")
        raise self.retry(exc=exc)


@celery.task(queue='high_priority', time_limit=60)
def urgent_task(data: str):
    """
    紧急任务（高优先级队列）
    
    这个任务会被发送到高优先级队列执行。
    """
    print(f"执行紧急任务: {data}")
    time.sleep(1)
    return {'status': 'completed', 'data': data}


def setup_scheduled_tasks():
    """配置定时任务"""
    
    @celery.task
    def cleanup_expired_sessions():
        print("清理过期会话...")
        return {'cleaned': 10}
    
    @celery.task
    def send_daily_report():
        print("发送每日报告...")
        return {'sent': True}
    
    celery.schedule(
        name='cleanup-every-30-minutes',
        task=cleanup_expired_sessions,
        schedule=30 * 60,
    )
    
    celery.schedule(
        name='daily-report',
        task=send_daily_report,
        schedule=crontab(hour=2, minute=0),
    )


setup_scheduled_tasks()


@route('/', name='index')
def index(request):
    """首页 - API 列表"""
    return {
        'message': 'Celery 任务队列示例',
        'endpoints': {
            '/task/email': 'POST - 发送邮件任务',
            '/task/file': 'POST - 处理文件任务',
            '/task/urgent': 'POST - 紧急任务',
            '/task/status/{task_id}': 'GET - 查询任务状态',
            '/task/result/{task_id}': 'GET - 获取任务结果',
            '/task/active': 'GET - 获取活跃任务',
            '/task/health': 'GET - 健康检查',
        }
    }


@post('/task/email', name='send_email_task')
def send_email_task(request):
    """发送邮件任务"""
    data = request.json or {}
    to = data.get('to', 'user@example.com')
    subject = data.get('subject', 'Test Email')
    body = data.get('body', 'This is a test email.')
    
    result = send_email.delay(to, subject, body)
    task_id = result.id
    
    return {
        'message': '邮件任务已提交',
        'task_id': task_id,
        'status_url': f'/task/status/{task_id}',
    }


@post('/task/file', name='process_file_task')
def process_file_task(request):
    """处理文件任务"""
    data = request.json or {}
    filepath = data.get('filepath', '/tmp/test.txt')
    
    result = process_file.delay(filepath)
    task_id = result.id
    
    return {
        'message': '文件处理任务已提交',
        'task_id': task_id,
        'status_url': f'/task/status/{task_id}',
    }


@post('/task/urgent', name='urgent_task')
def urgent_task_endpoint(request):
    """紧急任务"""
    data = request.json or {}
    task_data = data.get('data', 'urgent data')
    
    result = urgent_task.delay(task_data)
    task_id = result.id
    
    return {
        'message': '紧急任务已提交',
        'task_id': task_id,
        'status_url': f'/task/status/{task_id}',
    }


@route('/task/status/{task_id}', name='task_status')
def task_status(request, task_id):
    """查询任务状态"""
    status = celery.get_task_status(task_id)
    
    return {
        'task_id': task_id,
        'status': status,
    }


@route('/task/result/{task_id}', name='task_result')
def task_result(request, task_id):
    """获取任务结果"""
    try:
        result = celery.get_task_result(task_id, timeout=1)
        return {
            'task_id': task_id,
            'status': 'success',
            'result': result,
        }
    except Exception as e:
        return {
            'task_id': task_id,
            'status': 'pending',
            'error': str(e),
        }


@route('/task/active', name='active_tasks')
def active_tasks(request):
    """获取活跃任务"""
    tasks = celery.get_active_tasks()
    
    return {
        'count': len(tasks),
        'tasks': tasks,
    }


@route('/task/health', name='task_health')
def task_health(request):
    """健康检查"""
    health = celery.health_check()
    
    return health


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("Celery 任务队列集成示例")
    print("=" * 60)
    print()
    print("前置条件：")
    print("  1. 安装依赖: pip install celery redis")
    print("  2. 启动 Redis 服务")
    print("  3. 启动 Celery Worker:")
    print("     celery -A app.celery worker --loglevel=info")
    print("  4. 启动 Celery Beat (定时任务):")
    print("     celery -A app.celery beat --loglevel=info")
    print()
    print("API 端点：")
    print("  POST /task/email      - 发送邮件任务")
    print("  POST /task/file       - 处理文件任务")
    print("  POST /task/urgent     - 紧急任务")
    print("  GET  /task/status/<id> - 查询任务状态")
    print("  GET  /task/result/<id> - 获取任务结果")
    print("  GET  /task/active     - 获取活跃任务")
    print("  GET  /task/health     - 健康检查")
    print()
    print("测试命令：")
    print("  # 发送邮件任务")
    print("  curl -X POST http://localhost:8080/task/email \\")
    print("       -H 'Content-Type: application/json' \\")
    print("       -d '{\"to\": \"user@example.com\", \"subject\": \"Hello\"}'")
    print()
    print("  # 查询任务状态")
    print("  curl http://localhost:8080/task/status/<task_id>")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
