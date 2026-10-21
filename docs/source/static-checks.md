# Litefs 静态检查规范

**更新日期**: 2026-10-21
**适用版本**: v0.9.0（开发中）

## 概述

Litefs 采用 **flake8 + ruff + mypy** 三件套作为静态检查门禁，三者全部通过方可合并。

| 工具 | 版本 | 职责 | 门禁范围 |
|------|------|------|----------|
| [flake8](https://flake8.pycqa.org/) | 7.4.1 | PEP 8 代码风格（含 E501 长行、空白、命名） | `src/` |
| [ruff](https://docs.astral.sh/ruff/) | 0.15.10 | 快速静态检查（语法错误、未使用导入/变量、f-string 空占位） | `src/` |
| [mypy](https://mypy-lang.org/) | 1.20.1 | 静态类型检查 | `src/` |

当前基线：`src/` 共 **90 个 Python 文件、约 22,900 行代码**，三工具均 **零告警**。

## 快速使用

```bash
# 一键执行三件套（推荐，与 CI 完全一致）
make lint

# 仅应用 ruff 的安全自动修复
make lint-fix
```

手动执行时使用与 CI 完全相同的命令：

```bash
python -m flake8 src
python -m ruff check src
python -m mypy src
```

## 配置说明

### flake8

配置文件为仓库根目录的 [.flake8](file:///home/zhanglei3/Desktop/dev/litefs/.flake8)：

```ini
[flake8]
max-line-length = 100
extend-exclude =
    .eggs, .git, __pycache__, .mypy_cache, .ruff_cache, .tox, .venv, venv, build, dist, docs
```

- `max-line-length = 100`：与 `black` / `ruff` 的 `line-length` 保持一致
- 排除 `docs/`（文档构建产物含自动生成代码）

### ruff

配置位于 `pyproject.toml` 的 `[tool.ruff]` 段：

```toml
[tool.ruff]
line-length = 100
extend-exclude = ["docs", "build", "dist"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F"]
```

- `select` 采用默认规则集（E4 导入、E7 语句、E9 语法、F 系列未使用/未定义），
  与 flake8 常用规则对齐，后续按目录逐步扩展
- ruff 相对 flake8 快一个数量级，作为 CI 的快速失败前置

### mypy

配置位于 `pyproject.toml` 的 `[tool.mypy]` 段：

```toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true
```

关键选项说明：

| 选项 | 作用 |
|------|------|
| `python_version = "3.9"` | 类型检查目标版本（mypy 1.20+ 不再支持 3.8 目标，运行时仍兼容 3.8） |
| `check_untyped_defs = true` | 即使函数未加注解也检查函数体 |
| `no_implicit_optional = true` | 禁止 `x: str = None` 式隐式 Optional |
| `warn_return_any = true` | 从注解函数返回 `Any` 时告警 |
| `strict_equality = true` | 严格相等比较检查，避免误判类型 |

第三方库缺少类型存根（`mako`、`pymemcache`、`memcache`、`watchdog`）通过独立 override 豁免：

```toml
[[tool.mypy.overrides]]
module = ["mako.*", "memcache.*", "pymemcache.*", "watchdog.*"]
ignore_missing_imports = true
```

### 分阶段类型化治理

`src/` 中仍有 49 个模块尚未完成类型注解收敛。为避免「一次性阻塞开发」，
采用 mypy 的 `ignore_errors` override 标记为**待治理**，这些模块的错误不阻断 CI，
但每收敛一个模块即可从列表中移除，使门禁范围逐步扩大：

```toml
[[tool.mypy.overrides]]
module = [
    "litefs.auth",
    "litefs.auth.decorators",
    # ... 其余待治理模块
]
ignore_errors = true
```

治理顺序建议：先 `routing/`、`middleware/`、`handlers/`，再 `cache/`、`session/`、
`database/`，最后 `auth/`、`websocket/`、`server/`。类型注解编写规范详见
[类型注解规范](type-hints.md)。

## CI 流水线

配置文件为仓库根目录的 [.gitlab-ci.yml](file:///home/zhanglei3/Desktop/dev/litefs/.gitlab-ci.yml)，
包含两个 stage：

| Stage | Job | 内容 | 是否阻断合并 |
|-------|-----|------|--------------|
| `lint` | `lint` | `flake8 src` → `ruff check src` → `mypy src`，串行执行 | 是 |
| `test` | `unit-test` | `pytest tests/`，产出 JUnit XML 报告 | 是 |
| `test` | `coverage` | `pytest --cov`，产出 `coverage.xml` | 否（仅质量参考） |

执行策略：

- `lint` 三个命令以 **串行** 方式执行，任一失败即 job 失败、pipeline 失败
- `unit-test` 依赖 `memcached:11211` 与 `redis:6379`，CI 镜像内通过 apt 安装并启动
- `coverage` 设 `allow_failure: true`，避免覆盖率波动阻塞业务合并
- `workflow.rules` 限定 MR、分支推送与 Tag 三类触发场景，避免重复流水线

### 门禁范围说明

flake8 / ruff / mypy 的检查范围限定为 `src/`，原因：

- `tests/` 目录历史遗留问题规模较大（flake8 约 2300 项、ruff 约 220 项），
  纳入门禁会阻塞所有后续开发，需单独立项治理
- 框架对外暴露的 API 与运行时行为均由 `src/` 决定，静态检查的重点在此

## 常见问题排查

### E501 line too long

单行超过 100 字符。修复时**不得改变运行时行为**，按以下优先级处理：

1. **括号包裹换行**：函数签名、调用参数、列表/元组字面量优先拆为多行
2. **隐式字符串拼接**：长 f-string 拆为相邻字符串字面量，语义完全等价
3. **正则分段拼接**：长正则字面量拆为两段 raw string 拼接（`r"..." r"..."`）

```python
# 不推荐：截断字符串或缩短变量名，改变可读性与语义
# 推荐：括号包裹换行
headers.append((
    "Content-Disposition",
    f'attachment; filename="{filename}"',
))

# 推荐：隐式字符串拼接
logger.info(
    "请求处理失败: %s, 耗时 %.3fs, "
    "traceback: %s",
    path, elapsed, exc_text,
)
```

### mypy: Implicit Optional / no-any-return

- `def f(x: str = None)` → 改为 `def f(x: Optional[str] = None)`
- `return some_any_value` → 显式转换（`bool(...)`、`str(...)`）或补充精确注解

### mypy: attr-defined（Mixin 场景）

`Litefs` 由多个 Mixin 组合，Mixin 方法依赖宿主装配的属性，mypy 单独检查时无法感知。
解法是在 Mixin 类体中补充**仅注解不赋值**的属性声明，运行时零开销：

```python
if TYPE_CHECKING:
    from ..config import Config


class ServerMixin:
    #: 由 Litefs.__init__ 装配的宿主属性
    logger: logging.Logger
    config: "Config"
```

详见 [类型注解规范](type-hints.md) 的「Mixin 属性声明模式」。

## 相关文档

- [类型注解规范](type-hints.md)：mypy 配置、Mixin 属性声明模式、已修复的签名注解清单
- [单元测试文档](unit-tests.md)：测试结构、覆盖率现状
- [开发任务清单](todolist.md)：P0 质量与稳定性计划
