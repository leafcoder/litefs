# Litefs 类型注解规范

**更新日期**: 2026-10-20
**适用版本**: v0.9.0（开发中）

## 概述

Litefs 核心模块使用 [mypy](https://mypy-lang.org/) 进行静态类型检查，
当前检查范围为应用核心（`src/litefs/app/` 包 + `src/litefs/core.py`），已达成 **mypy 零错误**。

- 基线：81 个错误（74 attr-defined + 4 assignment + 2 arg-type + 1 no-any-return）
- 现状：`Success: no issues found in 8 source files`

## 运行检查

```bash
# 核心目录检查（当前验收范围）
python -m mypy src/litefs/app src/litefs/core.py --ignore-missing-imports
```

## Mixin 属性声明模式

`Litefs` 类由 4 个 Mixin 组合（Routing / Protocol / Extension / Server），
Mixin 方法依赖宿主装配的属性（`logger`、`config`、`router` 等），
mypy 单独检查 Mixin 时无法感知这些属性。

**解决方案**：在每个 Mixin 类体中添加属性声明注解（仅注解、不赋值），跨 Mixin 方法在
`TYPE_CHECKING` 块中声明签名。运行时零开销（纯注解不产生类属性），且被
`[tool.coverage.report]` 的 `exclude_lines` 排除，不影响覆盖率统计。

以 [server_mixin.py](file:///home/zhanglei3/Desktop/dev/litefs/src/litefs/app/server_mixin.py) 为例：

```python
if TYPE_CHECKING:
    from ..config import Config


class ServerMixin:
    """服务器启动、关闭与热重载生命周期管理"""

    #: 由 Litefs.__init__ 装配的宿主属性
    server: Optional[Union[HTTPServer, ProcessHTTPServer]]
    logger: logging.Logger
    host: str
    port: int
    config: "Config"

    if TYPE_CHECKING:
        # 跨 Mixin 方法：由 ExtensionMixin / ProtocolMixin / RoutingMixin 提供
        def load_plugins(self) -> Any: ...
        def get_websocket(self) -> Any: ...
        def handler(self, request, rw, environ, server) -> Any: ...
```

各 Mixin 声明的依赖：

| Mixin | 宿主属性 | 跨 Mixin 方法 |
|-------|----------|---------------|
| RoutingMixin | `router: Router`、`port: int`、`_websocket_instance` | — |
| ProtocolMixin | `logger`、`middleware_manager` | — |
| ExtensionMixin | `middleware_manager`、`_middleware_instances`、`db_manager`、`config`、`plugin_manager`、`plugin_loader` | — |
| ServerMixin | `server`、`logger`、`host`、`port`、`config` | `load_plugins`、`get_websocket`、`handler` |

## 本次修复的签名注解

| 位置 | 问题 | 修复 |
|------|------|------|
| `app/helpers.py` `make_config` | `**kwargs: Dict[str, Any]` 注解错误（每项应为配置值） | 改为 `**kwargs: Any` |
| `app/routing_mixin.py` `websocket` | `Callable = None` / `int = None` 隐式 Optional | 改为 `Optional[...] = None` |
| `app/routing_mixin.py` WebSocket 实例获取 | `hasattr` 分支无法类型收窄 | 改为 `getattr` + `is None` 判断（行为等价） |
| `websocket/server.py` 构造函数 | `auth_handler: Callable = None` 注解与实际不符 | 改为 `Optional[Callable] = None` |
| `app/extension_mixin.py` `has_plugin` | 返回 `Any` 触发 no-any-return | `bool(...)` 显式转换 |

## mypy 配置

配置位于 `pyproject.toml` 的 `[tool.mypy]` 段：

- `python_version = "3.9"`：类型检查目标版本（mypy 1.20+ 不再支持 3.8 目标，运行时仍兼容 3.8）
- `check_untyped_defs = true`：检查未注解函数体
- `no_implicit_optional = true`：禁止 `X = None` 式隐式 Optional
- `warn_return_any = true`：从注解函数返回 `Any` 时告警
- `strict_equality = true`：严格相等比较检查

## 改动文件清单

- `src/litefs/app/server_mixin.py`：属性声明 + 跨 Mixin 方法签名
- `src/litefs/app/extension_mixin.py`：属性声明 + `has_plugin` 返回类型
- `src/litefs/app/routing_mixin.py`：属性声明 + `websocket` 签名与收窄
- `src/litefs/app/protocol_mixin.py`：属性声明
- `src/litefs/app/helpers.py`：`make_config` 签名
- `src/litefs/websocket/server.py`：`auth_handler` 注解修正 + 历史遗留 flake8 问题清理
- `pyproject.toml`：mypy `python_version` 3.8 → 3.9

## 验证结果

- mypy：81 → **0** 错误
- pytest 全量回归：1306 passed（与基线一致，3 failed + 14 errors 均为 Memcache 环境问题）
- flake8：改动文件全部通过
- websocket / routing 专项测试：38 passed

## 后续计划

静态检查流水线已上线（详见 [静态检查规范](static-checks.md)），`src/` 全量纳入 mypy 检查范围。
尚未完成类型注解收敛的 **49 个模块**通过 `[[tool.mypy.overrides]]` + `ignore_errors = true`
标记为待治理，错误不阻断 CI；每收敛一个模块即从列表中移除，使门禁范围逐步扩大。

按相同模式逐步扩展检查范围（每收敛一个目录即从 override 列表移除）：

1. `routing/`、`middleware/`、`handlers/`
2. `cache/`、`session/`、`database/`
3. `auth/`、`websocket/`、`server/`
