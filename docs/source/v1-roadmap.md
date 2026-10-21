# Litefs v1.0.0 升级方案

> 版本目标：**生产就绪**（API 稳定承诺 + 质量硬指标达标）
> 基线版本：v0.9.0（`cb2988f`）
> 编制日期：2026-10-21
> 对标对象：**Starlette**（近 8 年唯一真正走完 0.x → 1.0 的同代 ASGI 框架）

---

## 一、为什么是现在，以及对标谁

### 1.1 行业 1.0 的现实参照

| 框架 | 当前稳定版 | 是否到 1.0 | 1.0 首发 | 0.x → 1.0 耗时 | Python 要求 |
|------|-----------|-----------|---------|--------------|------------|
| Starlette | 1.9.0 | ✅ | 2026-03-22 | **约 7.8 年** | >=3.11 |
| FastAPI | 0.156.6 | ❌ 至今 0.x | — | **8 年未达成** | >=3.10 |
| Django | 6.1.2 | ✅ | 2008-09-04 | 约 2.7 年 | >=3.12 |
| Flask | 3.1.3 | ✅ | 2018-04-26 | 约 8 年 | >=3.9 |
| Tornado | 6.5.10 | ✅ | 2010-07-23 | 约 2 个月 | >=3.9 |
| Sanic | 25.12.1 | ❌ 跳过 1.x | — | — | >=3.10 |
| Litestar | 2.25.0 | ❌ 跳过 1.x | — | — | >=3.8 |
| aiohttp | 3.14.5 | ❌ 仍 3.x | — | — | >=3.10 |
| Quart | 0.23.1 | ❌ 仍 0.x | — | — | >=3.13 |

**结论：0.x → 1.0 的中位耗时是 3–8 年。** FastAPI 用了 8 年仍未发布 1.0，是最值得警惕的样本 —— 它的问题不是功能不足，而是**始终没有对 API 稳定性做出可依赖的承诺**。

因此 Litefs 的 1.0 **不以功能数量取胜**，而以「承诺的可信度」取胜：对标 Starlette 1.0 的做法，而不是对标 FastAPI 的功能面。

### 1.2 业界公认的「可以叫 1.0」判据（按重要性排序）

| # | 判据 | 行业实践 | Litefs 现状 |
|---|------|---------|------------|
| 1 | 成文的 API 稳定性承诺 + 严格 SemVer | Django《API stability》指南、Starlette 1.0 博客「We'll follow SemVer strictly」 | ❌ 无 |
| 2 | 长弃用期，破坏性变更只走 major | Django：弃用后至少保留 2 个 feature release | ❌ 无弃用机制 |
| 3 | 覆盖率成为硬门禁 | FastAPI / Starlette 公开声明 **100% 覆盖率**，pytest 开 `filterwarnings=error` | ⚠️ 72.2%，无 `fail_under` |
| 4 | 完整类型注解 + `py.typed` + `mypy --strict` | Starlette / FastAPI 均 `strict = true`；Django 是唯一无 `py.typed` 的一线框架 | ❌ 无 `py.typed`，52 模块豁免 |
| 5 | 明确的 Python 版本淘汰节奏 | Starlette 1.8 抬到 3.11、Sanic 25.12 弃 3.9、Quart 0.23 抬到 3.13 | ⚠️ 3.8–3.12，3.8 已 EOL |
| 6 | 安全响应闭环（GHSA / CVE / 分支回补） | Django 明确「security trumps the compatibility guarantee」 | ⚠️ 有依赖审计，无响应流程 |
| 7 | 版本化文档 + 迁移指南 + 废弃时间表 | Django 有专门的 Deprecation Timeline 页 | ❌ 无 |
| 8 | 生态可互操作（ASGI 中间件规范、插件注册） | Starlette `BaseHTTPMiddleware` 互操作 | ❌ 无 lifespan、无 entry_points |

---

## 二、v1.0.0 范围与边界

