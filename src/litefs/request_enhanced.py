#!/usr/bin/env python
# coding: utf-8

"""
增强的请求处理器

提供分离的 query 和 post 参数，以及表单验证功能
"""

from typing import Any, Dict, List, Optional, Tuple
from .validators import FormValidator, ValidationError


class EnhancedRequestHandler:
    """
    增强的请求处理器
    
    提供分离的 query 和 post 参数，以及表单验证功能
    """

    def __init__(self, request_handler):
        """
        初始化增强的请求处理器
        
        Args:
            request_handler: 原始请求处理器实例
        """
        self._request = request_handler
        self._form_validator: Optional[FormValidator] = None

    @property
    def query(self) -> Dict[str, Any]:
        """
        获取 URL 查询参数
        
        Returns:
            查询参数字典
        """
        return self._request.get

    @property
    def post(self) -> Dict[str, Any]:
        """
        获取 POST 请求体参数
        
        Returns:
            POST 参数字典
        """
        return self._request.post

    @property
    def files(self) -> Dict[str, Any]:
        """
        获取上传的文件
        
        Returns:
            文件字典
        """
        return self._request.files

    @property
    def body(self) -> str:
        """
        获取请求体
        
        Returns:
            请求体字符串
        """
        return self._request.body

    @property
    def json(self) -> Dict[str, Any]:
        """
        获取 JSON 请求体
        
        Returns:
            JSON 数据字典
        """
        return self._request.json

    @property
    def session(self):
        """
        获取会话对象
        
        Returns:
            会话对象
        """
        return self._request.session

    @property
    def session_id(self) -> Optional[str]:
        """
        获取会话 ID
        
        Returns:
            会话 ID
        """
        return self._request.session_id

    @property
    def environ(self) -> Dict[str, Any]:
        """
        获取环境变量
        
        Returns:
            环境变量字典
        """
        return self._request.environ

    @property
    def request_method(self) -> str:
        """
        获取请求方法
        
        Returns:
            请求方法（GET, POST, PUT, DELETE 等）
        """
        return self._request.request_method

    @property
    def content_type(self) -> Optional[str]:
        """
        获取内容类型
        
        Returns:
            内容类型
        """
        return self._request.content_type

    @property
    def content_length(self) -> int:
        """
        获取内容长度
        
        Returns:
            内容长度
        """
        return self._request.content_length

    @property
    def path_info(self) -> str:
        """
        获取路径信息
        
        Returns:
            路径信息
        """
        return self._request.path_info

    @property
    def query_string(self) -> str:
        """
        获取查询字符串
        
        Returns:
            查询字符串
        """
        return self._request.query_string

    @property
    def request_uri(self) -> str:
        """
        获取请求 URI
        
        Returns:
            请求 URI
        """
        return self._request.request_uri

    @property
    def referer(self) -> Optional[str]:
        """
        获取来源页面
        
        Returns:
            来源页面 URL
        """
        return self._request.referer

    @property
    def cookie(self):
        """
        获取 Cookie
        
        Returns:
            Cookie 对象
        """
        return self._request.cookie

    @property
    def config(self):
        """
        获取配置对象
        
        Returns:
            配置对象
        """
        return self._request.config

    def get_query_param(self, key: str, default: Any = None) -> Any:
        """
        获取单个查询参数
        
        Args:
            key: 参数名
            default: 默认值
        
        Returns:
            参数值
        """
        return self.query.get(key, default)

    def get_post_param(self, key: str, default: Any = None) -> Any:
        """
        获取单个 POST 参数
        
        Args:
            key: 参数名
            default: 默认值
        
        Returns:
            参数值
        """
        return self.post.get(key, default)

    def get_file(self, key: str, default: Any = None) -> Any:
        """
        获取单个上传文件
        
        Args:
            key: 文件字段名
            default: 默认值
        
        Returns:
            文件对象
        """
        return self.files.get(key, default)

    def set_form_validator(self, validator: FormValidator):
        """
        设置表单验证器
        
        Args:
            validator: 表单验证器实例
        """
        self._form_validator = validator

    def validate_query(self, rules: Dict[str, List]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        验证查询参数
        
        Args:
            rules: 验证规则字典 {字段名: [验证器列表]}
        
        Returns:
            (是否验证成功, 错误字典)
        """
        validator = FormValidator()
        for field_name, validators in rules.items():
            validator.add_field(field_name, validators)
        return validator.validate(self.query)

    def validate_post(self, rules: Dict[str, List]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        验证 POST 参数
        
        Args:
            rules: 验证规则字典 {字段名: [验证器列表]}
        
        Returns:
            (是否验证成功, 错误字典)
        """
        validator = FormValidator()
        for field_name, validators in rules.items():
            validator.add_field(field_name, validators)
        return validator.validate(self.post)

    def validate_files(self, rules: Dict[str, List]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        验证上传文件
        
        Args:
            rules: 验证规则字典 {字段名: [验证器列表]}
        
        Returns:
            (是否验证成功, 错误字典)
        """
        validator = FormValidator()
        for field_name, validators in rules.items():
            validator.add_field(field_name, validators)
        return validator.validate(self.files)

    def validate_all(
        self,
        query_rules: Optional[Dict[str, List]] = None,
        post_rules: Optional[Dict[str, List]] = None,
        file_rules: Optional[Dict[str, List]] = None,
    ) -> Tuple[bool, Dict[str, Dict[str, List[str]]]]:
        """
        验证所有参数
        
        Args:
            query_rules: 查询参数验证规则
            post_rules: POST 参数验证规则
            file_rules: 文件验证规则
        
        Returns:
            (是否验证成功, {参数类型: 错误字典})
        """
        all_valid = True
        all_errors: Dict[str, Dict[str, List[str]]] = {}

        if query_rules:
            query_valid, query_errors = self.validate_query(query_rules)
            all_valid = all_valid and query_valid
            all_errors["query"] = query_errors

        if post_rules:
            post_valid, post_errors = self.validate_post(post_rules)
            all_valid = all_valid and post_valid
            all_errors["post"] = post_errors

        if file_rules:
            files_valid, files_errors = self.validate_files(file_rules)
            all_valid = all_valid and files_valid
            all_errors["files"] = files_errors

        return all_valid, all_errors

    def start_response(self, status_code: int = 200, headers=None):
        """
        开始响应
        
        Args:
            status_code: HTTP 状态码
            headers: 响应头列表
        """
        self._request.start_response(status_code, headers)

    def set_cookie(self, key: str, value: str, **kwargs):
        """
        设置 Cookie
        
        Args:
            key: Cookie 名称
            value: Cookie 值
            **kwargs: 其他 Cookie 参数
        """
        self._request.set_cookie(key, value, **kwargs)


__all__ = [
    "EnhancedRequestHandler",
]
