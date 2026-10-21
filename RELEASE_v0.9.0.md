# LiteFS v0.9.0 Release Notes

**发布日期**: 2026-10-21
**上一个版本**: v0.8.3
**变更规模**: 178 个文件，+24199 / -4542

---

## 重大改进

### 架构重构：`core.py` 拆分为 `app/` 子包

- 将 `src/litefs/core.py` 按职责拆分为 `src/litefs/app/` 子包下的 6 个 Mixin：
  - `extension_mixin.py` —— 扩展属性与钩子
  - `helpers.py` —— 内部辅助方法
  - `protocol_mixin.py` —— WSGI / ASGI 协议适配
  - `routing_mixin.py` —— 路由注册
  - `server_cli.py` —— 命令行入口参数
  - `server_mixin.py` —— 服务器生命周期
- 全部原有公共 / 私有符号经 `app/__init__.py` 重新导出，**对外 API 零变更**
- 新增 `src/litefs/cli_db.py`，数据库子命令从 `cli.py` 中拆出，避免单文件膨胀
- 拆分过程使用延迟导入 + 再导出策略规避循环导入，行为保持完全一致

### 全量类型注解

- `src/litefs/app/` 与 `core.py` 完成全量类型注解，修复 **81 个 mypy 错误**
- 4 个 Mixin 类通过 `TYPE_CHECKING` 下的显式 `property` 声明解决 **74 个 `attr-defined` 报错**，
  运行时零开销
- `mypy` 目标 Python 版本调整为 3.9，覆盖范围由局部扩展至整个 `src/` 目录
- 新增模块（`cli_db.py`、`metrics.py`、Prometheus 中间件等）**不进入** mypy 豁免列表

### 静态检查流水线落地

- `.gitlab-ci.yml` 新增 `lint` 阶段，串行执行 **flake8 → ruff → mypy**（`allow_failure: false`），
  `test` 阶段并行执行单元测试与覆盖率
- 测试任务补装并启动 memcached / redis，消除本地环境噪音导致的用例失败
- `Makefile` 新增 `lint` / `lint-fix` 目标
- 新增 `scripts/sync_deps.py`，修复 `make sync-deps` 目标（内联 Python 块缩进错误曾导致
  整个 Makefile 解析失败、所有目标不可用），同时保留可选依赖注释

### Prometheus 监控

- 新增 `src/litefs/metrics.py`：延迟加载的指标注册表，内置 7 项指标
- 新增 `src/litefs/middleware/prometheus.py`：同步 / 异步双路径中间件，提供 `/metrics` 端点
- 标签基于**路由路径**（不含路径参数原值）匹配，保证低基数，避免监控指标基数爆炸
- 全部缓存后端（Memory / Tree / Redis / Memcache / Database）接入缓存命中 / 未命中统计

### Alembic 数据库迁移

- 新增 `src/litefs/database/migrations.py`：统一的迁移管理器，返回值规范化
- `cli.py` 新增 `db` 命令组，拆分为 `init` / `revision` / `upgrade` / `downgrade` /
  `current` / `history` 子命令
- 规避 4 个 Alembic 已知陷阱：模板字面量 `{}` 与 `str.format` 冲突、`messaging_opts.quiet`
  抑制必要输出、`fileConfig` 劫持根 logger、`StringIO` 未指定 UTF-8 编码导致中文乱码

### 邮件服务（零新增依赖）

- 新增 `src/litefs/mail/` 子包：
  - `message.py` —— Message / Attachment MIME 结构
  - `smtp.py` —— SMTP 客户端，支持 STARTTLS / SSL，指数退避重试
  - `template.py` —— Mako 双模板（HTML + 纯文本）配对与缓存
  - `tasks.py` —— Celery 发送任务，**Celery 不可用时自动降级为同步发送**

### 国际化 i18n（零新增依赖）

- 新增 `src/litefs/i18n/` 子包：
  - `locale.py` —— 四级 locale 协商（路径 → 查询参数 → Cookie → `Accept-Language`）
  - `translator.py` —— gettext 封装，线程局部保存请求级 locale
  - `middleware.py` —— 同步 / 异步双路径中间件，写入 `Content-Language` 响应头与 locale Cookie
  - `template.py` —— 模板翻译函数注入，回退为恒等函数以保证零行为变化

### 性能回归门禁

- 新增 `tests/performance/thresholds.json`：固化 RPS / P99 基线阈值
- 新增 `tests/performance/compare_benchmark.py`：自动比对并给出通过 / 失败判定
- 集成到 CI，作为 `allow_failure: true` 的参考门禁

