#!/usr/bin/env python
# coding: utf-8

"""
表单验证模块

提供表单数据验证功能，支持多种验证规则。

验证器说明：
- 本模块的 Validator 子类用于命令式/程序化验证场景
- litefs.forms 模块的 Validator 子类用于 Form + Field 声明式表单验证场景
- ValidationError 统一使用 litefs.exceptions.ValidationError
"""

import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .exceptions import ValidationError


class Validator:
    """验证器基类"""

    def __init__(self, message: Optional[str] = None):
        self.message = message or "验证失败"

    def validate(self, value: Any, field_name: str = None) -> Any:
        """
        验证值
        
        Args:
            value: 要验证的值
            field_name: 字段名称
        
        Returns:
            验证后的值
        
        Raises:
            ValidationError: 验证失败
        """
        raise NotImplementedError("子类必须实现 validate 方法")


class RequiredValidator(Validator):
    """必填验证器"""

    def __init__(self, message: str = "此字段为必填项"):
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None or value == "":
            raise ValidationError(self.message, field_name)
        return value


class TypeValidator(Validator):
    """类型验证器"""

    def __init__(self, expected_type: type, message: Optional[str] = None):
        self.expected_type = expected_type
        if message is None:
            message = f"此字段必须为 {expected_type.__name__} 类型"
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is not None and not isinstance(value, self.expected_type):
            raise ValidationError(self.message, field_name)
        return value


class StringValidator(Validator):
    """字符串验证器"""

    def __init__(
        self,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        super().__init__(message or "字符串验证失败")

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValidationError("此字段必须为字符串", field_name)

        if self.min_length is not None and len(value) < self.min_length:
            raise ValidationError(
                f"字符串长度不能少于 {self.min_length} 个字符", field_name
            )

        if self.max_length is not None and len(value) > self.max_length:
            raise ValidationError(
                f"字符串长度不能超过 {self.max_length} 个字符", field_name
            )

        if self.pattern is not None and not self.pattern.match(value):
            raise ValidationError("字符串格式不正确", field_name)

        return value


class NumberValidator(Validator):
    """数字验证器"""

    def __init__(
        self,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        message: Optional[str] = None,
    ):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(message or "数字验证失败")

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None:
            return value

        if not isinstance(value, (int, float)):
            raise ValidationError("此字段必须为数字", field_name)

        if self.min_value is not None and value < self.min_value:
            raise ValidationError(
                f"数值不能小于 {self.min_value}", field_name
            )

        if self.max_value is not None and value > self.max_value:
            raise ValidationError(
                f"数值不能大于 {self.max_value}", field_name
            )

        return value


class EmailValidator(Validator):
    """邮箱验证器"""

    def __init__(
        self,
        message: str = "请输入有效的邮箱地址"
    ):
        self.pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValidationError("此字段必须为字符串", field_name)

        if not self.pattern.match(value):
            raise ValidationError(self.message, field_name)

        return value


class URLValidator(Validator):
    """URL 验证器"""

    def __init__(
        self,
        message: str = "请输入有效的 URL"
    ):
        self.pattern = re.compile(
            r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)$'
        )
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValidationError("此字段必须为字符串", field_name)

        if not self.pattern.match(value):
            raise ValidationError(self.message, field_name)

        return value


class ChoiceValidator(Validator):
    """选择验证器"""

    def __init__(
        self,
        choices: List[Any],
        message: Optional[str] = None,
    ):
        self.choices = choices
        if message is None:
            message = f"此字段必须为以下值之一: {', '.join(map(str, choices))}"
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None:
            return value

        if value not in self.choices:
            raise ValidationError(self.message, field_name)

        return value


class RegexValidator(Validator):
    """正则表达式验证器"""

    def __init__(
        self,
        pattern: str,
        message: str = "格式不正确"
    ):
        self.pattern = re.compile(pattern)
        super().__init__(message)

    def validate(self, value: Any, field_name: str = None) -> Any:
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValidationError("此字段必须为字符串", field_name)

        if not self.pattern.match(value):
            raise ValidationError(self.message, field_name)

        return value


class FormValidator:
    """表单验证器"""

    def __init__(self):
        self._validators: Dict[str, List[Validator]] = {}
        self._errors: List[ValidationError] = []

    def add_field(
        self,
        field_name: str,
        validators: Union[Validator, List[Validator]],
    ):
        """
        添加字段验证器
        
        Args:
            field_name: 字段名称
            validators: 验证器或验证器列表
        """
        if isinstance(validators, Validator):
            validators = [validators]
        self._validators[field_name] = validators

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, Dict[str, List[str]]]:
        """
        验证表单数据
        
        Args:
            data: 表单数据字典
        
        Returns:
            (是否验证成功, 错误字典)
        """
        self._errors = []
        errors: Dict[str, List[str]] = {}

        for field_name, validators in self._validators.items():
            field_errors = []
            value = data.get(field_name)

            for validator in validators:
                try:
                    validator.validate(value, field_name)
                except ValidationError as e:
                    field_errors.append(str(e))

            if field_errors:
                errors[field_name] = field_errors

        return len(errors) == 0, errors

    def get_errors(self) -> List[ValidationError]:
        """获取所有验证错误"""
        return self._errors


def required(message: str = "此字段为必填项") -> RequiredValidator:
    """必填验证器快捷函数"""
    return RequiredValidator(message)


def string_type(
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
    message: Optional[str] = None,
) -> StringValidator:
    """字符串验证器快捷函数"""
    return StringValidator(min_length, max_length, pattern, message)


def number_type(
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    message: Optional[str] = None,
) -> NumberValidator:
    """数字验证器快捷函数"""
    return NumberValidator(min_value, max_value, message)


def email(message: str = "请输入有效的邮箱地址") -> EmailValidator:
    """邮箱验证器快捷函数"""
    return EmailValidator(message)


def url(message: str = "请输入有效的 URL") -> URLValidator:
    """URL 验证器快捷函数"""
    return URLValidator(message)


def choice(choices: List[Any], message: Optional[str] = None) -> ChoiceValidator:
    """选择验证器快捷函数"""
    return ChoiceValidator(choices, message)


def regex(pattern: str, message: str = "格式不正确") -> RegexValidator:
    """正则表达式验证器快捷函数"""
    return RegexValidator(pattern, message)


__all__ = [
    "ValidationError",
    "Validator",
    "RequiredValidator",
    "TypeValidator",
    "StringValidator",
    "NumberValidator",
    "EmailValidator",
    "URLValidator",
    "ChoiceValidator",
    "RegexValidator",
    "FormValidator",
    "required",
    "string_type",
    "number_type",
    "email",
    "url",
    "choice",
    "regex",
]
