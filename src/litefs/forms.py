#!/usr/bin/env python
# coding: utf-8

"""
表单验证系统

提供强大的表单验证功能
"""

import re
from typing import Any, Optional, List, Dict, Callable
from datetime import datetime


class ValidationError(Exception):
    """验证错误异常"""
    
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class Validator:
    """验证器基类"""
    
    def __init__(self, message: Optional[str] = None):
        self.message = message
    
    def validate(self, value: Any) -> bool:
        """
        验证值
        
        Args:
            value: 要验证的值
            
        Returns:
            是否通过验证
            
        Raises:
            ValidationError: 验证失败
        """
        raise NotImplementedError
    
    def __call__(self, value: Any) -> bool:
        """使验证器可调用"""
        return self.validate(value)


class Required(Validator):
    """必填验证器"""
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "This field is required")
    
    def validate(self, value: Any) -> bool:
        if value is None or value == '' or (isinstance(value, (list, dict)) and len(value) == 0):
            raise ValidationError(self.message)
        return True


class Length(Validator):
    """长度验证器"""
    
    def __init__(
        self, 
        min_length: Optional[int] = None, 
        max_length: Optional[int] = None,
        message: Optional[str] = None
    ):
        self.min_length = min_length
        self.max_length = max_length
        super().__init__(message)
    
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        
        length = len(str(value))
        
        if self.min_length is not None and length < self.min_length:
            message = self.message or f"Length must be at least {self.min_length} characters"
            raise ValidationError(message)
        
        if self.max_length is not None and length > self.max_length:
            message = self.message or f"Length must be at most {self.max_length} characters"
            raise ValidationError(message)
        
        return True


class Email(Validator):
    """邮箱验证器"""
    
    PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "Invalid email address")
    
    def validate(self, value: Any) -> bool:
        if not value:
            return True
        
        if not self.PATTERN.match(str(value)):
            raise ValidationError(self.message)
        
        return True


class URL(Validator):
    """URL 验证器"""
    
    PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "Invalid URL")
    
    def validate(self, value: Any) -> bool:
        if not value:
            return True
        
        if not self.PATTERN.match(str(value)):
            raise ValidationError(self.message)
        
        return True


class Number(Validator):
    """数字验证器"""
    
    def __init__(
        self, 
        min_value: Optional[float] = None, 
        max_value: Optional[float] = None,
        message: Optional[str] = None
    ):
        self.min_value = min_value
        self.max_value = max_value
        super().__init__(message)
    
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        
        try:
            num = float(value)
        except (ValueError, TypeError):
            raise ValidationError(self.message or "Must be a number")
        
        if self.min_value is not None and num < self.min_value:
            raise ValidationError(self.message or f"Must be at least {self.min_value}")
        
        if self.max_value is not None and num > self.max_value:
            raise ValidationError(self.message or f"Must be at most {self.max_value}")
        
        return True


class Regex(Validator):
    """正则表达式验证器"""
    
    def __init__(self, pattern: str, message: Optional[str] = None):
        self.pattern = re.compile(pattern)
        super().__init__(message or "Invalid format")
    
    def validate(self, value: Any) -> bool:
        if not value:
            return True
        
        if not self.pattern.match(str(value)):
            raise ValidationError(self.message)
        
        return True


class Choice(Validator):
    """选择验证器"""
    
    def __init__(self, choices: List[Any], message: Optional[str] = None):
        self.choices = choices
        super().__init__(message or f"Must be one of: {', '.join(map(str, choices))}")
    
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        
        if value not in self.choices:
            raise ValidationError(self.message)
        
        return True


class Function(Validator):
    """自定义函数验证器"""
    
    def __init__(self, func: Callable[[Any], bool], message: Optional[str] = None):
        self.func = func
        super().__init__(message or "Validation failed")
    
    def validate(self, value: Any) -> bool:
        if not self.func(value):
            raise ValidationError(self.message)
        return True


class Field:
    """
    表单字段
    
    用于定义表单字段和验证规则
    """
    
    def __init__(
        self, 
        label: Optional[str] = None,
        required: bool = False,
        validators: Optional[List[Validator]] = None,
        default: Any = None
    ):
        """
        初始化字段
        
        Args:
            label: 字段标签
            required: 是否必填
            validators: 验证器列表
            default: 默认值
        """
        self.label = label
        self.required = required
        self.validators = validators or []
        self.default = default
        self.errors: List[str] = []
        self.value: Any = None
    
    def validate(self, value: Any) -> bool:
        """
        验证字段值
        
        Args:
            value: 字段值
            
        Returns:
            是否通过验证
        """
        self.errors = []
        self.value = value if value is not None else self.default
        
        # 必填验证
        if self.required:
            try:
                Required().validate(self.value)
            except ValidationError as e:
                self.errors.append(e.message)
                return False
        
        # 如果值为空且非必填，跳过其他验证
        if self.value is None or self.value == '':
            return True
        
        # 执行其他验证器
        for validator in self.validators:
            try:
                validator.validate(self.value)
            except ValidationError as e:
                self.errors.append(e.message)
        
        return len(self.errors) == 0


class Form:
    """
    表单基类
    
    用于定义和验证表单
    """
    
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        """
        初始化表单
        
        Args:
            data: 表单数据
        """
        self._data = data or {}
        self._fields: Dict[str, Field] = {}
        self._errors: Dict[str, List[str]] = {}
        
        # 自动发现字段
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, Field):
                self._fields[name] = attr
    
    def validate(self) -> bool:
        """
        验证整个表单
        
        Returns:
            是否通过验证
        """
        self._errors = {}
        
        for name, field in self._fields.items():
            value = self._data.get(name)
            
            if not field.validate(value):
                self._errors[name] = field.errors
        
        return len(self._errors) == 0
    
    @property
    def errors(self) -> Dict[str, List[str]]:
        """获取所有错误"""
        return self._errors
    
    @property
    def data(self) -> Dict[str, Any]:
        """获取所有字段值"""
        return {name: field.value for name, field in self._fields.items()}
    
    def get(self, name: str, default: Any = None) -> Any:
        """
        获取字段值
        
        Args:
            name: 字段名
            default: 默认值
            
        Returns:
            字段值
        """
        field = self._fields.get(name)
        return field.value if field else default


class LoginForm(Form):
    """登录表单示例"""
    
    username = Field(
        label='Username',
        required=True,
        validators=[Length(min_length=3, max_length=20)]
    )
    
    password = Field(
        label='Password',
        required=True,
        validators=[Length(min_length=6)]
    )
    
    email = Field(
        label='Email',
        required=False,
        validators=[Email()]
    )


class RegistrationForm(Form):
    """注册表单示例"""
    
    username = Field(
        label='Username',
        required=True,
        validators=[
            Length(min_length=3, max_length=20),
            Regex(r'^[a-zA-Z0-9_]+$', message="Username can only contain letters, numbers and underscores")
        ]
    )
    
    email = Field(
        label='Email',
        required=True,
        validators=[Email()]
    )
    
    password = Field(
        label='Password',
        required=True,
        validators=[Length(min_length=8, max_length=100)]
    )
    
    confirm_password = Field(
        label='Confirm Password',
        required=True
    )
    
    age = Field(
        label='Age',
        required=False,
        validators=[Number(min_value=0, max_value=150)]
    )
    
    def validate(self) -> bool:
        """验证表单，包括密码确认"""
        if not super().validate():
            return False
        
        # 自定义验证：密码确认
        if self.password.value != self.confirm_password.value:
            self._errors['confirm_password'] = ['Passwords do not match']
            return False
        
        return True
