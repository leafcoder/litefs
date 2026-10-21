# Litefs 数据库迁移

**更新日期**: 2026-10-21
**适用版本**: v0.9.0（开发中）

## 概述

Litefs 基于 [Alembic](https://alembic.sqlalchemy.org/) 封装数据库版本化迁移能力，提供完整的 `init / migrate / upgrade / downgrade / current / history` 命令组。

设计原则：

| 原则 | 实现方式 |
|------|----------|
| 可选依赖 | `alembic` 懒加载，未安装时框架核心功能不受影响 |
| 无状态污染 | 每次命令在独立配置对象中执行，不改写全局配置 |
| 不劫持日志 | 仅配置 `alembic` 日志命名空间，不触碰宿主应用的 root logger |
| 向后兼容 | 旧的扁平入口 `litefs db-init` / `litefs db-migrate` 保留 |

## 安装

```bash
# 仅启用迁移能力
pip install 'litefs[db]'

# 或直接安装依赖
pip install alembic
```

未安装时执行迁移命令会抛出 `AlembicNotAvailable`（继承 `ImportError`），并给出安装指引：

```text
未安装 alembic，请执行 pip install 'litefs[db]' 或 pip install alembic
```

## 命令清单

### `litefs db` 命令组

| 命令 | 说明 | 参数 |
|------|------|------|
| `litefs db init` | 初始化 Alembic 迁移环境 | `directory`（默认 `migrations`） |
| `litefs db migrate` | 生成迁移脚本（对比模型与库结构） | `-m/--message`（默认 `auto migration`） |
| `litefs db upgrade` | 升级数据库到指定版本 | `revision`（默认 `head`） |
| `litefs db downgrade` | 回退数据库到指定版本 | `revision`（默认 `-1`，即回退一版） |
| `litefs db current` | 显示当前数据库版本 | — |
| `litefs db history` | 显示迁移历史 | — |
| `litefs db create-tables` | 直接创建全部数据表（不生成迁移脚本） | — |

### 旧入口（保持兼容）

| 命令 | 说明 |
|------|------|
| `litefs db-init` | 建表（旧行为不变） |
| `litefs db-migrate` | 生成迁移脚本（旧占位提示已升级为真正实现） |

> `db-init` 与 `db create-tables` 等价；`db-migrate` 与 `db migrate` 等价。新代码推荐使用嵌套子命令形式。

## 快速开始

```bash
# 1. 初始化迁移环境（在项目根目录执行）
$ litefs db init
迁移环境初始化完成
  配置文件: /path/to/project/alembic.ini
  迁移目录: /path/to/project/migrations
下一步: litefs db migrate -m '初始迁移'

# 2. 修改模型后生成迁移脚本
$ litefs db migrate -m "新增用户表"
迁移脚本已生成: 新增用户表
Generating /path/to/project/migrations/versions/92f20e175f75_新增用户表.py ...  done

# 3. 应用迁移
$ litefs db upgrade
已升级到版本: head

# 4. 查看当前版本与历史
$ litefs db current
Current revision(s) for sqlite:///litefs.db:
Rev: 92f20e175f75 (head)
Parent: <base>
Path: /path/to/project/migrations/versions/92f20e175f75_新增用户表.py

$ litefs db history
<base> -> 92f20e175f75 (head), 新增用户表

# 5. 需要时回退
$ litefs db downgrade
已回退到版本: -1
```

## 生成的目录结构

```text
project/
├── alembic.ini               # Alembic 配置（script_location / sqlalchemy.url）
├── app.py
├── models.py                 # 自定义模型（需被 autogenerate 感知）
└── migrations/
    ├── env.py                # 由 Litefs 生成的自定义环境脚本
    ├── script.py.mako        # 迁移脚本模板
    └── versions/             # 迁移脚本存放目录
        └── 92f20e175f75_新增用户表.py
```

### 自定义 env.py

`litefs db init` 会用框架自带的模板覆盖 Alembic 默认的 `env.py`，与默认模板的差异：

1. **`target_metadata = Base.metadata`** —— 指向 `litefs.database.models.Base`，`autogenerate` 依赖它对比模型差异；默认模板的 `target_metadata = None` 会导致 autogenerate 直接报错。
2. **SQLite 批处理模式** —— `render_as_batch=connection.dialect.name == "sqlite"`，SQLite 不支持大部分 `ALTER TABLE`，批处理模式可自动改写为"新建表 + 拷贝数据"。
3. **不调用 `fileConfig()`** —— 程序化构造的 ini 不含完整 logging 配置段，调用会抛异常；同时也避免劫持宿主应用的 root logger。改为仅配置 `alembic` 日志命名空间。
4. **显式插入项目根目录到 `sys.path`** —— 保证能导入项目自定义的模型模块。

模板中还预留了自定义模型的导入位置：

```python
# 用户自定义模型模块的导入语句
# import models
```

`litefs db init` 会自动探测项目根目录下的 `models.py` 或 `models/` 包并填入该位置。若模型不在根目录，需手工编辑 `migrations/env.py` 补充导入语句，否则 `autogenerate` 无法感知这些模型。

## 数据库连接解析

`AlembicManager.database_url` 的解析优先级：

1. 构造时**显式传入**的 `database_url`
2. **环境变量** `DATABASE_URL`
3. Litefs 配置中的 `database_url`
4. 默认值 `sqlite:///litefs.db`

CLI 场景下，框架会先从项目的 `app.py` 中读取 `app.db.database_url`，读取成功时以最高优先级传入；读取失败则回退到上述顺序。

```bash
# 通过环境变量指定数据库
export DATABASE_URL="postgresql://user:pass@127.0.0.1:5432/appdb"
litefs db upgrade
```

## 编程接口

```python
from litefs.database import AlembicManager

manager = AlembicManager(
    database_url='postgresql://user:pass@127.0.0.1:5432/appdb',
    script_location='migrations',
    project_root='/path/to/project',
)

code, output = manager.init()
if code != 0:
    raise RuntimeError(output)

code, output = manager.migrate('新增用户表')
print(output)
```

所有公开方法统一返回 `(exit_code: int, output: str)` 二元组，由调用方决定如何展示输出与退出码。

| 方法 | 说明 |
|------|------|
| `init(directory=None)` | 初始化迁移环境，生成 `alembic.ini` 与迁移目录 |
| `migrate(message='auto migration')` | 生成迁移脚本 |
| `upgrade(revision='head')` | 升级到指定版本 |
| `downgrade(revision='-1')` | 回退到指定版本 |
| `current()` | 查看当前版本 |
| `history()` | 查看迁移历史 |

### 属性

| 属性 | 说明 |
|------|------|
| `database_url` | 解析后的数据库连接 URL |
| `base_metadata` | autogenerate 使用的模型元数据（默认 `litefs.database.models.Base.metadata`） |
| `migrations_path` | 迁移目录绝对路径 |
| `ini_path` | `alembic.ini` 绝对路径 |
| `is_initialized` | 迁移环境是否已初始化（`env.py` 是否存在） |

### 异常

| 异常 | 触发条件 |
|------|----------|
| `AlembicNotAvailable` | 未安装 `alembic`（继承 `ImportError`） |

## 生产实践

### 1. 迁移脚本必须进版本库

`migrations/versions/` 与 `alembic.ini` 都应提交到 Git，它们是数据库结构变更的**唯一事实来源**。

```bash
# .gitignore 中不要忽略
# !migrations/
```

### 2. 在发布流程中执行升级

```bash
# 典型发布脚本
set -e
python -m pip install -e ".[db]"
litefs db upgrade          # 失败则中止发布
gunicorn -w 4 -b :8080 wsgi:application
```

`litefs db upgrade` 的退出码非 0 时表示迁移失败，可直接用于阻断发布。

### 3. 先备份再迁移

生产环境的 `downgrade` 通常**不可逆**（`DROP COLUMN` 等操作无法回滚）。执行前请确保有可用的备份或快照。

### 4. 并发控制

Alembic 自身不带迁移锁。若多个实例同时执行 `upgrade`，可能出现并发 DDL 冲突。建议：

- 在发布流程中只由**一个**实例执行迁移；
- 或在数据库层加 advisory lock。

### 5. 大表迁移

SQLite 走批处理模式（`render_as_batch=True`），大数据量下会走"建新表 → 拷贝数据 → 改名"流程，耗时较长，建议在低峰期执行。

## 常见问题

**Q：执行 `litefs db migrate` 报 "does not provide a MetaData object"？**

A：`migrations/env.py` 被手工改动过，导致 `target_metadata` 未赋值。重新执行 `litefs db init` 重建环境（或将 `target_metadata = Base.metadata` 补回）。

**Q：生成的迁移脚本是空的？**

A：说明模型未被 `env.py` 感知。请确认 `migrations/env.py` 中已导入自定义模型模块（`import models`），且模型类继承自 `litefs.database.models.Base` 或已加入该 Base 的 `metadata`。

**Q：`litefs db current` 没有输出？**

A：数据库中尚未应用任何迁移，执行一次 `litefs db upgrade` 后再查看。

**Q：提示"迁移环境未初始化"？**

A：需先在项目根目录执行 `litefs db init`。

**Q：如何在不生成迁移脚本的情况下建表？**

A：使用 `litefs db create-tables`（等价旧的 `litefs db-init`），直接按模型元数据创建全部数据表。

## 相关文档

- :doc:`configuration` —— 配置项完整列表
- :doc:`prometheus-monitoring` —— Prometheus 监控
- :doc:`static-checks` —— 静态检查规范
