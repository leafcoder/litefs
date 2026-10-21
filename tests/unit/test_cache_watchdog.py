#!/usr/bin/env python
# coding: utf-8

"""
文件监控事件处理器测试

覆盖 FileEventHandler 的重载判定、冷却控制与各类文件系统事件处理。
"""

import unittest
from unittest.mock import Mock


def make_app(server=None):
    """构造带 caches/logger/server 的应用 Mock"""
    app = Mock(spec=[])
    app.logger = Mock()
    app.caches = Mock()
    app.caches.data = {}
    app.server = server
    app._need_reload = False
    return app


class TestShouldReload(unittest.TestCase):
    """_should_reload 重载判定"""

    def test_python_and_config_files_reload(self):
        """Python 源文件与配置文件触发重载"""
        from litefs.cache.cache import FileEventHandler
        handler = FileEventHandler(make_app())
        for path in ('app.py', 'conf/settings.yaml', 'config.yml', 'a.json', 'b.ini', 'c.conf'):
            self.assertTrue(handler._should_reload(path), path)

    def test_excluded_files_no_reload(self):
        """日志、编译产物、备份与临时文件不触发重载"""
        from litefs.cache.cache import FileEventHandler
        handler = FileEventHandler(make_app())
        for path in ('app.log', 'a.pyc', 'lib.so', 'b.pyo', 'f.py~', 'x.bak',
                     'y.tmp', 'z.swp', 'w.orig', 'foo~bar.py'):
            self.assertFalse(handler._should_reload(path), path)

    def test_special_dirs_no_reload(self):
        """__pycache__/.git/.svn/.hg/node_modules 目录不触发重载"""
        from litefs.cache.cache import FileEventHandler
        handler = FileEventHandler(make_app())
        for path in ('p/__pycache__/a.py', '__pycache__/a.py', '.git/x', 'p/.git/config',
                     'p/.svn/base', 'p/.hg/data', 'p/node_modules/lib.py'):
            self.assertFalse(handler._should_reload(path), path)

    def test_other_files_no_reload(self):
        """其他类型文件不触发重载"""
        from litefs.cache.cache import FileEventHandler
        handler = FileEventHandler(make_app())
        self.assertFalse(handler._should_reload('data.txt'))


class TestReloadControl(unittest.TestCase):
    """重载冷却控制"""

    def test_can_reload_cooldown(self):
        """冷却期内只允许触发一次"""
        from litefs.cache.cache import FileEventHandler
        handler = FileEventHandler(make_app())
        self.assertTrue(handler._can_reload_now())
        self.assertFalse(handler._can_reload_now())

    def test_add_monitored_file(self):
        """添加监控文件记录"""
        from litefs.cache.cache import FileEventHandler
        handler = FileEventHandler(make_app())
        handler.add_monitored_file('/x/app.py')
        self.assertIn('/x/app.py', handler._monitored_files)


class TestFileEvents(unittest.TestCase):
    """文件系统事件处理"""

    def setUp(self):
        self.app = make_app(server=Mock())
        from litefs.cache.cache import FileEventHandler
        self.handler = FileEventHandler(self.app)

    def _event(self, src_path, dest_path=None):
        event = Mock()
        event.src_path = src_path
        event.dest_path = dest_path
        return event

    def test_on_modified_python_file_reloads(self):
        """修改 .py 文件标记重载并关闭服务器"""
        self.handler.on_modified(self._event('/x/app.py'))
        self.assertTrue(self.app._need_reload)
        self.app.server.server_close.assert_called_once()
        self.assertEqual(self.app.caches.data, {})

    def test_on_modified_excluded_file_ignored(self):
        """修改日志文件不触发任何动作"""
        self.handler.on_modified(self._event('/x/app.log'))
        self.assertFalse(self.app._need_reload)
        self.app.server.server_close.assert_not_called()

    def test_on_created_and_deleted_reload(self):
        """创建与删除 .py 文件触发重载"""
        self.handler.on_created(self._event('/x/new.py'))
        self.assertTrue(self.app._need_reload)
        # 冷却期内第二次不重复执行，但仍不报错
        self.handler.on_deleted(self._event('/x/new.py'))

    def test_on_moved_python_file_reloads(self):
        """移动 .py 文件触发重载"""
        self.handler.on_moved(self._event('/x/a.py', '/x/b.py'))
        self.assertTrue(self.app._need_reload)

    def test_on_moved_backup_skipped(self):
        """编辑器保存产生的备份移动不触发重载"""
        self.handler.on_moved(self._event('/x/a.py', '/x/a.py~'))
        self.assertFalse(self.app._need_reload)

    def test_on_moved_non_reload_types_ignored(self):
        """移动非监控类型文件提前返回，不做任何动作"""
        self.app.caches.data['k'] = 'v'
        self.handler.on_moved(self._event('/x/a.log', '/x/b.log'))
        self.assertFalse(self.app._need_reload)
        self.assertEqual(self.app.caches.data, {'k': 'v'})

    def test_reload_without_server(self):
        """无 server 属性时重载不崩溃"""
        from litefs.cache.cache import FileEventHandler
        app = make_app()
        del app.server
        handler = FileEventHandler(app)
        handler.on_modified(self._event('/x/app.py'))
        self.assertTrue(app._need_reload)

    def test_reload_server_close_exception_swallowed(self):
        """server_close 抛异常被吞掉"""
        self.app.server.server_close.side_effect = RuntimeError('closed')
        self.handler.on_modified(self._event('/x/app.py'))
        self.assertTrue(self.app._need_reload)


if __name__ == '__main__':
    unittest.main()