### 依赖安全审计

- 新增 `scripts/audit_dependencies.py`，基于 `pip-audit` 的依赖漏洞扫描
- 集成到 `make audit` 与 CI 流水线，扫描报告归档

---

## Bug 修复

- 修复 Prometheus 指标在 **Socket 原生响应路径**下未采集的问题
  （`process_response` 仅收到响应体字符串，响应头存于 `request_handler._response_headers` 字典，
  与 WSGI / ASGI 的三元组返回形式不同）
- 修复 i18n 中间件在 Socket 路径下未写入 `Content-Language` 响应头与 locale Cookie 的问题
- 修复 `LocaleMiddleware` 未将配置的 `locale_dir` 同步到线程局部存储的缺陷
  （非默认 locale 目录会导致翻译查找失败），并补充 2 个回归测试用例
- 修复 `make sync-deps` 目标因内联 Python 块缩进错误导致整个 Makefile 解析失败的问题

---

## 版本号治理

- 消除源码中 **7 处版本号硬编码**（`handlers/socket.py` 5 处、`server/greenlet.py` 1 处、
  `cli.py` 1 处），统一由 `src/litefs/_version.py` 派生
- 新增 `server_software` 常量（对应 WSGI `SERVER_SOFTWARE` 语义，仅含框架版本号），
  与 `server_info`（含 Python 版本号，用于 WSGI / ASGI 的 `Server` 头）职责分离，
  **两条响应链路的输出格式保持完全不变**
- `cli.py` 版本命令在包未安装时回退为 `unknown`，不再硬编码版本号
- `pyproject.toml` / `setup.py` 均已使用动态版本读取，无需同步维护

---

## 文档

- 新增文档：`prometheus-monitoring.md`、`database-migrations.md`、`mail-service.md`、
  `i18n.md`、`static-checks.md`、`type-hints.md`、`performance-regression.md`、`dependency-audit.md`
- 新增 `docs/source/api.rst` 与 `api/modules`，补全 API 参考
- `index.rst` 补入此前未收录的文档（`keep-alive`、`asyncio-server`、
  `performance-benchmark-v0.8.1`、`performance-greenlet-vs-asyncio`）
- **Sphinx 构建告警清零**（30 → 22 → 0）：
  - RST 单冒号 → 双冒号字面块语法（definition list 误解析）
  - `**kwargs` → `\*\*kwargs`（inline strong 未闭合）
  - `LITEFS_` → ` ``LITEFS_`` `（未知引用目标）
  - HTTP 代码块请求行补 `HTTP/1.1` 协议版本（Pygments http lexer 报错）
- 新增 `CHANGELOG.md`（Keep a Changelog 格式），并新增 4 个可运行示例：
  `06-prometheus-monitoring`、`07-database-migrations`、`08-mail-service`、`09-i18n`

---

## 文件变更统计

### 新增模块（21 个）

| 目录 | 文件 |
|------|------|
| `src/litefs/app/` | `__init__.py`、`extension_mixin.py`、`helpers.py`、`protocol_mixin.py`、`routing_mixin.py`、`server_cli.py`、`server_mixin.py` |
| `src/litefs/database/` | `migrations.py` |
| `src/litefs/i18n/` | `__init__.py`、`locale.py`、`middleware.py`、`template.py`、`translator.py` |
| `src/litefs/mail/` | `__init__.py`、`message.py`、`smtp.py`、`tasks.py`、`template.py` |
| `src/litefs/middleware/` | `prometheus.py` |
| `src/litefs/` | `cli_db.py`、`metrics.py` |

### 新增示例（4 套）

- `examples/06-prometheus-monitoring/`
- `examples/07-database-migrations/`
- `examples/08-mail-service/`
- `examples/09-i18n/`

### 测试

- 单元测试从 1306 例扩充至 **1640 例**（P0 基线 → v0.9.0），全部通过（7 例因本地环境跳过）
- 新增 `tests/performance/thresholds.json`、`tests/performance/compare_benchmark.py`
- 新增 `tests/unit/test_i18n.py` 中的 `TestLocaleMiddlewareSocketPath`（6 个 Socket 链路用例）

### 兼容性

- **无破坏性变更**。`core.py` 拆分后所有原有导入路径与符号均保持可用。

---

## 升级指引

```bash
pip install --upgrade litefs==0.9.0
```

从源码安装：

```bash
git clone https://github.com/leafcoder/litefs.git
cd litefs
pip install -r requirements.txt
pip install -e .
```

升级后建议执行一次静态检查确认环境：

```bash
make lint
```
