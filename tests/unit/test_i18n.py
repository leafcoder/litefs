#!/usr/bin/env python
# coding: utf-8

"""
国际化模块测试

覆盖 Accept-Language 解析、locale 规范化与匹配、请求级 locale 协商、
翻译表加载与缓存、翻译函数注入、LocaleMiddleware 的请求/响应处理，
以及完整的 WSGI 请求链路集成验证。
"""

import os
import struct
import unittest
from unittest.mock import MagicMock

from litefs.i18n import (
    LocaleMiddleware,
    Translator,
    get_current_locale,
    get_current_locale_dir,
    get_translations,
    gettext,
    inject_translations,
    match_locale,
    negotiate_locale,
    ngettext,
    normalize_locale,
    parse_accept_language,
    set_current_locale,
    set_current_locale_dir,
)
from litefs.i18n.translator import clear_translation_cache


class MockRequestHandler:
    """模拟请求处理器"""

    def __init__(self, path="/api", method="GET", headers=None, params=None, cookies=None):
        self._environ = {
            "PATH_INFO": path,
            "REQUEST_METHOD": method,
        }
        if headers:
            self._environ.update(headers)
        if cookies:
            self._environ["HTTP_COOKIE"] = cookies
        self._get = params or {}
        self._request_headers = {
            key.replace("_", "-").lower(): value
            for key, value in (headers or {}).items()
            if key.startswith("HTTP_")
        }
        self.cookies = {}

    @property
    def get(self):
        """查询参数字典"""
        return self._get

    def set_cookie(self, key, value, **kwargs):
        """记录写入的 Cookie"""
        self.cookies[key] = value


class TestNormalizeLocale(unittest.TestCase):
    """locale 规范化"""

    def test_normalize_dash(self):
        """连字符转换为下划线"""
        self.assertEqual(normalize_locale("zh-CN"), "zh_CN")

    def test_normalize_lower_territory(self):
        """地区代码转换为大写"""
        self.assertEqual(normalize_locale("zh_cn"), "zh_CN")

    def test_normalize_language_only(self):
        """仅语言代码时全部小写"""
        self.assertEqual(normalize_locale("EN"), "en")

    def test_normalize_empty(self):
        """空字符串返回空字符串"""
        self.assertEqual(normalize_locale(""), "")

    def test_normalize_variant(self):
        """变体标识保持原样"""
        self.assertEqual(normalize_locale("zh-Hans-CN"), "zh_Hans_CN")


class TestParseAcceptLanguage(unittest.TestCase):
    """Accept-Language 解析"""

    def test_empty_header(self):
        """空请求头返回空列表"""
        self.assertEqual(parse_accept_language(""), [])

    def test_single_language(self):
        """单语言解析"""
        self.assertEqual(parse_accept_language("zh-CN"), [("zh-CN", 1.0)])

    def test_quality_sorted_desc(self):
        """按 q 值降序排列"""
        result = parse_accept_language("en;q=0.5,zh-CN;q=0.9,fr;q=0.8")

        self.assertEqual([item[0] for item in result], ["zh-CN", "fr", "en"])

    def test_default_quality_is_one(self):
        """未指定 q 值时默认为 1"""
        result = parse_accept_language("zh-CN,en")

        self.assertEqual(result[0], ("zh-CN", 1.0))
        self.assertEqual(result[1], ("en", 1.0))

    def test_invalid_quality_becomes_zero(self):
        """非法 q 值按 0 处理"""
        result = parse_accept_language("zh-CN;q=abc")

        self.assertEqual(result[0][1], 0.0)

    def test_whitespace_tolerated(self):
        """容忍多余空白"""
        result = parse_accept_language(" zh-CN ; q=0.9 , en ; q=0.5 ")

        self.assertEqual(result[0], ("zh-CN", 0.9))
        self.assertEqual(result[1], ("en", 0.5))

    def test_empty_segments_skipped(self):
        """跳过空片段"""
        result = parse_accept_language("zh-CN,,en")

        self.assertEqual(len(result), 2)


class TestMatchLocale(unittest.TestCase):
    """locale 匹配"""

    def test_exact_match(self):
        """精确匹配"""
        self.assertEqual(match_locale("zh_CN", ["en", "zh_CN"]), "zh_CN")

    def test_case_insensitive_exact(self):
        """大小写不敏感的精确匹配"""
        self.assertEqual(match_locale("zh-cn", ["en", "zh_CN"]), "zh_CN")

    def test_prefix_fallback(self):
        """前缀回退"""
        self.assertEqual(match_locale("zh_CN", ["en", "zh"]), "zh")

    def test_no_match(self):
        """无匹配返回 None"""
        self.assertIsNone(match_locale("fr", ["en", "zh_CN"]))

    def test_empty_supported(self):
        """受支持列表为空时返回 None"""
        self.assertIsNone(match_locale("en", []))


