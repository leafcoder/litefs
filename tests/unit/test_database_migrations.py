#!/usr/bin/env python
# coding: utf-8

"""
数据库迁移测试

覆盖 AlembicManager 的初始化、迁移脚本生成、升级/回退/查询等能力，
可选依赖缺失时的异常提示，以及 litefs db 命令组的注册情况。
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from litefs.database.migrations import (
    ALEMBIC_INI_NAME,
    AlembicManager,
    AlembicNotAvailable,
    detect_models_imports,
    load_alembic,
)


class TestAlembicNotAvailable(unittest.TestCase):
    """可选依赖缺失场景"""

    def test_load_alembic_raises(self):
        """未安装 alembic 时抛出明确异常"""
        with patch.dict(sys.modules, {"alembic": None, "alembic.command": None}):
            with self.assertRaises(AlembicNotAvailable) as ctx:
                load_alembic()

        self.assertIn("alembic", str(ctx.exception))

    def test_init_raises(self):
        """迁移命令在依赖缺失时抛出明确异常"""
        with patch.dict(sys.modules, {"alembic": None, "alembic.command": None}):
            manager = AlembicManager()
            with self.assertRaises(AlembicNotAvailable):
                manager.init()


class TestAlembicManager(unittest.TestCase):
    """AlembicManager 基础能力"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = self.temp_dir.name
        self.db_path = os.path.join(self.root, "test.db")
        self.manager = AlembicManager(
            database_url=f"sqlite:///{self.db_path}",
            project_root=self.root,
        )

    # ==================== 属性 ====================

    def test_database_url_explicit(self):
        """显式传入的数据库 URL 优先"""
        self.assertEqual(self.manager.database_url, f"sqlite:///{self.db_path}")

    def test_database_url_from_env(self):
        """环境变量 DATABASE_URL 次优先"""
        manager = AlembicManager(project_root=self.root)
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///from_env.db"}):
            self.assertEqual(manager.database_url, "sqlite:///from_env.db")

    def test_migrations_path(self):
        """迁移目录基于项目根目录"""
        self.assertEqual(
            self.manager.migrations_path, os.path.join(self.root, "migrations")
        )

    def test_ini_path(self):
        """ini 路径基于项目根目录"""
        self.assertEqual(
            self.manager.ini_path, os.path.join(self.root, ALEMBIC_INI_NAME)
        )

    def test_is_initialized(self):
        """初始化前 is_initialized 为 False"""
        self.assertFalse(self.manager.is_initialized)

    # ==================== 初始化 ====================

    def test_init_creates_structure(self):
        """初始化生成 ini、env.py 与 versions 目录"""
        code, output = self.manager.init()

        self.assertEqual(code, 0)
        self.assertIn("迁移环境初始化完成", output)
        self.assertTrue(os.path.exists(os.path.join(self.root, ALEMBIC_INI_NAME)))
        self.assertTrue(os.path.exists(os.path.join(self.root, "migrations", "env.py")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, "migrations", "versions")))
        self.assertTrue(self.manager.is_initialized)

    def test_generated_env_py_uses_base_metadata(self):
        """生成的 env.py 指向 Base.metadata，保证 autogenerate 可用"""
        self.manager.init()

        with open(os.path.join(self.root, "migrations", "env.py"), encoding="utf-8") as f:
            content = f.read()

        self.assertIn("target_metadata = Base.metadata", content)
        self.assertIn("from litefs.database.models import Base", content)
        self.assertNotIn("{models_imports}", content)

    def test_init_twice_returns_error(self):
        """重复初始化返回错误码与提示"""
        self.manager.init()
        code, output = self.manager.init()

        self.assertEqual(code, 1)
        self.assertIn("迁移环境已存在", output)

    # ==================== 未初始化保护 ====================

    def test_migrate_requires_initialization(self):
        """未初始化时拒绝执行迁移"""
        code, output = self.manager.migrate("test")

        self.assertEqual(code, 1)
        self.assertIn("迁移环境未初始化", output)

    def test_upgrade_requires_initialization(self):
        """未初始化时拒绝升级"""
        code, output = self.manager.upgrade()

        self.assertEqual(code, 1)
        self.assertIn("迁移环境未初始化", output)

    def test_current_requires_initialization(self):
        """未初始化时拒绝查询"""
        code, output = self.manager.current()

        self.assertEqual(code, 1)
        self.assertIn("迁移环境未初始化", output)

    # ==================== 迁移全流程 ====================

    def test_full_migration_flow(self):
        """init -> migrate -> upgrade -> current -> history -> downgrade 全流程"""
        self.assertEqual(self.manager.init()[0], 0)

        code, output = self.manager.migrate("init tables")
        self.assertEqual(code, 0)
        self.assertIn("迁移脚本已生成", output)

        versions_dir = os.path.join(self.root, "migrations", "versions")
        scripts = [f for f in os.listdir(versions_dir) if f.endswith(".py")]
        self.assertEqual(len(scripts), 1)

        code, output = self.manager.upgrade()
        self.assertEqual(code, 0)
        self.assertIn("已升级到版本", output)

        code, output = self.manager.current()
        self.assertEqual(code, 0)
        self.assertIn("Current revision", output)

        code, output = self.manager.history()
        self.assertEqual(code, 0)
        self.assertIn("init tables", output)

        code, output = self.manager.downgrade()
        self.assertEqual(code, 0)
        self.assertIn("已回退到版本", output)

    def test_upgrade_creates_database_file(self):
        """升级后数据库文件被创建"""
        self.manager.init()
        self.manager.migrate("init tables")
        self.manager.upgrade()

        self.assertTrue(os.path.exists(self.db_path))


class TestDetectModelsImports(unittest.TestCase):
    """模型模块探测"""

    def test_detect_models_file(self):
        """根目录存在 models.py 时生成导入语句"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "models.py"), "w", encoding="utf-8") as f:
                f.write("# models\n")

            self.assertEqual(detect_models_imports(tmpdir), ["import models"])

    def test_detect_models_package(self):
        """根目录存在 models 包时生成导入语句"""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "models"))
            with open(
                os.path.join(tmpdir, "models", "__init__.py"), "w", encoding="utf-8"
            ) as f:
                f.write("# models package\n")

            self.assertEqual(detect_models_imports(tmpdir), ["import models"])

    def test_detect_nothing(self):
        """未找到模型模块时返回空列表"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(detect_models_imports(tmpdir), [])


class TestDatabaseCli(unittest.TestCase):
    """litefs db 命令组注册"""

    def test_db_subcommands_registered(self):
        """嵌套子命令全部注册"""
        from litefs.cli_db import DB_SUBCOMMANDS

        names = {func.__name__ for func in DB_SUBCOMMANDS}
        self.assertEqual(
            names,
            {
                "db_sub_init",
                "db_sub_migrate",
                "db_sub_upgrade",
                "db_sub_downgrade",
                "db_sub_current",
                "db_sub_history",
                "db_sub_create_tables",
            },
        )

    def test_legacy_flat_commands_preserved(self):
        """旧的扁平入口保留"""
        from litefs.cli import db_init, db_migrate

        self.assertTrue(callable(db_init))
        self.assertTrue(callable(db_migrate))


if __name__ == "__main__":
    unittest.main()
