# Litefs 代码深度审计与升级方案

**审计日期**: 2026-10-23
**审计版本**: v0.10.0（含未发布变更）
**审计范围**: `src/litefs` 全量源码
**方法**: 五路子系统并行审查（核心请求链路 / 服务器与网络层 / 数据与状态层 / 安全与中间件 / 生态与工程化），全部结论均经过源码逐行核实，未核实项明确标注

---

## 一、审计结论摘要

| 维度 | 结论 |
|------|------|
| 确认的功能缺陷 / BUG | **15 项**（高 5 / 中 6 / 低 4） |
| 已规划待交付项 | mypy strict、TestClient、ASGI lifespan、entry_points 等（见 release-roadmap.md，不重复列入） |
| 核心风险集中区 | **服务器网络层资源治理**（连接/内存无上限）与 **请求体解析**（multipart 全量驻留内存） |
| 与业内框架最大差距 | 上传流式化、连接治理、分布式限流、WebSocket 帧上限——均为"生产可用"层面的差距，而非 API 面差距 |

---

## 二、缺陷与 BUG 清单

### 2.1 高严重程度

#### D1 WebSocket 帧与接收缓冲区均无大小上限（内存放大 DoS）

- 位置：`src/litefs/websocket/protocol.py` L96-L115、`src/litefs/websocket/connection.py` 接收循环
- 问题：`Frame.parse` 对 64 位长度（`payload_len == 127`）无上限校验，恶意客户端声明 2^63 长度后，连接层 `buf += chunk` 无限累积直至 OOM；同一条连接的慢速发送即可打满内存
- 对标：Gin / Actix / Starlette 均有默认帧上限（如 Starlette `max_text_size`），超限即断连并回 1009

#### D2 原生服务器无连接数上限、无空闲读超时（slowloris 无防护）

- 位置：`src/litefs/server/greenlet_server_base.py` L387-L403
- 问题：`verify_request` 恒返回 `True`，每连接占用一个 epoll 注册项 + greenlet；客户端建立连接后不发数据可无限占用，fd 与 greenlet 数量随连接线性增长直至耗尽。asyncio 路径仅有 keep-alive 超时（`reader._timeout`），greenlet / epoll 多进程路径完全无防护
- 对标：Gin `ReadTimeout/WriteTimeout`、Nginx `client_body_timeout`、gunicorn `timeout` 均为标配

#### D3 500 响应泄漏内部异常信息

- 位置：`src/litefs/server/asyncio.py` L121-L125
- 问题：`_send_error(500, f"Internal server error: {str(e)}")` 将原始异常消息（可能含文件路径、SQL 片段、内网地址）直接返回给客户端
- 对标：Flask 生产模式返回统一 500 页并在服务端记录详情；Django `DEBUG=False` 同理

#### D4 multipart 全量驻留内存 + 解析正确性缺陷

- 位置：`src/litefs/handlers/form.py` L141-L178
- 问题（4 项）：
  1. `data = wsgi_input.read(content_length)` 整个请求体一次读入内存后再写 TemporaryFile——50MB 默认上限 × 并发上传即内存放大，流式 spool 形同虚设
  2. `data.split(begin_boundary)` 朴素分割，文件内容中出现与 boundary 相同的字节序列即解析损坏（正确实现要求 boundary 前有 CRLF）
  3. `posts[name] = content.strip()` 丢失用户字段值的合法前后空白
  4. 同名多值字段直接覆盖（与 urlencoded 路径的 list 语义不一致）
- 对标：Werkzeug 逐块流式解析 + 临时文件 spool；Go `multipart.Reader` 流式；Express multer 同理

#### D5 CORS 对字符串响应丢失全部响应头 + 通配符与凭证组合未拦截

- 位置：`src/litefs/middleware/cors.py` L90-L110
- 问题：
  1. 响应为非 tuple（原生 Socket 路径的 str 响应）时，CORS 头计算后从未应用，静默丢失——与已修复的 i18n / Prometheus「Socket 链路丢头」同类缺陷
  2. `allow_origins=["*"]` 与 `allow_credentials=True` 组合未校验，产出 `ACAO: *` + `ACAC: true` 的规范禁止组合（浏览器会拒绝，但服务端应直接拒绝配置并告警）
- 对标：Starlette `CORSMiddleware` 在 credentials 模式下强制逐 origin 回显并拒绝 `*`；Sanic 明确抛配置错误

