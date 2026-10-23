# LiteFS v0.10.0 Release Notes

**发布日期**: 2026-10-22
**上一个版本**: v0.9.0
**变更规模**: 48 个文件，+3439 / -139

---

v0.10.0 是「契约与结构重构」版本：公共 API 首次全量分级冻结、弃用机制落地、
JSON 序列化切换 orjson，5 个超 600 行的大文件全部拆分至规范上限以内。
对应硬性标准 H1、H2、H3、H6 全部达成。

## 重大改进

### 公共 API 分级冻结（H2）

- 新增 `litefs/_stable.py` 契约注册表，登记全部 **548 个公共符号**：
  - `stable`（Tier 1）：70 个模块，410 个符号
  - `provisional`（Tier 2）：32 个模块，138 个符号
  - `internal`（Tier 3）：未登记符号一律视为 internal，不受稳定性承诺保护
- 契约测试 `tests/unit/test_api_contract.py` 强制：
  - 包内每个模块必须登记分级或进入豁免清单（`EXEMPT_MODULES`）
  - 登记模块的公共符号面（`__all__` + `dir()` 非下划线名）不得缩小
- 提供 `api_tier` / `public_symbols` / `stable_symbols` 分级查询接口

### API 稳定性与 SemVer 政策（H1）

- 新增 `docs/source/api-stability.md`：分级体系、冻结基线、SemVer 语义、破坏性变更流程
- 承诺：`stable` 面不兼容变更仅随 major 版本；破坏性变更必须走弃用流程，
  弃用后至少保留 2 个 feature release（对标 Django）

### 弃用机制与废弃时间表（H6）

- 新增 `litefs/deprecation.py`：
  - `LitefsDeprecationWarning` 专用告警类别
  - `deprecated` 装饰器与 `warn_deprecated` 运行时告警，
    替代符号 / 弃用版本 / 移除版本自动从 `_stable.DEPRECATED` 登记表回填
- 新增 `docs/source/deprecation-timeline.md`：废弃时间表与新增废弃流程
- 本版宣告：`Litefs.session` 废弃（计划 1.3.0 移除，替代 `Litefs.db_session`）

### 大文件拆分（H3）：全部源文件 ≤600 行

| 文件 | 拆分前 | 拆分后 | 方式 |
|------|--------|--------|------|
| `handlers/socket.py` | 827 | 598 | 请求属性 / 响应转换拆为 Mixin（`socket_request` / `socket_response`） |
| `server/greenlet.py` | 780 | 365 | SocketIO / Epoll / TCPServer 拆至 `greenlet_server_base` |
| `error_pages.py` | 775 | 包 | HTML 模板拆至 `templates_4xx` / `templates_5xx` |
| `config.py` | 627 | 包 | 加密 / 文件加载拆为 `crypto` / `loaders` Mixin |
| `handlers/base.py` | 639 | 489 | 请求属性拆至 `base_request` Mixin |

- 拆分代码逐字符原样搬运，公开 API 零变更（再导出保持全部原符号）
- Mixin 宿主属性按项目约定以 `TYPE_CHECKING` 声明，运行时零开销

### JSON 序列化切换 orjson

- 新增 `litefs/_json.py` 序列化抽象层，框架内 24 处 `import json` 全部替换，
  源码零 `import json` 残留
- orjson（Rust 实现）编解码吞吐约为标准库的 3~5 倍，直接改善请求热路径 P99
- 三个出口按下游约束区分：`dumps`（bytes）/ `dumps_str`（str）/ `dumps_ascii`
  （ASCII 安全，非 ASCII 转 `\uXXXX`，与标准库 `ensure_ascii=True` 逐字节一致）
- 语义对齐：`OPT_NON_STR_KEYS` 对齐非字符串键；`OPT_PASSTHROUGH_DATETIME` /
  `OPT_PASSTHROUGH_DATACLASS` 交由 `default` 回调，保持与标准库一致的输出语义
- 依赖同步至 `pyproject.toml` / `requirements.txt` / 脚手架模板（`orjson>=3.10`）

### 缓存与缺陷修复

- Memcache 缓存后端新增 `incr` / `decr` 原子计数器（memcached 原生命令，
  与 JSON 整数存储天然兼容；键不存在返回 `None`，递减下限钳位 0）
- 修复 `MemcacheCache` / `MemcacheSession` 注入 `memcache_client` 时
  `_use_pymemcache` 未设置导致 `put()` 抛 `AttributeError` 的问题
  （按客户端所属模块自动判定调用约定）
- 修复 Memcache 后端写入非 ASCII 内容失败的问题（orjson 迁移暴露：
  抽象层新增 `dumps_ascii` 出口，迁移前旧缓存数据双向兼容）

### 工程化

- Makefile 新增 `test` / `test-unit` / `test-cov` 目标
- 新增文档：`api-stability.md`、`deprecation-timeline.md`、`json-serialization.md`

## 兼容性说明

- **公开 API 零变更**：全部原有符号经再导出保持可用；唯一弃用项 `Litefs.session`
  运行时发出 `LitefsDeprecationWarning`，1.3.0 前功能不受影响
- **JSON 输出格式差异**：orjson 紧凑分隔符（`{"a":1}`）与标准库（`{"a": 1}`）不同，
  依赖响应体字节级字面量的下游需改用语义解析（对标准 JSON 解析器无影响）
- **orjson 边界**：大整数支持至 2^64-1（超出抛 `TypeError`）；`NaN` / `Infinity`
  序列化为 `null`（详见 `docs/source/json-serialization.md` 差异对照表）

## 质量门禁

- flake8 + ruff + mypy 全绿（117 个源文件）
- pytest：1813 passed / 3 skipped / 0 failed（skip 均为环境依赖项）
- Sphinx 文档构建零告警
- 全部源文件 ≤600 行（最大 598）
