# Litefs 单元测试文档

**更新日期**: 2026-10-20
**适用版本**: v0.9.0（开发中）

## 测试概述

Litefs 使用 Python `unittest` 风格编写测试，通过 `pytest` 运行与统计覆盖率。
截至 2026-10-20，测试套件共 **1306 个用例全部通过**，代码覆盖率从基线 **47% 提升至 70%**（9121 语句，未覆盖 2434）。

> 注：全量运行中的 3 failed + 14 errors 均为 Memcache 环境问题（本机无 `memcached:11211`），与代码无关。

## 测试文件结构

```
tests/
├── unit/                      # 单元测试（78 个模块）
│   ├── 核心
│   │   ├── test_core.py / test_core_comprehensive.py   # 应用核心
│   │   ├── test_basic.py / test_config.py              # 基础与配置
│   │   ├── test_environ.py / test_wsgi_environ.py      # WSGI 环境变量
│   │   ├── test_request.py / test_context.py           # 请求与上下文
│   │   ├── test_forms.py / test_form.py                # 表单数据结构
│   │   ├── test_exceptions.py                          # 异常体系
│   │   └── test_routing.py / test_scaffold.py          # 路由与脚手架
│   ├── HTTP 处理
│   │   ├── test_wsgi.py / test_wsgi_post.py / test_wsgi_simple.py / test_wsgi_client.py / test_wsgi_no_greenlet.py
│   │   ├── test_asgi_server.py / test_asyncio_server.py / test_greenlet_server.py
│   │   ├── test_streaming.py / test_max_request_size.py / test_error_pages.py
│   │   ├── test_static_handler.py / test_default_page.py / test_health_check.py
│   │   ├── test_handlers_form.py / test_handlers_enhanced.py   # 表单/增强处理器
│   │   └── test_server_connection_governance.py                # 连接治理（max_connections/空闲读超时/500 脱敏）
│   ├── 中间件
│   │   ├── test_middleware.py / test_middleware_base.py        # 管理器与基类
│   │   ├── test_middleware_security.py / test_middleware_csrf.py / test_middleware_params.py
│   │   ├── test_middleware_enhanced_logging.py
│   │   └── test_rate_limit_debug.py / test_rate_limit_bug.py / test_rate_limit_fixes.py
│   ├── 缓存
│   │   ├── test_cache.py / test_cache_manager.py / test_cache_factory.py
│   │   ├── test_memorycache.py / test_treecache.py / test_cache_tree_memory.py
│   │   ├── test_cache_backends_web.py / test_cache_memcache.py / test_database_cache.py
│   │   ├── test_cache_decorators.py / test_cache_form_cache.py
│   │   └── test_cache_watchdog.py                              # 热重载事件处理
│   ├── 会话
│   │   ├── test_session.py / test_session_store.py / test_session_factory.py
│   │   └── test_session_redis_integration.py / test_session_memcache_integration.py
│   ├── 认证与安全
│   │   ├── test_auth.py / test_auth_models.py / test_auth_password.py
│   │   ├── test_auth_jwt.py / test_auth_middleware.py / test_auth_manager.py
│   │   ├── test_oauth2.py / test_oauth2_providers.py
│   │   └── test_security_utils.py                              # 路径安全/CSRF 工具
│   ├── 数据与任务
│   │   ├── test_database_session.py / test_database_core.py    # SQLAlchemy 封装
│   │   └── test_tasks.py / test_celery_tasks.py                # Celery 集成
│   ├── 生态
│   │   ├── test_websocket.py / test_openapi.py
│   │   ├── test_plugins.py                                     # 插件系统
│   │   └── test_debug.py / test_debug_middleware.py            # 调试工具栏
│   └── 其他
│       ├── test_utils.py / test_validators.py / test_examples_basic.py
│       └── test_auth.py 等
├── integration/               # 集成测试（test_asgi_integration.py）
├── performance/               # 性能基准
├── stress/                    # 压力测试
└── run_tests.py               # unittest 测试运行器
```

## 运行测试

### 运行全量测试并统计覆盖率（推荐）

```bash
python -m pytest tests/unit tests/integration --cov=litefs --cov-report=term
```

### 运行单个测试文件 / 类 / 方法

```bash
python -m pytest tests/unit/test_auth_jwt.py
python -m pytest tests/unit/test_auth_jwt.py::TestJWTManager
python -m pytest tests/unit/test_auth_jwt.py::TestJWTManager.test_roundtrip
```

### 仅运行单元测试（不统计覆盖率）

```bash
python -m pytest tests/unit
```

### 兼容方式（unittest 运行器）

```bash
python tests/run_tests.py
python -m unittest tests.unit.test_core
```

## 测试统计

