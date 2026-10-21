# P1 可观测性与数据工具实施计划

## Context

`docs/source/todolist.md` 的 P1 阶段包含两项当前空缺的能力：

1. **Prometheus 监控** —— 框架目前没有任何指标暴露能力，运维无法观测请求吞吐、延迟、错误率、数据库连接池与缓存命中情况。
2. **数据库迁移** —— `src/litefs/cli.py` 的 `db_migrate()` 只是一个打印 "此功能需要安装 Alembic" 的提示占位，项目没有任何版本化迁移能力。

目标产出：Prometheus 监控中间件（含 `/metrics` 端点、请求/延迟/错误率/连接池/缓存命中指标）与基于 Alembic 的迁移 CLI（`litefs db init/migrate/upgrade/downgrade/current/history`，保留旧的扁平入口）。

已确认的两项决策：**使用 prometheus-client**；**CLI 采用嵌套子命令 + 保留旧别名**。

### 勘察中发现的 7 个关键事实（决定实现细节，务必遵守）

| # | 事实 | 影响 |
|---|------|------|
| 1 | `process_request` **每请求被调用两次**：`app/protocol_mixin.py:118` + `handlers/wsgi.py:152`（ASGI 同理） | 起始时间写入必须**幂等**（已存在则不覆盖） |
| 2 | `process_response(request_handler, response)` 的 `response` 是 **3 元组** `(status_line: str, headers: list, content)` | 状态码须从 `response[0].split()[0]` 解析；**不可用 `_status_code`**（`_prepare_response` 不更新它，恒为 200） |
| 3 | `handlers/socket.py:368 handle_response` 对非 `Response` 对象原样返回 | `process_response` 收到的可能不是 3 元组，需防御性判断 `isinstance(response, tuple) and len(response) == 3` |
| 4 | 中间件实例是 **App 级共享**（`app/extension_mixin.py:74` 缓存到 `_middleware_instances`） | 每请求状态必须存 request handler，不能存中间件实例 |
| 5 | 业务异常在 `handlers/wsgi.py:175` 被 `_process_route_error` 吞掉 → 走 `process_response(500)`；`process_exception` 几乎不触发 | 错误计数由 **`process_response` 中 status ≥ 400** 判定；`process_exception` 仅作 ASGI HttpError 兜底，且需与 `process_response` **互斥去重** |
| 6 | SQLite 内存库用 `SingletonThreadPool`，其 `size` 是 int 属性而非方法 → `get_pool_status()` 抛 `TypeError` | 连接池采集必须 try/except 兜底 |
| 7 | `argh.add_subcommands` 的子命令名由函数名推导（`db_init` → `db-init`）；`argh.named('init')` 会把 `ATTR_NAME` 写到**函数对象**上 | 嵌套组必须用**独立函数对象** + `@argh.named(...)`，否则顶层 `db-init` 会被改成 `init` |

补充实测结论：`prometheus_client` 0.26 顶层公开 `Counter / Gauge / Histogram / CollectorRegistry / generate_latest / CONTENT_TYPE_LATEST`；`generate_latest` 返回 **bytes**；无 `Gauge.set_multi`。`alembic.command.init` 要求 `Config(ini_path)`（无参会 AssertionError），生成的 `alembic.ini` 落在 `config.config_file_name` 所在目录，`sqlalchemy.url` 是占位符需 `set_main_option` 覆盖；自定义 `env.py` **不可**调用 `fileConfig()`（程序化 ini 无 logging 段会抛错）。

---

## 任务一：Prometheus 监控

### 1. 新建 `src/litefs/metrics.py`（新建，约 320 行）

指标注册中心与自定义采集器。**模块顶层绝不 import prometheus_client**，全部懒加载。

```
load_prometheus_client()  →  成功返回模块；失败抛 PrometheusNotAvailable(ImportError)
```

`PrometheusNotAvailable` 继承 `ImportError`，消息形如
`未安装 prometheus-client，请执行 pip install 'litefs[prometheus]'`。

`DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)`

`MetricsRegistry` 类（每个中间件实例持有一个，**必须显式传 `registry=`**，否则多 App 场景 `DuplicateTimeseries`）：

| 指标 | 类型 | 标签 |
|------|------|------|
| `litefs_http_requests_total` | Counter | method, path, status |
| `litefs_http_request_duration_seconds` | Histogram | method, path |
| `litefs_http_response_size_bytes` | Histogram | method, path |
| `litefs_http_errors_total` | Counter | method, path, status |
| `litefs_db_pool_connections` | Gauge | database, state |
| `litefs_cache_operations_total` | Counter | cache, backend, result |
| `litefs_cache_entries` | Gauge | cache, backend |

`MetricsRegistry.refresh()` —— **scrape 时**刷新两类动态指标（这是本方案的核心，避免自定义 Collector 的兼容性风险）：

- **连接池**：遍历 `DatabaseManager.get_databases()` → `db.get_pool_status()` → 逐个 `gauge.labels(database=..., state=...).set(v)`（**无 `set_multi`，必须循环**）。整个调用包 try/except（事实 #6）。`state` 取值：`pool_size / checked_in / checked_out / overflow / invalid`。
- **缓存**：遍历 `CacheManager.list_cache_instances()` → 读 `cache.stats.snapshot()` → 与**上次快照**做差值后 `counter.labels(cache=..., backend=..., result='hit'|'miss').inc(delta)`；条目数 `gauge.labels(cache=..., backend=...).set(len(cache))`。首次调用 delta 视为 0。

`MetricsRegistry.render()` → `generate_latest(self.registry).decode('utf-8')`。

`MetricsRegistry.content_type` → `CONTENT_TYPE_LATEST`（`text/plain; version=0.0.4; charset=utf-8`）。

### 2. 新建 `src/litefs/middleware/prometheus.py`（新建，约 300 行）

`PrometheusMiddleware(Middleware)`：

构造参数：`app, path='/metrics', namespace='litefs', buckets=None, exclude_paths=None`。

- `process_request(request_handler)`：
  1. **幂等**取/设起始时间：仅当 `getattr(request_handler, '_prom_start_time', None) is None` 时写入 `time.perf_counter()`（事实 #1）。
  2. 若 `GET` 且 `PATH_INFO == self.path` → 返回 **3 元组** `(status_line, headers, content)`。
     ⚠️ 必须返回 3 元组而非 `Response` 对象：`_parse_result_tuple`（`app/helpers.py:86`）不识别 `Response`，会退化成 `content=<Response object at 0x...>`（现有 `HealthCheck` 即有该缺陷）。
     构造方式：`"200 OK", [("Content-Type", registry.content_type)], registry.render()`。
     该路径直接短路，`process_response` 不会被调用 → 自身不产生指标（无自监控噪声）。
- `process_response(request_handler, response)`：
  1. 若 handler 上已有 `_prom_recorded` 标记 → 直接返回 response（与 `process_exception` 互斥去重，事实 #5）。
  2. 防御性解析：`if not (isinstance(response, tuple) and len(response) == 3): return response`（事实 #3）。
  3. `status_code = int(response[0].split()[0])`（事实 #2）。
  4. `route_path = getattr(request_handler, 'route_path', None) or 'unmatched'`（低基数标签）。
  5. `method = request_handler._environ.get('REQUEST_METHOD', 'GET')`。
  6. 记录：`requests_total.labels(method, route_path, str(status_code)).inc()`；`duration_seconds.labels(method, route_path).observe(time.perf_counter() - start)`；响应大小 `response_size_bytes.labels(method, route_path).observe(size)`；`status_code >= 400` 时 `errors_total.labels(method, route_path, str(status_code)).inc()`。
  7. 响应大小：从 `response[1]`（headers 列表）找 `Content-Length`；找不到则 `len(content.encode('utf-8'))`（content 为 str）/ `len(content)`（bytes）/ 0（生成器等 Iterable）。
  8. 置 `_prom_recorded = True`。
