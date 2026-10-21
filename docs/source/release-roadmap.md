# Litefs 版本演进路线（0.10.0 → 1.0.0）

> 定位：**生产就绪** —— API 稳定承诺 + 质量硬指标达标
> 基线版本：v0.9.0（`cb2988f`）
> 编制日期：2026-10-21
> 对标对象：**Starlette**（近 8 年唯一真正走完 0.x → 1.0 的同代 ASGI 框架）
> 核心原则：**硬性标准未全部达成，不升 v1.0**

---

## 一、路线调整说明（决策变更记录）

### 1.1 变更内容

| 项 | 原方案（2026-10-21 初版） | 现方案（本版） |
|---|---------------------------|---------------|
| 交付形态 | v1.0.0 一次性执行 P0–P3 全部内容 | 拆分为 **6 个 0.x.x 版本**，逐版交付可发布成果 |
| 破坏性变更 | 集中在 v1.0.0 一次性执行（B1–B8） | **分散到各 0.x 版本**，利用 SemVer 0.x 允许破坏的特性 |
| v1.0.0 性质 | 「大量变更的交付版本」 | **「稳定性声明版本」** —— 几乎零代码变更，只做 API 冻结宣告 + 政策定稿 + 标签 |
| 晋级条件 | 一次性满足 15 条 DoD | **每一版 0.x 都是可发布版本**；15 条 DoD 全部达成才允许打 v1.0.0 标签 |
| 发布粒度 | 1 次大版本 | 7 次发布（0.10.0 – 0.15.0 + 1.0.0），每次均含 CHANGELOG 与 Release Notes |

**变更理由**：行业数据显示 0.x → 1.0 的中位耗时是 3–8 年（Starlette 7.8 年，Flask 约 8 年，FastAPI 8 年仍未达成 1.0）。把 3–8 年的工程量压进单次发布，风险不可控且无法持续验证。分版本路线让每一批改动都被真实用户验证过 —— **1.0 应该是「验证完毕的既有事实」，而不是「一次性押注的未来承诺」**。

### 1.2 SemVer 0.x 下的破坏性变更处理

SemVer 规范中 `0.y.z` 阶段「任何变更都可能发生」，因此：

- **0.x 阶段**：`0.MINOR` 位递增即视为破坏性版本（Django 1.0 前、Flask 1.0 前均遵循此惯例）。跨 `0.MINOR` 边界的破坏性变更**无需弃用期**，但必须在 CHANGELOG 单列 `Changed` / `Removed` 专章。
- **1.0 之后**：破坏性变更只走 major，且弃用项须在移除前保留至少 2 个 feature release（对标 Django）。
- **0.x 阶段的过渡期保护**：对**用户可见的公共 API**（`litefs.__all__` 中的 stable 分级符号），即使在 0.x 阶段也须至少保留 1 个 minor 版本的 `DeprecationWarning` 过渡；纯内部重构（`_` 前缀符号）不受此约束。

### 1.3 与既有决策的关系

- 决策「范围定位 = 聚焦稳定性硬指标」**保持不变**。
- 决策「Python 基线 = 3.10–3.14」**保持不变**，落地于 v0.14.0。
- 决策「ASGI 深度 = 渐进增强」**保持不变**，落地于 v0.13.0。
- 原决策「破坏性变更 = 1.0.0 一次性执行」**被本方案覆盖**，改为分散执行。

---

## 二、为什么是现在，以及对标谁

### 2.1 行业 1.0 的现实参照

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

### 2.2 业界公认的「可以叫 1.0」判据（按重要性排序）