### 2.1 已确认的四项决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 范围定位 | **聚焦稳定性硬指标** | 3–8 年的行业周期不可压缩到一版发布；先把承诺做实 |
| 破坏性变更 | **1.0.0 一次性执行** | FastAPI 的教训：Pydantic v1/v2 双栈共存 2.5 年后仍在 0.128.0 硬切换，不如一次切干净 |
| Python 基线 | **3.10–3.14** | 对标 Django 3.12 / Starlette 3.11 / FastAPI 3.10 / aiohttp 3.10 的 2026 现状 |
| ASGI 深度 | **渐进增强** | 保留 WSGI 复用优势，补 lifespan + streaming + 中间件签名兼容，不做全量重写 |

### 2.2 v1.0.0 包含（P0–P3）

| 领域 | 内容 |
|------|------|
| **契约** | API 稳定性政策、SemVer 承诺、弃用时间表、196 个公共符号 API 分级与冻结 |
| **质量** | `mypy --strict` 全量零豁免、覆盖率 ≥85%（核心模块 ≥80%）、`py.typed`、`conftest.py` + `TestClient`、拆分 5 个超 600 行文件、`filterwarnings=error` |
| **协议** | ASGI lifespan 协议、原生 streaming 响应、ASGI 中间件签名兼容 |
| **生态** | `entry_points` 插件发现、GitHub PR 级 CI 门禁 |
| **打包** | 删除 `setup.py`、核心依赖 optional 化、extras 重整、Python 3.10–3.14 |
| **发布** | 版本化文档站、`SECURITY.md` 与 CVE 响应流程、SBOM、签名发布、LTS 政策 |

### 2.3 v1.0.0 明确**不**包含（列入 v1.x 长期路线）

| 项 | 理由 | 归属 |
|---|------|------|
| HTTP/2 | 需引入 `h2` 状态机并重写帧层；Sanic 至今也仅 HTTP/1.1 + HTTP/3 | v1.1+ |
| HTTP/3 | 需 aioquic + QUIC 栈，改动面过大 | v2.x |
| OpenTelemetry 集成 | 已有 Prometheus 满足多数场景；Starlette 亦提供可选 `OpenTelemetryMiddleware` | v1.2+（先出可选中间件） |
| ASGI 原生重写 | 与「渐进增强」决策冲突，回归面过大 | v2.x |
| gRPC 协议 | 独立协议栈，与 HTTP 框架定位弱相关 | v2.x |
| Rust/C 扩展热点路径 | 性能优化手段而非 1.0 必备 | v2.x |

---

## 三、当前状态快照（2026-10-21 实测）

| 指标 | 数值 | 1.0 目标 |
|------|------|---------|
| 源码规模 | 26,817 行 / 108 模块 | 拆分后单文件 ≤600 行 |
| 测试用例 | 1641 passed / 7 skipped | ≥2400，核心模块全绿 |
| 测试覆盖率 | **72.2%**（7693/10247 语句） | **≥85%**，核心模块 ≥80% |
| mypy 豁免模块 | **52 个** | **0 个**（`--strict` 全量通过） |
| 公共 API（`__all__`） | 196 个符号 / 17 子包 | 分级冻结 + 100% 文档覆盖 |
| 超 600 行文件 | **5 个** | **0 个** |
| `py.typed` | ❌ 不存在（`setup.py` 却已声明） | ✅ 随 wheel 正确发布 |
| `tests/conftest.py` | ❌ 不存在 | ✅ 共享 fixtures |
| `TestClient` | ❌ 不存在 | ✅ httpx 驱动 |
| ASGI lifespan | ❌ `scope['type'] != 'http'` 直接报错 | ✅ 完整支持 |
| ASGI WebSocket | ❌ 未实现（WebSocket 为独立裸 socket 服务器） | v1.x |
| 插件发现 | 仅目录/文件扫描 | ✅ entry_points |
| GitHub CI | 仅 `publish.yml`（无 PR 门禁） | ✅ PR 级 lint + test + coverage |
| Python 支持 | 3.8–3.12（3.8 已 EOL） | 3.10–3.14 |
| 硬依赖 | SQLAlchemy / watchdog / greenlet 均为必装 | SQLAlchemy / watchdog 移入 optional |

### 3.1 最需警惕的覆盖率洼地

覆盖率最低的模块，恰恰是框架**最核心**的自研服务器代码：

