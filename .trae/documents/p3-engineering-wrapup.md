# P3 工程化收尾实施计划

**创建日期**: 2026-10-21
**目标**: 完成 `docs/source/todolist.md` 中 P3 阶段的三项任务
**上游**: P0/P1/P2 已完成并通过全量验证（pytest 1586 passed / flake8+ruff+mypy 全绿 / Sphinx 30 warnings）

---

## 一、目标范围

P3 包含三个相互独立的子任务：

| 子任务 | 目标 |
|--------|------|
| P3-1 性能回归基准 | 以 `benchmarks/` 为基础固化阈值，防止发布回退 |
| P3-2 示例与文档同步 | 新功能各配 1 个可运行示例，同步 `examples/README.md`，修复失效交叉引用 |
| P3-3 依赖安全审计 | pip-audit 定期扫描，接入 CI 与 Makefile |

---

## 二、关键技术决策

### P3-1 性能回归基线

**决策：复用现有基准引擎，不重造。**

现有资产：
- `benchmarks/run_benchmark.py`：wrk 驱动的基准采集脚本，输出 `results/<ts>/data.json`
- `benchmarks/results/latest/data.json`：基线结果（20260420_153048，16 组数据，4 种 server_type × 2 workers × 2 connections）
- `benchmarks/Makefile`：install / benchmark / report / clean 目标

实现方式：
1. `benchmarks/thresholds.json` —— 固化阈值，按 `server_type` + `workers` + `connections` 三元组索引，
   每项包含 `min_rps`（吞吐下限）与 `max_p99_ms`（P99 延迟上限）。
   阈值按基线结果的 **85%** 设定，容忍环境抖动，同时能捕获真实回退。
2. `benchmarks/compare_benchmark.py` —— 纯标准库实现，读取 `results/latest/data.json` 与
   `thresholds.json` 逐项对比，输出表格化报告；任一项越界则退出码 1。
   阈值文件缺失或基线数据缺失时以明确信息跳过（不误伤 CI）。
3. CI 侧 `benchmark-regression` job：**仅做「已提交基线的一致性检查」**，不在 CI 内跑 wrk
   （CI 环境无 wrk，且压测需要独占资源）。job 为 `allow_failure: true`，
   本地 `make benchmark && make benchmark-check` 完成真正的压测与比对。

**为什么阈值取基线的 85%**：单机压测受 CPU 频率、内存带宽、后台进程影响明显，
波动幅度常达 ±10%；15% 的容忍带既能过滤噪声，又能捕获 20% 以上的真实回退。

### P3-2 示例与文档同步

**决策：新增 4 个示例（P1 两项 + P2 两项），并重写失效的 `examples/README.md`。**

现状问题：
- `examples/` 实际目录为 `01-quickstart` … `05-production`（5 个）
- 但 `examples/README.md` 描述的是 `01-hello-world` … `12-enhanced-logging`（12 个），
  **全部不存在**，属过时文档，需按「及时清除不再准备的文档内容」规则重写
- `docs/source/celery-integration.md:146` 与 `docs/source/openapi-integration.md:177`
  交叉引用 `examples/16-celery-tasks/app.py`、`examples/17-openapi-docs/app.py`，
  两者均不存在 → Sphinx 产生 `myst.xref_missing` 警告

新增示例目录（延续现有两位数编号）：

| 目录 | 对应功能 | 对应文档 |
|------|---------|---------|
| `06-prometheus-monitoring/` | Prometheus 指标暴露 | prometheus-monitoring.md |
| `07-database-migrations/` | Alembic 迁移管理 | database-migrations.md |
| `08-mail-service/` | SMTP 发送 + Mako 模板 | mail-service.md |
| `09-i18n/` | locale 协商 + 模板翻译 | i18n.md |

每个示例包含 `app.py`（可独立运行）+ 必要资源（模板 / 配置 / locales）。