| # | 判据 | 行业实践 | Litefs 现状 | 交付版本 |
|---|------|---------|------------|---------|
| 1 | 成文的 API 稳定性承诺 + 严格 SemVer | Django《API stability》指南、Starlette 1.0 博客「We'll follow SemVer strictly」 | ❌ 无 | v0.10.0 |
| 2 | 长弃用期，破坏性变更只走 major | Django：弃用后至少保留 2 个 feature release | ❌ 无弃用机制 | v0.10.0 |
| 3 | 覆盖率成为硬门禁 | FastAPI / Starlette 公开声明 **100% 覆盖率**，pytest 开 `filterwarnings=error` | ⚠️ 72.2%，无 `fail_under` | v0.12.0 |
| 4 | 完整类型注解 + `py.typed` + `mypy --strict` | Starlette / FastAPI 均 `strict = true`；Django 是唯一无 `py.typed` 的一线框架 | ❌ 无 `py.typed`，53 模块豁免 | v0.11.0 |
| 5 | 明确的 Python 版本淘汰节奏 | Starlette 1.8 抬到 3.11、Sanic 25.12 弃 3.9、Quart 0.23 抬到 3.13 | ⚠️ 3.8–3.12，3.8 已 EOL | v0.14.0 |
| 6 | 安全响应闭环（GHSA / CVE / 分支回补） | Django 明确「security trumps the compatibility guarantee」 | ⚠️ 有依赖审计，无响应流程 | v0.15.0 |
| 7 | 版本化文档 + 迁移指南 + 废弃时间表 | Django 有专门的 Deprecation Timeline 页 | ❌ 无 | v0.10.0 / v0.15.0 |
| 8 | 生态可互操作（ASGI 中间件规范、插件注册） | Starlette `BaseHTTPMiddleware` 互操作 | ❌ 无 lifespan、无 entry_points | v0.13.0 |

### 2.3 Litefs 硬性标准总表（15 条 DoD）

全部满足方可发布 v1.0.0。每条标注交付版本。

| # | 硬性标准 | 判定方式 | 交付版本 |
|---|---------|---------|---------|
| H1 | 《API 稳定性与 SemVer 政策》已发布并经评审 | 文档存在 + 评审记录 | v0.10.0 |
| H2 | 196 个公共符号完成 `stable` / `experimental` 分级 | 清单文件 + 逐项 `__all__` 核对 | v0.10.0 |
| H3 | 全部源文件 ≤600 行 | 脚本校验纳入 CI | v0.10.0 |
| H4 | `py.typed` 随 wheel 正确分发 | 解包 wheel 验证 | v0.11.0 |
| H5 | `mypy --strict src/` 零错误、零豁免 | CI lint 门禁 `allow_failure: false` | v0.11.0 |
| H6 | 弃用机制与废弃时间表就位 | `DeprecationWarning` 工具 + 时间表文档 | v0.10.0 |
| H7 | 整体覆盖率 ≥85% | `coverage report --fail-under=85` | v0.12.0 |
| H8 | 核心模块覆盖率 ≥80% | `handlers/socket.py` / `server/greenlet.py` / `app/server_mixin.py` ≥80%，`websocket/` ≥75% | v0.12.0 |
| H9 | `filterwarnings = error` 生效 | pytest 配置核对 | v0.12.0 |
| H10 | `TestClient` 与 `tests/conftest.py` 就位 | 单元测试 + 文档示例 | v0.12.0 |
| H11 | ASGI lifespan 可被 uvicorn / hypercorn 托管 | 集成测试用例 | v0.13.0 |
| H12 | ASGI 中间件签名兼容 + `entry_points` 插件可被发现 | 集成测试 + 示例 | v0.13.0 |
| H13 | GitHub PR 级 CI 全部通过 + Python 3.10–3.14 矩阵全绿 | PR 状态检查 + CI 矩阵 | v0.14.0 |
| H14 | `SECURITY.md` + SBOM + 签名就绪 + 版本化文档站 | 发布产物核验 | v0.15.0 |
| H15 | 迁移指南 + 变更日志齐备，无未登记的破坏性变更 | 文档评审 + 破坏性变更清单逐条核对 | v0.15.0 / v1.0.0 |

---

## 三、0.x.x 版本路线总览

### 3.1 版本序列

