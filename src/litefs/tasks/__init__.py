#!/usr/bin/env python
# coding: utf-8

"""
Celery 任务队列集成模块

提供与 Litefs 框架的无缝集成，简化 Celery 的配置和使用。

特性：
- 自动配置 Broker 和 Backend
- 与 Litefs 配置系统集成
- 简化的任务装饰器
- 任务状态查询 API
- 支持 Redis、RabbitMQ 等多种 Broker

使用示例：
    from litefs.tasks import Celery, task
    
    # 初始化 Celery
    celery = Celery(app, broker='redis://localhost:6379/0')
    
    # 定义任务
    @task
    def send_email(to, subject, body):
        # 发送邮件
        pass
    
    # 异步执行
    result = send_email.delay('user@example.com', 'Hello', 'World')
    
    # 查询状态
    status = result.status
    result.get()  # 获取结果
"""

try:
    from celery import Celery as _Celery
    from celery.result import AsyncResult
    from celery.schedules import crontab
    HAS_CELERY = True
except ImportError:
    _Celery = None
    AsyncResult = None
    crontab = None
    HAS_CELERY = False

from typing import Any, Callable, Dict, List, Optional, Union
import functools


class CeleryConfig:
    """Celery 配置类"""
    
    DEFAULT_CONFIG = {
        'broker_url': None,
        'result_backend': None,
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
        'timezone': 'Asia/Shanghai',
        'enable_utc': True,
        'task_track_started': True,
        'task_time_limit': 300,
        'task_soft_time_limit': 270,
        'worker_prefetch_multiplier': 4,
        'worker_max_tasks_per_child': 1000,
        'task_acks_late': True,
        'task_reject_on_worker_lost': True,
        'task_default_queue': 'default',
        'task_default_exchange': 'tasks',
        'task_default_routing_key': 'task.default',
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._config = self.DEFAULT_CONFIG.copy()
        if config:
            self._config.update(config)
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        return self._config.copy()


class Celery:
    """
    Celery 集成类
    
    提供与 Litefs 框架的无缝集成。
    """
    
    _instance = None
    _app = None
    
    def __init__(
        self,
        app=None,
        broker: Optional[str] = None,
        backend: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 Celery
        
        Args:
            app: Litefs 应用实例
            broker: Broker URL (如 redis://localhost:6379/0)
            backend: Result Backend URL
            config: 额外配置
        """
        if not HAS_CELERY:
            raise ImportError(
                "Celery is not installed. "
                "Please install it with: pip install celery"
            )
        
        self._litefs_app = app
        self._tasks: Dict[str, Callable] = {}
        self._scheduled_tasks: Dict[str, Dict] = {}
        
        celery_config = CeleryConfig(config)
        
        if broker:
            celery_config._config['broker_url'] = broker
        if backend:
            celery_config._config['result_backend'] = backend
        
        if app and hasattr(app, 'config'):
            self._configure_from_app(app, celery_config)
        
        self._celery_app = _Celery(
            'litefs_tasks',
            broker=celery_config.get('broker_url'),
            backend=celery_config.get('result_backend'),
        )
        self._celery_app.conf.update(celery_config.to_dict())
        
        Celery._instance = self
    
    def _configure_from_app(self, app, config: CeleryConfig):
        """从 Litefs 应用配置中读取 Celery 配置"""
        app_config = getattr(app, 'config', None)
        if app_config:
            broker = getattr(app_config, 'celery_broker', None)
            backend = getattr(app_config, 'celery_backend', None)
            
            if broker:
                config._config['broker_url'] = broker
            if backend:
                config._config['result_backend'] = backend
            
            celery_config = getattr(app_config, 'celery_config', None)
            if celery_config and isinstance(celery_config, dict):
                config._config.update(celery_config)
    
    @property
    def celery_app(self):
        """获取底层 Celery 应用实例"""
        return self._celery_app
    
    def task(
        self,
        func: Optional[Callable] = None,
        *,
        name: Optional[str] = None,
        queue: str = 'default',
        bind: bool = False,
        max_retries: int = 3,
        default_retry_delay: int = 60,
        time_limit: Optional[int] = None,
        soft_time_limit: Optional[int] = None,
        **kwargs
    ) -> Callable:
        """
        任务装饰器
        
        Args:
            func: 被装饰的函数
            name: 任务名称
            queue: 队列名称
            bind: 是否绑定任务实例
            max_retries: 最大重试次数
            default_retry_delay: 默认重试延迟（秒）
            time_limit: 硬时间限制
            soft_time_limit: 软时间限制
            **kwargs: 其他 Celery 任务选项
            
        Returns:
            任务函数
            
        Example:
            @celery.task
            def send_email(to, subject, body):
                # 发送邮件
                pass
            
            @celery.task(bind=True, max_retries=5)
            def process_file(self, filepath):
                # 处理文件
                pass
        """
        def decorator(f: Callable) -> Callable:
            task_name = name or f.__name__
            
            task_options = {
                'name': task_name,
                'queue': queue,
                'bind': bind,
                'max_retries': max_retries,
                'default_retry_delay': default_retry_delay,
            }
            
            if time_limit:
                task_options['time_limit'] = time_limit
            if soft_time_limit:
                task_options['soft_time_limit'] = soft_time_limit
            
            task_options.update(kwargs)
            
            celery_task = self._celery_app.task(**task_options)(f)
            
            self._tasks[task_name] = celery_task
            
            return celery_task
        
        if func is not None:
            return decorator(func)
        return decorator
    
    def schedule(
        self,
        name: str,
        task: Union[str, Callable],
        schedule,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
    ):
        """
        配置定时任务
        
        Args:
            name: 定时任务名称
            task: 任务函数或任务名称
            schedule: 调度配置（crontab 或秒数）
            args: 任务参数
            kwargs: 任务关键字参数
            
        Example:
            # 每 30 秒执行
            celery.schedule('cleanup', cleanup_task, 30)
            
            # 每天凌晨 2 点执行
            from celery.schedules import crontab
            celery.schedule('daily_report', send_report, crontab(hour=2, minute=0))
        """
        task_name = task if isinstance(task, str) else task.__name__
        
        self._scheduled_tasks[name] = {
            'task': task_name,
            'schedule': schedule,
            'args': args or (),
            'kwargs': kwargs or {},
        }
        
        self._celery_app.conf.beat_schedule = self._scheduled_tasks
    
    def get_task(self, task_id: str) -> Optional[AsyncResult]:
        """
        获取任务结果对象
        
        Args:
            task_id: 任务 ID
            
        Returns:
            AsyncResult 对象
        """
        return AsyncResult(task_id, app=self._celery_app)
    
    def get_task_status(self, task_id: str) -> str:
        """
        获取任务状态
        
        Args:
            task_id: 任务 ID
            
        Returns:
            任务状态字符串
        """
        result = self.get_task(task_id)
        return result.status if result else 'UNKNOWN'
    
    def get_task_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """
        获取任务结果
        
        Args:
            task_id: 任务 ID
            timeout: 超时时间
            
        Returns:
            任务结果
        """
        result = self.get_task(task_id)
        if result:
            return result.get(timeout=timeout)
        return None
    
    def revoke_task(self, task_id: str, terminate: bool = False):
        """
        撤销任务
        
        Args:
            task_id: 任务 ID
            terminate: 是否终止正在执行的任务
        """
        self._celery_app.control.revoke(task_id, terminate=terminate)
    
    def get_active_tasks(self) -> List[Dict]:
        """
        获取正在执行的任务列表
        
        Returns:
            活跃任务列表
        """
        inspect = self._celery_app.control.inspect()
        active = inspect.active()
        
        if not active:
            return []
        
        tasks = []
        for worker, worker_tasks in active.items():
            for task in worker_tasks:
                tasks.append({
                    'id': task.get('id'),
                    'name': task.get('name'),
                    'worker': worker,
                    'args': task.get('args'),
                    'kwargs': task.get('kwargs'),
                })
        
        return tasks
    
    def get_registered_tasks(self) -> List[str]:
        """
        获取已注册的任务列表
        
        Returns:
            任务名称列表
        """
        return list(self._tasks.keys())
    
    def get_queue_length(self, queue: str = 'default') -> int:
        """
        获取队列长度
        
        Args:
            queue: 队列名称
            
        Returns:
            队列长度
        """
        inspect = self._celery_app.control.inspect()
        reserved = inspect.reserved()
        
        if not reserved:
            return 0
        
        count = 0
        for worker_tasks in reserved.values():
            for task in worker_tasks:
                if task.get('delivery_info', {}).get('routing_key') == queue:
                    count += 1
        
        return count
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态信息
        """
        inspect = self._celery_app.control.inspect()
        
        stats = inspect.stats()
        active = inspect.active()
        registered = inspect.registered()
        
        workers = []
        if stats:
            for worker_name, worker_stats in stats.items():
                workers.append({
                    'name': worker_name,
                    'status': 'online',
                    'tasks_processed': worker_stats.get('total', {}),
                    'pool': worker_stats.get('pool', {}),
                })
        
        return {
            'status': 'healthy' if workers else 'no_workers',
            'workers': workers,
            'registered_tasks': len(self._tasks),
            'active_tasks': sum(len(t) for t in (active or {}).values()),
        }
    
    @classmethod
    def get_instance(cls) -> Optional['Celery']:
        """获取 Celery 实例"""
        return cls._instance


def task(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    queue: str = 'default',
    **kwargs
) -> Callable:
    """
    便捷任务装饰器（使用全局 Celery 实例）
    
    Args:
        func: 被装饰的函数
        name: 任务名称
        queue: 队列名称
        **kwargs: 其他选项
        
    Returns:
        任务函数
        
    Example:
        from litefs.tasks import task
        
        @task
        def send_email(to, subject, body):
            # 发送邮件
            pass
        
        # 异步执行
        send_email.delay('user@example.com', 'Hello', 'World')
    """
    celery_instance = Celery.get_instance()
    
    if celery_instance is None:
        raise RuntimeError(
            "Celery not initialized. "
            "Please create a Celery instance first: celery = Celery(app, broker='...')"
        )
    
    return celery_instance.task(func, name=name, queue=queue, **kwargs)


def get_celery() -> Optional[Celery]:
    """获取全局 Celery 实例"""
    return Celery.get_instance()


__all__ = [
    'Celery',
    'CeleryConfig',
    'task',
    'get_celery',
    'AsyncResult',
    'crontab',
    'HAS_CELERY',
]
