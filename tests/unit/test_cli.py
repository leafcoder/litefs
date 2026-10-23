#!/usr/bin/env python
# coding: utf-8

"""
CLI 工具测试

覆盖 litefs.cli 的 runserver 中间件配置驱动解析与 Litefs 应用创建时
按 ``middleware`` 配置自动挂载内置中间件的框架行为。
"""

import os
import unittest
from unittest import mock

from litefs.cli import _RUNSERVER_MIDDLEWARE, _parse_middleware_selection


class TestParseMiddlewareSelection(unittest.TestCase):
    """测试 runserver 中间件选择解析（配置驱动）"""

    def test_none_enables_none(self):
        """配置缺失（None）不启用任何中间件"""
        self.assertEqual(_parse_middleware_selection(None), [])

    def test_list_from_config_yaml(self):
        """config.yaml 的列表形式按配置顺序解析"""
        result = _parse_middleware_selection(['logging', 'security', 'cors'])
        self.assertEqual(result, ['logging', 'security', 'cors'])

    def test_csv_string_from_env(self):
        """环境变量逗号分隔字符串形式解析"""
        result = _parse_middleware_selection('logging,cors')
        self.assertEqual(result, ['logging', 'cors'])

    def test_whitespace_and_empty_segments_tolerated(self):
        """容忍列表元素与 CSV 段中的空白与空段"""
        self.assertEqual(
            _parse_middleware_selection([' cors ', '', ' logging ']),
            ['cors', 'logging'],
        )
        self.assertEqual(
            _parse_middleware_selection(' cors , , logging '),
            ['cors', 'logging'],
        )

    def test_empty_string_enables_none(self):
        """空字符串不启用任何中间件"""
        self.assertEqual(_parse_middleware_selection(''), [])

    def test_empty_list_enables_none(self):
        """空列表不启用任何中间件"""
        self.assertEqual(_parse_middleware_selection([]), [])

    def test_unknown_name_exits(self):
        """未知中间件名称退出并给出可选值提示"""
        with self.assertRaises(SystemExit) as ctx:
            _parse_middleware_selection('cors,bogus')
        self.assertEqual(ctx.exception.code, 1)

    def test_whitelist_covers_all_choices(self):
        """白名单常量与文档口径一致"""
        self.assertEqual(
            _RUNSERVER_MIDDLEWARE, ('logging', 'security', 'cors', 'health')
        )


class TestMiddlewareConfig(unittest.TestCase):
    """测试 middleware 配置键（Config 默认值与环境变量覆盖）"""

    def test_default_config_middleware_is_none(self):
        """DEFAULT_CONFIG 中 middleware 默认为 None（未配置不挂载，零行为变化）"""
        from litefs.config import Config

        self.assertIsNone(Config.DEFAULT_CONFIG['middleware'])

    def test_default_middleware_mounts_nothing(self):
        """默认构造的应用不自动挂载任何配置中间件"""
        from litefs.core import Litefs

        app = Litefs()
        self.assertEqual(
            app.middleware_manager.get_middleware_instances(app), []
        )

    def test_env_var_overrides_middleware(self):
        """LITEFS_MIDDLEWARE 环境变量覆盖配置（CSV 字符串，由框架归一化）"""
        from litefs.config import Config

        original = os.environ.get('LITEFS_MIDDLEWARE')
        os.environ['LITEFS_MIDDLEWARE'] = 'logging,cors'
        try:
            config = Config()
            self.assertEqual(config.get('middleware'), 'logging,cors')
        finally:
            if original is None:
                os.environ.pop('LITEFS_MIDDLEWARE', None)
            else:
                os.environ['LITEFS_MIDDLEWARE'] = original


class TestConfigMiddlewareMount(unittest.TestCase):
    """测试 Litefs 应用创建时按 middleware 配置自动挂载内置中间件"""

    def test_mount_by_config_list_with_section_kwargs(self):
        """列表配置按序挂载，同名配置段作为构造参数注入"""
        from litefs.core import Litefs

        app = Litefs(
            middleware=['cors', 'health'],
            cors={'allow_origins': ['*']},
            health_check={'path': '/custom/health'},
        )
        instances = app.middleware_manager.get_middleware_instances(app)
        by_type = {type(inst).__name__: inst for inst in instances}
        self.assertEqual(
            list(by_type), ['CORSMiddleware', 'HealthCheck']
        )
        self.assertEqual(by_type['CORSMiddleware'].allow_origins, ['*'])
        self.assertEqual(by_type['HealthCheck'].path, '/custom/health')

    def test_mount_by_csv_string(self):
        """逗号分隔字符串配置归一化后按序挂载"""
        from litefs.core import Litefs

        app = Litefs(middleware='logging,security')
        names = [
            type(inst).__name__
            for inst in app.middleware_manager.get_middleware_instances(app)
        ]
        self.assertEqual(names, ['LoggingMiddleware', 'SecurityMiddleware'])

    def test_unknown_name_raises_value_error(self):
        """未知中间件名称在应用创建时抛出 ValueError"""
        from litefs.core import Litefs

        with self.assertRaises(ValueError) as ctx:
            Litefs(middleware=['bogus'])
        self.assertIn('bogus', str(ctx.exception))

    def test_empty_list_mounts_nothing(self):
        """空列表显式关闭全部中间件"""
        from litefs.core import Litefs

        app = Litefs(middleware=[])
        self.assertEqual(
            app.middleware_manager.get_middleware_instances(app), []
        )


class TestRunserverMiddlewareDefault(unittest.TestCase):
    """测试 runserver 未配置时默认启用全部内置中间件（历史行为兼容）"""

    def _run_runserver(self):
        from litefs import cli

        with mock.patch('litefs.core.Litefs') as mock_litefs:
            cli.runserver()
        return mock_litefs.call_args.kwargs

    def test_default_all_enabled(self):
        """未配置 middleware 时默认四件套全开"""
        kwargs = self._run_runserver()
        self.assertEqual(
            kwargs['middleware'],
            ['logging', 'security', 'cors', 'health'],
        )

    def test_env_var_selection(self):
        """环境变量选择的子集生效"""
        original = os.environ.get('LITEFS_MIDDLEWARE')
        os.environ['LITEFS_MIDDLEWARE'] = 'cors'
        try:
            kwargs = self._run_runserver()
            self.assertEqual(kwargs['middleware'], ['cors'])
        finally:
            if original is None:
                os.environ.pop('LITEFS_MIDDLEWARE', None)
            else:
                os.environ['LITEFS_MIDDLEWARE'] = original


class TestRunserverSignature(unittest.TestCase):
    """测试 runserver 命令签名（argh 据此生成 CLI 参数）"""

    def test_middleware_not_a_cli_argument(self):
        """中间件选择仅由配置驱动，不暴露 CLI 参数"""
        import inspect

        from litefs.cli import runserver

        sig = inspect.signature(runserver)
        self.assertNotIn('middleware', sig.parameters)
        self.assertNotIn('no_middleware', sig.parameters)
        # 既有 CLI 参数保持不变
        for name in ('host', 'port', 'config', 'debug', 'reload', 'workers'):
            self.assertIn(name, sig.parameters)


if __name__ == '__main__':
    unittest.main()