class TestNegotiateLocale(unittest.TestCase):
    """locale 协商"""

    def test_param_has_highest_priority(self):
        """URL 参数优先级最高"""
        result = negotiate_locale(
            supported=["en", "zh_CN", "fr"],
            default_locale="en",
            accept_language="fr",
            cookie_locale="zh_CN",
            param_locale="zh_CN",
        )

        self.assertEqual(result, "zh_CN")

    def test_cookie_before_header(self):
        """Cookie 优先于请求头"""
        result = negotiate_locale(
            supported=["en", "zh_CN", "fr"],
            default_locale="en",
            accept_language="fr",
            cookie_locale="zh_CN",
        )

        self.assertEqual(result, "zh_CN")

    def test_header_used_when_no_param_or_cookie(self):
        """无参数与 Cookie 时使用请求头"""
        result = negotiate_locale(
            supported=["en", "zh_CN", "fr"],
            default_locale="en",
            accept_language="fr-FR,en;q=0.5",
        )

        self.assertEqual(result, "fr")

    def test_wildcard_uses_default(self):
        """通配符使用默认 locale"""
        result = negotiate_locale(
            supported=["en", "zh_CN"],
            default_locale="zh_CN",
            accept_language="*",
        )

        self.assertEqual(result, "zh_CN")

    def test_fallback_to_default(self):
        """全部不匹配时使用默认 locale"""
        result = negotiate_locale(
            supported=["en", "zh_CN"],
            default_locale="en",
            accept_language="ja,ko",
        )

        self.assertEqual(result, "en")

    def test_invalid_param_falls_through(self):
        """非法参数被忽略并继续协商"""
        result = negotiate_locale(
            supported=["en", "zh_CN"],
            default_locale="en",
            accept_language="zh_CN",
            param_locale="ja",
        )

        self.assertEqual(result, "zh_CN")


class TestTranslator(unittest.TestCase):
    """翻译器"""

    def setUp(self):
        """准备翻译文件目录并清理缓存"""
        import tempfile

        self._tmpdir = tempfile.TemporaryDirectory()
        self.locale_dir = self._tmpdir.name
        self.addCleanup(self._tmpdir.cleanup)
        self.addCleanup(clear_translation_cache)

    def _write_mo(self, locale, catalog):
        """
        写入最小可用的 .mo 翻译文件

        Args:
            locale: locale 名称
            catalog: {原文: 译文} 字典
        """
        # 元数据条目（msgid 为空）用于声明字符集，gettext 依赖它解析 UTF-8
        entries = {"": "Content-Type: text/plain; charset=UTF-8\n"}
        entries.update(catalog)

        keys = sorted(entries.keys())
        offsets = []
        ids = b""
        strs = b""
        for key in keys:
            encoded_key = key.encode("utf-8")
            encoded_value = entries[key].encode("utf-8")
            offsets.append((len(ids), len(encoded_key), len(strs), len(encoded_value)))
            ids += encoded_key + b"\x00"
            strs += encoded_value + b"\x00"

        count = len(keys)
        key_start = 7 * 4 + 16 * count
        value_start = key_start + len(ids)
        key_offsets = []
        value_offsets = []
        for id_offset, id_len, str_offset, str_len in offsets:
            key_offsets.extend([id_len, id_offset + key_start])
            value_offsets.extend([str_len, str_offset + value_start])

        output = struct.pack(
            "Iiiiiii",
            0x950412DE,       # 魔数
            0,                # 版本号
            count,            # 条目数
            7 * 4,            # 原文表偏移
            7 * 4 + count * 8,  # 译文表偏移
            0,                # 哈希表大小
            key_start,        # 哈希表偏移
        )
        output += struct.pack("i" * len(key_offsets), *key_offsets)
        output += struct.pack("i" * len(value_offsets), *value_offsets)
        output += ids
        output += strs

        locale_dir = os.path.join(self.locale_dir, locale, "LC_MESSAGES")
        os.makedirs(locale_dir, exist_ok=True)
        with open(os.path.join(locale_dir, "messages.mo"), "wb") as fp:
            fp.write(output)

    def test_missing_translation_returns_original(self):
        """翻译文件缺失时返回原文"""
        translator = Translator(self.locale_dir, "zh_CN")

        self.assertEqual(translator.gettext("Hello"), "Hello")

    def test_translation_loaded(self):
        """翻译文件存在时返回译文"""
        self._write_mo("zh_CN", {"Hello": "你好"})

        translator = Translator(self.locale_dir, "zh_CN")

        self.assertEqual(translator.gettext("Hello"), "你好")

    def test_untranslated_key_returns_original(self):
        """未收录的原文返回自身"""
        self._write_mo("zh_CN", {"Hello": "你好"})

        translator = Translator(self.locale_dir, "zh_CN")

        self.assertEqual(translator.gettext("Other"), "Other")

    def test_ngettext(self):
        """复数翻译"""
        # .mo 中复数条目的 msgid 形如 "单数\x00复数"，译文同样以 \x00 分隔
        self._write_mo("zh_CN", {"apple\x00apples": "苹果\x00苹果们"})

        translator = Translator(self.locale_dir, "zh_CN")

        self.assertEqual(translator.ngettext("apple", "apples", 1), "苹果")
        self.assertEqual(translator.ngettext("apple", "apples", 3), "苹果们")

    def test_translation_cache(self):
        """翻译表被缓存复用"""
        self._write_mo("zh_CN", {"Hello": "你好"})

        first = get_translations("zh_CN", self.locale_dir)
        second = get_translations("zh_CN", self.locale_dir)

        self.assertIs(first, second)

    def test_clear_cache(self):
        """清空缓存后重新加载"""
        self._write_mo("zh_CN", {"Hello": "你好"})

        first = get_translations("zh_CN", self.locale_dir)
        clear_translation_cache()
        second = get_translations("zh_CN", self.locale_dir)

        self.assertIsNot(first, second)