失效交叉引用处理：celery 指向实际存在的 `examples/05-production/celery_tasks.py`；
openapi 无对应示例目录，改为指向 `examples/02-rest-api/app.py` 的 API 路由组织方式说明，
并在文档中明确说明「暂无独立示例目录」。

### P3-3 依赖安全审计

**决策：pip-audit + 自研脚本包装 + CI 定期任务。**

- `scripts/audit_deps.py`：调用 `pip-audit`（通过 `python -m pip_audit`），
  支持 `--format json|text`、`--output` 落盘；pip-audit 未安装时给出明确安装指引并返回非零
- 根 `Makefile` 新增 `audit` 目标
- CI 新增 `security` stage，`allow_failure: true`（安全漏洞不阻断开发期合并，
  但保留可见性；发布前应人工确认结果）

---

## 三、文件清单

### 新增

```text
benchmarks/thresholds.json            # 性能阈值基线
benchmarks/compare_benchmark.py       # 回归比对脚本
scripts/audit_deps.py                 # 依赖安全审计脚本
examples/06-prometheus-monitoring/    # Prometheus 示例
examples/07-database-migrations/      # Alembic 迁移示例
examples/08-mail-service/             # 邮件发送示例
examples/09-i18n/                     # 国际化示例
docs/source/performance-regression.md # 性能回归文档
docs/source/dependency-audit.md       # 依赖审计文档
tests/unit/test_compare_benchmark.py  # 比对脚本单元测试
```

### 修改

```text
benchmarks/Makefile                   # 新增 check 目标
Makefile                              # 新增 benchmark-check / audit 目标
.gitlab-ci.yml                        # 新增 benchmark-regression / security job
examples/README.md                    # 重写（清理 12 个不存在的旧示例）
docs/source/index.rst                 # toctree 追加 performance-regression、dependency-audit
docs/source/celery-integration.md    # 修正失效交叉引用
docs/source/openapi-integration.md   # 修正失效交叉引用
docs/source/todolist.md               # P3 标记完成
```

---

## 四、实施步骤

1. P3-1：`thresholds.json` → `compare_benchmark.py` → 单测 → Makefile → CI job → 文档
2. P3-2：4 个示例 → `examples/README.md` 重写 → 交叉引用修正 → index.rst
3. P3-3：`audit_deps.py` → Makefile → CI job → 文档
4. 更新 `todolist.md`，阶段进度改为 P0 ✅ → P1 ✅ → P2 ✅ → **P3 ✅**
5. 全量验证

---

## 五、验证命令

```bash
# 静态检查
python -m flake8 src tests/unit/test_compare_benchmark.py scripts/audit_deps.py benchmarks/compare_benchmark.py
python -m ruff check src
python -m mypy src

# 单元测试
python -m pytest tests/unit/test_compare_benchmark.py -q
python -m pytest -q                      # 对比基线 1586 passed

# 性能回归比对（使用已提交基线）
python benchmarks/compare_benchmark.py

# 文档构建
cd docs && make clean html               # 对比基线 30 warnings
```

---

## 六、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 压测数据缺失导致 CI 误报 | 中 | 阈值文件或基线数据缺失时脚本输出「跳过」而非失败 |
| 阈值过紧导致频繁误报 | 中 | 容忍带取基线 85%，阈值可由 `make benchmark` 后人工复核调整 |
| 示例代码与框架行为漂移 | 中 | 示例使用框架公开 API，不使用内部实现；CI lint 覆盖 examples 目录 |
| pip-audit 未安装导致 CI 失败 | 低 | 脚本检测安装状态并给出安装指引；job 为 allow_failure |
| 新增示例引入循环依赖 | 低 | 示例只依赖 `litefs` 公开接口 |

---

## 七、硬约束

- 新增模块不得进入 `pyproject.toml` 的 mypy ignore 列表
- flake8 max-line-length = 100；单文件 ≤ 600 行
- 注释 / docstring / 文档全中文；verbose_name 用中文
- Python 代码生成后必须通过 flake8
- 不主动 commit