```
v0.9.0  ── 2026-10-21 ── 技术债务清理 & 架构统一（已发布）
   │
v0.10.0  契约与结构重构   API 政策 + 符号分级 + 弃用机制 + 拆分 5 个大文件
   │
v0.11.0  类型系统与打包契约 py.typed 落盘 + mypy --strict 零豁免
   │
v0.12.0  测试基础设施与质量基线 conftest + TestClient + 覆盖率 ≥85% + warnings 严格化
   │
v0.13.0  ASGI 协议与插件生态  lifespan + streaming + 中间件兼容 + entry_points
   │
v0.14.0  工程化与 Python 基线收敛 PR CI 门禁 + 删 setup.py + 依赖 optional 化 + 3.10–3.14
   │
v0.15.0  发布基础设施与安全闭环 SECURITY.md + SBOM/签名 + 版本化文档站 + 迁移指南
   │
v1.0.0   稳定性声明发布   API 冻结宣告 + 政策定稿 + 标签（几乎零代码变更）
   │
v1.0.x   仅安全与严重缺陷修复（1.0 稳定分支）
   │
v1.1.x   OpenTelemetry 可选中间件
   │
v1.2.x   HTTP/2 支持
   │
v2.0.x   ASGI 原生重写 / HTTP/3 / 边缘轻量构建
```

### 3.2 判据 × 版本覆盖矩阵

| 版本 | 主题 | 绑定判据 | 可发布的独立价值 | 工作量 |
|------|------|---------|----------------|--------|
| **v0.10.0** | 契约与结构重构 | ① ② ⑦ | 用户可依赖「哪些 API 会变、什么会被弃用」，代码结构达标 | ≈7d |
| **v0.11.0** | 类型系统与打包契约 | ④ | 首次提供完整类型支持，IDE 补全与静态检查全量可用 | ≈6d |
| **v0.12.0** | 测试基础设施与质量基线 | ③ | 质量可度量、可门禁，回归风险显著下降 | ≈12d |
| **v0.13.0** | ASGI 协议与插件生态 | ⑧ | 可被 uvicorn/hypercorn 直接托管，插件生态开放 | ≈10.5d |
| **v0.14.0** | 工程化与 Python 基线收敛 | ⑤ | 安装更轻，Python 淘汰节奏明确 | ≈8d |
| **v0.15.0** | 发布基础设施与安全闭环 | ⑥ ⑦ | 供应链可信，安全响应有流程 | ≈7d |
| **v1.0.0** | 稳定性声明发布 | 全部 8 条 | 兑现可依赖的长期承诺 | ≈4d |
| | | | **合计** | **≈54.5d** |

**每一版都是完整可发布版本**：CHANGELOG 更新、Release Notes、全量回归通过、性能基线不回退、GitHub Release 打标。不存在「半成品中间态发布」。

---

## 四、各版本详细规划

### 4.1 v0.10.0 —— 契约与结构重构

> 行业第一判据。**先立承诺，再动结构。**

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| 0.10-1 | 编写《Litefs API 稳定性与 SemVer 政策》 | `docs/source/api-stability.md` | 明确：稳定 API 定义、弃用流程、破坏性变更仅走 major、弃用后至少保留 2 个 minor（对标 Django） | 1d |
| 0.10-2 | 公共 API 分级与冻结 | `litefs/_stable.py` 清单 + 各子包 `__all__` 标注 | 196 个符号逐个判定 `stable` / `experimental` / `private`；`private` 加 `_` 前缀或移出 `__all__` | 2d |
| 0.10-3 | 弃用机制与时间表 | `DeprecationWarning` 工具 + `docs/source/deprecation-timeline.md` | 弃用项带「计划移除版本」；迁移指南模板就位 | 1d |
| 0.10-4 | 拆分 5 个超 600 行文件 | 见 §六 表 | 全部 ≤600 行；公开 API 零变更；全量回归通过 | 3d |

**本版允许的破坏性变更**：B4（内部符号加 `_` 前缀）、B5（`ValidationError` 导入路径收敛）、B6（`core.py` 拆分后私有方法迁移）。

**出口门禁**：

- [ ] H1、H2、H3、H6 达成
- [ ] 全部源文件 ≤600 行
- [ ] 全量 pytest 通过，无行为回归
- [ ] CHANGELOG 含 `Changed` / `Removed` 专章

