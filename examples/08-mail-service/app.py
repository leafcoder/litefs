#!/usr/bin/env python
# coding: utf-8

"""
邮件服务示例

展示 Litefs 的邮件发送能力：

- Mako 邮件模板渲染（纯文本 + HTML 双模板）
- SMTP 客户端（STARTTLS / SSL、指数退避重试）
- 同步发送与 Celery 异步发送（未启用 Celery 时自动降级为同步）
- 附件与自定义邮件头

运行::

    python app.py

无需 SMTP 服务器即可体验（默认开启「预览模式」）::

    curl -X POST http://localhost:8085/api/mail/preview \
        -H 'Content-Type: application/json' \
        -d '{"name": "张三", "email": "zhangsan@example.com"}'

接入真实 SMTP 服务器::

    export MAIL_ENABLED=1
    export SMTP_HOST=smtp.example.com
    export SMTP_PORT=587
    export SMTP_USERNAME=noreply@example.com
    export SMTP_PASSWORD=your-password
    python app.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.core import Litefs
from litefs.handlers import Response
from litefs.mail import Message, render_mail_template
from litefs.routing import get, post

APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(APP_DIR, 'templates', 'email')

# 是否真正连接 SMTP 服务器发送邮件；关闭时仅渲染模板做预览
MAIL_ENABLED = os.environ.get('MAIL_ENABLED', '0') == '1'

# ============================================================================
# 应用配置
# ============================================================================

app = Litefs(
    host='0.0.0.0',
    port=8085,
    debug=True,
    mail_host=os.environ.get('SMTP_HOST', 'localhost'),
    mail_port=int(os.environ.get('SMTP_PORT', '25')),
    mail_username=os.environ.get('SMTP_USERNAME') or None,
    mail_password=os.environ.get('SMTP_PASSWORD') or None,
    mail_use_tls=os.environ.get('SMTP_TLS', '1') == '1',
    mail_use_ssl=os.environ.get('SMTP_SSL', '0') == '1',
    mail_default_from=os.environ.get('MAIL_FROM', 'noreply@example.com'),
    mail_template_dir=TEMPLATE_DIR,
    mail_max_retries=3,
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))


# ============================================================================
# 业务路由
# ============================================================================

@get('/', name='index')
def index(request):
    """首页：说明邮件能力与调用方式"""
    return request.render_template('index.html', **{
        'title': 'Litefs 邮件服务示例',
        'mail_enabled': MAIL_ENABLED,
        'smtp_host': app.config.mail_host,
        'smtp_port': app.config.mail_port,
        'endpoints': [
            {'path': '/api/mail/preview', 'desc': 'POST 渲染欢迎邮件模板，返回预览内容（不发送）'},
            {'path': '/api/mail/welcome', 'desc': 'POST 渲染并发送欢迎邮件'},
        ],
    })


@post('/api/mail/preview', name='api_mail_preview')
def api_mail_preview(request):
    """渲染欢迎邮件模板并返回预览内容（不实际发送）"""
    payload = request.json or {}
    name = (payload.get('name') or '').strip() or '朋友'
    email = (payload.get('email') or '').strip() or 'user@example.com'

    text_body, html_body = render_mail_template(
        'welcome',
        TEMPLATE_DIR,
        debug=app.config.debug,
        name=name,
        email=email,
        app_name='Litefs',
    )

    return Response.json({
        'subject': f'欢迎加入 Litefs，{name}！',
        'from_addr': app.config.mail_default_from,
        'to': [email],
        'text': text_body,
        'html': html_body,
    })


@post('/api/mail/welcome', name='api_mail_welcome')
def api_mail_welcome(request):
    """渲染并发送欢迎邮件

    未开启 ``MAIL_ENABLED`` 时仅做预览，返回 ``sent=False``，
    便于在没有 SMTP 服务器的环境下演示。
    """
    payload = request.json or {}
    name = (payload.get('name') or '').strip() or '朋友'
    email = (payload.get('email') or '').strip() or 'user@example.com'

    text_body, html_body = render_mail_template(
        'welcome',
        TEMPLATE_DIR,
        debug=app.config.debug,
        name=name,
        email=email,
        app_name='Litefs',
    )

    message = Message(
        subject=f'欢迎加入 Litefs，{name}！',
        body=text_body,
        html_body=html_body,
        to=[email],
        from_addr=app.config.mail_default_from,
        reply_to=app.config.mail_default_from,
        headers={'X-Mailer': 'Litefs'},
    )

    if not MAIL_ENABLED:
        return Response.json({
            'sent': False,
            'reason': '预览模式：设置 MAIL_ENABLED=1 后才会真正发送',
            'subject': message.subject,
            'to': message.to,
            'text': text_body,
        })

    result = app.send_mail(message)
    return Response.json({
        'sent': result.success,
        'dispatched': result.dispatched,
        'task_id': result.task_id,
        'error': result.error,
        'subject': message.subject,
        'to': message.to,
    }, status_code=200 if result.success else 502)


app.register_routes(__name__)


if __name__ == '__main__':
    print('=' * 60)
    print('Litefs 邮件服务示例')
    print('=' * 60)
    print()
    print('应用地址:   http://localhost:8085')
    print('SMTP:       %s:%s' % (app.config.mail_host, app.config.mail_port))
    print('发送模式:   %s' % ('已启用（真实发送）' if MAIL_ENABLED else '预览模式（不发送）'))
    print('邮件模板:   %s' % TEMPLATE_DIR)
    print()
    print('预览邮件:')
    print('  curl -X POST http://localhost:8085/api/mail/preview \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"name": "张三", "email": "zhangsan@example.com"}\'')
    print('=' * 60)

    app.run()
