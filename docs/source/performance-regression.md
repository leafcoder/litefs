# Litefs 性能回归基准

**文档版本**: 1.0
**最后更新**: 2026-10-21

---

## 概述

性能回归是指新版本发布后，吞吐量下降或延迟抬升。此类问题无法靠功能测试发现——
测试只验证"功能是否正确"，不验证"性能是否退步"。本文档说明 Litefs 如何通过
**基线 + 阈值 + 自动比对** 的方式，把性能退步挡在发布之前。

核心思路：

```
        压测                        基线固化                  自动比对
  ┌──────────────┐          ┌────────────────┐        ┌────────────────┐
  │ wrk 打满服务  │  ──────> │ data.json      │  ────> │ compare_       │
  │ 4 类服务形态  │          │ + thresholds.  │        │ benchmark.py   │
  │ 16 组场景     │          │   json         │        │ → PASS / FAIL  │
  └──────────────┘          └────────────────┘        └────────────────┘
```

## 组成

| 文件 | 作用 |
| --- | --- |
| `benchmarks/run_benchmark.py` | 压测驱动脚本，拉起服务并调用 `wrk` 采集数据 |
| `benchmarks/results/<时间戳>/data.json` | 单次压测的原始结果 |
| `benchmarks/thresholds.json` | **已提交**的阈值基线，版本化的性能契约 |
| `benchmarks/compare_benchmark.py` | 比对工具，判定是否发生性能回退 |
| `benchmarks/Makefile` | 压测套件的命令入口 |

## 阈值基线

`benchmarks/thresholds.json` 是**提交到版本库**的性能契约，结构如下：

```json
{
  "$schema_version": 1,
  "baseline": {
    "timestamp": "20260420_153048",
    "source": "benchmarks/results/latest/data.json",
    "tolerance": "RPS 下限 = 基线 × 0.85；P99 上限 = 基线 × 1.30"
  },
  "thresholds": {
    "litefs_greenlet": {
      "1-500": {"min_rps": 6200.0, "max_p99_ms": 165.0},
      "1-1000": {"min_rps": 6400.0, "max_p99_ms": 225.0}
    }
  }
}
```

### 索引键

阈值以 **`<server_type>-<workers>-<connections>`** 三元组为索引：

- `server_type`：`litefs_greenlet` / `litefs_asgi` / `litefs_wsgi` / `fastapi`
- `workers`：进程数（1 或 6）
- `connections`：并发连接数（500 或 1000）

4 种服务形态 × 2 组进程数 × 2 组并发数 = **16 组场景**，每组 2 项指标（RPS、P99），
共 32 项检查。

### 容忍带设计

阈值不是基线本身，而是基线的一个**容忍带**：

| 指标 | 阈值计算 | 含义 |
| --- | --- | --- |
| `min_rps` | 基线 RPS × **0.85** | 吞吐下降超过 15% 即判定回退 |
| `max_p99_ms` | 基线 P99 × **1.30** | P99 延迟上升超过 30% 即判定回退 |

选择容忍带而非零容忍的原因：

1. **压测结果存在天然抖动**。同一份代码在两次独立压测中，RPS 波动 3%~8% 属正常现象
   （受 CPU 频率调度、TCP 慢启动、页缓存冷热影响）。零容忍会产生大量假阳性。
2. **吞吐与延迟的容忍带宽不对称**。吞吐是稳定的宏观量，抖动幅度小；P99 尾延迟受
   GC、调度抢占影响大，波动可达 20% 以上。因此延迟侧给更宽的带。
3. **容忍带 = 可接受的回退预算**。15% 的吞吐下降在业务上通常已可感知，
   超过即应在发布说明中说明原因。

## 使用方式

### 日常压测 + 比对

```bash
# 1. 安装依赖（含 wrk）
cd benchmarks
make install

# 2. 运行压测（10s 持续时间，1/6 进程，500/1000 并发）
make benchmark

# 3. 与阈值基线比对
make check
```

从仓库根目录也可以直接：

```bash
make benchmark          # 代理到 benchmarks/Makefile
make benchmark-check    # 只做阈值比对
```

### 比对报告

```text
==============================================================================
性能回归比对报告
==============================================================================
场景                         指标                   实际值         阈值  结论
------------------------------------------------------------------------------
litefs_greenlet-1P-c500    requests_per_sec       7300.00 rps      >= 6200  PASS
litefs_greenlet-1P-c500    latency_p99_ms          128.40 ms      <= 165  PASS
------------------------------------------------------------------------------
合计: 32 项检查，32 项通过，0 项失败
==============================================================================
```

### 机器可读输出

```bash
python benchmarks/compare_benchmark.py --json
```

JSON 模式下 **stdout 仅输出 JSON 文档**，结论行写入 stderr，便于 CI 解析与归档：