### 2.2 中严重程度

#### D6 限流 / 节流中间件四项缺陷

- 位置：`src/litefs/middleware/rate_limit.py` L41-L102、L154、L183-L193
- 问题：
  1. 无锁 `defaultdict(list)`：过滤后整体回写 `self.requests[key] = request_times` 与并发 `append` 存在丢失窗口，限流可被并发绕过
  2. 键字典无淘汰：`requests` / `blocked_until` / `last_request_time` 随 IP 数无界增长（每个 IP 一条 list，60 秒内 100 条时间戳）
  3. IPv6 键错误：`":" in remote_addr → split(":")[0]` 将 `::1` 截为空串、所有 `2001:db8:*` 截为 `2001`——IPv6 用户互相共享限流配额
  4. 多进程模式（epoll 多 worker / ProcessHTTPServer）下各进程独立计数，实际配额 = 配置值 × 进程数
- 对标：Nginx limit_req 共享内存；Go tollbooth / Redis 令牌桶分布式计数是标准做法

#### D7 JWT 校验不完整

- 位置：`src/litefs/auth/jwt.py` L191-L227
- 问题：
  1. 只校验 `exp`，不校验 `nbf` / `iat`，无时钟偏移容忍（leeway）
  2. 不校验 `header.alg` 与实例配置一致（当前签名实现固定 HMAC-SHA256，不存在 RS256→HS256 混淆漏洞，但属于规范不合规，未来支持非对称算法时即成漏洞）
  3. `decode_token` 不校验 `type` claim——7 天有效期的 refresh token 可当作 access token 使用，缩短了凭证轮换的意义

#### D8 MemoryCache 无并发保护

- 位置：`src/litefs/cache/cache.py` L399-L453
- 问题：`OrderedDict` 的 `move_to_end` / `popitem` / 双结构（`_cache` + `_expiry`）操作全部无锁。greenlet 单线程路径安全，但多线程 WSGI 容器（gunicorn threads）下存在结构竞态；check-then-act（`_is_expired` 内 delete）亦是竞态点
- 对标：cachetools 的 TTLCache 配合外部锁使用；Flask-Caching 明确要求线程安全后端

#### D9 OpenAPI 生成器类型推断薄弱

- 位置：`src/litefs/openapi/generator.py` L50-L146、L205-L231
- 问题：仅从类注解提取 properties，复杂类型一律回退 `string`；不解析 handler 签名（query/body 参数完全靠手写 docstring），生成的 schema 与实际路由行为可静默不一致
- 对标：FastAPI / Litestar 基于 Pydantic 全量推断；Flask-Spectree / apispec 也做签名级推断

#### D10 插件加载无异常隔离

- 位置：`src/litefs/plugins/loader.py` L81-L133、`plugins/base.py` L129-L155
- 问题：插件失败仅 `print` 后继续（无日志器、无失败插件列表上报）；依赖检查只看是否注册，无版本兼容检测；一个插件在 import 副作用中抛错可能污染全局状态
- 对标：Django app registry 有明确的加载失败异常与 ready() 隔离；Celery 插件加载失败会显式 fail-fast

#### D11 chunked 传输编码未处理

- 位置：`src/litefs/handlers/form.py` L117-L141（WSGI 路径 `read(content_length)` 信任头部）、自研 Socket 链路同类
- 问题：请求体大小限制完全依赖 `Content-Length` 头；客户端以 chunked 编码发送（无 Content-Length）时，自研服务器链路无法读取或限制请求体。外部 WSGI 容器（gunicorn）会先行 dechunk，风险集中于自研服务器直连场景
- 对标：gunicorn / uvicorn 均在服务器层完成 dechunk 与大小限制

### 2.3 低严重程度

#### D12 监听 backlog 设置为 4194304

- 位置：`src/litefs/server/greenlet_server_base.py` L316
- 问题：内核实际截断到 `net.core.somaxconn`，超大值无意义且掩盖了「未暴露 backlog 配置项」的问题

#### D13 asyncio 路径篡改 StreamReader 私有属性

- 位置：`src/litefs/server/asyncio.py` L47
- 问题：`self.reader._timeout = ...` 依赖 CPython 私有实现细节，版本升级即碎

#### D14 CORS 反射 Access-Control-Request-Headers

