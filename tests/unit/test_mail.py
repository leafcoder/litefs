#!/usr/bin/env python
# coding: utf-8

"""
邮件发送模块测试

覆盖 Message / Attachment 模型、MIME 结构组装（纯文本 / HTML / 附件）、
SMTPClient 的连接与重试退避、Mako 邮件模板渲染，
以及同步发送与 Celery 异步发送入口。
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from litefs.mail import (
    Attachment,
    MailConfig,
    MailSendError,
    Message,
    SMTPClient,
    build_email_message,
    build_mail_body,
    get_mail_config,
    render_mail_template,
    send_mail,
    send_mail_async,
)
from litefs.mail.tasks import SEND_MAIL_TASK_NAME


class TestAttachment(unittest.TestCase):
    """附件"""

    def test_content_bytes(self):
        """字节内容直接读取"""
        attachment = Attachment(filename="a.bin", content=b"hello")

        self.assertEqual(attachment.read(), b"hello")

    def test_content_text_encoded(self):
        """文本内容按字符集编码"""
        attachment = Attachment(filename="a.txt", content="你好")

        self.assertEqual(attachment.read(), "你好".encode("utf-8"))

    def test_path_content(self):
        """从文件路径读取内容"""
        attachment = Attachment(filename="a.txt", path=__file__)

        with open(__file__, "rb") as fp:
            self.assertEqual(attachment.read(), fp.read())

    def test_require_content_or_path(self):
        """既无 content 也无 path 时报错"""
        with self.assertRaises(ValueError):
            Attachment(filename="a.txt")

    def test_content_and_path_mutually_exclusive(self):
        """同时提供 content 与 path 时报错"""
        with self.assertRaises(ValueError):
            Attachment(filename="a.txt", content=b"x", path=__file__)

    def test_mimetype_guessed_from_filename(self):
        """按文件名推断 MIME 类型"""
        attachment = Attachment(filename="a.png", content=b"x")

        self.assertEqual(attachment.mimetype, "image/png")

    def test_mimetype_explicit(self):
        """显式指定 MIME 类型优先"""
        attachment = Attachment(filename="a.png", content=b"x", mimetype="image/jpeg")

        self.assertEqual(attachment.mimetype, "image/jpeg")

    def test_unknown_mimetype_fallback(self):
        """无法推断时回退为二进制流"""
        attachment = Attachment(filename="a.unknownext", content=b"x")

        self.assertEqual(attachment.mimetype, "application/octet-stream")

    def test_to_dict_and_from_dict(self):
        """字典序列化与还原保持一致"""
        attachment = Attachment(filename="a.txt", content="你好")
        data = attachment.to_dict()

        self.assertIn("content_b64", data)
        restored = Attachment.from_dict(data)
        self.assertEqual(restored.filename, "a.txt")
        self.assertEqual(restored.read(), "你好".encode("utf-8"))

    def test_to_dict_with_path(self):
        """路径附件序列化保留路径"""
        data = Attachment(filename="a.txt", path=__file__).to_dict()

        self.assertEqual(data["path"], __file__)
        self.assertNotIn("content_b64", data)


class TestMessage(unittest.TestCase):
    """邮件消息模型"""

    def test_normalize_single_recipient(self):
        """字符串收件人归一化为列表"""
        message = Message(subject="s", to="a@example.com")

        self.assertEqual(message.to, ["a@example.com"])

    def test_normalize_multiple_recipients(self):
        """列表收件人去除空白"""
        message = Message(subject="s", to=[" a@example.com ", "", "b@example.com"])

        self.assertEqual(message.to, ["a@example.com", "b@example.com"])

    def test_recipients_include_all(self):
        """信封收件人包含 To / Cc / Bcc"""
        message = Message(
            subject="s",
            to=["a@example.com"],
            cc=["c@example.com"],
            bcc=["b@example.com"],
        )

        self.assertEqual(
            message.recipients(),
            ["a@example.com", "c@example.com", "b@example.com"],
        )

    def test_add_attachment_chain(self):
        """追加附件支持链式调用"""
        message = Message(subject="s")
        result = message.add_attachment(Attachment(filename="a.txt", content="x"))

        self.assertIs(result, message)
        self.assertEqual(len(message.attachments), 1)

    def test_to_dict_and_from_dict(self):
        """字典序列化与还原保持一致"""
        message = Message(
            subject="主题",
            body="正文",
            to=["a@example.com"],
            cc=["c@example.com"],
            bcc=["b@example.com"],
            from_addr="from@example.com",
            reply_to="reply@example.com",
            html_body="<p>正文</p>",
            headers={"X-Custom": "1"},
        )
        message.add_attachment(Attachment(filename="a.txt", content="x"))

        restored = Message.from_dict(message.to_dict())

        self.assertEqual(restored.subject, "主题")
        self.assertEqual(restored.body, "正文")
        self.assertEqual(restored.to, ["a@example.com"])
        self.assertEqual(restored.cc, ["c@example.com"])
        self.assertEqual(restored.bcc, ["b@example.com"])
        self.assertEqual(restored.from_addr, "from@example.com")
        self.assertEqual(restored.reply_to, "reply@example.com")
        self.assertEqual(restored.html_body, "<p>正文</p>")
        self.assertEqual(restored.headers, {"X-Custom": "1"})
        self.assertEqual(len(restored.attachments), 1)

    def test_to_dict_is_json_serializable(self):
        """字典结果可被 JSON 序列化"""
        import json

        message = Message(subject="s", to=["a@example.com"])
        message.add_attachment(Attachment(filename="a.txt", content="x"))

        payload = json.dumps(message.to_dict())

        self.assertIn("subject", payload)


class TestBuildEmailMessage(unittest.TestCase):
    """MIME 结构组装"""

    def test_plain_text_only(self):
        """仅正文时为 text/plain"""
        message = Message(subject="主题", body="正文", to=["a@example.com"])
        email_message = build_email_message(message)

        self.assertEqual(email_message.get_content_type(), "text/plain")
        self.assertIn("正文", email_message.get_content())

    def test_html_only(self):
        """仅 HTML 正文时为 text/html"""
        message = Message(subject="主题", html_body="<p>正文</p>", to=["a@example.com"])
        email_message = build_email_message(message)

        self.assertEqual(email_message.get_content_type(), "text/html")

    def test_alternative_structure(self):
        """正文 + HTML 时为 multipart/alternative"""
        message = Message(
            subject="主题",
            body="纯文本",
            html_body="<p>HTML</p>",
            to=["a@example.com"],
        )
        email_message = build_email_message(message)

        self.assertEqual(email_message.get_content_type(), "multipart/alternative")
        subtypes = [part.get_content_type() for part in email_message.iter_parts()]
        self.assertEqual(subtypes, ["text/plain", "text/html"])

    def test_attachment_makes_mixed(self):
        """存在附件时外层为 multipart/mixed"""
        message = Message(subject="主题", body="正文", to=["a@example.com"])
        message.add_attachment(Attachment(filename="a.txt", content="x"))
        email_message = build_email_message(message)

        self.assertEqual(email_message.get_content_type(), "multipart/mixed")

    def test_headers(self):
        """邮件头正确写入"""
        message = Message(
            subject="主题",
            body="正文",
            to=["a@example.com", "b@example.com"],
            cc=["c@example.com"],
            from_addr="from@example.com",
            reply_to="reply@example.com",
            headers={"X-Custom": "value"},
        )
        email_message = build_email_message(message)

        self.assertEqual(email_message["From"], "from@example.com")
        self.assertEqual(email_message["To"], "a@example.com, b@example.com")
        self.assertEqual(email_message["Cc"], "c@example.com")
        self.assertEqual(email_message["Reply-To"], "reply@example.com")
        self.assertEqual(email_message["X-Custom"], "value")

    def test_bcc_not_in_headers(self):
        """密送地址不出现在邮件头中"""
        message = Message(
            subject="主题",
            body="正文",
            to=["a@example.com"],
            bcc=["secret@example.com"],
        )
        email_message = build_email_message(message)

        self.assertIsNone(email_message["Bcc"])

    def test_chinese_subject_encoded(self):
        """中文主题按 RFC 2047 编码后可正确解码"""
        message = Message(subject="注册验证", body="正文", to=["a@example.com"])
        email_message = build_email_message(message)

        from email.header import decode_header, make_header

        decoded = str(make_header(decode_header(email_message["Subject"])))
        self.assertEqual(decoded, "注册验证")


class TestMailConfig(unittest.TestCase):
    """邮件配置"""

    def test_defaults(self):
        """默认配置值"""
        config = MailConfig()

        self.assertEqual(config.host, "localhost")
        self.assertEqual(config.port, 25)
        self.assertEqual(config.max_retries, 3)

    def test_to_dict_and_from_dict(self):
        """字典序列化与还原保持一致"""
        config = MailConfig(
            host="smtp.example.com",
            port=465,
            username="user",
            password="pass",
            use_ssl=True,
            default_from="from@example.com",
        )
        restored = MailConfig.from_dict(config.to_dict())

        self.assertEqual(restored.host, "smtp.example.com")
        self.assertEqual(restored.port, 465)
        self.assertEqual(restored.username, "user")
        self.assertEqual(restored.password, "pass")
        self.assertTrue(restored.use_ssl)
        self.assertEqual(restored.default_from, "from@example.com")

    def test_get_mail_config_from_config_object(self):
        """从配置对象读取邮件配置"""
        class FakeConfig:
            mail_host = "smtp.example.com"
            mail_port = 587
            mail_use_tls = True
            mail_default_from = "from@example.com"

        config = get_mail_config(FakeConfig())

        self.assertEqual(config.host, "smtp.example.com")
        self.assertEqual(config.port, 587)
        self.assertTrue(config.use_tls)
        self.assertEqual(config.default_from, "from@example.com")

    def test_get_mail_config_from_app(self):
        """从应用实例读取邮件配置"""
        class FakeApp:
            class config:
                mail_host = "smtp.app.com"
                mail_port = 25

        config = get_mail_config(FakeApp())

        self.assertEqual(config.host, "smtp.app.com")

    def test_get_mail_config_none(self):
        """无来源时返回默认配置"""
        config = get_mail_config(None)

        self.assertEqual(config.host, "localhost")


class TestSMTPClient(unittest.TestCase):
    """SMTP 客户端"""

    def _make_client(self, **kwargs):
        """构造使用默认配置的客户端"""
        params = {
            "host": "localhost",
            "port": 25,
            "username": None,
            "password": None,
            "use_tls": False,
            "use_ssl": False,
            "timeout": 5,
            "max_retries": 1,
        }
        params.update(kwargs)
        return SMTPClient(MailConfig(**params))

    def test_connect_plain(self):
        """普通连接调用 ehlo"""
        server = MagicMock()
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=server) as mocked:
            client = self._make_client()
            client.connect()

        mocked.assert_called_once_with("localhost", 25, timeout=5)
        server.ehlo.assert_called()
        server.starttls.assert_not_called()

    def test_connect_with_tls(self):
        """启用 TLS 时调用 starttls"""
        server = MagicMock()
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=server):
            self._make_client(use_tls=True).connect()

        server.starttls.assert_called_once()

    def test_connect_with_ssl(self):
        """启用 SSL 时使用 SMTP_SSL"""
        server = MagicMock()
        with patch("litefs.mail.smtp.smtplib.SMTP_SSL", return_value=server) as mocked:
            self._make_client(use_ssl=True).connect()

        mocked.assert_called_once_with("localhost", 25, timeout=5)
        server.starttls.assert_not_called()

    def test_connect_with_login(self):
        """配置了用户名时执行认证"""
        server = MagicMock()
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=server):
            self._make_client(username="user", password="pass").connect()

        server.login.assert_called_once_with("user", "pass")

    def test_connect_failure_raises(self):
        """连接失败抛出 MailSendError"""
        import smtplib

        with patch(
            "litefs.mail.smtp.smtplib.SMTP",
            side_effect=smtplib.SMTPConnectError(421, "refused"),
        ):
            with self.assertRaises(MailSendError):
                self._make_client().connect()

    def test_send_success(self):
        """发送成功返回 True"""
        server = MagicMock()
        message = Message(
            subject="主题",
            body="正文",
            to=["a@example.com"],
            from_addr="from@example.com",
        )
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=server):
            result = self._make_client().send(message)

        self.assertTrue(result)
        server.send_message.assert_called_once()

    def test_send_requires_recipient(self):
        """缺少收件人时报错"""
        with self.assertRaises(MailSendError):
            self._make_client().send(Message(subject="主题", body="正文"))

    def test_send_requires_sender(self):
        """缺少发件人时报错"""
        message = Message(subject="主题", body="正文", to=["a@example.com"])
        with self.assertRaises(MailSendError):
            self._make_client().send(message)

    def test_send_uses_default_from(self):
        """未指定发件人时使用配置中的默认发件人"""
        server = MagicMock()
        message = Message(subject="主题", body="正文", to=["a@example.com"])
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=server):
            self._make_client(default_from="noreply@example.com").send(message)

        self.assertEqual(message.from_addr, "noreply@example.com")

    def test_send_retry_then_success(self):
        """首次失败后重试成功"""
        import smtplib

        server = MagicMock()
        message = Message(
            subject="主题",
            body="正文",
            to=["a@example.com"],
            from_addr="from@example.com",
        )
        with patch(
            "litefs.mail.smtp.smtplib.SMTP",
            side_effect=[smtplib.SMTPConnectError(421, "refused"), server],
        ):
            with patch("litefs.mail.smtp.time.sleep"):
                result = self._make_client(max_retries=2).send(message)

        self.assertTrue(result)
        server.send_message.assert_called_once()

    def test_send_retry_exhausted(self):
        """重试耗尽后抛出 MailSendError"""
        import smtplib

        message = Message(
            subject="主题",
            body="正文",
            to=["a@example.com"],
            from_addr="from@example.com",
        )
        with patch(
            "litefs.mail.smtp.smtplib.SMTP",
            side_effect=smtplib.SMTPConnectError(421, "refused"),
        ):
            with patch("litefs.mail.smtp.time.sleep"):
                with self.assertRaises(MailSendError):
                    self._make_client(max_retries=1).send(message)

    def test_context_manager(self):
        """上下文管理器自动建连与关闭"""
        server = MagicMock()
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=server):
            with self._make_client() as client:
                self.assertIsNotNone(client._server)

        server.quit.assert_called_once()


class TestMailTemplate(unittest.TestCase):
    """邮件模板渲染"""

    def setUp(self):
        """准备模板目录"""
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.template_dir = self._tmpdir.name
        self.addCleanup(self._tmpdir.cleanup)

    def _write(self, name, content):
        """写入模板文件"""
        path = os.path.join(self.template_dir, name)
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(content)
        return path

    def test_render_text_template(self):
        """渲染纯文本模板"""
        self._write("welcome.txt", "你好 ${name}")

        text, html = render_mail_template(
            "welcome", self.template_dir, name="世界"
        )

        self.assertEqual(text, "你好 世界")
        self.assertIsNone(html)

    def test_render_html_template(self):
        """渲染 HTML 模板"""
        self._write("welcome.html", "<p>你好 ${name}</p>")

        text, html = render_mail_template(
            "welcome", self.template_dir, name="世界"
        )

        self.assertIsNone(text)
        self.assertEqual(html, "<p>你好 世界</p>")

    def test_render_paired_templates(self):
        """同时渲染纯文本与 HTML 模板"""
        self._write("welcome.txt", "你好 ${name}")
        self._write("welcome.html", "<p>你好 ${name}</p>")

        text, html = render_mail_template(
            "welcome", self.template_dir, name="世界"
        )

        self.assertEqual(text, "你好 世界")
        self.assertEqual(html, "<p>你好 世界</p>")

    def test_render_with_explicit_extension(self):
        """显式指定扩展名时只渲染对应模板"""
        self._write("welcome.txt", "你好")
        self._write("welcome.html", "<p>你好</p>")

        text, html = render_mail_template("welcome.txt", self.template_dir)

        self.assertEqual(text, "你好")
        self.assertEqual(html, "<p>你好</p>")

    def test_render_missing_template(self):
        """模板不存在时返回 None"""
        text, html = render_mail_template("missing", self.template_dir)

        self.assertIsNone(text)
        self.assertIsNone(html)

    def test_build_mail_body(self):
        """构造正文保证至少有一份可用内容"""
        self._write("welcome.txt", "你好")

        text, html = build_mail_body("welcome", self.template_dir)

        self.assertEqual(text, "你好")
        self.assertIsNone(html)

    def test_build_mail_body_missing_raises(self):
        """模板完全缺失时抛出 FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            build_mail_body("missing", self.template_dir)


