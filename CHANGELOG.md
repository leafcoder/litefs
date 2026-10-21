# Changelog

本文件记录 Litefs 的所有重要变更，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

暂无。

## [0.9.0] - 2026-10-21

v0.9.0 是「技术债务清理 & 架构统一」版本。核心变化是：`core.py` 拆分重构、全量类型注解、
静态检查流水线落地，以及 Prometheus 监控、Alembic 迁移、邮件服务、国际化四大新能力。

### 架构重构

- `src/litefs/core.py` 拆分为 `src/litefs/app/` 子包，按职责划分为 6 个 Mixin：
  - `extension_mixin.py` —— 扩展属性与钩子
  - `helpers.py` —— 内部辅助方法
  - `protocol_mixin.py` —— WSGI / ASGI 协议适配
  - `routing_mixin.py` —— 路由注册
  - `server_cli.py` —— 命令行入口参数
  - `server_mixin.py` —— 服务器生命周期
- 全部原有公共/私有符号经 `app/__init__.py` 重新导出，**对外 API 零变更**
- 新增 `src/litefs/cli_db.py`，数据库子命令从 `cli.py` 中拆出，避免单文件膨胀
- 新增 `src/litefs/app/extension_mixin.py` 中显式的 `TYPE_CHECKING` 属性声明，
  解决 Mixin 引用宿主类属性导致的 `mypy attr-defined` 报错，运行时零开销

### 类型注解与静态检查

- `src/litefs/app/` 与 `core.py` 完成全量类型注解，修复 **81 个 mypy 错误**
- 4 个 Mixin 类通过 `TYPE_CHECKING` 属性声明解决 **74 个 attr-defined 报错**
- `mypy` 目标 Python 版本调整为 3.9，覆盖范围扩展至整个 `src/` 目录
- 新增 `src/litefs/cli_db.py`、`src/litefs/metrics.py` 等模块**未进入** mypy 豁免列表

### Prometheus 监控

- 新增 `src/litefs/metrics.py`：延迟加载的指标注册表，内置 7 项指标
- 新增 `src/litefs/middleware/prometheus.py`：
  - 同步 / 异步双路径中间件
  - 提供 `/metrics` 端点
  - 基于路由路径的标签匹配，**保证低基数**（不引入路径参数原值）
- 全部缓存后端（Memory / Tree / Redis / Memcache / Database）接入缓存命中/未命中统计

### Alembic 数据库迁移

- 新增 `src/litefs/database/migrations.py`：统一的迁移管理器
- `cli.py` 新增 `db` 命令组，拆分为 `init` / `revision` / `upgrade` / `downgrade` / `current` / `history` 子命令
- 修复 Alembic 已知陷阱：模板字面量 `{}` 与 `str.format` 冲突、`messaging_opts.quiet` 抑制必要输出、
  `fileConfig` 劫持根 logger、`StringIO` 未指定 UTF-8 编码导致中文乱码

### 邮件服务

- 新增 `src/litefs/mail/` 子包（零新增依赖）：
  - `message.py` —— Message / Attachment MIME 结构
  - `smtp.py` —— SMTP 客户端，支持 STARTTLS / SSL，指数退避重试
  - `template.py` —— Mako 双模板（HTML + 纯文本）配对与缓存
  - `tasks.py` —— Celery 发送任务，**Celery 不可用时自动降级为同步发送**

### 国际化（i18n）

- 新增 `src/litefs/i18n/` 子包（零新增依赖）：
  - `locale.py` —— 四级 locale 协商（路径 → 查询参数 → Cookie → `Accept-Language`）
  - `translator.py` —— gettext 封装，线程局部保存请求级 locale
  - `middleware.py` —— 同步 / 异步双路径中间件，写入 `Content-Language` 响应头与 locale Cookie
  - `template.py` —— 模板翻译函数注入，回退为恒等函数以保证零行为变化
- 修复 `LocaleMiddleware` 未将配置的 `locale_dir` 同步到线程局部存储的缺陷
  （非默认 locale 目录会导致翻译查找失败），并补充 2 个回归测试用例

