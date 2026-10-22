# API 稳定性与 SemVer 政策

本文档是 Litefs 公共 API 稳定性承诺的权威说明，对应硬性标准 H1（API 稳定性与 SemVer 政策成文）与 H2（公共 API 分级冻结）。

## 分级体系

Litefs 将全部公共 API 划分为三个稳定性层级，权威登记表为 `litefs/_stable.py`：

| 层级 | 名称 | 稳定性承诺 | 破坏性变更允许窗口 |
|------|------|-----------|------------------|
| Tier 1 | `stable` | 严格保证，仅随 major 版本引入不兼容变更 | 仅 v1.0.0 及之后的 major 版本 |
| Tier 2 | `provisional` | 基本保证，语义保持但允许扩展性调整 | minor 版本，且必须走弃用流程 |
| Tier 3 | `internal` | 无任何保证，随时可能变更 | 任意版本 |

分级查询接口：

- `litefs._stable.api_tier(module_name, symbol)`：查询单个符号的层级，未登记符号返回 `internal`
- `litefs._stable.public_symbols(module)`：列出模块公共符号（`__all__` + 自定义非下划线符号）
- `litefs._stable.stable_symbols()`：返回全量 `stable` 符号扁平清单

## 冻结基线（v0.10.0）

v0.10.0 完成首次全量符号分级冻结，基线规模：

- `stable`：70 个模块，410 个符号
- `provisional`：32 个模块，138 个符号
- 合计：548 个公共符号

冻结规则：

1. `test_api_contract.py::test_every_module_is_classified` 强制包内每个模块必须登记分级或进入豁免清单，新增模块不登记则 CI 失败
2. `test_api_contract.py::test_public_symbols_classified` 强制登记模块的每个公共符号逐项核对
3. 登记模块的公共符号面（`__all__` 与 `dir()` 非下划线名）不得缩小——缩减符号视为破坏性变更

## 内部模块豁免

以下两类模块不纳入契约检查（`EXEMPT_MODULES`）：

- 入口与非库接口模块：`litefs.__main__`、`litefs._stable`、`litefs._json`
- 大文件拆分产生的内部实现模块：`litefs.config.core` / `litefs.config.crypto` / `litefs.config.loaders`、`litefs.error_pages.renderer` / `litefs.error_pages.templates_4xx` / `litefs.error_pages.templates_5xx`、`litefs.handlers.socket_request` / `litefs.handlers.socket_response`

这些模块由所属公共模块再导出，不构成公共 API，不受稳定性承诺保护。

## SemVer 语义

Litefs 版本号遵循语义化版本 `MAJOR.MINOR.PATCH`：

- **PATCH**：缺陷修复、文档修订、内部实现调整，零接口变更
- **MINOR**：新增功能、新增符号、功能废弃（启动弃用期）；0.x 阶段允许在 MINOR 内对 `provisional` 面做破坏性调整，但必须提前至少一个版本发出弃用告警
- **MAJOR**：`stable` 面的不兼容变更；v1.0.0 之前不发布任何 major 版本

`stable` 面的不兼容变更在 v1.0.0 之前一律禁止。当前 0.x 各版本的不兼容调整仅允许出现在 `internal` 与豁免模块中。

## 破坏性变更流程

对任何已登记符号的移除或语义变更，必须：

1. 启动弃用期：通过 `litefs.deprecation.deprecated` 装饰器接入运行时告警，并在 `litefs._stable.DEPRECATED` 登记表登记（详见 :doc:`deprecation-timeline`）
2. 至少保留 2 个 feature release（对齐 Django 的弃用周期惯例），移除版本由登记表 `removal` 字段固化
3. 在 CHANGELOG 中记录弃用与替代符号
4. 移除时同步更新 `_stable.py` 分级登记、契约测试与本文档基线
