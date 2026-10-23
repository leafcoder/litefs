# Changelog

本文件记录 Litefs 的所有重要变更，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### Added

- 内置中间件支持配置驱动自动挂载：应用创建时（`Litefs(...)` 构造阶段）按
  `middleware` 配置项（名称列表或 `LITEFS_MIDDLEWARE` 环境变量逗号分隔字符串）
  自动挂载，无需手动调用 `add_middleware`；默认值为 `None`（不挂载），
  存量应用零行为变化，`litefs runserver` 未配置时保持默认启用全部的历史行为
- 支持自定义中间件配置：`middleware` 条目可使用模块路径
  （如 `myapp.middleware.ThrottleMiddleware`），应用创建时动态导入；
  构造参数经新增的 `middleware_options` 配置段注入（以条目原文为键，
  内置中间件亦可用同名配置段 `cors` / `health_check`）
- `Config` 新增 `cors` / `health_check` 中间件构造参数配置段：
  config.yaml 中的同名嵌套段作为 `CORSMiddleware` / `HealthCheck` 构造参数注入
  （此前嵌套段因配置键白名单被静默丢弃，属于死配置）
- 补齐低覆盖模块测试用例 211 个（新增 7 个测试文件），整体覆盖率 76% → 84%：
  - `app/server_mixin.py` 10% → 86%（启动/信号/清理/热重载链路）
  - `server/greenlet_server_base.py` 43% → 87%（SocketIO greenlet 切换、
    Epoll 事件分发、TCPServer 请求分派、finish_request 全链路集成）
  - `server/greenlet.py` 23% → 81%（HTTPServer/WSGIServer 绑定、
    ProcessHTTPServer PID 文件/信号/Master-Worker 生命周期）
  - `websocket/connection.py` 29% → 93%、`websocket/server.py` 13% → 93%
    （连接收发/房间/关闭语义、握手/认证/广播真实回环集成）
  - `session/memcache.py` 65% → 97%、`session/db.py` 69% → 95%、
    `session/redis.py` 67% → 98%（双客户端分支判定、连接池、过期清理、SCAN）

### Changed

- 脚手架模板（`litefs startproject`）全面更新至当前框架口径：
  - 应用代码仅创建 `Litefs(config_file='config.yaml')`，
    中间件由框架在创建时按 `middleware` 配置自动挂载
  - 处理器改用返回值风格（`str` 以 `<` 开头自动 `text/html`，
    `dict` 自动 `application/json`），移除旧式 `start_response` 调用与手工 orjson 序列化
  - 修正导入路径（`from litefs.core import Litefs`）、`database_path` → `database_url`、
    依赖下限提升至 `litefs>=0.10.0`

### Fixed

- 修复 `litefs runserver --config` 指定配置文件时因重复传参抛 `TypeError` 的问题
- 修复 `litefs runserver` 未指定 `--config` 时不读取项目 `config.yaml` 的问题：
  现在自动发现当前目录的 `config.yaml` / `config.yml` / `config.json` /
  `config.toml`，对中间件等配置的修改直接生效
- 示例（01-quickstart / 03-web-app / 05-production）中间件改为 config.yaml
  配置驱动，03-web-app 演示自定义中间件模块路径配置

### Security

安全修复包（对应代码审计文档 `code-audit-upgrade-plan` 4.2 节，D1 / D2 / D3 / D5）：

- **WebSocket 帧与缓冲区上限（D1）**：`Frame.parse` 新增 `max_payload_size`
  参数，帧头声明长度超限立即拒绝（`FrameTooLargeError`）；
  `WebSocketConnection` 默认单条消息上限 1MB（含接收缓冲区纵深防御上限），
  超限回 1009（Message Too Big）关闭帧并断连；`WebSocketServer` 握手请求头
  同步设上限。新增配置项 `websocket_max_message_size`（默认 1048576）
- **原生服务器连接治理（D2）**：`TCPServer` 新增 `max_connections`
  （达到上限后新连接被快速拒绝，不再无限接受）与 `idle_read_timeout`
  （默认 30 秒，阻塞读超时的连接被断开，slowloris 防护）；asyncio 服务器
  同语义支持。新增配置项 `max_connections`（默认 1024）、
  `idle_read_timeout`（默认 30.0，0/None 禁用）
- **500 响应信息泄露（D3）**：asyncio 服务器路径的 500 响应不再携带
  内部异常细节与堆栈，统一返回 `Internal Server Error`；
  debug 模式保留完整细节。socket / wsgi / asgi 路径经核实此前已按
  `config.debug` 门控，无泄露
- **CORS 加固（D5）**：`CORSMiddleware.process_response` 修复非 tuple
  响应（Socket 链路 str/bytes 返回值）丢失全部 CORS 响应头的问题，
  现经请求处理器 `_add_header` 补写；`allow_origins=['*']` 与
  `allow_credentials=True` 危险组合改为启动期（中间件构造期）抛 `ValueError`

## [0.10.0] - 2026-10-22

v0.10.0 是「契约与结构重构」版本：公共 API 首次全量分级冻结、弃用机制落地、
JSON 序列化切换 orjson，5 个超 600 行的大文件全部拆分至规范上限以内。

### Added

