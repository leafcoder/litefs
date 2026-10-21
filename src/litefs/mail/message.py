#!/usr/bin/env python
# coding: utf-8

"""
邮件消息模型

定义框架侧的邮件抽象（:class:`Message` / :class:`Attachment`），
并负责转换为标准库 :class:`email.message.EmailMessage`。

MIME 结构规则：
- 仅正文            -> ``text/plain``
- 正文 + HTML 正文  -> ``multipart/alternative``（纯文本在前，HTML 在后）
- 存在附件          -> 外层 ``multipart/mixed``（内含上述结构）

所有非 ASCII 头（主题、发件人等）由标准库按 RFC 2047 自动编码，
正文按 RFC 2046 自动选择 base64 / quoted-printable 编码。
"""

import base64
import mimetypes
import os
from typing import Any, Dict, List, Optional, Union

from email.message import EmailMessage

# 附件类型无法识别时的默认 MIME 类型
DEFAULT_MIMETYPE = "application/octet-stream"

# 文本附件的默认 MIME 类型
DEFAULT_TEXT_MIMETYPE = "text/plain"

# 附件内容的合法来源类型
AttachmentContent = Union[bytes, bytearray, str]


class Attachment:
    """
    邮件附件

    内容来源二选一：
    - ``path``：磁盘文件路径，发送时读取
    - ``content``：内存中的字节或文本

    使用示例::

        Attachment(filename='report.pdf', path='/tmp/report.pdf')
        Attachment(filename='data.csv', content='a,b\\n1,2\\n', mimetype='text/csv')
    """

    def __init__(
        self,
        filename: str,
        content: Optional[AttachmentContent] = None,
        path: Optional[str] = None,
        mimetype: Optional[str] = None,
        charset: str = "utf-8",
    ) -> None:
        """
        初始化附件

        Args:
            filename: 附件文件名（出现在 Content-Disposition 中）
            content: 内存内容，字节或文本
            path: 磁盘文件路径
            mimetype: MIME 类型，None 时按文件名推断
            charset: 文本附件的字符集

        Raises:
            ValueError: content 与 path 均未提供，或同时提供
        """
        if content is None and path is None:
            raise ValueError("附件必须提供 content 或 path 之一")
        if content is not None and path is not None:
            raise ValueError("附件的 content 与 path 不能同时提供")

        self.filename = filename
        self.path = path
        self.charset = charset
        self._content = content
        self.mimetype = mimetype or self._guess_mimetype(filename)

    def _guess_mimetype(self, filename: str) -> str:
        """
        按文件名推断 MIME 类型

        Args:
            filename: 附件文件名

        Returns:
            MIME 类型，推断失败时返回 application/octet-stream
        """
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or DEFAULT_MIMETYPE

    def read(self) -> bytes:
        """
        读取附件的二进制内容

        Returns:
            附件字节内容

        Raises:
            FileNotFoundError: path 指定的文件不存在
        """
        if self.path is not None:
            with open(self.path, "rb") as fp:
                return fp.read()

        content = self._content
        if content is None:
            return b""
        if isinstance(content, str):
            return content.encode(self.charset)
        return bytes(content)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为可 JSON 序列化的字典

        内存内容使用 base64 编码，保证 Celery 的 JSON 序列化器可直接使用。

        Returns:
            附件字典
        """
        data: Dict[str, Any] = {
            "filename": self.filename,
            "mimetype": self.mimetype,
        }
        if self.path is not None:
            data["path"] = self.path
        else:
            data["content_b64"] = base64.b64encode(self.read()).decode("ascii")
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attachment":
        """
        从字典还原附件

        Args:
            data: :meth:`to_dict` 生成的字典

        Returns:
            附件对象
        """
        content: Optional[bytes] = None
        if "content_b64" in data:
            content = base64.b64decode(data["content_b64"])
        return cls(
            filename=data["filename"],
            content=content,
            path=data.get("path"),
            mimetype=data.get("mimetype"),
        )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Attachment filename={self.filename!r} mimetype={self.mimetype!r}>"


class Message:
    """
    邮件消息

    描述一封邮件的全部元信息与正文，可转换为标准库邮件对象后投递 SMTP。

    使用示例::

        message = Message(
            subject='注册验证',
            body='您的验证码是 123456',
            to=['user@example.com'],
            from_addr='noreply@example.com',
        )
    """

    def __init__(
        self,
        subject: str = "",
        body: str = "",
        to: Optional[Union[str, List[str]]] = None,
        cc: Optional[Union[str, List[str]]] = None,
        bcc: Optional[Union[str, List[str]]] = None,
        from_addr: Optional[str] = None,
        reply_to: Optional[str] = None,
        html_body: Optional[str] = None,
        attachments: Optional[List[Attachment]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        初始化邮件消息

        Args:
            subject: 邮件主题
            body: 纯文本正文
            to: 收件人，字符串或列表
            cc: 抄送，字符串或列表
            bcc: 密送，字符串或列表
            from_addr: 发件人地址
            reply_to: 回复地址
            html_body: HTML 正文，None 表示纯文本邮件
            attachments: 附件列表
            headers: 附加邮件头
        """
        self.subject = subject
        self.body = body
        self.to = self._normalize_recipients(to)
        self.cc = self._normalize_recipients(cc)
        self.bcc = self._normalize_recipients(bcc)
        self.from_addr = from_addr
        self.reply_to = reply_to
        self.html_body = html_body
        self.attachments: List[Attachment] = list(attachments or [])
        self.headers: Dict[str, str] = dict(headers or {})

    @staticmethod
    def _normalize_recipients(
        recipients: Optional[Union[str, List[str]]],
    ) -> List[str]:
        """
        归一化收件人列表

        Args:
            recipients: 字符串或字符串列表

        Returns:
            去空白后的收件人列表
        """
        if recipients is None:
            return []
        if isinstance(recipients, str):
            recipients = [recipients]
        return [addr.strip() for addr in recipients if addr and addr.strip()]

    def add_attachment(self, attachment: Attachment) -> "Message":
        """
        追加附件

        Args:
            attachment: 附件对象

        Returns:
            self: 支持链式调用
        """
        self.attachments.append(attachment)
        return self

    def recipients(self) -> List[str]:
        """
        获取全部信封收件人

        包含 To / Cc / Bcc，Bcc 不会出现在邮件头中。

        Returns:
            收件人列表
        """
        return self.to + self.cc + self.bcc

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为可 JSON 序列化的字典

        用于 Celery 任务投递。

        Returns:
            邮件字典
        """
        return {
            "subject": self.subject,
            "body": self.body,
            "html_body": self.html_body,
            "to": list(self.to),
            "cc": list(self.cc),
            "bcc": list(self.bcc),
            "from_addr": self.from_addr,
            "reply_to": self.reply_to,
            "headers": dict(self.headers),
            "attachments": [att.to_dict() for att in self.attachments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """
        从字典还原邮件消息

        Args:
            data: :meth:`to_dict` 生成的字典

        Returns:
            邮件消息对象
        """
        attachments = [Attachment.from_dict(item) for item in data.get("attachments", [])]
        return cls(
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            to=data.get("to"),
            cc=data.get("cc"),
            bcc=data.get("bcc"),
            from_addr=data.get("from_addr"),
            reply_to=data.get("reply_to"),
            html_body=data.get("html_body"),
            attachments=attachments,
            headers=data.get("headers"),
        )

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<Message subject={self.subject!r} to={self.to!r}>"


def build_email_message(message: Message) -> EmailMessage:
    """
    将框架侧的 Message 转换为标准库邮件对象

    Args:
        message: 邮件消息

    Returns:
        标准库 EmailMessage 对象
    """
    email_message = EmailMessage()

    if message.subject:
        email_message["Subject"] = message.subject
    if message.from_addr:
        email_message["From"] = message.from_addr
    if message.to:
        email_message["To"] = ", ".join(message.to)
    if message.cc:
        email_message["Cc"] = ", ".join(message.cc)
    if message.reply_to:
        email_message["Reply-To"] = message.reply_to

    for key, value in message.headers.items():
        email_message[key] = value

    _set_body(email_message, message)
    _add_attachments(email_message, message.attachments)

    return email_message


def _set_body(email_message: EmailMessage, message: Message) -> None:
    """
    填充邮件正文

    Args:
        email_message: 标准库邮件对象
        message: 邮件消息
    """
    if message.html_body:
        if message.body:
            # 纯文本在前、HTML 在后，保证不支持 HTML 的客户端可降级阅读
            email_message.set_content(message.body)
            email_message.add_alternative(message.html_body, subtype="html")
        else:
            email_message.set_content(message.html_body, subtype="html")
    else:
        email_message.set_content(message.body)


def _add_attachments(
    email_message: EmailMessage,
    attachments: List[Attachment],
) -> None:
    """
    追加附件

    Args:
        email_message: 标准库邮件对象
        attachments: 附件列表
    """
    for attachment in attachments:
        maintype, _, subtype = attachment.mimetype.partition("/")
        if not subtype:
            maintype, _, subtype = DEFAULT_MIMETYPE.partition("/")
        email_message.add_attachment(
            attachment.read(),
            maintype=maintype,
            subtype=subtype,
            filename=os.path.basename(attachment.filename),
        )


__all__ = [
    "Attachment",
    "Message",
    "build_email_message",
]
