# Litefs 邮件发送

**更新日期**: 2026-10-21
**适用版本**: v0.9.0（开发中）

## 概述

Litefs 内置邮件发送模块，基于 Python 标准库 `smtplib` 与 `email.message.EmailMessage` 实现，
**零新增第三方依赖**，提供：

- **消息模型**：`Message` / `Attachment`，与传输层解耦
- **SMTP 客户端**：`SMTPClient`，支持 STARTTLS / 隐式 SSL、超时控制、失败重试与指数退避
- **模板邮件**：基于已有的 Mako 引擎，支持纯文本 + HTML 双模板配对
- **异步发送**：优先投递 Celery 队列，Celery 不可用时自动降级为同步发送

设计原则：

| 原则 | 实现方式 |
|------|----------|
| 零新增依赖 | 仅使用 `smtplib` / `email` / `gettext` 等标准库，Mako 与 Celery 复用已有依赖 |
| 传输解耦 | 消息模型不感知 SMTP，Celery 投递通过 `to_dict()` / `from_dict()` 完成 JSON 序列化 |
| 优雅降级 | Celery 未初始化或队列不可用时自动回退同步发送，业务代码无需分支判断 |
| 编码正确 | 非 ASCII 主题由标准库按 RFC 2047 编码，正文按 RFC 2046 自动选择编码 |
| 配置驱动 | SMTP 参数统一来自应用配置，运行时快照化为 `MailConfig`，避免隐式全局状态 |

## 快速开始

### 最小示例

```python
from litefs.core import Litefs
from litefs.mail import Message

app = Litefs(
    mail_host='smtp.example.com',
    mail_port=587,
    mail_use_tls=True,
    mail_username='noreply@example.com',
    mail_password='secret',
    mail_default_from='noreply@example.com',
)

message = Message(
    subject='注册验证',
    body='您的验证码是 123456',
    to=['user@example.com'],
)

result = app.send_mail(message)
print(result.success, result.error)
```

### 应用级发送入口

`Litefs.send_mail()` 是应用级封装，自动从应用配置读取 SMTP 参数：

```python
# 同步发送（阻塞当前请求线程）
result = app.send_mail(message)

# 异步发送（投递到 Celery 队列）
result = app.send_mail(message, asynchronous=True)
print(result.dispatched)  # True 表示已进入队列
print(result.task_id)     # Celery 任务 ID
```

> **返回语义**：`MailSendResult.success` 表示「投递成功或同步发送成功」；`dispatched` 区分两者——
> `True` 表示已投递到 Celery 队列（实际发送在 worker 侧完成），`False` 表示已同步发送完成。
> `error` 在失败时给出可读的原因。

### 独立使用（不依赖应用实例）

```python
from litefs.mail import SMTPClient, get_mail_config, send_mail
from litefs.core import Litefs

config = get_mail_config(Litefs())  # 从应用配置读取

with SMTPClient(config) as client:
    client.send(message)
```

## MIME 结构规则

框架根据传入内容自动选择 MIME 结构，无需手工拼装：

| 内容 | MIME 结构 |
|------|-----------|
| 仅 `body` | `text/plain` |
| `body` + `html_body` | `multipart/alternative`（纯文本在前，HTML 在后） |
| 含附件 | 外层 `multipart/mixed`，内含上述结构 |

> **为什么纯文本在前**：不支持 HTML 的邮件客户端会展示 `multipart/alternative` 中的第一个部分，
> 因此纯文本必须排在前面，否则部分客户端只能看到 HTML 源码。

## 附件

`Attachment` 的内容来源二选一，同时提供会抛出 `ValueError`：

```python
from litefs.mail import Attachment, Message

message = Message(
    subject='月度报表',
    body='报表已生成，详见附件。',
    to=['user@example.com'],
    from_addr='noreply@example.com',
)

# 来源一：磁盘文件
message.add_attachment(Attachment(filename='report.pdf', path='/tmp/report.pdf'))

# 来源二：内存内容
message.add_attachment(
    Attachment(filename='data.csv', content='a,b\n1,2\n', mimetype='text/csv')
)
```

