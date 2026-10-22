#!/usr/bin/env python
# coding: utf-8

"""
公共 API 稳定性契约

本模块是 Litefs 公共 API 的**唯一权威清单**，与 :doc:`api-stability`
政策文档、:doc:`deprecation-timeline` 废弃时间表一一对应。

分级定义
--------
Tier 1 ``stable``
    冻结契约。1.0.0 发布后仅允许在 major 版本中变更，
    且必须提供迁移指南（参见 ``docs/source/deprecation-timeline.md``）。

Tier 2 ``provisional``
    暂定契约。0.x 期间允许增删改，1.0.0 发布时统一裁定并转入 Tier 1
    或明确宣告废弃。

Tier 3 ``internal``
    内部实现。默认状态下**不提供任何兼容承诺**，
    可在任意 minor 版本中调整。

未在本模块登记的公开符号一律视为 Tier 3。

符号命名
--------
清单中的键为模块名（``litefs.handlers.response``），
值为该模块对外承诺的符号名元组。

弃用登记
--------
``DEPRECATED`` 记录已宣告废弃的符号及其移除版本；
``ALIASES`` 记录为兼容历史用法而保留的别名。

数据来源
--------
``STABLE`` / ``PROVISIONAL`` 由 ``tests/unit/test_api_contract.py``
做双向校验：登记的符号必须真实存在，模块已公开的符号必须被登记。
"""

import importlib
import inspect
from typing import Dict, FrozenSet, NamedTuple, Tuple

__all__ = [
    'STABLE',
    'PROVISIONAL',
    'EXEMPT_MODULES',
    'FULL_SURFACE_MODULES',
    'Deprecation',
    'DEPRECATED',
    'ALIASES',
    'public_symbols',
    'api_tier',
    'qualified_symbols',
    'stable_symbols',
    'provisional_symbols',
]

