#!/usr/bin/env python
# coding: utf-8

"""
SMTP 客户端

基于标准库 :mod:`smtplib` 封装邮件投递能力，提供：

- TLS / SSL 两种加密模式
- 连接与发送超时控制
- 失败重试与指数退避
- 上下文管理器支持（自动建连与关闭）
"""

import smtplib
import time
from typing import Any, Optional

from .message import Message, build_email_message


class MailSendError(Exception):
    """邮件发送失败时抛出的异常"""


class MailConfig:
    """
    邮件配置快照

    从应用的 :class:`~litefs.config.Config` 读取邮件相关配置项，
    转换为独立对象，避免运行时依赖应用实例。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 25,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        use_ssl: bool = False,
        timeout: float = 30.0,
        default_from: Optional[str] = None,
        template_dir: str = "templates/email",
        max_retries: int = 3,
    ) -> None:
        """
        初始化邮件配置

        Args:
            host: SMTP 服务器地址
            port: SMTP 服务器端口
            username: 认证用户名
            password: 认证密码
            use_tls: 是否在连接后升级为 STARTTLS
            use_ssl: 是否使用隐式 SSL
            timeout: 连接与发送超时（秒）
            default_from: 默认发件人地址
            template_dir: 邮件模板目录
            max_retries: 发送失败的最大重试次数
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
        self.default_from = default_from
        self.template_dir = template_dir
        self.max_retries = max_retries

    def to_dict(self) -> dict:
        """
        转换为字典

        用于 Celery 任务投递时的 JSON 序列化。

        Returns:
            配置字典
        """
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "use_tls": self.use_tls,
            "use_ssl": self.use_ssl,
            "timeout": self.timeout,
            "default_from": self.default_from,
            "template_dir": self.template_dir,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MailConfig":
        """
        从字典还原配置

        Args:
            data: :meth:`to_dict` 生成的字典

        Returns:
            邮件配置
        """
        return cls(
            host=data.get("host", "localhost"),
            port=int(data.get("port", 25)),
            username=data.get("username"),
            password=data.get("password"),
            use_tls=bool(data.get("use_tls", False)),
            use_ssl=bool(data.get("use_ssl", False)),
            timeout=float(data.get("timeout", 30.0)),
            default_from=data.get("default_from"),
            template_dir=data.get("template_dir", "templates/email"),
            max_retries=int(data.get("max_retries", 3)),
        )

    def __repr__(self) -> str:
        """字符串表示（隐藏密码）"""
        return f"<MailConfig {self.host}:{self.port} tls={self.use_tls} ssl={self.use_ssl}>"


def get_mail_config(source: Any = None) -> MailConfig:
    """
    从应用实例或配置对象构建邮件配置

    Args:
        source: Litefs 应用实例、Config 对象或 None

    Returns:
        邮件配置快照
    """
    if source is None:
        config = None
    elif hasattr(source, "config"):
        config = source.config
    else:
        config = source

    def _get(key: str, default: Any) -> Any:
        if config is None:
            return default
        value = getattr(config, key, default)
        return default if value is None and default is not None else value

    return MailConfig(
        host=_get("mail_host", "localhost"),
        port=int(_get("mail_port", 25)),
        username=_get("mail_username", None),
        password=_get("mail_password", None),
        use_tls=bool(_get("mail_use_tls", False)),
        use_ssl=bool(_get("mail_use_ssl", False)),
        timeout=float(_get("mail_timeout", 30.0)),
        default_from=_get("mail_default_from", None),
        template_dir=_get("mail_template_dir", "templates/email"),
        max_retries=int(_get("mail_max_retries", 3)),
    )


class SMTPClient:
    """
    SMTP 邮件客户端

    使用示例::

        with SMTPClient(get_mail_config(app)) as client:
            client.send(message)
    """

    def __init__(self, config: Optional[MailConfig] = None) -> None:
        """
        初始化 SMTP 客户端

        Args:
            config: 邮件配置，None 时使用默认配置
        """
        self.config = config or MailConfig()
        self._server: Optional[smtplib.SMTP] = None

    # ==================== 连接管理 ====================

    def connect(self) -> smtplib.SMTP:
        """
        建立 SMTP 连接

        Returns:
            已连接的 SMTP 对象
        """
        config = self.config
        try:
            if config.use_ssl:
                server: smtplib.SMTP = smtplib.SMTP_SSL(
                    config.host, config.port, timeout=config.timeout
                )
            else:
                server = smtplib.SMTP(config.host, config.port, timeout=config.timeout)

            server.ehlo()
            if config.use_tls and not config.use_ssl:
                server.starttls()
                server.ehlo()

            if config.username:
                server.login(config.username, config.password or "")
        except (smtplib.SMTPException, OSError) as exc:
            raise MailSendError(f"连接 SMTP 服务器失败: {exc}") from exc

        self._server = server
        return server

    def close(self) -> None:
        """
        关闭 SMTP 连接

        连接失败或已关闭时静默返回。
        """
        if self._server is None:
            return
        try:
            self._server.quit()
        except (smtplib.SMTPException, OSError):
            # 关闭阶段的异常不应覆盖发送结果
            try:
                self._server.close()
            except (smtplib.SMTPException, OSError):
                pass
        finally:
            self._server = None

    def __enter__(self) -> "SMTPClient":
        """进入上下文，建立连接"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        """退出上下文，关闭连接"""
        self.close()

    # ==================== 发送 ====================

    def send(self, message: Message) -> bool:
        """
        发送邮件（失败自动重试）

        Args:
            message: 邮件消息

        Returns:
            是否发送成功

        Raises:
            MailSendError: 全部重试均失败
        """
        if not message.recipients():
            raise MailSendError("邮件缺少收件人")

        if not message.from_addr:
            message.from_addr = self.config.default_from
        if not message.from_addr:
            raise MailSendError("邮件缺少发件人地址，请配置 mail_default_from")

        email_message = build_email_message(message)
        envelope = message.recipients()

        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                self._deliver(email_message, envelope)
                return True
            except (smtplib.SMTPException, OSError, MailSendError) as exc:
                last_error = exc
                self.close()
                if attempt >= self.config.max_retries:
                    break
                # 指数退避，避免对故障服务器形成密集重试
                time.sleep(min(2 ** attempt, 30))

        raise MailSendError(
            f"邮件发送失败（已重试 {self.config.max_retries} 次）: {last_error}"
        ) from last_error

    def _deliver(self, email_message, envelope) -> None:
        """
        通过已建立的连接投递邮件

        Args:
            email_message: 标准库邮件对象
            envelope: 信封收件人列表

        Raises:
            MailSendError: 连接不可用
        """
        server = self._server or self.connect()
        server.send_message(
            email_message,
            from_addr=email_message.get("From"),
            to_addrs=envelope,
        )


__all__ = [
    "MailConfig",
    "MailSendError",
    "SMTPClient",
    "get_mail_config",
]