### 4.2 v0.11.0 —— 类型系统与打包契约

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| 0.11-1 | `py.typed` 落盘 | `src/litefs/py.typed` + 打包配置 | wheel 内实际包含 `py.typed`（`twine check` + 解包验证） | 0.5d |
| 0.11-2 | `mypy --strict` 全量收敛 | 53 个豁免清零 | `mypy --strict src/` 零错误；CI 门禁切换为 strict | 5d |
| 0.11-3 | 公共 API 标注补齐 | 稳定符号补全类型注解与 docstring | 196 个 stable 符号 100% 有类型注解与文档 | 0.5d |

**出口门禁**：

- [ ] H4、H5 达成
- [ ] `mypy --strict src/` 零错误、零豁免（CI `allow_failure: false`）
- [ ] wheel 解包确认含 `py.typed`
- [ ] 运行时行为零变化（回归全绿）

### 4.3 v0.12.0 —— 测试基础设施与质量基线

> **本版是 1.0 最大的实质风险所在**：框架最核心的自研服务器代码覆盖率最低。

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| 0.12-1 | 核心服务器覆盖率补齐 | 新增测试模块 | `handlers/socket.py` ≥80%、`server/greenlet.py` ≥80%、`app/server_mixin.py` ≥80%、`websocket/` ≥75% | 6d |
| 0.12-2 | `tests/conftest.py` + 共享 fixtures | 测试基础设施 | `app` / `client` / `tmp_config` / `mock_redis` / `mock_memcache` 等 fixtures；测试重复代码下降 | 1d |
| 0.12-3 | `TestClient` 实现 | `litefs/testclient.py` | httpx 驱动，支持 WSGI + ASGI 两种 app，Cookie 持久化、状态码断言 | 2d |
| 0.12-4 | 覆盖率补齐（非核心模块） | 新增/扩充测试 | 整体 ≥85%；`app/` `cache/` `session/` `routing/` `middleware/` `auth/` 均 ≥80% | 5d |
| 0.12-5 | pytest 严格化 | `pyproject.toml` | 启用 `filterwarnings = error`；`--strict-markers --strict-config` 保持；`coverage fail_under = 85` | 1d |

**本版允许的破坏性变更**：B8（pytest `filterwarnings=error`，仅影响项目自身测试）。

**出口门禁**：

- [ ] H7、H8、H9、H10 达成
- [ ] `coverage report --fail-under=85` 通过
- [ ] `pytest` 在 `filterwarnings = error` 下全绿
- [ ] 性能回归门禁 RPS ≥ v0.9.0 基线

### 4.4 v0.13.0 —— ASGI 协议与插件生态

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| 0.13-1 | ASGI lifespan 协议 | `handlers/asgi.py` 支持 `scope['type'] == 'lifespan'` | uvicorn / hypercorn 直接托管 Litefs ASGI app 正常启停；`startup` / `shutdown` 钩子可注册 | 2d |
| 0.13-2 | 原生 ASGI streaming 响应 | 响应对象直通 `send()` | 不再经过 WSGI environ 转换；SSE / 流式大文件不缓冲 | 3d |
| 0.13-3 | ASGI 中间件签名兼容 | `litefs/middleware/asgi.py` | Starlette 风格 `async def mw(request, call_next)` 中间件可直接挂载 | 2d |
| 0.13-4 | `entry_points` 插件发现 | `plugins/loader.py` 双通道 | 支持 `[project.entry-points."litefs.plugins"]`；保留现有目录扫描 | 1.5d |
| 0.13-5 | 集成测试与示例 | 测试 + `examples/` | uvicorn/hypercorn 托管用例；entry_points 示例；streaming 示例 | 2d |

**出口门禁**：

- [ ] H11、H12 达成
- [ ] uvicorn / hypercorn 托管 Litefs ASGI app 启停正常
- [ ] Starlette 风格中间件可直接挂载并通过用例
- [ ] `entry_points` 插件可被发现（集成测试通过）