#: Tier 1 冻结契约：1.0.0 之后仅允许 major 版本变更
STABLE: Dict[str, Tuple[str, ...]] = {
    "litefs._version": (
        "format_version", "get_major_version", "get_micro_version", "get_minor_version",
        "get_version", "get_version_info", "get_version_tuple",
    ),
    "litefs.core": (
        "CacheBackend", "CacheManager", "DatabaseManager", "ErrorPageRenderer", "ExtensionMixin",
        "HTTPServer", "Litefs", "MiddlewareManager", "PluginLoader", "PluginManager",
        "ProcessHTTPServer", "ProtocolMixin", "Router", "RoutingMixin", "ServerMixin",
        "init_session_manager", "is_port_available", "make_config", "make_logger", "make_server",
        "test_server",
    ),
    "litefs.config": (
        "Config", "load_config", "merge_configs",
    ),
    "litefs.context": (
        "G", "RequestContext", "RequestContextData", "RequestContextManager", "g",
        "get_current_request", "has_request_context", "with_request_context",
    ),
    "litefs.deprecation": (
        "F", "LitefsDeprecationWarning", "deprecated", "format_deprecation_message",
        "warn_deprecated",
    ),
    "litefs.exceptions": (
        "BadGateway", "BadRequest", "CacheError", "ConfigurationError", "Conflict", "DatabaseError",
        "ErrorHandler", "Forbidden", "GatewayTimeout", "Gone", "HTTPException", "HttpError",
        "InternalServerError", "MethodNotAllowed", "NotAcceptable", "NotFound", "NotImplemented",
        "PayloadTooLarge", "RequestTimeout", "RouteNotFound", "ServiceUnavailable",
        "TooManyRequests", "Unauthorized", "UnprocessableEntity", "UnsupportedMediaType",
        "ValidationError", "abort", "error_handler",
    ),
    "litefs.handlers": (
        "ASGIRequestHandler", "BaseRequestHandler", "DEFAULT_STATUS_MESSAGE", "EOFS",
        "EnhancedRequestHandler", "FILES_HEADER_NAME", "POSTS_HEADER_NAME", "RequestHandler",
        "Response", "SocketRequestHandler", "WSGIRequestHandler", "default_content_type",
        "double_slash_sub", "http_status_codes", "imap", "is_bytes", "json_content_type",
        "parse_form", "parse_header", "parse_multipart_asgi", "parse_multipart_stream",
        "parse_multipart_wsgi", "server_info", "server_software", "should_retry_error",
        "startswith_dot_sub", "suffixes",
    ),
    "litefs.handlers.base": (
        "BaseRequestHandler",
    ),
    "litefs.handlers.wsgi": (
        "WSGIRequestHandler",
    ),
    "litefs.handlers.asgi": (
        "ASGIRequestHandler",
    ),
    "litefs.handlers.socket": (
        "EOFS", "FILES_HEADER_NAME", "POSTS_HEADER_NAME", "RequestHandler", "SocketRequestHandler",
        "double_slash_sub", "imap", "is_bytes", "should_retry_error", "startswith_dot_sub",
        "suffixes",
    ),
    "litefs.handlers.response": (
        "DEFAULT_STATUS_MESSAGE", "Response", "default_content_type", "http_status_codes",
        "json_content_type", "server_info", "server_software",
    ),
    "litefs.handlers.form": (
        "form_dict_match", "parse_form", "parse_header", "parse_multipart_asgi",
        "parse_multipart_stream", "parse_multipart_wsgi",
    ),
    "litefs.handlers.enhanced": (
        "EnhancedRequestHandler",
    ),
    "litefs.routing": (
        "RadixNode", "RadixTree", "Route", "RouteNotFound", "Router", "delete", "get", "head",
        "options", "patch", "post", "put", "route",
    ),
    "litefs.routing.router": (
        "Route", "Router", "delete", "get", "head", "options", "patch", "post", "put", "route",
    ),
    "litefs.routing.radix_tree": (
        "RadixNode", "RadixTree",
    ),
    "litefs.server": (
        "BufferedRWPair", "DEFAULT_BUFFER_SIZE", "HAS_EPOLL", "HAS_GREENLET", "HTTPServer",
        "ProcessHTTPServer", "SocketIO", "TCPServer", "WSGIServer", "epoll", "mainloop",
        "make_environ", "make_headers",
    ),
    "litefs.server.greenlet": (
        "Epoll", "HTTPServer", "ProcessHTTPServer", "SocketIO", "TCPServer", "WSGIServer", "epoll",
        "mainloop", "make_environ", "make_headers", "parse_header", "server_forever",
    ),
    "litefs.middleware": (
        "AuthMiddleware", "CORSMiddleware", "CSRFMiddleware", "EnhancedLoggingMiddleware",
        "HealthCheck", "LoggingMiddleware", "Middleware", "MiddlewareManager",
        "PrometheusMiddleware", "RateLimitMiddleware", "RequestContextLogger", "SecurityMiddleware",
        "ThrottleMiddleware", "log_async_performance", "log_performance",
    ),
    "litefs.middleware.base": (
        "Middleware", "MiddlewareManager",
    ),
    "litefs.middleware.cors": (
        "CORSMiddleware",
    ),
    "litefs.middleware.csrf": (
        "CSRFMiddleware",
    ),
    "litefs.middleware.logging": (
        "LoggingMiddleware",
    ),
    "litefs.middleware.enhanced_logging": (
        "EnhancedLoggingMiddleware", "RequestContextLogger", "log_async_performance",
        "log_performance",
    ),
    "litefs.middleware.rate_limit": (
        "RateLimitMiddleware", "ThrottleMiddleware",
    ),
    "litefs.middleware.security": (
        "AuthMiddleware", "SecurityMiddleware",
    ),
    "litefs.middleware.health_check": (
        "HealthCheck",
    ),
    "litefs.cache": (
        "CacheBackend", "CacheBackendBase", "CacheFactory", "CacheManager", "DatabaseCache",
        "FileEventHandler", "FormCache", "LiteFile", "MemcacheCache", "MemoryCache", "RedisCache",
        "TreeCache", "get_global_cache",
    ),
    "litefs.cache.base": (
        "CacheBackendBase", "CacheStats",
    ),
    "litefs.cache.cache": (
        "FileEventHandler", "LiteFile", "MemoryCache", "TreeCache",
    ),
    "litefs.cache.factory": (
        "CacheBackend", "CacheFactory",
    ),
    "litefs.cache.manager": (
        "CacheManager", "get_global_cache",
    ),
    "litefs.cache.form_cache": (
        "FormCache",
    ),
    "litefs.cache.db": (
        "DatabaseCache",
    ),
    "litefs.cache.redis": (
        "RedisCache",
    ),
    "litefs.cache.memcache": (
        "MemcacheCache",
    ),
    "litefs.cache_decorators": (
        "MemoryCacheStore", "cache_method", "cache_property", "cache_response", "cached",
        "clear_all_cache", "get_cache_stats", "get_cache_store",
    ),
    "litefs.session": (
        "CachedSessionStore", "DatabaseSession", "MemcacheSession", "RedisSession", "Session",
        "SessionBackend", "SessionFactory", "SessionStoreBase",
    ),
    "litefs.session.base": (
        "SessionStoreBase",
    ),
    "litefs.session.session": (
        "MemorySessionStore", "Session",
    ),
    "litefs.session.factory": (
        "SessionBackend", "SessionFactory",
    ),
    "litefs.session.manager": (
        "SessionManager", "get_global_session_cache",
    ),
    "litefs.session.db": (
        "DatabaseSession",
    ),
    "litefs.session.redis": (
        "RedisSession",
    ),
    "litefs.session.memcache": (
        "MemcacheSession",
    ),
    "litefs.session.cache_session": (
        "CachedSessionStore",
    ),
    "litefs.auth": (
        "Auth", "AuthMiddleware", "BaseUserStore", "GitHubProvider", "GoogleProvider", "JWTManager",
        "MemoryUserStore", "OAuth2", "OAuth2Provider", "OAuth2State", "OAuth2UserInfo",
        "Permission", "Role", "User", "WeChatProvider", "WeComProvider", "create_oauth2_blueprint",
        "create_token", "current_user", "decode_token", "get_provider", "get_user_store",
        "hash_password", "init_default_roles_and_permissions", "login_required",
        "permission_required", "role_required", "set_user_store", "verify_password",
    ),
    "litefs.auth.decorators": (
        "admin_required", "current_user", "owner_or_admin_required", "permission_required",
    ),
    "litefs.auth.jwt": (
        "JWTManager", "TokenBlacklist", "create_token", "decode_token",
    ),
    "litefs.auth.middleware": (
        "AuthMiddleware", "login_required", "role_required",
    ),
    "litefs.auth.models": (
        "BaseUserStore", "MemoryUserStore", "Permission", "Role", "User", "get_user_store",
        "init_default_roles_and_permissions", "set_user_store",
    ),
    "litefs.auth.oauth2": (
        "OAuth2", "OAuth2State", "create_oauth2_blueprint",
    ),
    "litefs.auth.password": (
        "check_password_breach", "check_password_breach_async", "clear_breach_cache",
        "generate_password", "get_breach_count", "get_breach_count_async", "hash_password",
        "validate_password_strength", "verify_password",
    ),
    "litefs.auth.providers": (
        "GitHubProvider", "GoogleProvider", "OAuth2Provider", "OAuth2UserInfo", "WeChatProvider",
        "WeComProvider", "get_provider",
    ),
    "litefs.database": (
        "AlembicManager", "Base", "Database", "DatabaseManager",
    ),
    "litefs.database.core": (
        "Database", "DatabaseManager",
    ),
    "litefs.database.models": (
        "TimestampMixin",
    ),
    "litefs.forms": (
        "Choice", "Email", "Field", "Form", "Function", "Length", "LoginForm", "Number", "Regex",
        "RegistrationForm", "Required", "URL", "Validator",
    ),
    "litefs.validators": (
        "ChoiceValidator", "EmailValidator", "FormValidator", "NumberValidator", "RegexValidator",
        "RequiredValidator", "StringValidator", "TypeValidator", "URLValidator", "ValidationError",
        "Validator", "choice", "email", "number_type", "regex", "required", "string_type", "url",
    ),
    "litefs.utils": (
        "gmt_date", "log_debug", "log_error", "log_info", "make_logger", "render_error",
    ),
    "litefs.utils.utils": (
        "format_gmt_date", "gmt_date", "log_debug", "log_error", "log_info", "make_logger",
        "render_error",
    ),
    "litefs.static_handler": (
        "StaticFileHandler", "create_static_handler",
    ),
    "litefs.security": (
        "generate_csrf_token", "secure_path_join", "validate_csrf_token",
    ),
    "litefs.error_pages": (
        "ErrorPageRenderer",
    ),
    "litefs.websocket": (
        "CloseCode", "ConnectionManager", "Frame", "Opcode", "WebSocket", "WebSocketConnection",
        "WebSocketServer",
    ),
    "litefs.websocket.connection": (
        "ConnectionManager", "WebSocketConnection",
    ),
    "litefs.websocket.protocol": (
        "CloseCode", "Frame", "Opcode", "build_close_payload", "compute_accept_key",
        "parse_close_payload",
    ),
    "litefs.websocket.server": (
        "WebSocket", "WebSocketServer",
    ),
    "litefs.cli": (
        "db_init", "db_migrate", "main", "routes", "runserver", "shell", "startproject", "test",
        "version",
    ),
}

