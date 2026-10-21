#!/usr/bin/env python
# coding: utf-8

"""
邮件发送入口

提供同步发送与 Celery 异步发送两种入口：

- :func:`send_mail`：同步发送，直接走 SMTP
- :func:`send_mail_async`：投递到 Celery 队列；未启用 Celery 时自动降级为同步发送

Celery 未安装或未初始化时不会抛出异常，而是返回降级结果标识，
保证业务代码无需感知底层差异。
"""

import logging
from typing import Any, Dict, Optional

from .message import Message
from .smtp import MailConfig, MailSendError, SMTPClient, get_mail_config

logger = logging.getLogger(__name__)

# Celery 任务名
SEND_MAIL_TASK_NAME = "litefs.mail.send"

# 已注册的 Celery 任务缓存：{id(celery 实例): 任务对象}
_TASK_CACHE: Dict[int, Any] = {}


class MailSendResult:
    """
    邮件发送结果

    区分「已投递到队列」与「已同步发送完成」两种语义。
    """

    def __init__(
        self,
        success: bool,
        dispatched: bool = False,
        task_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        初始化发送结果

        Args:
            success: 是否成功（投递成功或同步发送成功）
            dispatched: 是否投递到 Celery 队列
            task_id: Celery 任务 ID
            error: 失败原因
        """
        self.success = success
        self.dispatched = dispatched
        self.task_id = task_id
        self.error = error

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"<MailSendResult success={self.success} "
            f"dispatched={self.dispatched} task_id={self.task_id!r}>"
        )


def send_mail(
    message: Message,
    config: Optional[MailConfig] = None,
) -> MailSendResult:
    """
    同步发送邮件

    Args:
        message: 邮件消息
        config: 邮件配置，None 时从应用配置读取

    Returns:
        发送结果
    """
    mail_config = config or get_mail_config()
    try:
        with SMTPClient(mail_config) as client:
            client.send(message)
    except MailSendError as exc:
        logger.error("邮件同步发送失败: %s", exc)
        return MailSendResult(success=False, dispatched=False, error=str(exc))

    return MailSendResult(success=True, dispatched=False)


def send_mail_async(
    message: Message,
    config: Optional[MailConfig] = None,
) -> MailSendResult:
    """
    异步发送邮件

    优先投递到 Celery 队列；若 Celery 未安装或未初始化，
    自动降级为同步发送并返回 ``dispatched=False`` 的结果。

    Args:
        message: 邮件消息
        config: 邮件配置，None 时从应用配置读取

    Returns:
        发送结果
    """
    celery = _get_celery_instance()
    if celery is None:
        logger.debug("Celery 未初始化，邮件发送降级为同步模式")
        return send_mail(message, config)

    mail_config = config or get_mail_config()
    task = _get_send_task(celery)
    try:
        async_result = task.delay(
            message.to_dict(),
            mail_config.to_dict(),
        )
    except Exception as exc:  # 队列不可用等异常
        logger.warning("邮件任务投递失败，降级为同步发送: %s", exc)
        return send_mail(message, config)

    task_id = getattr(async_result, "id", None)
    return MailSendResult(success=True, dispatched=True, task_id=task_id)


def _get_celery_instance() -> Optional[Any]:
    """
    获取全局 Celery 实例

    Returns:
        Celery 实例，未初始化时返回 None
    """
    try:
        from ..tasks import get_celery
    except ImportError:
        return None
    return get_celery()


def _get_send_task(celery: Any) -> Any:
    """
    获取（或注册）邮件发送任务

    任务注册需要 Celery 实例存在，因此采用延迟注册策略，
    避免模块导入时 Celery 尚未初始化的时序问题。

    Args:
        celery: Celery 实例

    Returns:
        Celery 任务对象
    """
    cache_key = id(celery)
    cached = _TASK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    def deliver(message_data: Dict[str, Any], config_data: Dict[str, Any]) -> bool:
        """
        任务体：还原消息与配置并发送邮件

        Args:
            message_data: 邮件消息字典
            config_data: 邮件配置字典

        Returns:
            是否发送成功
        """
        message = Message.from_dict(message_data)
        mail_config = MailConfig.from_dict(config_data)
        result = send_mail(message, mail_config)
        if not result.success:
            raise MailSendError(result.error or "邮件发送失败")
        return True

    task = celery.task(deliver, name=SEND_MAIL_TASK_NAME, queue="mail")
    _TASK_CACHE[cache_key] = task
    return task


__all__ = [
    "MailSendResult",
    "SEND_MAIL_TASK_NAME",
    "send_mail",
    "send_mail_async",
]