- `process_exception(request_handler, exception)`：
  仅当 handler 上**没有** `_prom_recorded` 时补记一次（status 记 500），并置 `_prom_recorded = True`；返回 None 继续抛出。
  同时实现 `async_process_request` / `async_process_response` / `async_process_exception` 直接委托同步实现，避免 ASGI 下走 `run_in_executor` 的线程切换开销（同步实现本身是纯 CPU 轻量操作）。

### 3. 路由模板（低基数标签）—— 3 个文件

`src/litefs/routing/router.py` 新增：

```python
def match_with_route(self, path, method) -> Optional[Tuple[Route, Dict[str, Any]]]
```

必须**复刻 `match()` 的全部 3 条匹配分支**（精确匹配 / 去尾斜杠 / 加尾斜杠），否则会出现"路由命中但 route 为 None"。原 `match()` 保持不变（零行为变化），内部委托给 `match_with_route`。

`src/litefs/handlers/wsgi.py:165`、`asgi.py:197`、`socket.py:766` 三处改为：

```python
route_match = app.router.match_with_route(path_info, request_method)
if route_match:
    route, params = route_match
    handler = route.handler
    setattr(self, 'route_path', route.path)   # 新增
    setattr(self, 'route_params', params)
    ...
```

`route_path` 全局无冲突（仅 `websocket/server.py` 有同名局部变量，与 request handler 无关）；request handler 每请求新建且无 `__slots__`，`setattr` 安全。
`socket.py:771` 原本漏设 `path_params`，本次一并补齐以统一三处行为。

### 4. 缓存命中统计 —— 6 个文件

`src/litefs/cache/base.py` 新增 `CacheStats` 类（hits/misses/sets/deletes 计数，`threading.Lock` 保护）与 `CacheBackendBase.stats` **懒加载 property**：

```python
@property
def stats(self) -> CacheStats:
    # 子类均未调用 super().__init__()，因此必须懒加载
```

`src/litefs/cache/cache.py`（`TreeCache.get` L306、`MemoryCache.get` L440）、`redis.py`（L135）、`db.py`（L187）、`memcache.py`（L102）的 `get()` 各加 2 行：`self.stats.record_hit()` / `self.stats.record_miss()`。语义：返回值为 `None` 即视为 miss（存储值为 None 的 key 会被误判为 miss，属可接受取舍，文档中说明）。

`src/litefs/cache/manager.py` 新增 `list_cache_instances()` 返回 `list(manager._caches.values())`；并在 `get_cache()` 创建实例时打上 `cache._litefs_backend = backend`（新增属性，不影响既有行为），供 `{backend}` 标签使用（否则只能用 `type(cache).__name__` 近似）。

> `src/litefs/cache/form_cache.py` 的 `FormCache` **不继承** `CacheBackendBase`，本次不改（无 `stats`），文档中注明。

### 5. 数据库连接池访问器 —— 1 个文件

`src/litefs/database/core.py` 的 `DatabaseManager` 新增类方法：

```python
@classmethod
def get_databases(cls) -> Dict[str, Database]:
    """获取所有已初始化的数据库实例（只读副本）"""
```

### 6. 配置与依赖 —— 2 个文件

`src/litefs/config.py` 的 `DEFAULT_CONFIG` 新增（沿用现有键值对 + 行内中文注释风格）：

```python
# Prometheus 监控配置
'prometheus_enabled': False,       # 是否启用 Prometheus 监控中间件
'prometheus_path': '/metrics',     # 指标暴露路径
'prometheus_namespace': 'litefs',  # 指标命名空间前缀
```

`src/litefs/middleware/__init__.py` 增加 `from .prometheus import PrometheusMiddleware` + `__all__` 追加。

`pyproject.toml` `[project.optional-dependencies]` 新增：

```toml
prometheus = ["prometheus-client>=0.20"]
```

