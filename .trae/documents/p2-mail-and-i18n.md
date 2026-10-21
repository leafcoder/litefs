# P2 功能扩展实施计划（邮件发送 + i18n 国际化）

**创建日期**: 2026-10-21
**目标版本**: v0.9.0-rc
**来源**: docs/source/todolist.md 的「P2 功能扩展」

---

## 一、目标与范围

| 任务 | todolist 原文要求 | 交付物 |
|------|--------------------|--------|
| 邮件发送 | smtplib 封装、Message 类、Mako 模板邮件、附件、Celery 异步发送 | `src/litefs/mail/` 包（5 模块） |
| i18n 国际化 | gettext 封装、请求级 locale 协商、模板翻译函数 | `src/litefs/i18n/` 包（4 模块） |

**明确不做**：用户级 locale 持久化（DB/session）、Babel 引入、邮件队列自建、P3 工程化收尾。

---

## 二、关键技术决策

### 2.1 依赖策略：零新增第三方依赖

| 能力 | 实现 | 理由 |
|------|------|------|
| SMTP 发送 | 标准库 `smtplib` | 标准库足够，无新增依赖 |
| MIME 组装 | 标准库 `email.message.EmailMessage` | 避免手写 MIME，边界情况由标准库兜底 |
| 模板渲染 | 已有 `mako`（框架已依赖） | 复用现成依赖 |
| gettext | 标准库 `gettext` | 标准库自带 `NullTranslations`/`GNUTranslations` |
| Celery | 已有可选依赖 `litefs.tasks` | 复用 `@task` 装饰器；Celery 缺失时降级同步发送 |

### 2.2 复用既有基础设施（勘察结论）

- **模板渲染**：`src/litefs/handlers/base.py:54` `BaseRequestHandler.render_template()`，内部延迟构建 `TemplateLookup(directories=[template_dir], input_encoding='utf-8', encoding_errors='replace', cache_enabled=not debug_mode)`，模板目录来自 `app.config.template_dir`。
- **请求上下文**：`src/litefs/context.py` 提供 `RequestContext`（threading.local）+ `g` 全局对象（`src/litefs/context.py:322`）。请求级 locale 存 `g.locale`。
- **请求头读取**：`src/litefs/handlers/base.py:505` `headers` property（已缓存，O(1)，键为小写连字符形式如 `accept-language`）。`self._environ['HTTP_ACCEPT_LANGUAGE']` 也可直接取。
- **中间件基类**：`src/litefs/middleware/base.py:7` `Middleware`，钩子 `process_request` / `process_response` / `process_exception` + 三个 async 版本（默认委托同步实现）。
- **中间件实例**：`MiddlewareManager` 创建，**App 级共享**（不是每请求新建）→ 请求级状态必须挂在 `request_handler` 实例上或 `g` 上。
- **Celery**：`src/litefs/tasks/__init__.py` — `Celery` 类 + 模块级 `task` 装饰器（第 339 行）+ `get_celery()`（第 360 行）+ `HAS_CELERY` 标志（第 42 行）。
- **配置**：`src/litefs/config.py:24` `DEFAULT_CONFIG` 字典；`Config.__getattr__`（第 527 行）支持属性访问；`__setattr__`（第 533 行）**只接受 DEFAULT_CONFIG 中已存在的 key**，新增配置项必须同时加进 DEFAULT_CONFIG。
- **可选依赖懒加载范式**：参考 `src/litefs/metrics.py` 的 `load_prometheus_client()`。

### 2.3 邮件 MIME 结构

- 仅 body → `text/plain`
- body + html → `multipart/alternative`（plain 在前，html 在后）
- 有附件 → 外层 `multipart/mixed`（内含 alternative 或单正文 + 附件）
- 附件支持：路径（path）、内存字节（content）、文本（content + mimetype）
- 使用 `EmailMessage` + `add_attachment` / `set_content` / `add_alternative`，标准库自动处理 Content-Transfer-Encoding 与 boundary

### 2.4 i18n locale 协商优先级

```
1. URL 查询参数 ?locale=zh_CN        （最高，显式指定）
2. Cookie（cookie_name，默认 'locale'）
3. HTTP Accept-Language 头           （按 q 值降序匹配 supported_locales）
4. default_locale（默认 'en'）
```

协商结果写入 `request_handler.locale`（实例属性）与 `g.locale`；响应阶段回写 `Content-Language: <locale>` 头。

**语言匹配规则**：
- 规范化：`zh-CN` → `zh_CN`（gettext 目录命名约定用下划线）
- 精确匹配 → 前缀回退（`zh_CN` → `zh`）→ 失败用 default_locale
- `*` 通配符视为匹配 default_locale

### 2.5 模板翻译函数注入

在 `BaseRequestHandler.render_template()` 的 kwargs 中注入 `_` / `gettext` / `ngettext`。
**零行为变化保障**：注入函数在无请求上下文 / 无 locale 时为恒等函数（返回原文）；i18n 模块用**函数内延迟导入**避免循环依赖。

---

## 三、文件清单

### 3.1 新建：`src/litefs/mail/`（5 个模块）

| 文件 | 预估行数 | 内容 |
|------|---------|------|
| `mail/__init__.py` | ~60 | 公开导出：`Message`、`EmailMessage` 别名、`Attachment`、`SMTPClient`、`MailSendError`、`render_mail_template`、`send_mail`、`send_mail_async`、`get_mail_config` |
| `mail/message.py` | ~280 | `Message` 类、`Attachment` 类、`build_email_message()` |
| `mail/smtp.py` | ~220 | `SMTPClient`（smtplib 封装）、`MailSendError`、重试退避、上下文管理器 |
| `mail/template.py` | ~150 | `render_mail_template()`：Mako 渲染 `.txt` / `.html` 配对模板 |
| `mail/tasks.py` | ~140 | Celery 异步任务 `send_mail_task`、`send_mail_async()`、`send_mail()` 同步入口 |