class TestRequestScopedTranslation(unittest.TestCase):
    """请求级翻译"""

    def setUp(self):
        """清理线程局部状态"""
        self.addCleanup(set_current_locale, None)
        self.addCleanup(set_current_locale_dir, None)
        clear_translation_cache()

    def test_no_context_returns_original(self):
        """无请求上下文时返回原文"""
        self.assertEqual(gettext("Hello"), "Hello")

    def test_ngettext_no_context(self):
        """无请求上下文时按数量返回对应原文"""
        self.assertEqual(ngettext("apple", "apples", 1), "apple")
        self.assertEqual(ngettext("apple", "apples", 2), "apples")

    def test_current_locale_setter(self):
        """设置与读取当前 locale"""
        set_current_locale("zh_CN")

        self.assertEqual(get_current_locale(), "zh_CN")

    def test_explicit_locale_overrides_current(self):
        """显式 locale 优先于当前 locale"""
        set_current_locale("zh_CN")

        self.assertEqual(gettext("Hello", locale="en"), "Hello")


class TestInjectTranslations(unittest.TestCase):
    """模板翻译函数注入"""

    def setUp(self):
        """清理线程局部状态"""
        self.addCleanup(set_current_locale, None)
        self.addCleanup(set_current_locale_dir, None)

    def test_inject_keys(self):
        """注入三个翻译函数"""
        context = inject_translations({})

        self.assertIn("_", context)
        self.assertIn("gettext", context)
        self.assertIn("ngettext", context)

    def test_no_locale_returns_identity(self):
        """无 locale 时为恒等函数"""
        context = inject_translations({})

        self.assertEqual(context["_"]("Hello"), "Hello")
        self.assertEqual(context["ngettext"]("apple", "apples", 2), "apples")

    def test_existing_keys_not_overwritten(self):
        """已存在的同名键不被覆盖"""
        context = inject_translations({"_": "占位"})

        self.assertEqual(context["_"], "占位")

    def test_inject_with_explicit_locale(self):
        """显式指定 locale 时使用该 locale"""
        context = inject_translations({}, locale="en")

        self.assertEqual(context["_"]("Hello"), "Hello")

    def test_returns_new_dict_when_none(self):
        """传入 None 时返回新字典"""
        context = inject_translations(None)

        self.assertIsInstance(context, dict)
        self.assertIn("_", context)