#: Tier 2 暂定契约：0.x 期间允许调整，1.0.0 时统一裁定
PROVISIONAL: Dict[str, Tuple[str, ...]] = {
    "litefs.i18n": (
        "DEFAULT_DOMAIN", "DEFAULT_LOCALE_DIR", "LocaleMiddleware", "Translator", "WILDCARD",
        "clear_translation_cache", "get_current_locale", "get_current_locale_dir",
        "get_translations", "gettext", "inject_translations", "install_translations",
        "match_locale", "negotiate_locale", "ngettext", "normalize_locale", "parse_accept_language",
        "set_current_locale", "set_current_locale_dir",
    ),
    "litefs.i18n.locale": (
        "WILDCARD", "match_locale", "negotiate_locale", "normalize_locale", "parse_accept_language",
    ),
    "litefs.i18n.middleware": (
        "LocaleMiddleware",
    ),
    "litefs.i18n.template": (
        "inject_translations", "make_translation_callables",
    ),
    "litefs.i18n.translator": (
        "DEFAULT_DOMAIN", "DEFAULT_LOCALE_DIR", "Translator", "clear_translation_cache",
        "get_current_locale", "get_current_locale_dir", "get_translations", "gettext",
        "install_translations", "ngettext", "set_current_locale", "set_current_locale_dir",
    ),
    "litefs.mail": (
        "Attachment", "MailConfig", "MailSendError", "MailSendResult", "Message",
        "SEND_MAIL_TASK_NAME", "SMTPClient", "build_email_message", "build_mail_body",
        "get_mail_config", "render_mail_template", "send_mail", "send_mail_async",
    ),
    "litefs.mail.message": (
        "Attachment", "Message", "build_email_message",
    ),
    "litefs.mail.smtp": (
        "MailConfig", "MailSendError", "SMTPClient", "get_mail_config",
    ),
    "litefs.mail.tasks": (
        "MailSendResult", "SEND_MAIL_TASK_NAME", "send_mail", "send_mail_async",
    ),
    "litefs.mail.template": (
        "build_mail_body", "get_template_lookup", "render_mail_template",
    ),
    "litefs.metrics": (
        "DEFAULT_BUCKETS", "DEFAULT_CONTENT_TYPE", "MetricsRegistry", "PrometheusNotAvailable",
        "UNMATCHED_ROUTE", "build_metrics_registry", "load_prometheus_client",
    ),
    "litefs.middleware.prometheus": (
        "PrometheusMiddleware",
    ),
    "litefs.openapi": (
        "OpenAPI", "OpenAPIGenerator", "SwaggerUI",
    ),
    "litefs.openapi.generator": (
        "OpenAPIGenerator",
    ),
    "litefs.openapi.ui": (
        "SwaggerUI",
    ),
    "litefs.plugins": (
        "Plugin", "PluginLoader", "PluginManager",
    ),
    "litefs.plugins.base": (
        "Plugin", "PluginManager",
    ),
    "litefs.plugins.loader": (
        "PluginLoader",
    ),
    "litefs.tasks": (
        "AsyncResult", "Celery", "CeleryConfig", "HAS_CELERY", "crontab", "get_celery", "task",
    ),
    "litefs.debug": (
        "DebugMiddleware", "DebugToolbar", "RequestDebug", "SQLQuery", "TerminalFormatter",
        "get_current_debug", "is_debug_enabled", "toolbar", "track_performance", "track_sql",
    ),
    "litefs.debug.middleware": (
        "DebugMiddleware", "track_performance", "track_sql",
    ),
    "litefs.cli_db": (
        "DB_SUBCOMMANDS", "build_migration_manager", "create_tables", "db_sub_create_tables",
        "db_sub_current", "db_sub_downgrade", "db_sub_history", "db_sub_init", "db_sub_migrate",
        "db_sub_upgrade", "load_project_database_url", "run_migration",
    ),
    "litefs.database.migrations": (
        "ALEMBIC_INI_NAME", "AlembicManager", "AlembicNotAvailable", "DEFAULT_SCRIPT_LOCATION",
        "detect_models_imports", "load_alembic",
    ),
    "litefs.server.asgi": (
        "ASGIServer", "asgi_application",
    ),
    "litefs.server.asyncio": (
        "AsyncHTTPRequestHandler", "AsyncHTTPServer", "parse_header", "run_asyncio",
    ),
    "litefs.app": (
    ),
    "litefs.app.helpers": (
        "init_session_manager", "is_port_available", "make_config", "make_server",
    ),
    "litefs.app.routing_mixin": (
        "RoutingMixin",
    ),
    "litefs.app.protocol_mixin": (
        "ProtocolMixin",
    ),
    "litefs.app.extension_mixin": (
        "ExtensionMixin",
    ),
    "litefs.app.server_mixin": (
        "ServerMixin",
    ),
    "litefs.app.server_cli": (
        "test_server",
    ),
}