| 参数 | 说明 |
|------|------|
| `filename` | 附件文件名（写入 `Content-Disposition`） |
| `content` | 内存内容，支持 `bytes` / `bytearray` / `str`（`str` 按 `charset` 编码） |
| `path` | 磁盘文件路径，发送时读取 |
| `mimetype` | MIME 类型，缺省时按文件名推断，推断失败回退 `application/octet-stream` |
| `charset` | 文本附件字符集，默认 `utf-8` |

> **Celery 投递注意**：`Attachment.to_dict()` 对内存内容做 base64 编码以保证 JSON 可序列化；
> `path` 方式在 worker 侧读取文件，因此**附件路径必须是 worker 可见的共享路径**（如 NFS、对象存储挂载）。

## 模板邮件

邮件模板复用框架已有的 Mako 引擎，模板目录由 `mail_template_dir` 指定（默认 `templates/email`）。

```text
templates/email/
├── welcome.txt     # 纯文本正文
└── welcome.html    # HTML 正文
```

```python
from litefs.mail import build_mail_body, Message

text, html = build_mail_body(
    'welcome',                       # 模板基础名（不带扩展名）
    'templates/email',
    username='张三',
    code='123456',
)

message = Message(
    subject='欢迎注册',
    body=text,
    html_body=html,
    to=['user@example.com'],
)
```

配对规则：

| 存在的模板 | 结果 |
|------------|------|
| 仅 `.txt` | `text` 有值，`html` 为 `None` → 纯文本邮件 |
| 仅 `.html` | `html` 有值，`text` 为 `""` → HTML 邮件 |
| 两者都有 | `text` 与 `html` 均有值 → `multipart/alternative` 邮件 |
| 都没有 | `build_mail_body()` 抛出 `FileNotFoundError` |

也可以直接调用 `render_mail_template()`，缺失的模板对应项返回 `None` 而不抛异常。

> 模板查找器按「目录 + debug 标志」缓存，调试模式下自动关闭缓存，保证模板改动立即生效。

## Celery 异步发送

```python
from litefs.mail import send_mail_async, Message

message = Message(
    subject='订单通知',
    body='您的订单已发货。',
    to=['user@example.com'],
)

result = send_mail_async(message)
```

异步链路：

```text
send_mail_async
   ├─ Celery 实例存在 → 注册任务 litefs.mail.send → task.delay() → 队列 mail
   │                    └─ worker：Message.from_dict() → MailConfig.from_dict() → SMTP 投递
   └─ Celery 未安装/未初始化 → 降级 send_mail()（dispatched=False）
```

要点：

| 项目 | 说明 |
|------|------|
| 任务名 | `litefs.mail.send`（常量 `SEND_MAIL_TASK_NAME`） |
| 队列 | `mail`（可在 worker 侧单独扩容与限流） |
| 任务注册 | 延迟注册，首次调用时按 `id(celery)` 缓存，避免模块导入时序问题 |
| 失败处理 | worker 内发送失败抛出 `MailSendError`，交由 Celery 重试策略处理 |

启动 worker：

```bash
celery -A your_app worker -Q mail -c 4
```

## 配置项

所有配置项均已内置默认值，可通过构造参数、`config.yaml` 或环境变量提供。

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `mail_host` | `localhost` | SMTP 服务器地址 |
| `mail_port` | `25` | SMTP 服务器端口 |
| `mail_username` | `None` | 认证用户名，None 表示不认证 |
| `mail_password` | `None` | 认证密码 |
| `mail_use_tls` | `True` | 是否在连接后升级为 STARTTLS |
| `mail_use_ssl` | `False` | 是否使用隐式 SSL（465 端口） |
| `mail_timeout` | `30` | 连接与发送超时（秒） |
| `mail_default_from` | `None` | 默认发件人地址，邮件未指定 `from_addr` 时使用 |
| `mail_template_dir` | `templates/email` | 邮件模板目录 |
| `mail_max_retries` | `3` | 发送失败的最大重试次数 |

`config.yaml` 示例：

