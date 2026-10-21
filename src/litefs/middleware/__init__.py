#!/usr/bin/env python
# coding: utf-8

from .base import Middleware, MiddlewareManager
from .cors import CORSMiddleware
from .csrf import CSRFMiddleware
from .logging import LoggingMiddleware
from .enhanced_logging import (
    EnhancedLoggingMiddleware,
    log_performance,
    log_async_performance,
    RequestContextLogger
)
from .rate_limit import RateLimitMiddleware, ThrottleMiddleware
from .security import AuthMiddleware, SecurityMiddleware
from .health_check import HealthCheck
from .prometheus import PrometheusMiddleware

__all__ = [
    "Middleware",
    "MiddlewareManager",
    "LoggingMiddleware",
    "EnhancedLoggingMiddleware",
    "log_performance",
    "log_async_performance",
    "RequestContextLogger",
    "CORSMiddleware",
    "CSRFMiddleware",
    "SecurityMiddleware",
    "AuthMiddleware",
    "RateLimitMiddleware",
    "ThrottleMiddleware",
    "HealthCheck",
    "PrometheusMiddleware",
    "LocaleMiddleware",
]


def __getattr__(name):
    """
    延迟导出 LocaleMiddleware

    i18n 模块依赖 middleware 基类，若在此处直接导入会形成循环依赖，
    因此改用模块级 ``__getattr__``（PEP 562）延迟解析。

    Args:
        name: 属性名

    Returns:
        对应的属性

    Raises:
        AttributeError: 属性不存在时抛出
    """
    if name == "LocaleMiddleware":
        from ..i18n import LocaleMiddleware
        return LocaleMiddleware
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
