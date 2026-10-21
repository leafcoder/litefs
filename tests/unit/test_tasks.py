#!/usr/bin/env python
# coding: utf-8

"""
Celery 任务队列集成测试

覆盖 CeleryConfig、Celery 集成类的任务注册/定时配置/状态查询代理，
以及模块级便捷函数。
"""

import unittest
from unittest.mock import Mock, patch

from litefs.tasks import Celery, CeleryConfig, get_celery, task

BROKER = 'memory://'
BACKEND = 'cache+memory://'


def make_celery():
    return Celery(broker=BROKER, backend=BACKEND)


class TestCeleryConfig(unittest.TestCase):
    """CeleryConfig 配置类"""

    def test_defaults(self):
        """默认配置完整"""
        config = CeleryConfig()
        self.assertEqual(config.get('task_serializer'), 'json')
        self.assertEqual(config.get('timezone'), 'Asia/Shanghai')
        self.assertIsNone(config.get('broker_url'))

    def test_custom_overrides(self):
        """自定义配置覆盖默认值"""
        config = CeleryConfig({'broker_url': 'redis://x', 'timezone': 'UTC'})
        self.assertEqual(config.get('broker_url'), 'redis://x')
        self.assertEqual(config.get('timezone'), 'UTC')
        self.assertEqual(config.get('task_serializer'), 'json')

    def test_get_with_default(self):
        """get 未命中时返回默认值"""
        self.assertEqual(CeleryConfig().get('nope', 'fallback'), 'fallback')

    def test_to_dict_returns_copy(self):
        """to_dict 返回副本，修改不影响内部状态"""
        config = CeleryConfig()
        exported = config.to_dict()
        exported['timezone'] = 'UTC'
        self.assertEqual(config.get('timezone'), 'Asia/Shanghai')


class CeleryTestCase(unittest.TestCase):
    """公共基类：创建 Celery 实例并清理全局单例"""

    def setUp(self):
        self.celery = make_celery()

    def tearDown(self):
        Celery._instance = None


class TestCeleryInit(CeleryTestCase):
    """Celery 初始化"""

    def test_configures_broker_and_backend(self):
        """broker/backend 写入底层 Celery 配置"""
        self.assertEqual(self.celery._app.conf.broker_url, BROKER)
        self.assertEqual(self.celery._app.conf.result_backend, BACKEND)

    def test_default_queue_config(self):
        """默认队列配置生效"""
        self.assertEqual(self.celery._app.conf.task_default_queue, 'default')

    def test_extra_config_merged(self):
        """额外配置合并进底层"""
        celery = Celery(broker=BROKER, config={'task_time_limit': 600})
        self.assertEqual(celery._app.conf.task_time_limit, 600)
        Celery._instance = None

    def test_configure_from_app_config(self):
        """从 Litefs 应用配置读取 broker/backend"""
        app = Mock()
        app.config.celery_broker = 'redis://app-broker'
        app.config.celery_backend = 'redis://app-backend'
        app.config.celery_config = {'task_time_limit': 900}

        celery = Celery(app=app, broker=BROKER)
        self.assertEqual(celery._app.conf.broker_url, 'redis://app-broker')
        self.assertEqual(celery._app.conf.result_backend, 'redis://app-backend')
        self.assertEqual(celery._app.conf.task_time_limit, 900)
        Celery._instance = None

    def test_init_without_celery_raises(self):
        """未安装 celery 时抛 ImportError"""
        with patch('litefs.tasks.HAS_CELERY', False):
            with self.assertRaises(ImportError):
                Celery(broker=BROKER)

    def test_getattr_proxies_to_celery_app(self):
        """未定义属性代理到底层 Celery 应用"""
        self.assertEqual(self.celery.main, 'litefs_tasks')

    def test_getattr_private_raises(self):
        """私有属性不代理"""
        with self.assertRaises(AttributeError):
            self.celery._not_defined_anywhere

    def test_get_instance(self):
        """构造后全局单例指向当前实例"""
        self.assertIs(Celery.get_instance(), self.celery)
        self.assertIs(get_celery(), self.celery)


class TestCeleryTaskRegistration(CeleryTestCase):
    """任务注册"""

    def test_task_decorator_with_arguments(self):
        """@cel.task(name=..., queue=...) 注册任务"""
        @self.celery.task(name='send-mail', queue='emails')
        def send_mail(to):
            return to

        self.assertEqual(send_mail.name, 'send-mail')
        self.assertIn('send-mail', self.celery.get_registered_tasks())

    def test_task_decorator_direct(self):
        """@cel.task 直接装饰使用函数名"""
        @self.celery.task
        def add(x, y):
            return x + y

        self.assertEqual(add.name, 'add')
        self.assertIn('add', self.celery.get_registered_tasks())

    def test_task_with_limits(self):
        """time_limit/soft_time_limit 传入任务选项"""
        @self.celery.task(name='limited', time_limit=60, soft_time_limit=50)
        def limited():
            return None

        self.assertEqual(limited.name, 'limited')