### 4.5 v0.14.0 —— 工程化与 Python 基线收敛

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| 0.14-1 | GitHub PR 级 CI 门禁 | `.github/workflows/ci.yml` | PR 触发 lint（flake8+ruff+mypy strict）+ test（3.10–3.14 矩阵）+ coverage 门禁；`allow_failure: false` | 2d |
| 0.14-2 | 删除 `setup.py` | 单一 `pyproject.toml` | 全部元数据迁入 PEP 621；`pip install .` 与 `python -m build` 均通过 | 1d |
| 0.14-3 | 核心依赖 optional 化 | `pyproject.toml` extras 重整 | `SQLAlchemy` / `watchdog` / `greenlet` 移出必装；`cache/cache.py` 与 `database/core.py` 的模块级 import 改为懒加载 | 2d |
| 0.14-4 | extras 矩阵重整 | `litefs[standard\|full\|db\|server\|mail\|i18n\|monitoring\|dev\|docs]` | 每个 extra 有明确用途与文档说明；`litefs[full]` 可复现全部功能 | 1d |
| 0.14-5 | Python 基线收敛 3.10–3.14 | `requires-python` + classifiers + CI 矩阵 | 弃 3.8/3.9；新增 3.13/3.14；`black` target-version 同步 | 1d |
| 0.14-6 | 可选依赖缺失时的友好提示 | 启动期检查 | 缺失可选依赖时给出**明确的中文错误提示与安装命令**（不做静默降级） | 1d |

**本版允许的破坏性变更**：B1（核心依赖 optional 化）、B2（删除 `setup.py`）、B3（Python 基线 3.10+）。

**出口门禁**：

- [ ] H13 达成
- [ ] PR 级 CI 三级门禁上线，Python 3.10–3.14 矩阵全绿
- [ ] `pip install litefs` 不再拉入 SQLAlchemy / watchdog / greenlet
- [ ] 迁移说明已在 CHANGELOG 给出（`pip install litefs[full]` 一键方案）

### 4.6 v0.15.0 —— 发布基础设施与安全闭环

| # | 任务 | 产出 | 验收标准 | 工作量 |
|---|------|------|---------|--------|
| 0.15-1 | `SECURITY.md` 与 CVE 响应流程 | 安全策略文档 + 私有报告通道 | 明确漏洞报告方式、响应时限、分支回补规则（对标 Django「安全优先于兼容承诺」） | 0.5d |
| 0.15-2 | SBOM 与签名发布 | `cyclonedx-py` 产物 + Sigstore 签名 | 每版发布附带 SBOM；wheel/sdist 签名并在 PyPI 展示 | 1.5d |
| 0.15-3 | 版本化文档站 | ReadTheDocs 配置 | 按版本发布；每版含迁移指南与废弃时间表 | 1.5d |
| 0.15-4 | LTS 政策 | 政策文档 | 对标 Django：每 2 年一个 LTS、支持期 3 年、LTS 命名为 `X.0` | 0.5d |
| 0.15-5 | 迁移指南 `migration-v1.md` | 文档 | 从 v0.9.0 逐版升级到 v0.15.0 的操作说明 + 0.15.0 → 1.0.0 预告 | 1.5d |
| 0.15-6 | 全量回归 + 性能基线复核 | 回归报告 | 覆盖率 ≥85%、mypy strict 零错误、pytest 全绿、RPS ≥ v0.9.0 基线 100% | 1.5d |

**出口门禁**：

- [ ] H14、H15 达成
- [ ] SBOM 与签名产物随发布产出
- [ ] 文档站可按版本访问
- [ ] 迁移指南覆盖 0.9.0 → 0.10.0 → … → 0.15.0 的全部破坏性变更

### 4.7 v1.0.0 —— 稳定性声明发布

> **本版几乎不做代码变更。** 当 0.10.0 – 0.15.0 逐版交付完毕、15 条硬性标准全部达成后，1.0.0 只是把「事实上已经稳定」的状态**正式宣告**出来。

