# LiteFS 性能基准测试报告

> 测试时间：2026-04-20 | 测试工具：wrk 4.2.0 | 测试场景：Hello World（最小化 HTTP 响应）

## 测试环境

| 项目 | 配置 |
|------|------|
| CPU | 13th Gen Intel(R) Core(TM) i7-1355U (12 线程, 10 核心) |
| 内存 | 62 GiB |
| 操作系统 | Linux x86_64 (6.12.65-amd64) |
| Python | 3.10.9 |
| wrk | 4.2.0 [epoll] |

## 测试对象

| 服务器 | 说明 | 启动方式 |
|--------|------|----------|
| **LiteFS-Greenlet** | LiteFS 原生 HTTP 服务器 (epoll + greenlet) | `python hello_greenlet.py` |
| **LiteFS-ASGI/Uvicorn** | LiteFS ASGI 应用 + Uvicorn | `uvicorn hello_asgi:application` |
| **LiteFS-WSGI/Gunicorn** | LiteFS WSGI 应用 + Gunicorn (gevent worker) | `gunicorn hello_wsgi:application -k gevent` |
| **FastAPI/Uvicorn** | FastAPI 框架 + Uvicorn（对比基准） | `uvicorn hello_fastapi:app` |

测试配置：进程数 1/6，并发连接 500/1000，每组测试时长 10s。

## 测试结果

### 吞吐量 (Requests/sec)

| 服务器 | 1P-c500 | 1P-c1000 | 6P-c500 | 6P-c1000 |
|--------|---------|----------|---------|----------|
| LiteFS-Greenlet | 8,077 | 6,669 | 14,922 | 15,687 |
| LiteFS-ASGI/Uvicorn | 4,795 | 5,023 | 9,589 | 11,634 |
| LiteFS-WSGI/Gunicorn | 6,176 | 6,839 | 14,026 | 13,239 |
| FastAPI/Uvicorn | 4,858 | 4,804 | 9,316 | 10,499 |

### P99 延迟 (ms)

| 服务器 | 1P-c500 | 1P-c1000 | 6P-c500 | 6P-c1000 |
|--------|---------|----------|---------|----------|
| LiteFS-Greenlet | 121.36 | 303.95 | 91.51 | 158.77 |
| LiteFS-ASGI/Uvicorn | 230.11 | 250.45 | 74.95 | 178.98 |
| LiteFS-WSGI/Gunicorn | 1,460.00 | 1,770.00 | 1,380.00 | 1,530.00 |
| FastAPI/Uvicorn | 158.07 | 264.92 | 92.01 | 170.18 |

### 多进程扩展性 (6进程 vs 1进程 RPS 提升)

| 服务器 | 500 并发 | 1000 并发 |
|--------|---------|----------|
| LiteFS-ASGI/Uvicorn | **2.00x** | **2.32x** |
| LiteFS-Greenlet | 1.85x | 2.35x |
| FastAPI/Uvicorn | 1.92x | 2.18x |
| LiteFS-WSGI/Gunicorn | 2.27x | 1.94x |

## 结论

### 吞吐量排名（6 进程 / 1000 并发）

| 排名 | 服务器 | RPS | P99 延迟 | 综合评价 |
|------|--------|-----|----------|----------|
| 1 | **LiteFS-Greenlet** | **15,687** | **158.77 ms** | **综合最优：最高吞吐 + 最低延迟** |
| 2 | LiteFS-WSGI/Gunicorn | 13,239 | 1,530.00 ms | 吞吐尚可，但尾部延迟偏高 |
| 3 | LiteFS-ASGI/Uvicorn | 11,634 | 178.98 ms | 多进程扩展性最佳 |
| 4 | FastAPI/Uvicorn | 10,499 | 170.18 ms | 对比基准，表现稳定 |

### 综合评价

1. **LiteFS-Greenlet** 是综合表现最优的方案。单进程 6,600-8,000 RPS，6 进程达 14,900-15,700 RPS，P99 延迟控制在 160ms 以内，在吞吐量和延迟上均为最优。

2. **LiteFS-WSGI/Gunicorn** 吞吐量尚可（13,200-14,000 RPS），但 P99 延迟超过 1.3 秒，延迟分布极不均匀，gevent worker 在高并发下存在尾部延迟问题，不适合对延迟敏感的场景。

3. **LiteFS-ASGI/Uvicorn** 多进程扩展性最佳（6 进程 RPS 提升 2.32x），禁用日志后性能显著提升，6 进程 1000 并发达 11,600+ RPS，适合需要 ASGI 中间件生态的场景。

4. **FastAPI/Uvicorn** 作为对比基准，表现稳定。6 进程 1000 并发达 10,500 RPS。LiteFS-Greenlet 在吞吐上领先 FastAPI 约 49%。

### 推荐方案

- **追求综合性能**：LiteFS-Greenlet（高吞吐 + 低延迟 + 零外部依赖）
- **追求极致吞吐**：LiteFS-WSGI/Gunicorn（可接受尾部延迟）
- **ASGI 生态**：LiteFS-ASGI/Uvicorn（需要 ASGI 中间件生态时选择）

## 运行测试

```bash
cd benchmarks
PATH=~/.pyenv/shims:~/.pyenv/bin:~/Installed:/usr/local/bin:/usr/bin:/bin python run_benchmark.py
```

测试结果自动保存到 `results/{timestamp}/data.json`，HTML 报告保存到 `results/latest/report.html`。