```json
{
  "results_file": "benchmarks/results/latest/data.json",
  "thresholds_file": "benchmarks/thresholds.json",
  "total": 32,
  "failed": 0,
  "passed": 32,
  "comparisons": [
    {
      "server_type": "litefs_greenlet",
      "workers": 1,
      "connections": 500,
      "metric": "requests_per_sec",
      "actual": 7300.0,
      "limit": 6200.0,
      "passed": true
    }
  ]
}
```

## 退出码语义

| 退出码 | 含义 | 触发条件 |
| --- | --- | --- |
| `0` | 通过 | 所有比较项均在阈值内 |
| `1` | **性能回退** | 至少一项越界 |
| `2` | 输入缺失 | 结果/阈值文件缺失或格式错误，且启用了 `--strict` |

默认（非严格模式）下，结果或阈值文件缺失时输出 `[SKIP]` 并返回 `0`，
避免误伤流水线；`--strict` 会将缺失视为失败。

```bash
python benchmarks/compare_benchmark.py --strict
```

## 与 CI 的关系

**压测不在 CI 中执行**。原因有三：

1. **CI 容器无 `wrk`**。压测依赖 `wrk` 这一外部工具，且需要系统级调优参数。
2. **压测需要独占资源**。共享 Runner 上的 CPU 争抢会让 RPS 数据完全失真，
   阈值比对必然产生假阳性。
3. **压测耗时长**。完整一轮 16 组场景需要数十分钟，会拖慢整个流水线。

因此 CI 中的 `benchmark-regression` job 只做一件事：**校验已提交的基线是否自洽**，
即 `data.json` 与 `thresholds.json` 的场景覆盖是否匹配、是否存在无人维护的孤儿阈值。
该 job 标记为 `allow_failure: true`，不阻塞发布。

```yaml
benchmark-regression:
  stage: verify
  extends: .python
  script:
    - echo ">>> 校验性能基线与阈值一致性"
    - python benchmarks/compare_benchmark.py
  allow_failure: true
```

真正的性能门禁在**发布前**由人工在专用压测机上执行：

```bash
make benchmark && make benchmark-check
```

## 基线更新流程

当框架做了**有意的性能优化**（如换用更快的序列化库、调整路由匹配算法），
或硬件环境变更（换机型、升级 CPU）时，需要重新固化基线：

1. 在**规格一致的机器**上跑完整压测：

   ```bash
   cd benchmarks && make clean && make benchmark
   ```

2. 确认新结果的波动在可接受范围内（建议连跑 3 次，取中位数）。

3. 更新 `benchmarks/thresholds.json`：
   - 用新基线重新计算 `min_rps = 基线 × 0.85`、`max_p99_ms = 基线 × 1.30`
   - 更新 `baseline.timestamp` 与 `baseline.source`
   - 保持 `$schema_version` 不变

4. 提交 `thresholds.json` 变更，并在提交说明中写明**基线变更原因**。

> **红线**：性能退化不得通过"下调阈值"来"修复"。若比对失败，正确做法是
> **定位并修复性能问题**；只有在确认是环境变更（换机型、换压测参数）导致基线漂移时，
> 才允许更新阈值，并在 PR 中说明。

## 常见问题

**Q：新增了一组压测场景，阈值文件怎么加？**

A：在 `thresholds.json` 对应的 `server_type` 下新增 `"<workers>-<connections>"` 键，
值为 `{"min_rps": ..., "max_p99_ms": ...}`。比对脚本会自动遍历阈值文件，
无需改动代码。

**Q：基线里有的场景在新结果中缺失，会怎样？**

A：跳过该项比较（`continue`），不算失败。这是为了容忍压测中途中断的场景。
若希望缺失即失败，使用 `--strict`。

**Q：为什么阈值文件的键是字符串 `"6-500"` 而不是数组？**

A：JSON 对象的键只能是字符串。用 `"<workers>-<connections>"` 复合键可在
O(1) 时间内定位阈值，且天然有序，便于人工审阅 diff。

**Q：WSGI 模式的 P99 明显高于其他模式，正常吗？**

A：正常。WSGI 模式下每次请求都要经过完整的 WSGI 协议栈（environ 构造、
响应迭代器封装），且在 `litefs_wsgi` 基线中 P99 上限本来就显著高于
`litefs_greenlet` / `litefs_asgi`。横向比较绝对值没有意义，回归检测只看
**同一 server_type 自身相对基线的变化**。

## 相关文档

- :doc:`performance-benchmark` —— 基准测试套件与压测方法论
- :doc:`asgi-deployment` —— ASGI 部署与并发模型
- :doc:`wsgi-deployment` —— WSGI 部署与进程模型
- :doc:`static-checks` —— 静态检查规范