### 3.2 新建：`src/litefs/i18n/`（4 个模块）

| 文件 | 预估行数 | 内容 |
|------|---------|------|
| `i18n/__init__.py` | ~60 | 公开导出：`LocaleMiddleware`、`Translator`、`gettext`、`ngettext`、`parse_accept_language`、`negotiate_locale`、`inject_translations` |
| `i18n/locale.py` | ~180 | `parse_accept_language()`、`normalize_locale()`、`match_locale()`、`negotiate_locale()` |
| `i18n/translator.py` | ~200 | `Translator` 封装、`get_translations()` 缓存、`translate()`、`install_translations()` |
| `i18n/middleware.py` | ~180 | `LocaleMiddleware` |

### 3.3 修改

| 文件 | 改动 |
|------|------|
| `src/litefs/config.py` | `DEFAULT_CONFIG` 新增邮件段（11 项）+ i18n 段（7 项） |
| `src/litefs/handlers/base.py` | `render_template()` 中注入翻译函数（延迟导入，幂等，无上下文时不变） |
| `src/litefs/middleware/__init__.py` | 导出 `LocaleMiddleware` |
| `pyproject.toml` | `[project.optional-dependencies]` 新增 `mail` 段（Celery 可选版本）；i18n 无需新依赖 |
| `docs/source/todolist.md` | P2 两行标记 ✅ 并链接新文档 |
| `docs/source/index.rst` | toctree 追加 `mail-service`、`i18n` |

### 3.4 新建文档

- `docs/source/mail-service.md` —— 邮件模块完整说明
- `docs/source/i18n.md` —— 国际化完整说明

### 3.5 新建测试

- `tests/unit/test_mail.py` —— Message/MIME/附件/SMTPClient/模板/异步任务（约 30 用例）
- `tests/unit/test_i18n.py` —— Accept-Language 解析/locale 匹配/中间件/翻译函数（约 25 用例）

**测试约束**：全部用 `tmp_path` / `tempfile` 隔离，不污染仓库；SMTP 用 mock（`unittest.mock.patch('smtplib.SMTP')`），不连真实服务器。

---

## 四、配置项设计

```python
# 邮件配置
'mail_host': 'localhost',
'mail_port': 25,
'mail_username': None,
'mail_password': None,
'mail_use_tls': True,
'mail_use_ssl': False,
'mail_timeout': 30,
'mail_default_from': None,
'mail_template_dir': 'templates/email',
'mail_max_retries': 3,

# 国际化配置
'i18n_enabled': False,
'i18n_default_locale': 'en',
'i18n_supported_locales': ['en'],
'i18n_locale_dir': 'locales',
'i18n_cookie_name': 'locale',
'i18n_param_name': 'locale',
```

---

## 五、实施步骤（严格按序）

1. 建 `src/litefs/mail/` 包：`message.py` → `smtp.py` → `template.py` → `tasks.py` → `__init__.py`
2. 建 `src/litefs/i18n/` 包：`locale.py` → `translator.py` → `middleware.py` → `__init__.py`
3. 改 `config.py`（新增两段配置）、`handlers/base.py`（注入翻译函数）、`middleware/__init__.py`（导出）、`pyproject.toml`
4. 写 `tests/unit/test_mail.py` 与 `tests/unit/test_i18n.py`
5. 写 `docs/source/mail-service.md` 与 `docs/source/i18n.md`；更新 `todolist.md` + `index.rst`
6. 全量验证（见下）

---

## 六、验证要求（全部必须通过）

```bash
source /home/zhanglei3/.pyenv/versions/litefs/bin/activate
cd /home/zhanglei3/Desktop/dev/litefs

# 1. 静态检查三件套（新增模块不得进 mypy ignore 列表，必须零错误）
python -m flake8 src
python -m ruff check src
python -m mypy src

# 2. 新增测试
python -m pytest tests/unit/test_mail.py tests/unit/test_i18n.py -v

# 3. 全量回归（基线 1476 passed；memcached 相关失败为已知环境问题）
python -m pytest tests/ -ra --tb=short -q

# 4. 文档构建（不得新增告警，基线 30 warnings）
cd docs && make html && cd ..
```

**硬约束**（来自项目记忆与用户规则）：
- 新增模块**不得**加入 `pyproject.toml` 的 mypy ignore 列表
- 单文件 ≤ 600 行
- 代码注释、docstring、文档全中文
- flake8 max-line-length = 100
- 不主动 commit（等待用户确认目标分支）

---

## 七、风险与对策

| 风险 | 对策 |
|------|------|
| `handlers/base.py` 改 `render_template` 影响既有行为 | 注入函数在无 locale 时为恒等函数；用测试断言无 i18n 时渲染结果逐字节一致 |
| `email` 标准库生成的中文主题编码 | `EmailMessage` 默认用 base64 编码非 ASCII 头，符合 RFC 2047；测试断言 `msg['Subject']` 解码正确 |
| Celery 未安装时 `send_mail_async` 崩溃 | 降级为同步发送并返回明确标识；`HAS_CELERY` 判空 |
| gettext .mo 文件缺失 | `gettext.NullTranslations` 回退到原文，不抛异常 |
| SMTP 连接阻塞请求线程 | 异步走 Celery；同步路径提供 `timeout` 配置与 `mail_max_retries` 重试 |
