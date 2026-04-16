#!/usr/bin/env python
# coding: utf-8

"""
统一异常处理体系

提供完整的 HTTP 异常类和错误处理机制
"""

from typing import Optional, Dict, Any, List


HTTP_STATUS_CODES = {
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Payload Too Large',
    414: 'URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Range Not Satisfiable',
    417: 'Expectation Failed',
    418: "I'm a teapot",
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    425: 'Too Early',
    426: 'Upgrade Required',
    428: 'Precondition Required',
    429: 'Too Many Requests',
    431: 'Request Header Fields Too Large',
    451: 'Unavailable For Legal Reasons',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    506: 'Variant Also Negotiates',
    507: 'Insufficient Storage',
    508: 'Loop Detected',
    510: 'Not Extended',
    511: 'Network Authentication Required',
}


class HTTPException(Exception):
    """
    HTTP 异常基类
    
    所有 HTTP 异常都应该继承此类
    
    Args:
        status_code: HTTP 状态码
        message: 错误消息
        headers: 响应头列表
        description: 详细描述
    """
    
    def __init__(
        self, 
        status_code: int = 500, 
        message: Optional[str] = None,
        headers: Optional[List[tuple]] = None,
        description: Optional[str] = None
    ):
        self.status_code = status_code
        self.message = message or HTTP_STATUS_CODES.get(status_code, 'Unknown Error')
        self.headers = headers or []
        self.description = description
        
        super().__init__(f"{status_code} {self.message}")
    
    def __str__(self):
        return f"{self.status_code} {self.message}"
    
    def __repr__(self):
        return f"<{self.__class__.__name__} [{self.status_code}]>"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            包含错误信息的字典
        """
        data = {
            'error': self.__class__.__name__,
            'status_code': self.status_code,
            'message': self.message
        }
        
        if self.description:
            data['description'] = self.description
        
        return data


class BadRequest(HTTPException):
    """400 Bad Request - 客户端请求语法错误"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(400, message or 'Bad Request', description=description)


class Unauthorized(HTTPException):
    """401 Unauthorized - 需要身份认证"""
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        description: Optional[str] = None,
        www_authenticate: Optional[str] = None
    ):
        headers = []
        if www_authenticate:
            headers.append(('WWW-Authenticate', www_authenticate))
        
        super().__init__(401, message or 'Unauthorized', headers=headers, description=description)


class Forbidden(HTTPException):
    """403 Forbidden - 服务器拒绝请求"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(403, message or 'Forbidden', description=description)


class NotFound(HTTPException):
    """404 Not Found - 请求的资源不存在"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(404, message or 'Not Found', description=description)


class MethodNotAllowed(HTTPException):
    """405 Method Not Allowed - 请求方法不被允许"""
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        description: Optional[str] = None,
        allowed_methods: Optional[List[str]] = None
    ):
        headers = []
        if allowed_methods:
            headers.append(('Allow', ', '.join(allowed_methods)))
        
        super().__init__(405, message or 'Method Not Allowed', headers=headers, description=description)


class NotAcceptable(HTTPException):
    """406 Not Acceptable - 无法满足请求的 Accept 头部"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(406, message or 'Not Acceptable', description=description)


class RequestTimeout(HTTPException):
    """408 Request Timeout - 请求超时"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(408, message or 'Request Timeout', description=description)


class Conflict(HTTPException):
    """409 Conflict - 请求冲突"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(409, message or 'Conflict', description=description)


class Gone(HTTPException):
    """410 Gone - 请求的资源已不存在"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(410, message or 'Gone', description=description)


class PayloadTooLarge(HTTPException):
    """413 Payload Too Large - 请求实体过大"""
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        description: Optional[str] = None,
        max_size: Optional[int] = None
    ):
        desc = description
        if max_size:
            desc = f"{description or ''} Maximum allowed size: {max_size} bytes".strip()
        
        super().__init__(413, message or 'Payload Too Large', description=desc)


class UnsupportedMediaType(HTTPException):
    """415 Unsupported Media Type - 不支持的媒体类型"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(415, message or 'Unsupported Media Type', description=description)


class UnprocessableEntity(HTTPException):
    """422 Unprocessable Entity - 无法处理的实体"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(422, message or 'Unprocessable Entity', description=description)


class TooManyRequests(HTTPException):
    """429 Too Many Requests - 请求过多"""
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        description: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        headers = []
        if retry_after:
            headers.append(('Retry-After', str(retry_after)))
        
        super().__init__(429, message or 'Too Many Requests', headers=headers, description=description)