#: 不纳入契约检查的模块（入口脚本等非库接口模块）
EXEMPT_MODULES: Tuple[str, ...] = (
    'litefs.__main__',
    'litefs._json',
    'litefs._stable',
)

#: 这些模块的全部非下划线导出均视为公共面（向后兼容再导出聚合模块）
FULL_SURFACE_MODULES: FrozenSet[str] = frozenset({
    'litefs.core',
})


class Deprecation(NamedTuple):
    """废弃声明

    Attributes:
        since: 宣告废弃的版本
        removal: 计划移除的版本
        replacement: 推荐的替代符号
        reason: 废弃原因
    """

    since: str
    removal: str
    replacement: str
    reason: str


#: 已宣告废弃的符号，键为 ``模块:符号``
DEPRECATED: Dict[str, Deprecation] = {
    'litefs.core:Litefs.session': Deprecation(
        since='0.10.0',
        removal='1.3.0',
        replacement='Litefs.db_session',
        reason='方法名与 cache/session 子系统语义冲突，统一为数据库会话命名',
    ),
}

#: 为兼容历史用法保留的别名，键为 ``模块:符号``，值为规范符号
ALIASES: Dict[str, str] = {
    'litefs.exceptions:HttpError': 'litefs.exceptions:HTTPException',
    'litefs.handlers.response:responses': 'litefs.handlers.response:http_status_codes',
    'litefs.handlers.socket:RequestHandler': 'litefs.handlers.socket:SocketRequestHandler',
}


