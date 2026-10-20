#!/usr/bin/env python
# coding: utf-8

"""
插件系统测试

覆盖 Plugin 基类配置读写、PluginManager 注册加载卸载、
PluginLoader 从文件系统加载插件。
"""

import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import Mock

from litefs.plugins.base import Plugin, PluginManager
from litefs.plugins.loader import PluginLoader


class DummyPlugin(Plugin):
    """测试用插件"""

    name = 'dummy'
    version = '1.0.0'
    description = '测试插件'
    dependencies = []

    def initialize(self):
        self.initialized = True


class DependentPlugin(Plugin):
    """依赖 dummy 的测试插件"""

    name = 'dependent'
    dependencies = ['dummy']

    def initialize(self):
        self.initialized = True


class FakeConfig:
    """模拟应用配置对象"""

    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class TestPluginBase(unittest.TestCase):
    """Plugin 基类"""

    def setUp(self):
        self.app = Mock()
        self.app.config = FakeConfig()

    def test_init_stores_app_and_config(self):
        """初始化保存 app 与 config 引用"""
        plugin = DummyPlugin(self.app)
        self.assertIs(plugin.app, self.app)
        self.assertIs(plugin.config, self.app.config)

    def test_shutdown_default_noop(self):
        """默认 shutdown 为空操作"""
        DummyPlugin(self.app).shutdown()

    def test_get_config_default(self):
        """未配置时 get_config 返回默认值"""
        plugin = DummyPlugin(self.app)
        self.assertIsNone(plugin.get_config('opt'))
        self.assertEqual(plugin.get_config('opt', 'fallback'), 'fallback')

    def test_set_and_get_config(self):
        """set_config 写入后可读回"""
        plugin = DummyPlugin(self.app)
        plugin.set_config('opt', 42)
        self.assertEqual(plugin.get_config('opt'), 42)


class TestPluginManager(unittest.TestCase):
    """PluginManager 插件管理"""

    def setUp(self):
        self.app = Mock()
        self.app.config = FakeConfig()
        self.manager = PluginManager(self.app)

    def test_register_and_load(self):
        """注册并加载插件"""
        self.manager.register(DummyPlugin)
        self.manager.load('dummy')
        self.assertTrue(self.manager.has_plugin('dummy'))
        plugin = self.manager.get_plugin('dummy')
        self.assertIsInstance(plugin, DummyPlugin)
        self.assertTrue(plugin.initialized)

    def test_register_rejects_non_plugin(self):
        """非 Plugin 子类注册抛 TypeError"""
        with self.assertRaises(TypeError):
            self.manager.register(object)

    def test_register_requires_name(self):
        """未设置 name 的插件注册抛 ValueError"""
        class NoName(Plugin):
            name = ''

            def initialize(self):
                pass

        with self.assertRaises(ValueError):
            self.manager.register(NoName)

    def test_load_unregistered_raises(self):
        """加载未注册插件抛 ValueError"""
        with self.assertRaises(ValueError):
            self.manager.load('ghost')

    def test_load_missing_dependency_raises(self):
        """依赖未注册时抛 ValueError"""
        self.manager.register(DependentPlugin)
        with self.assertRaises(ValueError):
            self.manager.load('dependent')

    def test_load_resolves_dependencies(self):
        """依赖插件自动先加载"""
        self.manager.register(DummyPlugin)
        self.manager.register(DependentPlugin)
        self.manager.load('dependent')
        names = [p.name for p in self.manager.get_all_plugins()]
        self.assertEqual(names, ['dummy', 'dependent'])

    def test_load_all(self):
        """load_all 加载全部注册插件"""
        self.manager.register(DummyPlugin)
        self.manager.register(DependentPlugin)
        self.manager.load_all()
        self.assertEqual(len(self.manager.get_all_plugins()), 2)

    def test_unload_calls_shutdown(self):
        """unload 关闭并移除插件"""
        self.manager.register(DummyPlugin)
        self.manager.load('dummy')
        plugin = self.manager.get_plugin('dummy')
        plugin.shutdown = Mock()
        self.manager.unload('dummy')
        self.assertFalse(self.manager.has_plugin('dummy'))
        plugin.shutdown.assert_called_once()

    def test_unload_missing_plugin_noop(self):
        """卸载不存在的插件不崩溃"""
        self.manager.unload('nothing')

    def test_unload_all_reverse_order(self):
        """unload_all 逆序关闭全部插件"""
        order = []

        class Tracker(Plugin):
            def __init__(self, app):
                super().__init__(app)
                self.name = f'tracker-{self._seq}'

            def initialize(self):
                pass

            def shutdown(self):
                order.append(self.name)

        first = type('First', (Tracker,), {'_seq': 1, 'name': 'tracker-1'})
        second = type('Second', (Tracker,), {'_seq': 2, 'name': 'tracker-2'})

        self.manager.register(first)
        self.manager.register(second)
        self.manager.load_all()
        self.manager.unload_all()
        self.assertEqual(order, ['tracker-2', 'tracker-1'])
        self.assertEqual(self.manager.get_all_plugins(), [])

    def test_get_plugin_missing_returns_none(self):
        """获取未加载插件返回 None"""
        self.assertIsNone(self.manager.get_plugin('nothing'))