- 位置：`src/litefs/middleware/cors.py` L156-L157
- 问题：预检响应原样回显请求头列表，未与 `allow_headers` 白名单求交集

#### D15 /metrics 仅进程内聚合

- 位置：`src/litefs/metrics.py`、`middleware/prometheus.py`
- 问题：多 worker 部署下每个进程暴露自己的 /metrics，Prometheus 抓取单实例会低估；需要文档说明抓取全部 worker 或提供聚合端口
- 对标：gunicorn + prometheus_client 的标准做法是每 worker 独立端口或 push gateway

---

## 三、与业内框架功能对比

### 3.1 横向对比表

| 能力 | Litefs | Flask 3 | FastAPI | Starlette 1.0 | Django 6 | Gin (Go) | Actix (Rust) | Express/Fastify (Node) |
|------|--------|---------|---------|---------------|----------|----------|--------------|------------------------|
| 内置生产级服务器 | ✅ 三套（自研，特色） | ❌ 依赖 gunicorn | ❌ 依赖 uvicorn | ❌ 依赖 uvicorn | ❌ wsgiref 仅开发 | ✅ net/http | ✅ 内置 | ✅ 内置（建议前置 Nginx） |
| 上传流式化 | ❌ 全量驻留内存 | ✅ Werkzeug spool | ✅ SpooledTemporaryFile | ✅ 流式 | ✅ 流式 | ✅ 流式 | ✅ 流式 | ✅ multer/fastify-multipart 流式 |
| 连接治理（超时/上限） | ❌ 无 | N/A（服务器层） | N/A | N/A | N/A | ✅ Read/WriteTimeout | ✅ 内置 | ✅ server.timeout |
| WebSocket | ✅ 内置（❌ 无帧上限） | ❌ 需扩展 | ✅（有帧上限） | ✅（有帧上限） | ✅ Channels | ✅ gorilla/websocket | ✅ actix-ws | ✅ ws 库（有上限） |
| CORS 默认安全 | ⚠️ 通配符+凭证可配 | ✅ 扩展规范 | ✅ 规范强制 | ✅ 规范强制 | ✅ | ✅ 手动 | ✅ 手动 | ✅ cors 中间件规范 |
| 限流 | ⚠️ 仅进程内内存 | ✅ 扩展生态 | ✅ slowapi/Redis | ✅ 扩展 | ✅ DRF 内置多后端 | ✅ tollbooth 等 | ✅ 扩展 | ✅ 插件生态 |
| 请求/响应类型与文档 | ⚠️ OpenAPI 弱推断 | ⚠️ 扩展 | ✅ Pydantic 全量 | ⚠️ 手动 | ✅ DRF Schema | ⚠️ swaggo 注释 | ✅ utoipa | ⚠️ 注释式 |
| 生命周期钩子 | ❌ 无 lifespan | ✅ before/after | ✅ lifespan | ✅ lifespan | ✅ ready()/signals | N/A | ✅ 内置 | ✅ 内置 |
| 可观测性 | ⚠️ Prometheus（无 OTel） | 扩展 | ✅ OTel 生态 | 扩展 | ✅ 内置+生态 | ✅ 生态 | ✅ tracing 生态 | ✅ OTel 生态 |
| 原生同步 + 协程双栈 | ✅（特色） | ❌ 仅同步 | ❌ 仅异步 | ❌ 仅异步 | ❌ 仅同步（3.x ASGI 单栈） | N/A | N/A | N/A |

### 3.2 差距定性

1. **Litefs 的差异化优势**：三套自研服务器（epoll/greenlet/asyncio）+ 同步/异步双栈共存 + 零外部服务器依赖的部署体验，业内无对标物；Hello World 性能基准优于 FastAPI 1.4~2.0 倍
2. **最大短板不在 API 面，而在资源治理**：连接、内存、缓冲区三个维度均无上限——这是「能跑分」与「能上生产」的差距，D1/D2/D4 三项即可在公网环境被单机打挂
3. **安全默认值弱于 Django 惯例**：Django 的安全头/CSRF/密码哈希开箱即安全；Litefs 需要用户显式配置（`cookie_secure=False` 默认、CORS 通配符默认）
4. **生态互操作是硬缺口**（已在路线图 v0.13.0 规划）：无 lifespan 意味着无法被 uvicorn/hypercorn 正确托管，无 entry_points 意味着插件生态无法开放