| # | 任务 | 验收标准 | 工作量 |
|---|------|---------|--------|
| 1.0-1 | API 冻结确认 | 196 个符号分级清单签字冻结，stable 集合不再变更 | 0.5d |
| 1.0-2 | 《API 稳定性与 SemVer 政策》正式版定稿 | 文档从「草案」转「生效」，明确 1.0 后的兼容承诺 | 0.5d |
| 1.0-3 | `CHANGELOG.md` 破坏性变更汇总专章 | 汇总 0.9.0 → 1.0.0 全部 `Changed` / `Removed` 条目 | 0.5d |
| 1.0-4 | 全量回归 + 性能基线复核 | 覆盖率 ≥85%、mypy strict 零错误、pytest 全绿、RPS ≥ v0.9.0 基线 100% | 1d |
| 1.0-5 | `Development Status` 分类升级 | `4 - Beta` → `5 - Production/Stable`（B7） | 0.5d |
| 1.0-6 | 打标签 + 发布 + GitHub Release | `v1.0.0` 标签、PyPI 正式发布、Release Notes | 0.5d |
| 1.0-7 | `1.0` 稳定分支 | 建立 `1.0` 分支，仅接受安全与严重缺陷修复 | 0.5d |

**出口门禁（硬性）**：

- [ ] **H1 – H15 全部达成，无一例外**
- [ ] 0.10.0 – 0.15.0 全部已发布并可被用户安装
- [ ] `Development Status` 为 `5 - Production/Stable`
- [ ] v1.0.0 相对 v0.15.0 的代码变更量 ≤ 政策性改动（无功能性变更）

---

## 五、破坏性变更清单与分配

> 每项均须在 `docs/source/migration-v1.md` 中给出前后对照。

| # | 变更 | 影响 | 兼容处理 | 分配版本 |
|---|------|------|---------|---------|
| B1 | 核心依赖 optional 化 | `pip install litefs` 不再装 SQLAlchemy / watchdog / greenlet | 需功能者改用 `litefs[db]` / `litefs[standard]`；提供一键迁移提示 | v0.14.0 |
| B2 | 删除 `setup.py` | 仅影响源码安装者 | `pip install -e .` 行为不变 | v0.14.0 |
| B3 | Python 基线 3.10+ | 弃 3.8 / 3.9 | `Requires-Python` 声明；文档给出升级指引 | v0.14.0 |
| B4 | 内部符号加 `_` 前缀 | 少数用户可能引用了内部符号 | 保留旧名别名 + `DeprecationWarning` 一个 minor 周期 | v0.10.0 |
| B5 | `ValidationError` 导入路径收敛 | `forms.py` / `validators.py` / `exceptions.py` 三处 | 统一到 `litefs.exceptions`；旧路径保留别名 + 警告 | v0.10.0 |
| B6 | `core.py` 拆分后的私有方法迁移 | 极少数用户直接调 `core.py` 私有方法 | `_` 前缀标记为私有，文档明示不承诺兼容 | v0.10.0 |
| B7 | `Development Status` 分类升级 | 无运行时影响 | `4 - Beta` → `5 - Production/Stable` | v1.0.0 |
| B8 | pytest `filterwarnings=error` | 仅影响项目自身测试 | 用户测试不受影响 | v0.12.0 |

**范围约束**：以上 8 项之外，各 0.x 版本不引入新的破坏性变更。已弃用但未列入的项，一律推迟到 2.0。

---

## 六、超 600 行文件拆分方案（v0.10.0 交付）

| 文件 | 当前行数 | 拆分方案 | 目标 |
|------|---------|---------|------|
| `handlers/socket.py` | 828 | 抽出 `socket_request.py`（请求解析）/ `socket_response.py`（响应序列化）/ `socket_multipart.py`（multipart 解析） | 3 个 ≤350 行 |
| `server/greenlet.py` | 780 | 抽出 `greenlet_request.py`（请求处理）/ `greenlet_worker.py`（多进程 worker 与信号） | 2 个 ≤450 行 |
| `error_pages.py` | 775 | 模板外置为 `templates/error/*.html`，类内仅保留渲染逻辑 | ≤200 行 |
| `handlers/base.py` | 639 | 抽出 `handlers/properties.py`（请求属性访问器） | 2 个 ≤400 行 |
| `config.py` | 628 | 抽出 `config/env.py`（环境变量解析） | 2 个 ≤400 行 |

