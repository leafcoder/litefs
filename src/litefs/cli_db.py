#!/usr/bin/env python
# coding: utf-8

"""
数据库管理 CLI 命令

提供 `litefs db` 命令组下的全部子命令：
- init / migrate / upgrade / downgrade / current / history：基于 Alembic 的迁移管理
- create-tables：直接创建全部数据表（不生成迁移脚本）
"""

import os
import sys
from typing import Any, Optional

import argh


def create_tables() -> None:
    """
    创建数据库表

    通过项目的 app.py 获取数据库引擎，使用模型元数据创建全部数据表。
    """
    print("初始化数据库...")

    try:
        # 尝试导入项目的 app 和 models
        if os.path.exists('app.py'):
            import importlib.util
            spec = importlib.util.spec_from_file_location("app", "app.py")
            if spec is None or spec.loader is None:
                print("警告: 无法加载 app.py")
                return
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)

            app = getattr(app_module, 'app', None)

            if app and hasattr(app, 'db'):
                # 创建所有表
                from litefs.database.models import Base
                Base.metadata.create_all(bind=app.db.engine)
                print("数据库表创建成功!")
            else:
                print("警告: 未找到数据库配置")
        else:
            print("错误: 当前目录不是 Litefs 项目")
            print("请在项目根目录运行此命令")
            sys.exit(1)

    except Exception as e:
        print(f"错误: 数据库初始化失败: {e}")
        sys.exit(1)


def load_project_database_url() -> Optional[str]:
    """
    从项目的 app.py 中读取数据库连接 URL

    Returns:
        数据库连接 URL，未找到时返回 None
    """
    if not os.path.exists('app.py'):
        return None

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("app", "app.py")
        if spec is None or spec.loader is None:
            return None
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)

        app = getattr(app_module, 'app', None)
        if app and hasattr(app, 'db'):
            return str(app.db.database_url)
    except Exception:
        return None

    return None


def build_migration_manager() -> Any:
    """
    构建迁移管理器

    优先使用项目 app.py 中配置的数据库连接 URL。

    Returns:
        AlembicManager 实例
    """
    from litefs.database.migrations import AlembicManager, detect_models_imports

    return AlembicManager(
        database_url=load_project_database_url(),
        models_imports=detect_models_imports(),
    )


def run_migration(action: str, *args: Any, **kwargs: Any) -> None:
    """
    执行迁移操作并输出结果

    Args:
        action: 要执行的迁移方法名（init/migrate/upgrade/downgrade/current/history）
        *args: 传递给迁移方法的 positional 参数
        **kwargs: 传递给迁移方法的 keyword 参数
    """
    from litefs.database.migrations import AlembicNotAvailable

    try:
        manager = build_migration_manager()
        code, output = getattr(manager, action)(*args, **kwargs)
    except AlembicNotAvailable as e:
        print(f"错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: 迁移操作失败: {e}")
        sys.exit(1)

    if output:
        print(output, end="" if output.endswith("\n") else "\n")

    if code != 0:
        sys.exit(code)


@argh.named('init')
def db_sub_init(directory: str = "migrations"):
    """
    初始化 Alembic 迁移环境

    生成 alembic.ini 配置与迁移脚本目录。

    Args:
        directory: 迁移脚本目录，默认为 migrations
    """
    run_migration('init', directory)


@argh.named('migrate')
def db_sub_migrate(message: str = "auto migration"):
    """
    生成数据库迁移脚本

    对比模型与数据库结构，自动生成差异迁移脚本。

    Args:
        message: 迁移说明
    """
    run_migration('migrate', message)


@argh.named('upgrade')
def db_sub_upgrade(revision: str = "head"):
    """
    升级数据库到指定版本

    Args:
        revision: 目标版本，默认为 head（最新版本）
    """
    run_migration('upgrade', revision)


@argh.named('downgrade')
def db_sub_downgrade(revision: str = "-1"):
    """
    回退数据库到指定版本

    Args:
        revision: 目标版本，默认为 -1（回退一个版本）
    """
    run_migration('downgrade', revision)


@argh.named('current')
def db_sub_current():
    """
    显示当前数据库版本
    """
    run_migration('current')


@argh.named('history')
def db_sub_history():
    """
    显示数据库迁移历史
    """
    run_migration('history')


@argh.named('create-tables')
def db_sub_create_tables():
    """
    创建全部数据表（不生成迁移脚本）
    """
    create_tables()


# `litefs db` 命令组的全部子命令
DB_SUBCOMMANDS = [
    db_sub_init,
    db_sub_migrate,
    db_sub_upgrade,
    db_sub_downgrade,
    db_sub_current,
    db_sub_history,
    db_sub_create_tables,
]


__all__ = [
    "DB_SUBCOMMANDS",
    "build_migration_manager",
    "create_tables",
    "db_sub_create_tables",
    "db_sub_current",
    "db_sub_downgrade",
    "db_sub_history",
    "db_sub_init",
    "db_sub_migrate",
    "db_sub_upgrade",
    "load_project_database_url",
    "run_migration",
]