class TestLocaleMiddleware(unittest.TestCase):
    """Locale 中间件"""

    def _make_middleware(self, **kwargs):
        """构造中间件"""
        params = {
            "supported_locales": ["en", "zh_CN"],
            "default_locale": "en",
            "locale_dir": "locales",
        }
        params.update(kwargs)
        app = MagicMock()
        app.config = MagicMock()
        # 避免 MagicMock 的属性自动生成干扰配置读取
        app.config.i18n_supported_locales = None
        app.config.i18n_default_locale = "en"
        app.config.i18n_locale_dir = "locales"
        app.config.i18n_cookie_name = "locale"
        app.config.i18n_param_name = "locale"
        return LocaleMiddleware(app, **params)

    def test_process_request_sets_locale(self):
        """请求阶段写入 locale"""
        middleware = self._make_middleware()
        handler = MockRequestHandler(headers={"HTTP_ACCEPT_LANGUAGE": "zh-CN"})

        middleware.process_request(handler)

        self.assertEqual(handler.locale, "zh_CN")

    def test_process_request_param_priority(self):
        """查询参数优先"""
        middleware = self._make_middleware()
        handler = MockRequestHandler(
            headers={"HTTP_ACCEPT_LANGUAGE": "zh-CN"},
            params={"locale": "en"},
        )

        middleware.process_request(handler)

        self.assertEqual(handler.locale, "en")

    def test_process_request_cookie(self):
        """Cookie 中的 locale 生效"""
        middleware = self._make_middleware()
        handler = MockRequestHandler(cookies="locale=zh_CN")

        middleware.process_request(handler)

        self.assertEqual(handler.locale, "zh_CN")

    def test_process_request_default(self):
        """无任何来源时使用默认 locale"""
        middleware = self._make_middleware(default_locale="en")
        handler = MockRequestHandler()

        middleware.process_request(handler)

        self.assertEqual(handler.locale, "en")

    def test_process_request_syncs_locale_dir(self):
        """请求阶段同步翻译目录到线程局部状态"""
        self.addCleanup(set_current_locale_dir, None)
        middleware = self._make_middleware(locale_dir="/srv/locales")
        handler = MockRequestHandler(headers={"HTTP_ACCEPT_LANGUAGE": "zh-CN"})

        middleware.process_request(handler)

        self.assertEqual(get_current_locale_dir(), "/srv/locales")

    def test_custom_locale_dir_translation_applies(self):
        """自定义翻译目录下模板翻译函数生效"""
        import tempfile

        self.addCleanup(set_current_locale, None)
        self.addCleanup(set_current_locale_dir, None)
        self.addCleanup(clear_translation_cache)

        with tempfile.TemporaryDirectory() as locale_dir:
            messages_dir = os.path.join(locale_dir, "zh_CN", "LC_MESSAGES")
            os.makedirs(messages_dir)
            with open(os.path.join(messages_dir, "messages.mo"), "wb") as fp:
                fp.write(self._build_mo({"Hello": "你好"}))

            clear_translation_cache()
            middleware = self._make_middleware(locale_dir=locale_dir)
            handler = MockRequestHandler(headers={"HTTP_ACCEPT_LANGUAGE": "zh-CN"})

            middleware.process_request(handler)

            context = inject_translations()
            self.assertEqual(context["_"]("Hello"), "你好")

    @staticmethod
    def _build_mo(catalog):
        """构造单条目的 .mo 字节内容

        Args:
            catalog: {原文: 译文} 字典

        Returns:
            .mo 文件字节内容
        """
        entries = {"": "Content-Type: text/plain; charset=UTF-8\n"}
        entries.update(catalog)

        keys = sorted(entries)
        ids = b""
        strs = b""
        offsets = []
        for key in keys:
            encoded_key = key.encode("utf-8")
            encoded_value = entries[key].encode("utf-8")
            offsets.append((len(ids), len(encoded_key), len(strs), len(encoded_value)))
            ids += encoded_key + b"\x00"
            strs += encoded_value + b"\x00"

        count = len(keys)
        key_start = 7 * 4 + 16 * count
        value_start = key_start + len(ids)
        key_offsets = []
        value_offsets = []
        for id_offset, id_len, str_offset, str_len in offsets:
            key_offsets.extend([id_len, id_offset + key_start])
            value_offsets.extend([str_len, str_offset + value_start])

        output = struct.pack(
            "Iiiiiii",
            0x950412DE,
            0,
            count,
            7 * 4,
            7 * 4 + count * 8,
            0,
            key_start,
        )
        output += struct.pack("i" * len(key_offsets), *key_offsets)
        output += struct.pack("i" * len(value_offsets), *value_offsets)
        output += ids
        output += strs
        return output

    def test_process_response_adds_content_language(self):
        """响应阶段写入 Content-Language"""
        middleware = self._make_middleware()
        handler = MockRequestHandler()
        handler.locale = "zh_CN"

        status, headers, content = middleware.process_response(
            handler, ("200 OK", [], "body")
        )

        self.assertIn(("Content-Language", "zh_CN"), headers)
        self.assertEqual(status, "200 OK")
        self.assertEqual(content, "body")

    def test_process_response_keeps_existing_header(self):
        """已存在 Content-Language 时不重复写入"""
        middleware = self._make_middleware()
        handler = MockRequestHandler()
        handler.locale = "zh_CN"

        _status, headers, _content = middleware.process_response(
            handler, ("200 OK", [("Content-Language", "en")], "body")
        )

        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], ("Content-Language", "en"))

    def test_process_response_writes_cookie(self):
        """响应阶段回写 locale Cookie"""
        middleware = self._make_middleware()
        handler = MockRequestHandler()
        handler.locale = "zh_CN"

        middleware.process_response(handler, ("200 OK", [], "body"))

        self.assertEqual(handler.cookies["locale"], "zh_CN")

    def test_process_response_without_locale(self):
        """无 locale 时不修改响应"""
        middleware = self._make_middleware()
        handler = MockRequestHandler()

        response = ("200 OK", [], "body")
        result = middleware.process_response(handler, response)

        self.assertIs(result, response)

    def test_process_response_non_tuple(self):
        """非三元组响应原样返回"""
        middleware = self._make_middleware()
        handler = MockRequestHandler()
        handler.locale = "zh_CN"

        response = "plain"
        result = middleware.process_response(handler, response)

        self.assertIs(result, response)

    def test_process_exception_passes_through(self):
        """异常阶段不做处理"""
        middleware = self._make_middleware()
        handler = MockRequestHandler()

        self.assertIsNone(
            middleware.process_exception(handler, RuntimeError("boom"))
        )

    def test_async_process_request(self):
        """异步请求阶段与同步一致"""
        import asyncio

        middleware = self._make_middleware()
        handler = MockRequestHandler(headers={"HTTP_ACCEPT_LANGUAGE": "zh-CN"})

        asyncio.run(middleware.async_process_request(handler))

        self.assertEqual(handler.locale, "zh_CN")

    def test_async_process_response(self):
        """异步响应阶段与同步一致"""
        import asyncio

        middleware = self._make_middleware()
        handler = MockRequestHandler()
        handler.locale = "zh_CN"

        _status, headers, _content = asyncio.run(
            middleware.async_process_response(handler, ("200 OK", [], "body"))
        )

        self.assertIn(("Content-Language", "zh_CN"), headers)