class TestSendMail(unittest.TestCase):
    """发送入口"""

    def _message(self):
        """构造测试用邮件"""
        return Message(
            subject="主题",
            body="正文",
            to=["a@example.com"],
            from_addr="from@example.com",
        )

    def test_send_mail_success(self):
        """同步发送成功"""
        config = MailConfig(host="localhost", port=25, default_from="from@example.com")
        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=MagicMock()):
            result = send_mail(self._message(), config)

        self.assertTrue(result.success)
        self.assertFalse(result.dispatched)
        self.assertIsNone(result.error)

    def test_send_mail_failure_returns_error(self):
        """同步发送失败返回错误信息"""
        import smtplib

        config = MailConfig(
            host="localhost",
            port=25,
            default_from="from@example.com",
            max_retries=0,
        )
        with patch(
            "litefs.mail.smtp.smtplib.SMTP",
            side_effect=smtplib.SMTPConnectError(421, "refused"),
        ):
            result = send_mail(self._message(), config)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)

    def test_send_mail_async_fallback_to_sync(self):
        """Celery 未初始化时降级为同步发送"""
        config = MailConfig(host="localhost", port=25, default_from="from@example.com")
        with patch("litefs.mail.tasks._get_celery_instance", return_value=None):
            with patch("litefs.mail.smtp.smtplib.SMTP", return_value=MagicMock()):
                result = send_mail_async(self._message(), config)

        self.assertTrue(result.success)
        self.assertFalse(result.dispatched)

    def test_send_mail_async_dispatched(self):
        """Celery 可用时投递到队列"""
        celery = MagicMock()
        task = MagicMock()
        async_result = MagicMock()
        async_result.id = "task-123"
        task.delay.return_value = async_result
        celery.task.return_value = task

        config = MailConfig(host="localhost", port=25, default_from="from@example.com")
        with patch("litefs.mail.tasks._get_celery_instance", return_value=celery):
            result = send_mail_async(self._message(), config)

        self.assertTrue(result.success)
        self.assertTrue(result.dispatched)
        self.assertEqual(result.task_id, "task-123")
        celery.task.assert_called_once()
        self.assertEqual(celery.task.call_args[1]["name"], SEND_MAIL_TASK_NAME)

    def test_send_mail_async_dispatch_error_fallback(self):
        """投递失败时降级为同步发送"""
        celery = MagicMock()
        task = MagicMock()
        task.delay.side_effect = RuntimeError("broker down")
        celery.task.return_value = task

        config = MailConfig(host="localhost", port=25, default_from="from@example.com")
        with patch("litefs.mail.tasks._get_celery_instance", return_value=celery):
            with patch("litefs.mail.smtp.smtplib.SMTP", return_value=MagicMock()):
                result = send_mail_async(self._message(), config)

        self.assertTrue(result.success)
        self.assertFalse(result.dispatched)


class TestAppMailHelper(unittest.TestCase):
    """应用级发送入口"""

    def test_app_send_mail(self):
        """应用实例的 send_mail 走同步通道"""
        from litefs.core import Litefs

        app = Litefs(mail_default_from="from@example.com")
        message = Message(subject="主题", body="正文", to=["a@example.com"])

        with patch("litefs.mail.smtp.smtplib.SMTP", return_value=MagicMock()):
            result = app.send_mail(message)

        self.assertTrue(result.success)

    def test_app_send_mail_async(self):
        """应用实例的 send_mail 支持异步通道"""
        from litefs.core import Litefs

        app = Litefs(mail_default_from="from@example.com")
        message = Message(subject="主题", body="正文", to=["a@example.com"])

        celery = MagicMock()
        task = MagicMock()
        task.delay.return_value = MagicMock(id="task-1")
        celery.task.return_value = task

        with patch("litefs.mail.tasks._get_celery_instance", return_value=celery):
            result = app.send_mail(message, asynchronous=True)

        self.assertTrue(result.dispatched)


if __name__ == "__main__":
    unittest.main()