def public_symbols(module_name: str) -> Tuple[str, ...]:
    """列出模块的公共符号

    公共符号定义为：模块 ``__all__`` 中声明的符号，
    以及由该模块自身定义的非下划线符号。

    Args:
        module_name: 模块名，例如 ``litefs.handlers.response``

    Returns:
        排序后的公共符号元组
    """
    module = importlib.import_module(module_name)
    declared = set(getattr(module, '__all__', []))
    names = set()
    for name in dir(module):
        if name.startswith('_'):
            continue
        obj = getattr(module, name)
        if inspect.ismodule(obj):
            continue
        owner = getattr(obj, '__module__', None)
        if owner in ('typing', 'typing_extensions', 'builtins'):
            continue
        if owner == module_name or name in declared:
            names.add(name)
        elif module_name in FULL_SURFACE_MODULES:
            names.add(name)
    return tuple(sorted(names))


def api_tier(module_name: str, symbol: str) -> str:
    """查询符号的契约分级

    Args:
        module_name: 模块名
        symbol: 符号名

    Returns:
        ``'stable'`` / ``'provisional'`` / ``'internal'``
    """
    if symbol in STABLE.get(module_name, ()):
        return 'stable'
    if symbol in PROVISIONAL.get(module_name, ()):
        return 'provisional'
    return 'internal'


def qualified_symbols(registry: Dict[str, Tuple[str, ...]]) -> Tuple[str, ...]:
    """将注册表展开为 ``模块:符号`` 形式的扁平清单"""
    result = []
    for module_name, symbols in registry.items():
        for symbol in symbols:
            result.append('%s:%s' % (module_name, symbol))
    return tuple(sorted(result))


def stable_symbols() -> Tuple[str, ...]:
    """返回全部 Tier 1 冻结符号（``模块:符号``）"""
    return qualified_symbols(STABLE)


def provisional_symbols() -> Tuple[str, ...]:
    """返回全部 Tier 2 暂定符号（``模块:符号``）"""
    return qualified_symbols(PROVISIONAL)