class TestAppI18nIntegration(unittest.TestCase):
    """应用级集成"""

    def test_i18n_disabled_by_default(self):
        """默认不挂载国际化中间件"""
        from litefs.core import Litefs

        app = Litefs()

        names = [cls.__name__ for cls, _ in app.middleware_manager._middlewares]
        self.assertNotIn("LocaleMiddleware", names)

    def test_i18n_enabled_mounts_middleware(self):
        """启用后自动挂载国际化中间件"""
        from litefs.core import Litefs

        app = Litefs(
            i18n_enabled=True,
            i18n_supported_locales=["zh_CN", "en"],
            i18n_default_locale="zh_CN",
        )

        names = [cls.__name__ for cls, _ in app.middleware_manager._middlewares]
        self.assertIn("LocaleMiddleware", names)

    def test_wsgi_request_sets_content_language(self):
        """完整 WSGI 请求链路写入 Content-Language"""
        import io

        from litefs.core import Litefs

        app = Litefs(
            i18n_enabled=True,
            i18n_supported_locales=["zh_CN", "en"],
            i18n_default_locale="en",
        )

        def index_handler(request):
            return "hello"

        app.add_get("/", index_handler, name="index")

        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgi.url_scheme": "http",
            "wsgi.input": io.BytesIO(b""),
            "HTTP_ACCEPT_LANGUAGE": "zh-CN",
        }
        captured = {}

        def start_response(status, headers, exc_info=None):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(app.wsgi()(environ, start_response))

        self.assertEqual(body, b"hello")
        header_map = {key.lower(): value for key, value in captured["headers"]}
        self.assertEqual(header_map.get("content-language"), "zh_CN")

    def test_render_template_without_i18n_unchanged(self):
        """未启用国际化时模板渲染结果不变"""
        import tempfile

        from litefs.handlers.base import BaseRequestHandler

        class _FakeConfig:
            """仅提供模板目录的最小配置对象"""

            template_dir = ""

        class _FakeApp:
            """轻量应用替身，避免引入真实框架的额外依赖"""

            def __init__(self, template_dir):
                self.config = _FakeConfig()
                self.config.template_dir = template_dir
                self.debug = False

        with tempfile.TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "a.html"), "w", encoding="utf-8") as fp:
                fp.write("<p>${value}</p>")

            handler = BaseRequestHandler(_FakeApp(template_dir), {"REQUEST_METHOD": "GET"})

            content = handler.render_template("a.html", value="x")

        self.assertEqual(content, "<p>x</p>")


if __name__ == "__main__":
    unittest.main()