---

## 四、升级方案

> 与既有 0.10.0 → 1.0.0 路线（release-roadmap.md）对齐，**不推翻既有版本序列**，
> 将本次审计发现按风险等级插入对应版本，新增项标注 ⭐。

### 4.1 插入位置总览

| 版本 | 既有主题 | 新增内容 |
|------|---------|---------|
| **v0.10.1**（新增补丁版） | — | ⭐ 安全缺陷紧急修复包（4.2 节） |
| v0.11.0 | 类型系统与打包契约 | ⭐ 并发安全治理 + JWT 加固（4.3 节） |
| v0.12.0 | 测试基础设施与质量基线 | ⭐ multipart 流式化 + 连接治理（4.4 节） |
| v0.13.0 | ASGI 协议与插件生态 | ⭐ 插件异常隔离（4.5 节） |
| v0.14.0 | 工程化与 Python 基线收敛 | ⭐ 限流分布式后端（4.6 节） |
| v0.15.0 / v1.0.0 | 发布基础设施 / 稳定性声明 | 无新增（安全闭环版本本就涵盖 D3 类问题的响应流程） |

### 4.2 v0.10.1 —— 安全缺陷紧急修复包（建议立即执行）

补丁号版本，只修高危，不含任何新功能：

| # | 修复项 | 对应缺陷 | 验收标准 |
|---|--------|---------|---------|
| 0.10.1-1 | WebSocket 帧上限（默认 1MB，可配）+ 缓冲区上限，超限回 1009 断连 | D1 | 超大帧用例 + 内存占用回归测试 |
| 0.10.1-2 | 原生服务器连接治理：`max_connections`、空闲读超时（默认 30s）、超限快速拒绝 | D2 | slowloris 压测用例 |
| 0.10.1-3 | 500 响应去掉异常细节，统一返回通用消息（debug 模式保留详情） | D3 | 三条服务器路径统一断言 |
| 0.10.1-4 | CORS：字符串响应补齐响应头写入；`*` + credentials 组合启动期抛错 | D5 | Socket 链路 CORS 用例 |

实施状态（全部完成，待随 0.10.1 发布）：

- **0.10.1-1 已完成**：`Frame.parse` 新增 `max_payload_size` 参数（帧头声明长度
  超限立即抛 `FrameTooLargeError`，无需等待完整负载到达）；
  `WebSocketConnection` 默认上限 1MB（含接收缓冲区纵深防御上限），超限回
  1009 关闭帧并断连；`WebSocketServer` 握手请求头同步设上限。
  配置项：`websocket_max_message_size`。
  测试：`tests/unit/test_websocket_server.py::TestWebSocketFrameLimits`
- **0.10.1-2 已完成**：`TCPServer` 新增 `max_connections`（达上限快速拒绝，
  不创建 greenlet 与 epoll 注册项）与 `idle_read_timeout`（默认 30s，
  `Epoll._check_read_deadlines` 对阻塞读超时的连接注入 `socket.timeout` 断连）；
  asyncio 路径（`AsyncHTTPServer`）同语义实现。
  配置项：`max_connections`（默认 1024）、`idle_read_timeout`（默认 30.0）。
  测试：`tests/unit/test_server_connection_governance.py`
- **0.10.1-3 已完成**：三条服务器路径逐一核实——socket / wsgi（`base.py`
  `_process_route_error`）与 asgi 路径此前已按 `config.debug` 门控，无需改动；
  asyncio 路径（`server/asyncio.py`）为唯一泄露点，已改为 `_internal_error_message`
  统一脱敏（debug 模式保留细节）。测试同上文件
- **0.10.1-4 已完成**：`CORSMiddleware.process_response` 对非 tuple 响应
  经 `request_handler._add_header` 补写 CORS 头（Socket 链路响应构建流程统一输出）；
  `allow_origins=['*']` 与 `allow_credentials=True` 组合在中间件构造期（启动期）
  抛 `ValueError`。测试：`tests/unit/test_middleware.py::TestCORSMiddlewareSecurity`

### 4.3 并入 v0.11.0 —— 并发安全与认证加固