| 模块 | 覆盖率 | 缺失语句 | 风险 |
|------|-------|---------|------|
| `app/server_mixin.py` | **9.5%** | 145/166 | `run()` 主入口几乎未测 |
| `websocket/server.py` | **13.0%** | 167/201 | 握手与帧处理未测 |
| `app/server_cli.py` | 16.7% | 20/24 | CLI 参数解析未测 |
| `handlers/socket.py` | **20.9%** | 369/503 | 原生 Socket 请求链路未测 |
| `cli_db.py` | 24.0% | 60/84 | 迁移命令未测 |
| `server/greenlet.py` | **32.7%** | 380/598 | epoll 事件循环未测 |
| `cli.py` | 34.0% | 111/169 | 命令行入口未测 |

**这是 1.0 最大的实质风险**：对外承诺「稳定」，而最核心的自研 HTTP 服务器只有 20%–33% 的语句被验证过。

---

## 四、阶段规划

### P0 — 契约先行（1.0 的立身之本）

> 行业第一判据。**先立承诺，再立版本号。**

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| P0-1 | 编写《Litefs API 稳定性与 SemVer 政策》 | `docs/source/api-stability.md` | 明确：稳定 API 定义、弃用流程、破坏性变更仅走 major、弃用后至少保留 2 个 minor（对标 Django） | 1d |
| P0-2 | 公共 API 分级与冻结 | `litefs/_stable.py` 清单 + 各子包 `__all__` 标注 | 196 个符号逐个判定 `stable` / `experimental` / `private`；`private` 加 `_` 前缀或移出 `__all__` | 2d |
| P0-3 | 弃用机制与时间表 | `DeprecationWarning` 工具 + `docs/source/deprecation-timeline.md` | 弃用项带「计划移除版本」；迁移指南模板就位 | 1d |
| P0-4 | 破坏性变更一次性执行 | 变更集 + `docs/source/migration-v1.md` | 见 §5 清单；每项附前后对照代码 | 3d |
| P0-5 | 拆分 5 个超 600 行文件 | 见 §6 表 | 全部 ≤600 行；公开 API 零变更；全量回归通过 | 3d |
| P0-6 | `py.typed` 落盘 | `src/litefs/py.typed` + 打包配置 | wheel 内实际包含 `py.typed`（`twine check` + 解包验证） | 0.5d |
| P0-7 | `mypy --strict` 全量收敛 | 52 个豁免清零 | `mypy --strict src/` 零错误；CI 门禁切换为 strict | 5d |
| P0-8 | 核心服务器覆盖率补齐 | 新增测试模块 | `handlers/socket.py` ≥80%、`server/greenlet.py` ≥80%、`app/server_mixin.py` ≥80%、`websocket/` ≥75% | 6d |
| P0-9 | `tests/conftest.py` + 共享 fixtures | 测试基础设施 | `app` / `client` / `tmp_config` / `mock_redis` / `mock_memcache` 等 fixtures；测试重复代码下降 | 1d |
| P0-10 | `TestClient` 实现 | `litefs/testclient.py` | httpx 驱动，支持 WSGI + ASGI 两种 app，Cookie 持久化、状态码断言 | 2d |

**P0 出口条件**：mypy strict 零豁免、核心模块覆盖率 ≥80%、`py.typed` 发布、API 政策文档评审通过。

### P1 — 协议与生态补齐

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| P1-1 | ASGI lifespan 协议 | `handlers/asgi.py` 支持 `scope['type'] == 'lifespan'` | uvicorn / hypercorn 直接托管 Litefs ASGI app 正常启停；`startup` / `shutdown` 钩子可注册 | 2d |
| P1-2 | 原生 ASGI streaming 响应 | 响应对象直通 `send()` | 不再经过 WSGI environ 转换；SSE / 流式大文件不缓冲 | 3d |
| P1-3 | ASGI 中间件签名兼容 | `litefs/middleware/asgi.py` | Starlette 风格 `async def mw(request, call_next)` 中间件可直接挂载 | 2d |
| P1-4 | `entry_points` 插件发现 | `plugins/loader.py` 双通道 | 支持 `[project.entry-points."litefs.plugins"]`；保留现有目录扫描 | 1.5d |
| P1-5 | GitHub PR 级 CI 门禁 | `.github/workflows/ci.yml` | PR 触发 lint（flake8+ruff+mypy strict）+ test（3.10–3.14 矩阵）+ coverage 门禁；`allow_failure: false` | 2d |
| P1-6 | pytest 严格化 | `pyproject.toml` | 启用 `filterwarnings = error`；`--strict-markers --strict-config` 保持；`coverage fail_under = 85` | 1d |
| P1-7 | 覆盖率补齐（非核心模块） | 新增/扩充测试 | 整体 ≥85%；`app/` `cache/` `session/` `routing/` `middleware/` `auth/` 均 ≥80% | 5d |