- **公共 API 分级冻结（H2）**：`litefs/_stable.py` 登记全部 548 个公共符号
  - `stable`：70 个模块 410 符号；`provisional`：32 个模块 138 符号
  - 契约测试（`tests/unit/test_api_contract.py`）强制包内每个模块登记分级或豁免，
    登记模块的公共符号面不得缩小
- **弃用机制（H6）**：新增 `litefs/deprecation.py`
  - `LitefsDeprecationWarning` 专用告警类别、`deprecated` 装饰器、`warn_deprecated` 运行时告警，
    替代符号与移除版本自动从 `_stable.DEPRECATED` 登记表回填
- Memcache 缓存后端新增 `incr` / `decr` 原子计数器方法
  - 基于 memcached 原生 `incr` / `decr` 命令，与 JSON 整数存储天然兼容
  - pymemcache 分支显式关闭 `noreply` 以获取返回值；键不存在返回 `None`；
    递减下限钳位为 0
  - 补充 mock 单元测试与真实服务集成测试（原先因方法缺失被 skip 的 2 个用例转正）
- Makefile 新增 `test` / `test-unit` / `test-cov` 目标（覆盖率报告含 HTML 输出）

### Changed

- **JSON 序列化统一改用 orjson，框架内不再使用标准库 `json`**
  - 新增 `src/litefs/_json.py` 序列化抽象层，作为框架内唯一的 JSON 编解码出口
  - 24 处 `import json` 全部替换为抽象层调用，覆盖：会话后端（DB / Redis / Memcache）、
    缓存后端（DB / Redis / Memcache）、HTTP 响应与请求体解析、Socket 处理器、
    中间件（增强日志 / 安全 / CSRF）、JWT 与 OAuth2 提供方、配置加密、
    Asyncio / Greenlet 服务器、调试中间件、WebSocket 帧编解码
  - orjson 基于 Rust 实现，JSON 编解码吞吐约为标准库的 3~5 倍，
    直接改善请求热路径的 P99 延迟
  - 依赖声明同步至 `pyproject.toml`、`requirements.txt` 与脚手架模板
    （`orjson>=3.10`，3.10.15 为支持 Python 3.8 的最高版本）
- **拆分 5 个超 600 行源文件（H3），全部 ≤600 行，公开 API 零变更**
  - `handlers/socket.py` 827 → 598（请求属性 / 响应转换拆为 Mixin 模块）
  - `server/greenlet.py` 780 → 365（SocketIO / Epoll / TCPServer 拆至 `greenlet_server_base`）
  - `error_pages.py` 775 → 包（HTML 模板拆至 `templates_4xx` / `templates_5xx`）
  - `config.py` 627 → 包（加密与文件加载拆为 `crypto` / `loaders` Mixin）
  - `handlers/base.py` 639 → 489（请求属性拆至 `base_request` Mixin）

### Deprecated

- `Litefs.session` 自 0.10.0 起废弃，计划 1.3.0 移除，替代符号 `Litefs.db_session`
  （详见 `docs/source/deprecation-timeline.md`）

### Fixed

- 修复 `MemcacheCache` / `MemcacheSession` 注入 `memcache_client` 实例时
  未设置 `_use_pymemcache` 属性的问题：调用 `put()` 会抛 `AttributeError`
  - 修复：按客户端所属模块自动判定调用约定（pymemcache 用 `expire=`，
    python-memcached 用 `time=`），注入原生 pymemcache 客户端开箱即用
- 修复 Memcache 后端写入非 ASCII 内容失败的问题
  - 根因：标准库 `json.dumps` 默认 `ensure_ascii=True` 保证了纯 ASCII 输出，
    而 orjson 始终输出原始 UTF-8，`pymemcache` 客户端默认按 ASCII 编码值，
    导致 `MemcacheIllegalInputError: Data values must be binary-safe`
  - 修复：抽象层新增 `dumps_ascii` 出口（非 ASCII 字符转义为 `\uXXXX`），
    与标准库 `ensure_ascii=True` 逐字节一致，Memcache 缓存与 Session 后端改用该出口
  - 迁移前写入的旧缓存数据可被新代码正确读取，双向兼容

### 文档

- 新增 `docs/source/api-stability.md`：API 稳定性与 SemVer 政策（分级体系、冻结基线、
  SemVer 语义、破坏性变更流程）
- 新增 `docs/source/deprecation-timeline.md`：弃用机制说明与废弃时间表
- 新增 `docs/source/json-serialization.md`：JSON 序列化规范，
  记录抽象层 API、语义对齐策略、与标准库的固有差异、ASCII 安全出口与迁移检查清单

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
- `dev` extra 补齐 `pymemcache` / `redis` / `celery`，保证单元测试在 CI 中可直接运行
- GitHub Actions 增加 memcached / redis 服务容器，对齐 GitLab CI 的运行环境
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
- 移除未使用的 `pathtools` 显式依赖：它在 Python 3.12 上构建失败
  （`No module named 'imp'`），导致 GitHub Actions 的 `Publish to PyPI` 工作流
  自 **v0.8.1** 起即在依赖安装步骤失败，v0.9.0 修复后首次跑通完整测试
- 修复 GitHub Actions 测试环境缺少 `pymemcache` / `redis` / `celery` 导致的
  **27 failed + 27 errors**（CI 已补齐依赖与服务容器）

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