class InternalServerError(HTTPException):
    """500 Internal Server Error - 服务器内部错误"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(500, message or 'Internal Server Error', description=description)


class NotImplemented(HTTPException):
    """501 Not Implemented - 服务器不支持请求的功能"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(501, message or 'Not Implemented', description=description)


class BadGateway(HTTPException):
    """502 Bad Gateway - 网关错误"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(502, message or 'Bad Gateway', description=description)


class ServiceUnavailable(HTTPException):
    """503 Service Unavailable - 服务不可用"""
    
    def __init__(
        self, 
        message: Optional[str] = None, 
        description: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        headers = []
        if retry_after:
            headers.append(('Retry-After', str(retry_after)))
        
        super().__init__(503, message or 'Service Unavailable', headers=headers, description=description)


class GatewayTimeout(HTTPException):
    """504 Gateway Timeout - 网关超时"""
    
    def __init__(self, message: Optional[str] = None, description: Optional[str] = None):
        super().__init__(504, message or 'Gateway Timeout', description=description)


# 向后兼容：HttpError 是 HTTPException 的别名
HttpError = HTTPException


class RouteNotFound(Exception):
    """路由未找到异常"""
    pass


class ConfigurationError(Exception):
    """配置错误异常"""
    
    def __init__(self, message: str, config_key: Optional[str] = None):
        self.config_key = config_key
        super().__init__(message)


class ValidationError(Exception):
    """验证错误异常"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        self.field = field
        self.value = value
        super().__init__(message)


class DatabaseError(Exception):
    """数据库错误异常"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message)


class CacheError(Exception):
    """缓存错误异常"""
    
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.original_error = original_error
        super().__init__(message)


def abort(
    status_code: int = 500, 
    message: Optional[str] = None,
    description: Optional[str] = None,
    **kwargs
):
    """
    抛出 HTTP 异常
    
    Args:
        status_code: HTTP 状态码
        message: 错误消息
        description: 详细描述
        **kwargs: 其他参数传递给异常类
        
    Raises:
        HTTPException: HTTP 异常
    """
    exception_class = _get_exception_class(status_code)
    raise exception_class(message=message, description=description, **kwargs)


def _get_exception_class(status_code: int) -> type:
    """
    根据状态码获取异常类
    
    Args:
        status_code: HTTP 状态码
        
    Returns:
        异常类
    """
    exception_map = {
        400: BadRequest,
        401: Unauthorized,
        403: Forbidden,
        404: NotFound,
        405: MethodNotAllowed,
        406: NotAcceptable,
        408: RequestTimeout,
        409: Conflict,
        410: Gone,
        413: PayloadTooLarge,
        415: UnsupportedMediaType,
        422: UnprocessableEntity,
        429: TooManyRequests,
        500: InternalServerError,
        501: NotImplemented,
        502: BadGateway,
        503: ServiceUnavailable,
        504: GatewayTimeout,
    }
    
    return exception_map.get(status_code, HTTPException)


class ErrorHandler:
    """
    错误处理器
    
    用于注册和管理自定义错误处理函数
    """
    
    def __init__(self):
        self._handlers = {}
    
    def register(self, status_code: int):
        """
        注册错误处理函数装饰器
        
        Args:
            status_code: HTTP 状态码
            
        Returns:
            装饰器函数
        """
        def decorator(func):
            self._handlers[status_code] = func
            return func
        return decorator
    
    def get_handler(self, status_code: int):
        """
        获取错误处理函数
        
        Args:
            status_code: HTTP 状态码
            
        Returns:
            错误处理函数，如果没有则返回 None
        """
        return self._handlers.get(status_code)
    
    def handle(self, error: Exception, request_handler):
        """
        处理错误
        
        Args:
            error: 异常对象
            request_handler: 请求处理器
            
        Returns:
            响应数据
        """
        if isinstance(error, HTTPException):
            status_code = error.status_code
            handler = self.get_handler(status_code)
            
            if handler:
                return handler(error, request_handler)
            
            return self._default_handle(error, request_handler)
        
        return self._default_handle(
            InternalServerError(description=str(error)), 
            request_handler
        )
    
    def _default_handle(self, error: HTTPException, request_handler):
        """
        默认错误处理
        
        Args:
            error: HTTP 异常
            request_handler: 请求处理器
            
        Returns:
            响应数据
        """
        return {
            'error': error.__class__.__name__,
            'status_code': error.status_code,
            'message': error.message,
            'description': error.description
        }, error.status_code, error.headers


# 全局错误处理器实例
error_handler = ErrorHandler()
