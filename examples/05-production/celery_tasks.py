#!/usr/bin/env python3
"""
Celery 任务配置

启动 Celery Worker:
    celery -A celery_tasks worker --loglevel=info

启动 Celery Beat (定时任务):
    celery -A celery_tasks beat --loglevel=info
"""

import os
from celery import Celery

celery_app = Celery(
    'litefs_tasks',
    broker=os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
    backend=os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


@celery_app.task(name='celery_tasks.process_task')
def process_task(task_name: str, data: dict) -> dict:
    import time
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"处理任务: {task_name}, 数据: {data}")

    time.sleep(2)

    result = {
        'task_name': task_name,
        'status': 'completed',
        'processed_data': data,
        'timestamp': time.time()
    }

    logger.info(f"任务完成: {task_name}")
    return result


@celery_app.task(name='celery_tasks.send_email')
def send_email(to: str, subject: str, body: str) -> dict:
    import logging

    logger = logging.getLogger(__name__)
    logger.info(f"发送邮件: to={to}, subject={subject}")

    return {
        'to': to,
        'subject': subject,
        'status': 'sent'
    }


@celery_app.task(name='celery_tasks.cleanup_cache')
def cleanup_cache() -> dict:
    import logging

    logger = logging.getLogger(__name__)
    logger.info("执行缓存清理任务")

    return {'status': 'completed', 'cleaned': True}


celery_app.conf.beat_schedule = {
    'cleanup-cache-every-hour': {
        'task': 'celery_tasks.cleanup_cache',
        'schedule': 3600.0,
    },
}

app = celery_app