### P2 — 打包与发布基础设施

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| P2-1 | 删除 `setup.py` | 单一 `pyproject.toml` | 全部元数据迁入 PEP 621；`pip install .` 与 `python -m build` 均通过 | 1d |
| P2-2 | 核心依赖 optional 化 | `pyproject.toml` extras 重整 | `SQLAlchemy` / `watchdog` / `greenlet` 移出必装；`cache/cache.py` 与 `database/core.py` 的模块级 import 改为懒加载 | 2d |
| P2-3 | extras 矩阵重整 | `litefs[standard|full|db|server|mail|i18n|monitoring|dev|docs]` | 每个 extra 有明确用途与文档说明；`litefs[full]` 可复现全部功能 | 1d |
| P2-4 | Python 基线收敛 3.10–3.14 | `requires-python` + classifiers + CI 矩阵 | 弃 3.8/3.9；新增 3.13/3.14；`black` target-version 同步 | 1d |
| P2-5 | `SECURITY.md` 与 CVE 响应流程 | 安全策略文档 + 私有报告通道 | 明确漏洞报告方式、响应时限、分支回补规则（对标 Django「安全优先于兼容承诺」） | 0.5d |
| P2-6 | SBOM 与签名发布 | `cyclonedx-py` 产物 + Sigstore 签名 | 每版发布附带 SBOM；wheel/sdist 签名并在 PyPI 展示 | 1.5d |
| P2-7 | 版本化文档站 | ReadTheDocs 配置 | 按版本发布；每版含迁移指南与废弃时间表 | 1.5d |
| P2-8 | LTS 政策 | 政策文档 | 对标 Django：每 2 年一个 LTS、支持期 3 年、LTS 命名为 `X.0` | 0.5d |

### P3 — 1.0 发布

| # | 任务 | 验收标准 | 工作量 |
|---|------|---------|--------|
| P3-1 | 全量回归 + 性能基线复核 | 覆盖率 ≥85%、mypy strict 零错误、pytest 全绿、RPS ≥ v0.9.0 基线 100% | 1d |
| P3-2 | `CHANGELOG.md` 破坏性变更专章 | 每条破坏性变更标注影响面与迁移方式 | 0.5d |
| P3-3 | 迁移指南 `migration-v1.md` | 从 v0.9.0 升级的逐步操作说明 | 1d |
| P3-4 | 打标签 + 发布 + GitHub Release | `v1.0.0` 标签、PyPI 正式发布、Release Notes | 0.5d |
| P3-5 | 1.0 稳定分支 | `1.0` 分支建立，仅接受安全与严重缺陷修复 | 0.5d |

---

## 五、破坏性变更清单（1.0.0 一次性执行）

> 每项均须在 `docs/source/migration-v1.md` 中给出前后对照。

| # | 变更 | 影响 | 兼容处理 |
|---|------|------|---------|
| B1 | 核心依赖 optional 化 | `pip install litefs` 不再装 SQLAlchemy / watchdog / greenlet | 需功能者改用 `litefs[db]` / `litefs[standard]`；提供一键迁移提示 |
| B2 | 删除 `setup.py` | 仅影响源码安装者 | `pip install -e .` 行为不变 |
| B3 | Python 基线 3.10+ | 弃 3.8 / 3.9 | `Requires-Python` 声明；文档给出升级指引 |
| B4 | 内部符号加 `_` 前缀 | 少数用户可能引用了内部符号 | 保留旧名别名 + `DeprecationWarning` 一个 minor 周期 |
| B5 | `ValidationError` 导入路径收敛 | `forms.py` / `validators.py` / `exceptions.py` 三处 | 统一到 `litefs.exceptions`；旧路径保留别名 + 警告 |
| B6 | `core.py` 拆分后的私有方法迁移 | 极少数用户直接调 `core.py` 私有方法 | `_` 前缀标记为私有，文档明示不承诺兼容 |
| B7 | `Development Status` 分类升级 | 无运行时影响 | `4 - Beta` → `5 - Production/Stable` |
| B8 | pytest `filterwarnings=error` | 仅影响项目自身测试 | 用户测试不受影响 |