class TestPluginLoader(unittest.TestCase):
    """PluginLoader 文件系统加载"""

    def setUp(self):
        self.app = Mock()
        self.app.config = FakeConfig()
        self.loader = PluginLoader(self.app)
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.plugin_root = Path(self.tmpdir.name)

    def _write_plugin_file(self, filename, content):
        path = self.plugin_root / filename
        path.write_text(textwrap.dedent(content), encoding='utf-8')
        return path

    def _write_package_plugin(self, dirname, class_name, plugin_name):
        pkg = self.plugin_root / dirname
        pkg.mkdir()
        (pkg / '__init__.py').write_text(textwrap.dedent(f"""
            from litefs.plugins.base import Plugin

            class {class_name}(Plugin):
                name = '{plugin_name}'

                def initialize(self):
                    pass
        """), encoding='utf-8')
        return pkg

    def test_add_plugin_dir_deduplicates(self):
        """重复添加插件目录会去重"""
        self.loader.add_plugin_dir('/a')
        self.loader.add_plugin_dir('/a')
        self.assertEqual(self.loader.plugin_dirs, ['/a'])

    def test_load_plugins_from_file(self):
        """从 .py 文件加载插件类"""
        self._write_plugin_file('standalone.py', """
            from litefs.plugins.base import Plugin

            class StandalonePlugin(Plugin):
                name = 'standalone'

                def initialize(self):
                    pass
        """)
        self.loader.add_plugin_dir(str(self.plugin_root))
        plugins = self.loader.load_plugins()
        self.assertIn('standalone', plugins)

    def test_load_plugins_from_package(self):
        """从包含 __init__.py 的目录加载插件类"""
        self._write_package_plugin('mypkg', 'PkgPlugin', 'pkg-plugin')
        self.loader.add_plugin_dir(str(self.plugin_root))
        plugins = self.loader.load_plugins()
        self.assertIn('pkg-plugin', plugins)

    def test_missing_dir_skipped(self):
        """不存在的目录被跳过"""
        self.loader.add_plugin_dir('/nonexistent-dir-xyz')
        self.assertEqual(self.loader.load_plugins(), {})

    def test_broken_plugin_file_reported(self):
        """语法错误的插件文件打印错误且不崩溃"""
        self._write_plugin_file('broken.py', 'def broken(:\n    pass')
        self.loader.add_plugin_dir(str(self.plugin_root))
        plugins = self.loader.load_plugins()
        self.assertEqual(plugins, {})

    def test_init_py_file_not_loaded_as_plugin(self):
        """根目录 __init__.py 不作为插件文件加载"""
        self._write_plugin_file('__init__.py', 'X = 1')
        self.loader.add_plugin_dir(str(self.plugin_root))
        self.assertEqual(self.loader.load_plugins(), {})


if __name__ == '__main__':
    unittest.main()