class TestCelerySchedule(CeleryTestCase):
    """定时任务配置"""

    def test_schedule_with_task_name(self):
        """按任务名字符串配置定时任务"""
        self.celery.schedule('nightly', 'cleanup', 3600)
        entry = self.celery._app.conf.beat_schedule['nightly']
        self.assertEqual(entry['task'], 'cleanup')
        self.assertEqual(entry['schedule'], 3600)
        self.assertEqual(entry['args'], ())

    def test_schedule_with_callable(self):
        """传任务函数时取函数名"""
        def do_work():
            return None

        self.celery.schedule('job', do_work, 60, args=(1,), kwargs={'x': 2})
        entry = self.celery._app.conf.beat_schedule['job']
        self.assertEqual(entry['task'], 'do_work')
        self.assertEqual(entry['args'], (1,))
        self.assertEqual(entry['kwargs'], {'x': 2})


class TestCeleryTaskQueries(CeleryTestCase):
    """任务状态查询（控制面 mock）"""

    def setUp(self):
        super().setUp()
        # Control.inspect 是类属性（值为 Inspect 类），必须 patch 类属性
        self.control = self.celery._app.control
        inspector_patcher = patch('celery.app.control.Control.inspect')
        self.insp = inspector_patcher.start().return_value
        self.addCleanup(inspector_patcher.stop)
        self.control.revoke = Mock()

    def test_get_task_status_pending(self):
        """未知任务 ID 状态为 PENDING"""
        self.assertEqual(self.celery.get_task_status('unknown-id'), 'PENDING')

    def test_get_task_result(self):
        """get_task_result 返回任务结果"""
        with patch('litefs.tasks.AsyncResult') as mock_result:
            mock_result.return_value.get.return_value = 42
            self.assertEqual(self.celery.get_task_result('tid'), 42)

    def test_get_task_result_no_result(self):
        """结果对象为假值时返回 None"""
        with patch('litefs.tasks.AsyncResult', return_value=None):
            self.assertIsNone(self.celery.get_task_result('tid'))

    def test_revoke_task(self):
        """revoke_task 调用底层 control.revoke"""
        self.celery.revoke_task('tid', terminate=True)
        self.control.revoke.assert_called_once_with('tid', terminate=True)

    def test_get_active_tasks(self):
        """get_active_tasks 汇总各 worker 的活动任务"""
        self.insp.active.return_value = {
            'worker-1': [{'id': '1', 'name': 'task-a', 'args': (1,), 'kwargs': {}}],
            'worker-2': [{'id': '2', 'name': 'task-b', 'args': (), 'kwargs': {'x': 1}}],
        }
        active = self.celery.get_active_tasks()
        self.assertEqual(len(active), 2)
        self.assertEqual(active[0], {
            'id': '1', 'name': 'task-a', 'worker': 'worker-1', 'args': (1,), 'kwargs': {},
        })

    def test_get_active_tasks_empty(self):
        """无活动任务时返回空列表"""
        self.insp.active.return_value = None
        self.assertEqual(self.celery.get_active_tasks(), [])

    def test_get_queue_length(self):
        """get_queue_length 按 routing_key 统计"""
        self.insp.reserved.return_value = {
            'worker-1': [
                {'delivery_info': {'routing_key': 'emails'}},
                {'delivery_info': {'routing_key': 'default'}},
            ],
            'worker-2': [{'delivery_info': {'routing_key': 'emails'}}],
        }
        self.assertEqual(self.celery.get_queue_length('emails'), 2)
        self.assertEqual(self.celery.get_queue_length('default'), 1)

    def test_get_queue_length_empty(self):
        """无预留任务时长度为 0"""
        self.insp.reserved.return_value = None
        self.assertEqual(self.celery.get_queue_length(), 0)

    def test_health_check_with_workers(self):
        """有 worker 时健康状态为 healthy"""
        self.insp.stats.return_value = {'worker-1': {'total': {'t': 5}, 'pool': {'a': 1}}}
        self.insp.active.return_value = {'worker-1': [{'id': '1'}]}

        report = self.celery.health_check()
        self.assertEqual(report['status'], 'healthy')
        self.assertEqual(report['workers'][0]['name'], 'worker-1')
        self.assertEqual(report['active_tasks'], 1)

    def test_health_check_without_workers(self):
        """无 worker 时状态为 no_workers"""
        self.insp.stats.return_value = None
        self.insp.active.return_value = None

        report = self.celery.health_check()
        self.assertEqual(report['status'], 'no_workers')
        self.assertEqual(report['workers'], [])


class TestModuleLevelTask(unittest.TestCase):
    """模块级便捷装饰器"""

    def tearDown(self):
        Celery._instance = None

    def test_task_without_instance_raises(self):
        """未初始化全局实例时抛 RuntimeError"""
        Celery._instance = None
        with self.assertRaises(RuntimeError):
            task(lambda: None)

    def test_task_uses_global_instance(self):
        """task 委托给全局实例注册任务"""
        celery = Celery(broker=BROKER)

        def global_job():
            return None

        registered = task(name='global-task')(global_job)
        self.assertEqual(registered.name, 'global-task')
        self.assertIn('global-task', celery.get_registered_tasks())


if __name__ == '__main__':
    unittest.main()
