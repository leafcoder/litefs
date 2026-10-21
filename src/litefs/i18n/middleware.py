#!/usr/bin/env python
# coding: utf-8

"""
Locale 中间件

按请求协商 locale，并把结果写入：

- ``request_handler.locale``：请求处理器实例属性
- ``g.locale``：请求上下文全局对象

响应阶段回写 ``Content-Language`` 响应头，便于客户端与 CDN 缓存识别。
"""

from http.cookies import SimpleCookie
from typing import Any, Optional, Sequence

from ..middleware.base import Middleware
from .locale import negotiate_locale
from .translator import set_current_locale, set_current_locale_dir


class LocaleMiddleware(Middleware):
    """
    Locale 协商中间件

    挂载方式::

        app.add_middleware(LocaleMiddleware)

    显式指定配置::

        app.add_middleware(
            LocaleMiddleware,
            supported_locales=['zh_CN', 'en'],
            default_locale='zh_CN',
            locale_dir='locales',
        )
    """

    def __init__(
        self,
        app: Any,
        supported_locales: Optional[Sequence[str]] = None,
        default_locale: str = "en",
        locale_dir: str = "locales",
        cookie_name: str = "locale",
        param_name: str = "locale",
        set_cookie: bool = True,
    ) -> None:
        """
        初始化 Locale 中间件

        Args:
            app: Litefs 应用实例
            supported_locales: 受支持的 locale 列表，None 时从应用配置读取
            default_locale: 默认 locale
            locale_dir: 翻译文件根目录
            cookie_name: 存放 locale 的 Cookie 名称
            param_name: 存放 locale 的查询参数名称
            set_cookie: 是否在响应中回写 locale Cookie
        """
        super().__init__(app)

        config = getattr(app, "config", None)
        if supported_locales is None:
            supported_locales = getattr(config, "i18n_supported_locales", None) or ["en"]
        if default_locale == "en" and config is not None:
            default_locale = getattr(config, "i18n_default_locale", "en")
        if locale_dir == "locales" and config is not None:
            locale_dir = getattr(config, "i18n_locale_dir", "locales")
        if cookie_name == "locale" and config is not None:
            cookie_name = getattr(config, "i18n_cookie_name", "locale")
        if param_name == "locale" and config is not None:
            param_name = getattr(config, "i18n_param_name", "locale")

        self.supported_locales = list(supported_locales)
        self.default_locale = default_locale
        self.locale_dir = locale_dir
        self.cookie_name = cookie_name
        self.param_name = param_name
        self.set_cookie = set_cookie

    # ==================== 中间件接口 ====================

    def process_request(self, request_handler: Any) -> None:
        """
        协商并设置本次请求的 locale

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
        """
        locale = self.negotiate(request_handler)
        self.apply_locale(request_handler, locale)
        return None

    def process_response(self, request_handler: Any, response: Any) -> Any:
        """
        在响应中回写 Content-Language 与 locale Cookie

        Args:
            request_handler: 请求处理器实例
            response: 响应数据，通常为 (status, headers, content) 三元组

        Returns:
            未修改的响应数据
        """
        locale = getattr(request_handler, "locale", None)
        if not locale:
            return response

        if not (isinstance(response, tuple) and len(response) == 3):
            return response

        status_line, headers, content = response
        if not isinstance(headers, list):
            return response

        if not any(str(key).lower() == "content-language" for key, _ in headers):
            headers.append(("Content-Language", locale))

        if self.set_cookie:
            self._write_locale_cookie(request_handler, locale)

        return (status_line, headers, content)

    def process_exception(self, request_handler: Any, exception: BaseException) -> None:
        """
        处理异常（无需特殊处理）

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
        """
        return None

    # ==================== 异步接口 ====================

    async def async_process_request(self, request_handler: Any) -> None:
        """
        异步版本的处理请求

        Args:
            request_handler: 请求处理器实例

        Returns:
            None: 继续处理请求
        """
        return self.process_request(request_handler)

    async def async_process_response(self, request_handler: Any, response: Any) -> Any:
        """
        异步版本的处理响应

        Args:
            request_handler: 请求处理器实例
            response: 响应数据

        Returns:
            未修改的响应数据
        """
        return self.process_response(request_handler, response)

    async def async_process_exception(
        self, request_handler: Any, exception: BaseException
    ) -> None:
        """
        异步版本的处理异常

        Args:
            request_handler: 请求处理器实例
            exception: 异常对象

        Returns:
            None: 继续抛出异常
        """
        return self.process_exception(request_handler, exception)

    # ==================== 内部方法 ====================

    def negotiate(self, request_handler: Any) -> str:
        """
        执行 locale 协商

        Args:
            request_handler: 请求处理器实例

        Returns:
            选定的 locale
        """
        return negotiate_locale(
            supported=self.supported_locales,
            default_locale=self.default_locale,
            accept_language=self._get_accept_language(request_handler),
            cookie_locale=self._get_cookie_locale(request_handler),
            param_locale=self._get_param_locale(request_handler),
        )

    def apply_locale(self, request_handler: Any, locale: str) -> None:
        """
        将 locale 写入请求处理器与请求上下文

        Args:
            request_handler: 请求处理器实例
            locale: 选定的 locale
        """
        setattr(request_handler, "locale", locale)
        set_current_locale(locale)
        # 同步翻译目录，保证翻译函数在自定义目录（如多租户场景）下也能命中翻译表
        set_current_locale_dir(self.locale_dir)

        try:
            from ..context import g
            g.locale = locale
        except AttributeError:
            # 无请求上下文时忽略（如中间件在请求周期外被调用）
            pass

    def _get_accept_language(self, request_handler: Any) -> Optional[str]:
        """
        读取 Accept-Language 请求头

        Args:
            request_handler: 请求处理器实例

        Returns:
            请求头值，缺失时返回 None
        """
        headers = getattr(request_handler, "headers", None)
        if isinstance(headers, dict):
            return headers.get("accept-language")
        environ = getattr(request_handler, "_environ", None)
        if isinstance(environ, dict):
            return environ.get("HTTP_ACCEPT_LANGUAGE")
        return None

    def _get_cookie_locale(self, request_handler: Any) -> Optional[str]:
        """
        从 Cookie 中读取 locale

        Args:
            request_handler: 请求处理器实例

        Returns:
            Cookie 中的 locale，缺失时返回 None
        """
        environ = getattr(request_handler, "_environ", None)
        if not isinstance(environ, dict):
            return None

        raw = environ.get("HTTP_COOKIE")
        if not raw:
            return None

        try:
            cookie = SimpleCookie(raw)
        except Exception:
            return None

        morsel = cookie.get(self.cookie_name)
        if morsel is None:
            return None
        return morsel.value or None

    def _get_param_locale(self, request_handler: Any) -> Optional[str]:
        """
        从查询参数中读取 locale

        Args:
            request_handler: 请求处理器实例

        Returns:
            参数中的 locale，缺失时返回 None
        """
        params = getattr(request_handler, "get", None)
        if isinstance(params, dict):
            value = params.get(self.param_name)
            if value:
                return str(value)
        return None

    def _write_locale_cookie(self, request_handler: Any, locale: str) -> None:
        """
        回写 locale Cookie

        Args:
            request_handler: 请求处理器实例
            locale: 选定的 locale
        """
        setter = getattr(request_handler, "set_cookie", None)
        if not callable(setter):
            return
        try:
            setter(self.cookie_name, locale, path="/", samesite="Lax")
        except Exception:
            # Cookie 写入失败不应影响响应
            pass


__all__ = [
    "LocaleMiddleware",
]
