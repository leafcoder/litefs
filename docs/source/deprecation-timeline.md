# 弃用机制与废弃时间表

本文档记录 Litefs 的弃用机制与当前生效的废弃时间表，对应硬性标准 H6（弃用机制与废弃时间表就位）与 H7（版本化文档 + 废弃时间表）。

## 弃用机制

弃用工具位于 `litefs/deprecation.py`，权威数据源为 `litefs/_stable.py`：

- `LitefsDeprecationWarning`：继承自 `DeprecationWarning` 的专用告警类别，便于用户按类别过滤或升级为错误
- `warn_deprecated(module_name, symbol, ...)`：发出弃用告警；`replacement` / `since` / `removal` 缺省时自动从 `_stable.DEPRECATED` 登记表回填，保证运行时告警与文档计划一致
- `deprecated(...)`：装饰器形态，声明 `replacement` / `since` / `removal` 后自动接入上述告警链路
- `format_deprecation_message(...)`：统一告警文案格式（"X 已废弃，自 Y 起，将于 Z 移除，请使用 R 替代"）

## 废弃时间表

当前生效的废弃登记（`_stable.DEPRECATED`）：

| 符号 | 弃用版本 | 计划移除 | 替代符号 | 原因 |
|------|---------|---------|---------|------|
| `litefs.core:Litefs.session` | 0.10.0 | 1.3.0 | `Litefs.db_session` | 方法名与 cache/session 子系统语义冲突，统一为数据库会话命名 |

## 兼容别名表

为兼容历史用法而保留的别名（`_stable.ALIASES`），键为别名，值为规范符号：

| 别名 | 规范符号 |
|------|---------|
| `litefs.exceptions:HttpError` | `litefs.exceptions:HTTPException` |
| `litefs.handlers.response:responses` | `litefs.handlers.response:http_status_codes` |
| `litefs.handlers.socket:RequestHandler` | `litefs.handlers.socket:SocketRequestHandler` |

别名不受 `stable` 承诺保护，随其规范符号的移除时间表一并处理。

## 新增废弃的流程

宣告新的弃用时必须：

1. 在 `litefs/_stable.py` 的 `DEPRECATED` 登记表新增条目，填写 `since` / `removal` / `replacement` / `reason` 四要素；`removal` 与 `since` 之间至少间隔 2 个 feature release
2. 目标符号通过 `deprecated` 装饰器或 `warn_deprecated` 接入运行时告警（契约测试会校验登记符号真实存在）
3. 更新本文档的废弃时间表
4. 在 CHANGELOG 的 `Deprecated` 段落记录
5. 若为语义迁移（而非直接废弃），同时在 `ALIASES` 登记别名，保证旧用法在弃用期内可用