| # | 任务 | 对应缺陷 |
|---|------|---------|
| 0.11-⭐1 | `MemoryCache` / `RateLimitMiddleware` / `ThrottleMiddleware` 加锁 + 键淘汰策略（LRU 上限） | D6、D8 |
| 0.11-⭐2 | JWT：校验 `nbf`/`iat`、leeway 参数、`header.alg` 白名单校验、access/refresh type 区分 | D7 |
| 0.11-⭐3 | IPv6 限流键修复（保留完整地址，不截断） | D6-3 |

实施状态（全部完成，待随 0.11.0 发布）：

- **0.11-⭐1 已完成**：`MemoryCache` 全部公共方法（put/get/delete/exists/
  clear/expire/ttl）受 `threading.RLock` 保护（`_is_expired` 内重入
  delete 安全）；`RateLimitMiddleware` / `ThrottleMiddleware` 状态读写
  加锁，并发不再突破配额（回归测试以 20 线程 × 10 请求断言恰好
  `max_requests` 个放行）。键字典改为 `OrderedDict` + `max_keys` 参数
  （默认 65536）LRU 淘汰：先清理窗口过期条目，仍超限时从最旧一端逐出。
  测试：`test_memorycache.py::TestMemoryCacheHardening`、
  `test_rate_limit_fixes.py::TestRateLimitHardening` / `TestThrottleHardening`
- **0.11-⭐2 已完成**：`JWTManager` 构造期白名单校验 `algorithm`
  （当前仅 `HS256`，其余抛 `ValueError`）；`decode_token` 校验
  `header.alg` 与实例算法一致（防算法混淆）、`nbf` 未生效与 `iat`
  未来时间（超 leeway）拒绝；新增 `leeway` 构造参数与
  `decode_token(expected_type=...)` 强制类型区分，并提供
  `decode_access_token` / `decode_refresh_token` 便捷方法。
  不传 `expected_type` 时行为不变（向后兼容）。
  测试：`test_auth_jwt.py::TestJWTManagerHardening`（9 项）
- **0.11-⭐3 已完成**：限流 / 节流默认键函数统一走 `_extract_client_ip`：
  基于 `ipaddress` 解析，完整 IPv6 地址（含 `::1`）不截断；
  `IPv4:port` / `[IPv6]:port` 剥离端口。原有 `IPv4:port` 剥离行为
  由既有测试 `test_remote_addr_port_removal` 持续保障。
  测试：`test_rate_limit_fixes.py::TestRateLimitHardening`

### 4.4 并入 v0.12.0 —— 请求体解析与连接治理重构

| # | 任务 | 对应缺陷 |
|---|------|---------|
| 0.12-⭐1 | multipart 流式化：逐块读入 + 边界感知解析（含 CRLF 前缀校验）+ 同名多值语义与 urlencoded 对齐 | D4 |
| 0.12-⭐2 | 自研服务器链路 chunked 请求体支持与实际读取大小强制限制 | D11 |
| 0.12-⭐3 | `request_queue_size` 暴露为配置项并给出合理默认值 | D12 |

实施状态（全部完成，待随 0.12.0 发布）：

- **0.12-⭐1 已完成**：`handlers/form.py` 新增流式核心解析器
  `_parse_multipart_fp`（逐块读取 + 滑动缓冲增量扫描），三条路径
  （WSGI / ASGI / Socket 流式）统一收敛到该实现：
  仅识别行首 `--boundary`（首个边界允许无 CRLF 前缀，RFC 2046），
  内容中类边界字节序列不再破坏解析；边界分隔符前的 CRLF 归属分隔符，
  不再计入文件内容；字段值不再 strip；同名多值字段（含多文件上传）
  与 urlencoded 语义对齐转为列表。WSGI 路径不再整包
  `read(content_length)`，文件部件边解析边写入临时文件；
  流式路径按实际读取字节数强制 `max_upload_size`（413）。
  测试：`test_handlers_form.py::TestMultipartHardening`
- **0.12-⭐2 已完成**：`handlers/form.py` 新增同步解码器
  `read_chunked_body`，Socket 链路（`SocketRequestHandler`）识别
  `HTTP_TRANSFER_ENCODING: chunked` 后解码请求体（含 chunk 扩展与
  trailer），`CONTENT_LENGTH` 同步为实际长度，按 `max_request_size`
  限制（413）；asyncio 链路（`AsyncHTTPRequestHandler`）新增
  `_read_request_body` / `_read_chunked_body`：chunked 解码、
  `Content-Length` 精确读取（`readexactly`，keep-alive 下不吞后续
  请求）、截断回 400、超限回 413。
  测试：`test_chunked_body.py`
