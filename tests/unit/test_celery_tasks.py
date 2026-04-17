#!/usr/bin/env python
# coding: utf-8

"""
Celery 任务队列集成单元测试
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestCeleryIntegration(unittest.TestCase):
    """Celery 集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.celery_available = True
        try:
            from litefs.tasks import HAS_CELERY
            self.celery_available = HAS_CELERY
        except ImportError:
            self.celery_available = False
    
    def test_celery_import(self):
        """测试 Celery 模块导入"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery, CeleryConfig, task, HAS_CELERY
        
        self.assertTrue(HAS_CELERY)
        self.assertIsNotNone(Celery)
        self.assertIsNotNone(CeleryConfig)
        self.assertIsNotNone(task)
    
    def test_celery_config(self):
        """测试 Celery 配置"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import CeleryConfig
        
        config = CeleryConfig()
        
        self.assertEqual(config.get('task_serializer'), 'json')
        self.assertEqual(config.get('result_serializer'), 'json')
        self.assertEqual(config.get('timezone'), 'Asia/Shanghai')
        self.assertTrue(config.get('enable_utc'))
        self.assertEqual(config.get('task_time_limit'), 300)
        
        custom_config = CeleryConfig({
            'task_time_limit': 600,
            'custom_option': 'value',
        })
        
        self.assertEqual(custom_config.get('task_time_limit'), 600)
        self.assertEqual(custom_config.get('custom_option'), 'value')
    
    def test_celery_config_to_dict(self):
        """测试配置转换为字典"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import CeleryConfig
        
        config = CeleryConfig()
        config_dict = config.to_dict()
        
        self.assertIsInstance(config_dict, dict)
        self.assertIn('broker_url', config_dict)
        self.assertIn('task_serializer', config_dict)
    
    @patch('litefs.tasks._Celery')
    def test_celery_initialization(self, mock_celery_class):
        """测试 Celery 初始化"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery
        
        mock_app = MagicMock()
        mock_app.config.celery_broker = 'redis://localhost:6379/0'
        mock_app.config.celery_backend = 'redis://localhost:6379/1'
        
        celery = Celery(
            app=mock_app,
            broker='redis://localhost:6379/0',
            backend='redis://localhost:6379/1',
        )
        
        self.assertIsNotNone(celery)
        mock_celery_class.assert_called_once()
    
    @patch('litefs.tasks._Celery')
    def test_task_decorator(self, mock_celery_class):
        """测试任务装饰器"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery
        
        mock_celery_app = MagicMock()
        mock_celery_class.return_value = mock_celery_app
        mock_celery_app.task = MagicMock(return_value=lambda f: f)
        
        celery = Celery(broker='memory://')
        
        @celery.task
        def test_task(x, y):
            return x + y
        
        self.assertIsNotNone(test_task)
        mock_celery_app.task.assert_called()
    
    @patch('litefs.tasks._Celery')
    def test_task_decorator_with_options(self, mock_celery_class):
        """测试带选项的任务装饰器"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery
        
        mock_celery_app = MagicMock()
        mock_celery_class.return_value = mock_celery_app
        mock_celery_app.task = MagicMock(return_value=lambda f: f)
        
        celery = Celery(broker='memory://')
        
        @celery.task(name='custom_task', queue='high_priority', max_retries=5)
        def custom_task(data):
            return data
        
        self.assertIsNotNone(custom_task)
        mock_celery_app.task.assert_called()
    
    @patch('litefs.tasks._Celery')
    def test_get_task_status(self, mock_celery_class):
        """测试获取任务状态"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery
        
        mock_celery_app = MagicMock()
        mock_celery_class.return_value = mock_celery_app
        
        celery = Celery(broker='memory://')
        
        with patch('litefs.tasks.AsyncResult') as mock_result:
            mock_result_instance = MagicMock()
            mock_result_instance.status = 'SUCCESS'
            mock_result.return_value = mock_result_instance
            
            status = celery.get_task_status('test-task-id')
            
            self.assertEqual(status, 'SUCCESS')
    
    @patch('litefs.tasks._Celery')
    def test_health_check(self, mock_celery_class):
        """测试健康检查"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery
        
        mock_celery_app = MagicMock()
        mock_celery_class.return_value = mock_celery_app
        
        mock_inspect = MagicMock()
        mock_inspect.stats.return_value = {
            'worker1': {'total': {'task1': 10}},
        }
        mock_inspect.active.return_value = {}
        mock_inspect.registered.return_value = {}
        
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        celery = Celery(broker='memory://')
        health = celery.health_check()
        
        self.assertIn('status', health)
        self.assertIn('workers', health)
    
    @patch('litefs.tasks._Celery')
    def test_get_registered_tasks(self, mock_celery_class):
        """测试获取已注册任务列表"""
        if not self.celery_available:
            self.skipTest("Celery not installed")
        
        from litefs.tasks import Celery
        
        mock_celery_app = MagicMock()
        mock_celery_class.return_value = mock_celery_app
        mock_celery_app.task = MagicMock(return_value=lambda f: f)
        
        celery = Celery(broker='memory://')
        
        @celery.task
        def task1():
            pass
        
        @celery.task
        def task2():
            pass
        
        tasks = celery.get_registered_tasks()
        
        self.assertIn('task1', tasks)
        self.assertIn('task2', tasks)


class TestCeleryConfigIntegration(unittest.TestCase):
    """Celery 配置集成测试"""
    
    def test_config_has_celery_options(self):
        """测试配置类包含 Celery 选项"""
        from litefs.config import Config
        
        config = Config()
        
        self.assertIsNone(config.celery_broker)
        self.assertIsNone(config.celery_backend)
        self.assertIsNone(config.celery_config)
    
    def test_config_with_celery_options(self):
        """测试带 Celery 选项的配置"""
        from litefs.config import Config
        
        config = Config(
            celery_broker='redis://localhost:6379/0',
            celery_backend='redis://localhost:6379/1',
            celery_config={'task_time_limit': 600},
        )
        
        self.assertEqual(config.celery_broker, 'redis://localhost:6379/0')
        self.assertEqual(config.celery_backend, 'redis://localhost:6379/1')
        self.assertEqual(config.celery_config, {'task_time_limit': 600})


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestCeleryIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCeleryConfigIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
