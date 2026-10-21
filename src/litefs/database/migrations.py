#!/usr/bin/env python
# coding: utf-8

"""
数据库迁移模块

基于 Alembic 封装数据库版本化迁移能力，提供 init / migrate / upgrade /
downgrade / current / history 六类操作。

设计要点：
- alembic 为可选依赖，本模块**顶层不导入**它，
  全部导入均通过 :func:`load_alembic` 懒加载。
- 每个方法返回 ``(exit_code, output)`` 二元组，
  由调用方（CLI）决定如何展示输出与退出码。
"""

import contextlib
import io
import os
from typing import Any, List, Optional, Tuple

# 安装指引
_INSTALL_HINT = (
    "未安装 alembic，请执行 pip install 'litefs[db]' 或 pip install alembic"
)

# 默认的迁移脚本目录名
DEFAULT_SCRIPT_LOCATION = "migrations"

# Alembic 生成的配置文件名
ALEMBIC_INI_NAME = "alembic.ini"

# 自定义 env.py 模板
#
# 与 Alembic 默认模板的差异：
# 1. 不调用 fileConfig —— 它会劫持宿主应用的 root logger，
#    这里只配置 alembic 命名空间的日志。
# 2. target_metadata 指向 LiteFS 的 Base.metadata，用于 autogenerate 自动对比。
# 3. 显式将项目根目录加入 sys.path，保证能导入用户自定义的 models 模块。
# 4. SQLite 下启用 render_as_batch，自动改写不支持 ALTER TABLE 的操作。
_ENV_PY_TEMPLATE = '''"""Alembic 迁移环境（由 LiteFS 自动生成，请按需调整）。

本文件由 `litefs db init` 生成。
- target_metadata 指向 LiteFS 的 Base.metadata，autogenerate 依赖它对比模型差异。
- 用户自定义的模型模块需在下方显式导入，否则 autogenerate 无法感知。
"""

import logging
import os
import sys

from sqlalchemy import engine_from_config, pool

from alembic import context

# Alembic 配置对象
config = context.config

# 项目根目录（alembic.ini 所在目录）
project_root = os.path.dirname(os.path.abspath(config.config_file_name)) \\
    if config.config_file_name else os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 日志配置：仅作用于 alembic 命名空间，避免劫持宿主应用的 root logger
_alembic_logger = logging.getLogger("alembic")
if not any(not isinstance(h, logging.NullHandler) for h in _alembic_logger.handlers):
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("%(levelname)-5.5s [%(name)s] %(message)s")
    )
    _alembic_logger.addHandler(_handler)
_alembic_logger.setLevel(logging.INFO)

from litefs.database.models import Base  # noqa: E402

# 用户自定义模型模块的导入语句
__MODELS_IMPORTS__

# autogenerate 使用的模型元数据
target_metadata = Base.metadata


def run_migrations_offline():
    """离线模式：仅生成 SQL 脚本，不连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """在线模式：连接数据库执行迁移。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''


class AlembicNotAvailable(ImportError):
    """alembic 未安装时抛出的异常"""


class _Utf8StringIO(io.StringIO):
    """
    声明 UTF-8 编码的字符串缓冲区

    alembic 的 ``write_outstream`` 依据流的 ``encoding`` 属性选择编码，
    默认取 ``ascii`` 会把中文替换为 ``?``，此处显式声明 UTF-8。
    """

    encoding = "utf-8"


def load_alembic() -> Any:
    """
    懒加载 alembic 模块

    同时导入 ``alembic.command`` 子模块，使其可通过 ``alembic.command``
    直接访问，无需调用方重复导入。

    Returns:
        alembic 模块对象

    Raises:
        AlembicNotAvailable: 未安装 alembic 时抛出
    """
    try:
        import alembic  # noqa: PLC0415  # 延迟导入，避免强制依赖
        import alembic.command  # noqa: PLC0415  # noqa: F401  # 绑定到父包命名空间
    except ImportError as exc:
        raise AlembicNotAvailable(_INSTALL_HINT) from exc
    return alembic


class AlembicManager:
    """
    Alembic 迁移管理器

    使用示例:
        manager = AlembicManager(database_url='sqlite:///app.db')
        code, output = manager.migrate('add user table')
        print(output)
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        script_location: str = DEFAULT_SCRIPT_LOCATION,
        base_metadata: Optional[Any] = None,
        models_imports: Optional[List[str]] = None,
        project_root: Optional[str] = None,
    ) -> None:
        """
        初始化迁移管理器

        Args:
            database_url: 数据库连接 URL，None 时自动探测
            script_location: 迁移脚本目录（相对项目根目录）
            base_metadata: autogenerate 使用的模型元数据，None 时使用 LiteFS Base
            models_imports: 用户自定义模型模块的导入语句列表
            project_root: 项目根目录，None 时使用当前工作目录
        """
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.script_location = script_location
        self.models_imports = list(models_imports or [])
        self._base_metadata = base_metadata
        self._database_url = database_url

    # ==================== 属性 ====================

    @property
    def database_url(self) -> str:
        """
        获取数据库连接 URL

        优先级：
        1. 构造时显式传入的参数
        2. 环境变量 DATABASE_URL
        3. LiteFS 配置中的 database_url
        4. 默认值 sqlite:///litefs.db

        Returns:
            数据库连接 URL
        """
        if self._database_url:
            return self._database_url

        env_url = os.environ.get('DATABASE_URL')
        if env_url:
            return env_url

        try:
            from ..config import Config
            config_url = getattr(Config(), 'database_url', None)
            if config_url:
                return str(config_url)
        except Exception:  # pragma: no cover - 配置异常时回退默认值
            pass

        return 'sqlite:///litefs.db'

    @property
    def base_metadata(self) -> Any:
        """
        获取 autogenerate 使用的模型元数据

        Returns:
            SQLAlchemy MetaData 实例
        """
        if self._base_metadata is not None:
            return self._base_metadata

        from .models import Base
        return Base.metadata

    @property
    def migrations_path(self) -> str:
        """
        迁移脚本目录的绝对路径

        Returns:
            目录绝对路径
        """
        if os.path.isabs(self.script_location):
            return self.script_location
        return os.path.join(self.project_root, self.script_location)

    @property
    def ini_path(self) -> str:
        """
        alembic.ini 配置文件的绝对路径

        Returns:
            文件绝对路径
        """
        return os.path.join(self.project_root, ALEMBIC_INI_NAME)

    @property
    def is_initialized(self) -> bool:
        """
        迁移环境是否已初始化

        Returns:
            env.py 存在则视为已初始化
        """
        return os.path.exists(os.path.join(self.migrations_path, 'env.py'))

    # ==================== 公开方法 ====================

    def init(self, directory: Optional[str] = None) -> Tuple[int, str]:
        """
        初始化迁移环境

        生成 alembic.ini、迁移脚本目录与自定义 env.py。

        Args:
            directory: 迁移脚本目录，None 时使用构造参数

        Returns:
            (退出码, 输出信息)
        """
        alembic = load_alembic()

        target_dir = directory or self.script_location
        if not os.path.isabs(target_dir):
            target_dir = os.path.join(self.project_root, target_dir)
        target_dir = os.path.abspath(target_dir)

        if os.path.exists(os.path.join(target_dir, 'env.py')):
            return 1, f"迁移环境已存在: {target_dir}\n如需重建请先删除该目录"

        ini_path = os.path.join(self.project_root, ALEMBIC_INI_NAME)
        config = self._build_config(ini_path, target_dir)

        try:
            with contextlib.redirect_stdout(config.stdout):
                alembic.command.init(config, target_dir)
        except Exception as exc:
            return 1, f"初始化失败: {exc}\n"

        # 用自定义 env.py 覆盖 Alembic 默认模板
        env_path = os.path.join(target_dir, 'env.py')
        try:
            with open(env_path, 'w', encoding='utf-8') as env_file:
                env_file.write(self._render_env_py())
        except OSError as exc:
            return 1, f"写入 env.py 失败: {exc}\n"

        return 0, (
            f"迁移环境初始化完成\n"
            f"  配置文件: {ini_path}\n"
            f"  迁移目录: {target_dir}\n"
            f"下一步: litefs db migrate -m '初始迁移'\n"
        )

    def migrate(self, message: str = "auto migration") -> Tuple[int, str]:
        """
        生成迁移脚本

        Args:
            message: 迁移说明

        Returns:
            (退出码, 输出信息)
        """
        alembic = load_alembic()

        config, error = self._require_initialized()
        if config is None:
            return 1, error

        try:
            with contextlib.redirect_stdout(config.stdout):
                alembic.command.revision(config, message=message, autogenerate=True)
        except Exception as exc:
            return 1, f"生成迁移脚本失败: {exc}\n"

        return 0, f"迁移脚本已生成: {message}\n{config.stdout.getvalue()}"

    def upgrade(self, revision: str = "head") -> Tuple[int, str]:
        """
        升级数据库到指定版本

        Args:
            revision: 目标版本，默认为 head

        Returns:
            (退出码, 输出信息)
        """
        alembic = load_alembic()

        config, error = self._require_initialized()
        if config is None:
            return 1, error

        try:
            with contextlib.redirect_stdout(config.stdout):
                alembic.command.upgrade(config, revision)
        except Exception as exc:
            return 1, f"升级失败: {exc}\n"

        return 0, f"已升级到版本: {revision}\n{config.stdout.getvalue()}"

    def downgrade(self, revision: str = "-1") -> Tuple[int, str]:
        """
        回退数据库到指定版本

        Args:
            revision: 目标版本，默认为回退一个版本（-1）

        Returns:
            (退出码, 输出信息)
        """
        alembic = load_alembic()

        config, error = self._require_initialized()
        if config is None:
            return 1, error

        try:
            with contextlib.redirect_stdout(config.stdout):
                alembic.command.downgrade(config, revision)
        except Exception as exc:
            return 1, f"回退失败: {exc}\n"

        return 0, f"已回退到版本: {revision}\n{config.stdout.getvalue()}"

    def current(self) -> Tuple[int, str]:
        """
        查看当前数据库版本

        Returns:
            (退出码, 输出信息)
        """
        alembic = load_alembic()

        config, error = self._require_initialized()
        if config is None:
            return 1, error

        try:
            with contextlib.redirect_stdout(config.stdout):
                alembic.command.current(config, verbose=True)
        except Exception as exc:
            return 1, f"查询当前版本失败: {exc}\n"

        return 0, config.stdout.getvalue() or "（无输出）\n"

    def history(self) -> Tuple[int, str]:
        """
        查看迁移历史

        Returns:
            (退出码, 输出信息)
        """
        alembic = load_alembic()

        config, error = self._require_initialized()
        if config is None:
            return 1, error

        try:
            with contextlib.redirect_stdout(config.stdout):
                alembic.command.history(config, verbose=False)
        except Exception as exc:
            return 1, f"查询迁移历史失败: {exc}\n"

        return 0, config.stdout.getvalue() or "（无迁移记录）\n"

    # ==================== 内部方法 ====================

    def _build_config(self, ini_path: str, script_location: str) -> Any:
        """
        构建 Alembic 配置对象

        Args:
            ini_path: alembic.ini 路径
            script_location: 迁移脚本目录

        Returns:
            alembic.config.Config 实例
        """
        from alembic.config import Config

        config = Config(ini_path)
        config.set_main_option('script_location', script_location)
        config.set_main_option('sqlalchemy.url', self.database_url)
        # 统一捕获输出通道：
        #   - print_stdout 走 config.stdout
        #   - util.msg 直写 sys.stdout
        # 二者共用同一个缓冲区，避免信息丢失
        config.stdout = _Utf8StringIO()
        return config

    def _require_initialized(self) -> Tuple[Optional[Any], str]:
        """
        构建配置并校验迁移环境是否已初始化

        Returns:
            (配置对象, 错误信息)；配置为 None 时表示校验失败
        """
        if not self.is_initialized:
            return None, (
                "迁移环境未初始化\n"
                "请先执行: litefs db init\n"
            )

        ini_path = self.ini_path
        if not os.path.exists(ini_path):
            # ini 文件缺失时使用临时占位路径，仅用于内存态配置
            ini_path = os.path.join(self.project_root, ALEMBIC_INI_NAME)

        return self._build_config(ini_path, self.migrations_path), ""

    def _render_env_py(self) -> str:
        """
        渲染自定义 env.py 内容

        Returns:
            env.py 文件内容
        """
        if self.models_imports:
            imports = "\n".join(self.models_imports)
            imports = f"# 用户自定义模型模块\n{imports}\n"
        else:
            imports = (
                "# 如需 autogenerate 感知自定义模型，请在此导入，例如：\n"
                "# import models\n"
            )

        return _ENV_PY_TEMPLATE.replace('__MODELS_IMPORTS__', imports)


def detect_models_imports(project_root: Optional[str] = None) -> List[str]:
    """
    探测项目中的模型模块

    在项目根目录查找常见的 models 模块并生成导入语句。

    Args:
        project_root: 项目根目录，None 时使用当前工作目录

    Returns:
        导入语句列表
    """
    root = os.path.abspath(project_root or os.getcwd())
    imports: List[str] = []

    models_file = os.path.join(root, 'models.py')
    if os.path.isfile(models_file):
        imports.append('import models')

    models_dir = os.path.join(root, 'models')
    if os.path.isdir(models_dir):
        init_file = os.path.join(models_dir, '__init__.py')
        if os.path.isfile(init_file):
            imports.append('import models')

    return imports


__all__ = [
    "ALEMBIC_INI_NAME",
    "DEFAULT_SCRIPT_LOCATION",
    "AlembicManager",
    "AlembicNotAvailable",
    "detect_models_imports",
    "load_alembic",
]