**约束**：拆分过程中公开 API 与运行时行为零变化；每个文件拆分后立即跑全量回归；优先使用延迟导入规避循环依赖（`core.py` 拆分已验证该路径可行）。

---

## 七、风险与对策

| 风险 | 等级 | 对策 |
|------|------|------|
| **核心服务器覆盖率补齐耗时超预期** | 高 | 优先用「协议级」测试（构造真实 socket 报文驱动 `SocketRequestHandler`）而非逐方法 mock，可显著压缩用例数；必要时将 v0.12.0 拆为 v0.12.0 / v0.12.1 两版 |
| **`mypy --strict` 收敛后暴露大量 `Any` 泄漏** | 高 | 0.11-2 与 0.12-1 并行；先收敛 `app/`（已有基础），再向外扩散；必要时以 `TypeAlias` 收窄边界类型 |
| **optional 化后用户环境碎片化** | 中 | 提供 `litefs[full]` 一键全装；启动时对缺失可选依赖给出**明确的中文错误提示与安装命令**（不做静默降级） |
| **0.x 版本序列拉得过长，用户产生疲劳** | 中 | 每版周期控制在 1–2 个迭代；每版必须有可感知的独立价值（类型支持 / 质量门禁 / ASGI 兼容 / 轻安装 / 安全闭环） |
| **1.0 承诺后被紧急修复破坏** | 中 | 建立 `1.0` 稳定分支；约定紧急修复需走补丁号且必须补回归用例 |
| **性能回退** | 中 | 每版复用 `tests/performance/thresholds.json` 门禁，RPS 不得低于 v0.9.0 基线 |
| **文档版本化与代码脱节** | 低 | CI 中加「文档代码块可执行性」抽样检查 |

---

## 八、版本策略、LTS 与弃用政策

### 8.1 里程碑与版本策略

```
0.x 阶段（v0.10.0 – v0.15.0）：minor 递增即可能含破坏性变更
   每一版独立可发布、独立验证、独立维护

1.0 之后：严格 SemVer
   破坏性变更只走 major；弃用项移除前至少保留 2 个 feature release
```

### 8.2 LTS 政策（对标 Django）

| 规则 | 内容 |
|------|------|
| 命名 | `X.0` 为 LTS 版本（如 `1.0`） |
| 频率 | 每 2 年一个 LTS |
| 支持期 | 3 年（mainstream 约 8 个月 + extended 约 2 年） |
| 微版本 | 不限（如 Django 4.2 出了 30 个微版本） |
| 回补 | 同一 LTS 分支内的安全修复同时回补到上一个 LTS |
| 优先级 | 安全问题优先于向后兼容承诺 |

### 8.3 弃用策略

- 弃用项必须同时标注「替代方案」与「计划移除版本」
- **0.x 阶段**：纯内部重构可直接 break（SemVer 允许）；用户可见的 stable 公共 API 须至少保留 1 个 minor 的 `DeprecationWarning` 过渡
- **1.0 之后**：弃用后**至少保留 2 个 feature release** 才可移除，且移除只发生在 major 版本
- 每次移除在 `CHANGELOG.md` 单列 `Removed` 专章

---

## 九、v1.x 长期技术方向

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

## 十、文档产出物

| 文档 | 路径 | 交付版本 |
|------|------|---------|
| API 稳定性政策 | `docs/source/api-stability.md` | v0.10.0 |
| 公共 API 分级清单 | `docs/source/api-stability.md`（附录，196 个符号逐项判定） | v0.10.0 |
| 弃用时间表 | `docs/source/deprecation-timeline.md` | v0.10.0 |
| 迁移指南 | `docs/source/migration-v1.md` | v0.15.0 |
| 安全策略 | `SECURITY.md`（仓库根目录） | v0.15.0 |
| 本文 | `docs/source/release-roadmap.md` | 本方案 |

---

**文档维护**: 开发团队
**评审状态**: 待评审
**上次更新**: 2026-10-21