`pyproject.toml` `[tool.mypy.overrides]` 的第三方缺存根列表新增 `"prometheus_client.*"`（prometheus-client 无 py.typed）。**新增模块不得进入 `ignore_errors` 列表**，必须 mypy 零错误。

---

## 任务二：数据库迁移

### 1. 新建 `src/litefs/database/migrations.py`（新建，约 380 行）

`AlembicManager` 类，**顶层不 import alembic**，全部方法内懒加载。

```python
class AlembicManager:
    def __init__(self, database_url=None, script_location='migrations',
                 base_metadata=None, app=None)
```

- `database_url` 解析优先级：`app.db.engine.url` > 显式参数 > `Config.database_url` > `DATABASE_URL` 环境变量 > `sqlite:///litefs.db`（与 `Database._get_database_url()` 对齐）。
- `base_metadata` 默认取 `litefs.database.models.Base.metadata`（模块级 Base）。注意 `Database.__init__` 里的 `self.Base = declarative_base()` 是**另一个空 Base**，autogenerate 不能用它。
- `config()` 方法构建 `alembic.config.Config`：传入 `ini_path`（必须，否则 `Config()` 抛 AssertionError），`set_main_option('script_location', abs_path)`、`set_main_option('sqlalchemy.url', url)`，并设 `config.stdout = io.StringIO()` 捕获输出、`config.messaging_opts = {'quiet': True}` 抑制 `util.msg` 直写 stdout。

六个公开方法：

| 方法 | 行为 |
|------|------|
| `init()` | `alembic.command.init(config, directory)` 生成 `alembic.ini` + `migrations/{env.py, script.py.mako, versions/}`，随后**覆盖 `env.py`** 为本项目模板 |
| `migrate(message)` | `alembic.command.revision(config, message=message, autogenerate=True)` |
| `upgrade(revision='head')` | `alembic.command.upgrade(config, revision)` |
| `downgrade(revision='-1')` | `alembic.command.downgrade(config, revision)` |
| `current()` | `alembic.command.current(config, verbose=True)` |
| `history()` | `alembic.command.history(config, verbose=False)` |

**自定义 `env.py` 模板**（内嵌为模块常量 `_ENV_PY_TEMPLATE`，写文件时格式化注入 database_url 与 models 导入路径）必须：

- `target_metadata = Base.metadata`（在 `context.configure()` **之前**赋值）
- 保留 `if context.is_offline_mode():` 分支
- **不得**调用 `fileConfig(config.config_file_name)`（程序化 ini 无 logging 段会抛错）
- 显式 import 用户的 models 模块（否则 autogenerate 生成空迁移）——通过 `models_imports` 参数传入

所有方法返回 `(exit_code: int, output: str)`，由 CLI 决定打印与退出码。

### 2. `src/litefs/database/__init__.py` 增加 `AlembicManager` 导出

```python
from .migrations import AlembicManager
__all__ = ['Database', 'DatabaseManager', 'Base', 'AlembicManager']
```

> 注意：`migrations.py` 顶层 import alembic 会破坏"懒加载"目标 —— 因此 `migrations.py` **不得**在模块顶层 import alembic，`database/__init__.py` 导入它时 alembic 缺失也不能报错（alembic 只在方法调用时 import）。

### 3. `src/litefs/cli.py` —— 嵌套子命令 + 保留旧扁平入口

**新增独立函数对象**（避免 `argh.named` 污染顶层命令名，事实 #7）：

```python
@argh.named('init')
def db_sub_init(directory: str = 'migrations'):
    """初始化 Alembic 迁移环境"""

@argh.named('migrate')
def db_sub_migrate(message: str = 'auto migration'):
    """生成迁移脚本"""

@argh.named('upgrade')
def db_sub_upgrade(revision: str = 'head'):
    """升级到指定版本"""

@argh.named('downgrade')
def db_sub_downgrade(revision: str = '-1'):
    """回退到指定版本"""

@argh.named('current')
def db_sub_current():
    """显示当前数据库版本"""

@argh.named('history')
def db_sub_history():
    """显示迁移历史"""
```

