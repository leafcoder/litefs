#!/usr/bin/env python
# coding: utf-8

"""
国际化（i18n）示例

展示 Litefs 的国际化能力：

- 基于 ``Accept-Language`` / Cookie / 查询参数的四级语言协商
- 请求级 locale（``request.locale`` / ``g.locale`` / 线程局部存储）
- 模板翻译函数注入（``_`` / ``gettext`` / ``ngettext``）
- 响应头 ``Content-Language`` 与 locale Cookie 回写

运行::

    python compile_messages.py     # 先编译翻译文件
    python app.py

验证::

    curl http://localhost:8086/                       # 使用 Accept-Language 协商
    curl "http://localhost:8086/?locale=en"           # 查询参数优先级最高
    curl -H "Accept-Language: en-US,en;q=0.9" http://localhost:8086/
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.core import Litefs
from litefs.handlers import Response
from litefs.i18n import gettext, ngettext
from litefs.routing import get

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALES_DIR = os.path.join(APP_DIR, 'locales')

# ============================================================================
# 应用配置
# ============================================================================

app = Litefs(
    host='0.0.0.0',
    port=8086,
    debug=True,
    # 启用国际化：框架自动挂载 LocaleMiddleware
    i18n_enabled=True,
    i18n_default_locale='zh_CN',
    i18n_supported_locales=['zh_CN', 'en'],
    i18n_locale_dir=LOCALES_DIR,
    i18n_cookie_name='locale',
    i18n_param_name='locale',
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))

# 未编译翻译文件时给出明确提示，避免「页面显示英文却不知原因」
if not os.path.exists(os.path.join(LOCALES_DIR, 'zh_CN', 'LC_MESSAGES', 'messages.mo')):
    print('[WARN] 未找到编译后的翻译文件，请先执行: python compile_messages.py')


# ============================================================================
# 业务路由
# ============================================================================

@get('/', name='index')
def index(request):
    """首页：模板中的文案全部走翻译函数"""
    locale = getattr(request, 'locale', '') or app.config.i18n_default_locale
    message_count = 3

    return request.render_template('index.html', **{
        'title': gettext('Internationalization demo'),
        'locale': locale,
        'message_count': message_count,
        'message_text': ngettext('%d message', '%d messages', message_count) % message_count,
        'menus': [
            {'key': 'dashboard', 'label': gettext('Dashboard')},
            {'key': 'settings', 'label': gettext('Settings')},
        ],
    })


@get('/api/locale', name='api_locale')
def api_locale(request):
    """查看本次请求协商出的语言"""
    locale = getattr(request, 'locale', '') or app.config.i18n_default_locale
    return Response.json({
        'locale': locale,
        'supported': list(app.config.i18n_supported_locales),
        'text': gettext('The current locale is %s') % locale,
    })


app.register_routes(__name__)


if __name__ == '__main__':
    print('=' * 60)
    print('Litefs 国际化示例')
    print('=' * 60)
    print()
    print('应用地址:   http://localhost:8086')
    print('翻译目录:   %s' % LOCALES_DIR)
    print('支持语言:   %s' % ', '.join(app.config.i18n_supported_locales))
    print('默认语言:   %s' % app.config.i18n_default_locale)
    print()
    print('语言切换:')
    print('  curl http://localhost:8086/?locale=en')
    print('  curl -H "Accept-Language: en-US,en;q=0.9" http://localhost:8086/')
    print('  curl http://localhost:8086/api/locale')
    print('=' * 60)

    app.run()