### 工程化与质量门禁

- `.gitlab-ci.yml` 新增静态检查流水线：`lint` 阶段串行执行 **flake8 → ruff → mypy**
  （`allow_failure: false`），`test` 阶段并行执行单元测试与覆盖率
- 测试任务补装并启动 memcached / redis，消除本地环境噪音导致的用例失败
- 新增 `scripts/sync_deps.py`，修复 `make sync-deps` 目标（保留可选依赖注释）
- `Makefile` 新增 `lint` / `lint-fix` 目标
- 单元测试从 1306 例扩充至 **1640 例**（P0 基线 → v0.9.0）

### 性能回归门禁

- 新增 `tests/performance/thresholds.json`：固化 RPS / P99 基线阈值
- 新增 `tests/performance/compare_benchmark.py`：自动比对并给出通过/失败判定
- 集成到 CI，作为 `allow_failure: true` 的参考门禁

### 依赖安全审计

- 新增 `scripts/audit_dependencies.py`，基于 `pip-audit` 的依赖漏洞扫描
- 集成到 `make audit` 与 CI 流水线，扫描报告归档

### Bug 修复

- 修复 Prometheus 指标在 **Socket 原生响应路径**下未采集的问题
  （`process_response` 仅收到响应体字符串，响应头存于 `request_handler._response_headers` 字典）
- 修复 i18n 中间件在 Socket 路径下未写入 `Content-Language` 响应头与 locale Cookie 的问题
- 修复 `make sync-deps` 目标因内联 Python 块缩进错误导致整个 Makefile 解析失败的问题

### 文档

- 新增文档：`prometheus-monitoring.md`、`database-migrations.md`、`mail-service.md`、
  `i18n.md`、`static-checks.md`、`type-hints.md`、`performance-regression.md`、`dependency-audit.md`
- 新增 `docs/source/api.rst` 与 `api/modules`，补全 API 参考
- `index.rst` 补入此前未收录的文档（`keep-alive`、`asyncio-server`、
  `performance-benchmark-v0.8.1`、`performance-greenlet-vs-asyncio`）
- **Sphinx 构建告警清零**（30 → 22 → 0），涉及 RST 字面块语法、inline strong 转义、
  引用目标字面量化、Pygments HTTP lexer 协议版本补全

### 版本号治理

- 消除源码中 **7 处版本号硬编码**（`handlers/socket.py` 5 处、`server/greenlet.py` 1 处、
  `cli.py` 1 处），统一由 `src/litefs/_version.py` 派生
- 新增 `server_software` 常量（对应 WSGI `SERVER_SOFTWARE` 语义），
  与 `server_info`（含 Python 版本）职责分离，**两条响应链路的输出格式保持不变**
- `cli.py` 版本命令在包未安装时回退为 `unknown`，不再硬编码版本号

### 破坏性变更

- **无**。`core.py` 拆分后所有原有导入路径与符号均保持可用。

## [0.8.3] - 2026-05-19

### 架构重构

- 简化包导入结构：移除 `__init__.py` 中的 `__getattr__` 延迟导入机制和庞大的 `__all__` 列表
  （203 行 → 31 行），所有代码改为从子模块直接导入

### Bug 修复

- 修复服务器关闭时 `DatabaseManager.close_all()` 的 `AttributeError`
- 修复 WSGI 输入流读取后未重置位置导致后续中间件无法读取请求体的问题
- 修复 `RateLimitMiddleware` 测试中 `'Response' object is not subscriptable` 错误
- 修复 `log_info` / `log_error` / `log_debug` 在 `logger=None` 时的 `AttributeError`

[未发布]: https://github.com/leafcoder/litefs/compare/v0.9.0...HEAD
[0.9.0]: https://github.com/leafcoder/litefs/compare/v0.8.3...v0.9.0
[0.8.3]: https://github.com/leafcoder/litefs/compare/v0.8.2...v0.8.3