注册：

```python
argh.add_subcommands(parser, 'db', [db_sub_init, db_sub_migrate, db_sub_upgrade,
                                    db_sub_downgrade, db_sub_current, db_sub_history],
                     title='数据库迁移命令')
```

**语义映射**（保持向后兼容）：

| 命令 | 语义 |
|------|------|
| `litefs db init` | 初始化 Alembic 迁移环境（新） |
| `litefs db migrate` | 生成迁移脚本（新，真正实现） |
| `litefs db upgrade/downgrade/current/history` | 迁移操作（新） |
| `litefs db create-tables` | 旧的建表能力（等价旧 `db-init`） |
| `litefs db-init` | **旧扁平入口，行为不变**（建表） |
| `litefs db-migrate` | 旧扁平入口，从提示占位升级为真正生成迁移脚本 |

顶层 `parser.add_commands([...])` 保留 `db_init`、`db_migrate` 不动（`db_init` 原样保留；`db_migrate` 改为委托 `AlembicManager.migrate`）。

`argh` 需在 `main()` 内 import（现有模式），`@argh.named` 装饰器需要在模块级使用 —— 因此在 `cli.py` 顶部 `import argh`（argh 是核心依赖，已在 `dependencies` 中，无兼容问题）。

### 4. `pyproject.toml` 新增可选依赖组

```toml
db = ["alembic>=1.13"]
```

---

## 测试与文档

### 测试（新建 2 个文件）

- `tests/unit/test_middleware_prometheus.py`：中间件挂载 → 请求 → `/metrics` 返回 200 且含 `litefs_http_requests_total`；状态码解析正确（200/404/500）；路由模板标签生效（`/user/{id}` 而非原始路径）；`process_request` 幂等（两次调用不覆盖起始时间）；`process_response` 非 3 元组时安全返回；缺 prometheus-client 时抛 `PrometheusNotAvailable`。
- `tests/unit/test_database_migrations.py`：`AlembicManager.init()` 在 tmp 目录生成 `alembic.ini` + `migrations/env.py` + `versions/`；`migrate()` 生成迁移脚本；`upgrade()`/`current()`/`history()` 在 SQLite 临时库上跑通；缺 alembic 时抛明确异常。

> 测试需临时目录隔离，**不得**污染仓库；SQLite 临时库用 `tmp_path` fixture。

### 文档

- 新建 `docs/source/prometheus-monitoring.md`：指标清单表、标签语义（低基数路由模板说明）、`/metrics` 用法、Grafana/Prometheus 配置示例、常见问题（多进程 gunicorn 需每个 worker 独立抓取）、可选依赖安装说明。
- 新建 `docs/source/database-migrations.md`：命令清单与语义表、`init` 流程、`migrate/upgrade/downgrade/current/history` 用法、自定义 `env.py` 说明、常见问题。
- `docs/source/todolist.md`：P1 两行标记 ✅ 并链接上述文档。
- `docs/source/index.rst`：toctree 追加 `prometheus-monitoring` 与 `database-migrations`。
- 文档遵循 Sphinx 规范、文件名小写、置于 `docs/source/`。

---

## 验证（全部必须通过）

```bash
cd /home/zhanglei3/Desktop/dev/litefs
source /home/zhanglei3/.pyenv/versions/litefs/bin/activate

# 1. 静态检查三件套（新增模块必须零错误，不得进 mypy ignore 列表）
python -m flake8 src
python -m ruff check src
python -m mypy src

# 2. 全量回归（对比基线 1424 passed；memcached 相关失败为已知环境问题）
python -m pytest tests/ -ra --tb=short -q

# 3. 专项测试
python -m pytest tests/unit/test_middleware_prometheus.py tests/unit/test_database_migrations.py -v

# 4. 文档构建（不得新增告警）
cd docs && make html && cd ..
```

验证通过后向用户报告结果，**不主动 commit**（等待用户确认目标分支）。