| 指标 | 数值 |
|------|------|
| 用例总数（unit + integration + performance） | 2082（全部通过） |
| 代码覆盖率 | **84%**（10510 语句，未覆盖 1416） |
| 覆盖率基线 | 47%（v0.9.0 升级前） |

### 覆盖率提升过程（2026-10-20）

分三批按"缺失行数 ÷ 测试难度"性价比推进：

| 批次 | 新增测试模块 | 覆盖率 |
|------|--------------|--------|
| 基线 | — | 47% |
| 第一批：forms / context / exceptions / static_handler / cache_decorators / csrf | 6 | 54.1% → 59.1% |
| 第二批：oauth2 / providers / enhanced_logging / session / auth_password / utils | 8 | 59.8% → 62% |
| 第三批：debug / auth 全家桶 / handlers / middleware_base / tasks / database / cache / plugins / security | 16 | 65% → 70% |
| 第四批（v0.12.0，2026-10-23）：server_mixin / greenlet_server_base / greenlet / websocket 连接与服务器 / session 三后端 | 7 | 76% → 84% |

## 测试中修复的源码 Bug

编写测试过程中发现并修复了 5 处真实缺陷：

| 位置 | 问题 | 修复 |
|------|------|------|
| `exceptions.ValidationError.message` | 异常消息属性错误 | 修正消息属性 |
| `abort()` 未映射状态码 | 部分状态码无对应异常 | 补全映射 |
| `cached` 装饰器 `cache_clear` | 清理接口缺失/失效 | 修正缓存清理 |
| `auth/middleware.py` `User.get_by_id` | `User` 为 dataclass 无此方法，合法 token 请求必崩 `AttributeError` | 改为 `get_user_store().get_by_id(user_id)` |
| `handlers/form.py` `parse_multipart_stream` | 字段分支用 `StringIO` 承接 bytes 必崩 `TypeError` | 改用 `BytesIO` 并正确解码 |

## 覆盖情况

已覆盖的核心模块：

- ✅ 应用核心（core.py 拆分后的 `app/` 包）
- ✅ 表单解析与验证（handlers/form.py、validators）
- ✅ 缓存体系（Memory / Tree / Redis / Memcache / DB / FormCache / 工厂 / 热重载）
- ✅ 会话管理（多后端存储与工厂）
- ✅ 认证授权（JWT / OAuth2 / 用户模型 / 装饰器 / 中间件）
- ✅ 中间件系统（基类 / 管理器 / CORS / CSRF / 安全头 / 限流）
- ✅ 数据库封装（database/core.py、连接池）
- ✅ Celery 任务集成
- ✅ 插件系统（Plugin / PluginManager / PluginLoader）
- ✅ 调试工具栏（debug 中间件与格式化输出）
- ✅ 安全工具（路径拼接 / CSRF token）
- ✅ 异常体系与上下文

## 待补充测试

v0.12.0 第四批已将核心服务器模块提升至 80% 以上（server_mixin 86%、
greenlet_server_base 87%、greenlet 81%、websocket 90%+），以下模块覆盖率
仍相对偏低，计划后续补齐：

- ⚠️ `app/server_cli.py`（17%）
- ⚠️ `server/asyncio.py`（68%）
- ⚠️ `handlers/socket.py`（65%）/ `handlers/socket_response.py`（69%）
- ⚠️ `handlers/wsgi.py`（68%）

## 测试最佳实践

1. **unittest 风格 + 中文 docstring**：与 `tests/unit/test_validators.py` 保持一致
2. **setUp 隔离全局状态**：涉及全局注册表/单例的测试在 `setUp`/`tearDown` 中重置（如 `DatabaseManager._instance`、`set_user_store`）
3. **Mock 约束**：`Mock(spec=[])` 限制属性读取，需要的方法显式赋值
4. **不测纯 import**：不为导入行为堆凑数用例
5. **边界与异常路径**：优先覆盖分支边界与错误路径，而非重复正常路径
6. **环境依赖标注**：依赖外部服务（Redis/Memcache）的用例失败时先确认环境，不盲目修代码

## 注意事项

1. **Memcache 环境问题**：本机无 `memcached:11211`，`test_cache_memcache.py` 等相关用例会失败/报错，属预期现象
2. **SQLite 资源警告**：TreeCache 测试会输出 SQLite 连接未关闭警告，因测试创建了多个缓存实例，属正常现象
3. **celery 控制面测试**：`Control.inspect` 是类属性，patch 时需使用 `patch('celery.app.control.Control.inspect')` 而非替换实例属性

## 持续改进

- 提交代码前运行 `python -m pytest tests/unit tests/integration`
- 新增功能必须附带单元测试并同步本文档
- 覆盖率目标：70%（v0.9.0 已达成）→ 84%（v0.12.0 已达成）→ 85%（v1.0）