```yaml
mail_host: smtp.example.com
mail_port: 587
mail_use_tls: true
mail_username: noreply@example.com
mail_password: ${MAIL_PASSWORD}
mail_default_from: noreply@example.com
mail_template_dir: templates/email
mail_max_retries: 3
```

### TLS 与 SSL 的选择

| 场景 | 配置 |
|------|------|
| 明文（仅内网） | `mail_use_tls: false`、`mail_use_ssl: false`，端口 `25` |
| STARTTLS（主流） | `mail_use_tls: true`、`mail_use_ssl: false`，端口 `587` |
| 隐式 SSL | `mail_use_tls: false`、`mail_use_ssl: true`，端口 `465` |

> `SMTPClient.connect()` 在 `use_ssl` 为真时**不会**再执行 STARTTLS（两个开关同时开启会与
> `smtplib` 的实现冲突）。

## 重试与超时

`SMTPClient.send()` 内置失败重试，退避时间为 `min(2 ** attempt, 30)` 秒：

```text
第 1 次失败 → 等待 1s  → 第 2 次失败 → 等待 2s → 第 3 次失败 → 等待 4s → 等待 8s …
```

全部重试失败后抛出 `MailSendError`，消息形如：

```text
邮件发送失败（已重试 3 次）: <最后一次异常>
```

> **超时是硬边界**：`mail_timeout` 同时作用于建连与 `send_message`，避免因 SMTP 服务器无响应
> 而长期占用请求线程。在高并发场景下，建议把发送动作交给 Celery，避免阻塞工作线程。

## API 参考

### `litefs.mail.Message`

| 参数 | 类型 | 说明 |
|------|------|------|
| `subject` | `str` | 邮件主题 |
| `body` | `str` | 纯文本正文 |
| `to` / `cc` / `bcc` | `str \| List[str]` | 收件人、抄送、密送，自动去空白 |
| `from_addr` | `str` | 发件人地址 |
| `reply_to` | `str` | 回复地址 |
| `html_body` | `str` | HTML 正文 |
| `attachments` | `List[Attachment]` | 附件列表 |
| `headers` | `Dict[str, str]` | 附加邮件头 |

主要方法：

| 方法 | 说明 |
|------|------|
| `add_attachment(attachment)` | 追加附件，返回自身以支持链式调用 |
| `recipients()` | 返回 To + Cc + Bcc 的信封收件人列表 |
| `to_dict()` / `from_dict(data)` | JSON 可序列化的字典互转（Celery 投递使用） |

### `litefs.mail.SMTPClient`

| 方法 | 说明 |
|------|------|
| `connect()` | 建立 SMTP 连接，返回 `smtplib.SMTP` 对象 |
| `send(message)` | 发送邮件，失败自动重试；全部失败抛 `MailSendError` |
| `close()` | 关闭连接，异常静默处理 |
| `__enter__` / `__exit__` | 上下文管理器支持 |

### 其他

| 名称 | 说明 |
|------|------|
| `get_mail_config(source)` | 从应用实例 / Config 对象构建 `MailConfig` 快照 |
| `build_email_message(message)` | `Message` → 标准库 `EmailMessage` 转换 |
| `MailSendError` | 邮件发送失败异常 |
| `MailSendResult` | 发送结果（`success` / `dispatched` / `task_id` / `error`） |

## 最佳实践

1. **发送动作不要阻塞请求线程**。注册验证、订单通知等场景使用 `asynchronous=True` 投递到 Celery，
   把 SMTP 的网络延迟从请求关键路径上摘除。
2. **密码不要硬编码**。通过环境变量或密钥管理服务注入 `mail_password`。
3. **生产环境务必启用加密**。公网 SMTP 至少使用 STARTTLS（587），回源内网建议隐式 SSL（465）。
4. **附件走共享存储**。Celery worker 与 Web 进程不在同一台机器时，`path` 附件需放在共享挂载上。
5. **用 `Content-Language` 做 CDN 缓存区分**需要与国际化模块配合，参见 :doc:`i18n`。

## 相关文档

- :doc:`i18n` —— 国际化与请求级 locale 协商
- :doc:`celery-integration` —— Celery 任务队列集成
- :doc:`configuration` —— 配置项完整列表
