#!/usr/bin/env python
# coding: utf-8

"""
邮件发送模块

提供基于标准库 :mod:`smtplib` 的邮件发送能力：

- :class:`Message` / :class:`Attachment`：邮件消息模型
- :class:`SMTPClient`：SMTP 客户端（TLS/SSL、重试退避）
- :func:`render_mail_template`：Mako 邮件模板渲染
- :func:`send_mail` / :func:`send_mail_async`：同步与异步发送入口

使用示例::

    from litefs.mail import Message, send_mail

    message = Message(
        subject='注册验证',
        body='您的验证码是 123456',
        to=['user@example.com'],
        from_addr='noreply@example.com',
    )
    send_mail(message)
"""

from .message import Attachment, Message, build_email_message
from .smtp import MailConfig, MailSendError, SMTPClient, get_mail_config
from .tasks import (
    SEND_MAIL_TASK_NAME,
    MailSendResult,
    send_mail,
    send_mail_async,
)
from .template import build_mail_body, render_mail_template

__all__ = [
    "Attachment",
    "Message",
    "build_email_message",
    "MailConfig",
    "MailSendError",
    "SMTPClient",
    "get_mail_config",
    "SEND_MAIL_TASK_NAME",
    "MailSendResult",
    "send_mail",
    "send_mail_async",
    "build_mail_body",
    "render_mail_template",
]