- **0.12-⭐3 已完成**：新增配置项 `request_queue_size`（默认 2048，
  内核截断到 `net.core.somaxconn`）；`TCPServer` 类属性由硬编码
  4194304 改为 2048 并支持构造参数覆盖（backlog 须在
  `server_activate` 前设置）；`ProcessHTTPServer` 透传；
  `server_mixin` 将应用配置传入两处服务器创建点；asyncio 服务器
  经 `asyncio.start_server(backlog=...)` 同语义支持。
  测试：`test_greenlet_server.py::TestRequestQueueSize`、
  `test_asyncio_server.py::TestBacklogConfig`

### 4.5 并入 v0.13.0 —— 插件生态配套

| # | 任务 | 对应缺陷 |
|---|------|---------|
| 0.13-⭐1 | 插件加载异常隔离：失败插件进入失败清单、走日志器、不污染全局；版本兼容声明 | D10 |
| 0.13-⭐2 | OpenAPI 类型推断增强：基于 `inspect` + `typing` 解析 handler 签名的 query/body 参数（渐进，不承诺 Pydantic 级） | D9 |

实施状态（全部完成，随 0.13.0 发布）：

- **0.13-⭐1 已完成**：`PluginManager` 新增 `failed_plugins` 失败清单
  （插件名 → 失败原因），实例化 / `initialize` 抛错不再向外传播，
  `load_all` 不再因单个插件失败整体中断；依赖插件失败时依赖方同样
  进入失败清单。`PluginLoader` 失败经 `litefs.plugins` 日志器记录
  （替代 `print`）、进入 `failed_plugins` 路径清单，并清理
  `sys.modules` 残留模块注册。`Plugin` 基类新增
  `required_litefs_version` 版本兼容声明，要求高于当前框架版本时
  拒绝加载并记录原因（未声明跳过检查，向后兼容）。
  测试：`test_plugins.py::TestPluginIsolation` / `TestLoaderIsolation`
- **0.13-⭐2 已完成**：`OpenAPIGenerator` 新增
  `_infer_signature_parameters`（基于 `inspect.signature` 渐进式推断）：
  首参数 `request` 之后的签名参数推断为 query 参数（类型取自注解、
  无默认值必填）；路径参数 schema 类型取自签名注解（此前硬编码
  string）；`data` / `body` / `payload` 保留名参数推断为 JSON
  requestBody。显式 `@openapi.doc` 参数始终优先，不产生重复；
  `*args` / `**kwargs` 跳过。
  测试：`test_openapi.py::TestSignatureInference`

### 4.6 并入 v0.14.0 —— 分布式与可观测性

| # | 任务 | 对应缺陷 |
|---|------|---------|
| 0.14-⭐1 | 限流共享后端（Redis 令牌桶），多进程/多实例配额一致 | D6-4 |
| 0.14-⭐2 | asyncio 路径去私有属性依赖（`loop.call_later` 实现读超时） | D13 |
| 0.14-⭐3 | /metrics 多 worker 聚合方案文档化（抓取策略或聚合端口） | D15 |

### 4.7 度量与门禁

- 每项修复必须附带**复现该缺陷的回归测试**（先红后绿）
- v0.10.1 起新增「资源占用回归」：上传 / WebSocket / 慢连接三场景的内存峰值纳入性能门禁（`tests/performance/thresholds.json` 扩展）
- 安全类缺陷修复在 CHANGELOG 单列 `Security` 专章（对标 Keep a Changelog）

---

## 五、风险与优先级

| 风险 | 等级 | 说明 |
|------|------|------|
| D1/D2/D4 在公网部署下可被单机 DoS | **高** | 建议以 v0.10.1 补丁版先行，不等 v0.12.0 |
| D3 信息泄漏 | 高 | 一行级修复，随 v0.10.1 |
| D6 限流失效 | 中 | 有 Nginx 前置时风险被部分遮蔽，但仍应修复 |
| D9/D10 生态质量 | 中 | 影响开发者体验，不阻塞生产部署 |
| 修复与既有版本计划的冲突 | 低 | 本方案全部为「插入」，未改变既有版本主题与硬性标准映射 |

---

**文档维护**: 开发团队
**评审状态**: 待评审
**上次更新**: 2026-10-23