**范围约束**：以上 8 项之外，1.0.0 不引入新的破坏性变更。已弃用但未列入的项，一律推迟到 2.0。

---

## 六、超 600 行文件拆分方案

| 文件 | 当前行数 | 拆分方案 | 目标 |
|------|---------|---------|------|
| `handlers/socket.py` | 828 | 抽出 `socket_request.py`（请求解析）/ `socket_response.py`（响应序列化）/ `socket_multipart.py`（multipart 解析） | 3 个 ≤350 行 |
| `server/greenlet.py` | 780 | 抽出 `greenlet_request.py`（请求处理）/ `greenlet_worker.py`（多进程 worker 与信号） | 2 个 ≤450 行 |
| `error_pages.py` | 775 | 模板外置为 `templates/error/*.html`，类内仅保留渲染逻辑 | ≤200 行 |
| `handlers/base.py` | 639 | 抽出 `handlers/properties.py`（请求属性访问器） | 2 个 ≤400 行 |
| `config.py` | 628 | 抽出 `config/env.py`（环境变量解析） | 2 个 ≤400 行 |

**约束**：拆分过程中公开 API 与运行时行为零变化；每个文件拆分后立即跑全量回归；优先使用延迟导入规避循环依赖（`core.py` 拆分已验证该路径可行）。

---

## 七、Definition of Done（1.0 验收门禁）

全部满足方可发布 v1.0.0：

| # | 门禁项 | 判定方式 |
|---|--------|---------|
| 1 | 《API 稳定性与 SemVer 政策》已发布并经评审 | 文档存在 + 评审记录 |
| 2 | 196 个公共符号完成 `stable` / `experimental` 分级 | 清单文件 + 逐项 `__all__` 核对 |
| 3 | `mypy --strict src/` 零错误、零豁免 | CI lint 门禁 `allow_failure: false` |
| 4 | `py.typed` 随 wheel 正确分发 | 解包 wheel 验证 |
| 5 | 整体覆盖率 ≥85%，核心模块 ≥80% | `coverage report --fail-under=85` |
| 6 | `filterwarnings = error` 生效 | pytest 配置核对 |
| 7 | 全部源文件 ≤600 行 | 脚本校验纳入 CI |
| 8 | ASGI lifespan 可被 uvicorn / hypercorn 托管 | 集成测试用例 |
| 9 | `TestClient` 可用 | 单元测试 + 文档示例 |
| 10 | `entry_points` 插件可被发现 | 集成测试 + 示例 |
| 11 | GitHub PR 级 CI 全部通过 | PR 状态检查 |
| 12 | 迁移指南 + 变更日志齐备 | 文档评审 |
| 13 | Python 3.10–3.14 矩阵全绿 | CI 矩阵 |
| 14 | `SECURITY.md` + SBOM + 签名就绪 | 发布产物核验 |
| 15 | 无未登记的破坏性变更 | 破坏性变更清单逐条核对 |

---

## 八、风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| **核心服务器覆盖率补齐耗时超预期** | 高 | 优先用「协议级」测试（构造真实 socket 报文驱动 `SocketRequestHandler`）而非逐方法 mock，可显著压缩用例数 |
| `mypy --strict` 收敛后暴露大量 `Any` 泄漏 | 高 | P0-7 与 P0-8 并行；先收敛 `app/`（已有基础），再向外扩散；必要时以 `TypeAlias` 收窄边界类型 |
| optional 化后用户环境碎片化 | 中 | 提供 `litefs[full]` 一键全装；启动时对缺失可选依赖给出**明确的中文错误提示与安装命令**（不做静默降级） |
| 1.0 承诺后被紧急修复破坏 | 中 | 建立 `1.0` 稳定分支；约定紧急修复需走补丁号且必须补回归用例 |
| 性能回退 | 中 | 复用已有 `tests/performance/thresholds.json` 门禁，RPS 不得低于 v0.9.0 基线 |
| 文档版本化与代码脱节 | 低 | CI 中加「文档代码块可执行性」抽样检查 |

---

## 九、里程碑与版本策略

```
v0.9.0  ── 2026-10-21 ── 技术债务清理 & 架构统一（已完成）
   │
v1.0.0-alpha   P0 契约先行：API 政策 + 分级冻结 + 破坏性变更执行 + strict mypy
   │
v1.0.0-beta    P1 协议与生态：ASGI lifespan + streaming + entry_points + PR CI
   │
v1.0.0-rc      P2 打包发布：删 setup.py + optional 化 + 文档站 + SBOM/签名
   │
v1.0.0         P3 正式发布：回归 + 迁移指南 + 打标签 + PyPI + 1.0 稳定分支
   │
v1.0.x         仅安全与严重缺陷修复
   │
v1.1.x         OpenTelemetry 可选中间件
   │
v1.2.x         HTTP/2 支持
   │
v2.0.x         ASGI 原生重写 / HTTP/3 / 边缘轻量构建
```

### LTS 政策（对标 Django）

| 规则 | 内容 |
|------|------|
| 命名 | `X.0` 为 LTS 版本（如 `1.0`） |
| 频率 | 每 2 年一个 LTS |
| 支持期 | 3 年（mainstream 约 8 个月 + extended 约 2 年） |
| 微版本 | 不限（如 Django 4.2 出了 30 个微版本） |
| 回补 | 同一 LTS 分支内的安全修复同时回补到上一个 LTS |
| 优先级 | 安全问题优先于向后兼容承诺 |

### 弃用策略（对标 Django / Starlette）

- 弃用项必须同时标注「替代方案」与「计划移除版本」
- 弃用后**至少保留 2 个 feature release** 才可移除
- 移除只发生在 major 版本
- 每次移除在 `CHANGELOG.md` 单列 `Removed` 专章

---

## 十、v1.x 长期技术方向

| 方向 | 说明 | 目标版本 |
|------|------|---------|
| **协议层抽象** | HTTP / WSGI / ASGI / WebSocket 统一为 Protocol 抽象层，新协议只需实现接口 | v2.x |
| **ASGI 原生化** | scope / receive / send 直通，WebSocket 纳入 ASGI scope，可与 Starlette 中间件完全互操作 | v2.x |
| **HTTP/2 / HTTP/3** | `h2` 帧层 / aioquic QUIC 栈 | v1.2 / v2.x |
| **OpenTelemetry** | 原生 `OpenTelemetryMiddleware`，与现有 Prometheus 并存 | v1.1 |
| **边缘轻量构建** | 去除 SQLAlchemy / greenlet 重依赖，产出 `litefs-lite` 变体，支持 Serverless | v2.x |
| **热点路径加速** | 路由匹配与序列化路径的 Rust / C 扩展，uvloop 集成 | v2.x |
| **插件市场** | 基于 `entry_points` 的官方插件目录与兼容性矩阵 | v1.3 |

---

## 十一、文档产出物

| 文档 | 路径 | 说明 |
|------|------|------|
| API 稳定性政策 | `docs/source/api-stability.md` | 1.0 核心承诺 |
| 弃用时间表 | `docs/source/deprecation-timeline.md` | 逐项标注计划移除版本 |
| 迁移指南 | `docs/source/migration-v1.md` | v0.9.0 → v1.0.0 逐步说明 |
| 公共 API 分级清单 | `docs/source/api-stability.md`（附录） | 196 个符号逐项判定 |
| 安全策略 | `SECURITY.md`（仓库根目录） | 漏洞报告与响应流程 |
| 本文 | `docs/source/v1-roadmap.md` | 本方案 |

---

**文档维护**: 开发团队
**评审状态**: 待评审
**上次更新**: 2026-10-21
