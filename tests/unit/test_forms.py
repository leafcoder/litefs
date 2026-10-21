#!/usr/bin/env python
# coding: utf-8

"""
表单验证系统测试

覆盖 litefs.forms 模块：Validator 系列、Field、Form 及内置示例表单。
"""

import unittest

from litefs.exceptions import ValidationError
from litefs.forms import (
    Required,
    Length,
    Email,
    URL,
    Number,
    Regex,
    Choice,
    Function,
    Field,
    LoginForm,
    RegistrationForm,
)


class TestValidators(unittest.TestCase):
    """测试各类验证器"""

    def test_validator_base_call(self):
        """验证器可通过 __call__ 触发 validate"""
        v = Required()
        self.assertTrue(v("ok"))
        with self.assertRaises(ValidationError):
            v("")

    def test_required_rejects_empty(self):
        """Required 拒绝 None、空字符串、空列表、空字典"""
        for value in (None, "", [], {}):
            with self.assertRaises(ValidationError):
                Required().validate(value)

    def test_required_accepts_non_empty(self):
        """Required 接受非空值（含 0/False 等假值）"""
        self.assertTrue(Required().validate(0))
        self.assertTrue(Required().validate(False))
        self.assertTrue(Required().validate([1]))

    def test_length_bounds(self):
        """Length 按字符串长度校验上下界"""
        v = Length(min_length=3, max_length=5)
        self.assertTrue(v.validate("abc"))
        self.assertTrue(v.validate("abcde"))
        with self.assertRaises(ValidationError):
            v.validate("ab")
        with self.assertRaises(ValidationError):
            v.validate("abcdef")

    def test_length_none_value_passes(self):
        """Length 对 None 值直接放行"""
        self.assertTrue(Length(min_length=3).validate(None))

    def test_length_custom_message(self):
        """Length 支持自定义错误消息"""
        v = Length(min_length=10, message="太短了")
        with self.assertRaises(ValidationError) as ctx:
            v.validate("ab")
        self.assertEqual(str(ctx.exception), "太短了")

    def test_email_valid_and_invalid(self):
        """Email 验证合法/非法地址"""
        v = Email()
        self.assertTrue(v.validate("user@example.com"))
        with self.assertRaises(ValidationError):
            v.validate("not-an-email")

    def test_email_empty_passes(self):
        """Email 对空值放行（空值由 Required 控制）"""
        self.assertTrue(Email().validate(""))
        self.assertTrue(Email().validate(None))

    def test_url_valid_and_invalid(self):
        """URL 验证合法/非法地址（严格模式要求域名带 TLD）"""
        v = URL()
        self.assertTrue(v.validate("https://example.com/path"))
        self.assertTrue(v.validate("http://www.example.com:8080/x"))
        with self.assertRaises(ValidationError):
            v.validate("ftp://example.com")
        with self.assertRaises(ValidationError):
            v.validate("not a url")

    def test_number_coerces_string(self):
        """Number 将字符串转换为数字后校验范围"""
        v = Number(min_value=0, max_value=150)
        self.assertTrue(v.validate("25"))
        self.assertTrue(v.validate(150))
        with self.assertRaises(ValidationError):
            v.validate("-1")
        with self.assertRaises(ValidationError):
            v.validate(151)

    def test_number_invalid_value(self):
        """Number 对无法转换的值报错"""
        with self.assertRaises(ValidationError):
            Number().validate("abc")

    def test_number_none_passes(self):
        """Number 对 None 放行"""
        self.assertTrue(Number(min_value=0).validate(None))

    def test_regex_validator(self):
        """Regex 按正则校验"""
        v = Regex(r"^[a-z]+$")
        self.assertTrue(v.validate("abc"))
        with self.assertRaises(ValidationError):
            v.validate("ABC")

    def test_regex_empty_passes(self):
        """Regex 对空值放行"""
        self.assertTrue(Regex(r"^[a-z]+$").validate(""))

    def test_choice_validator(self):
        """Choice 校验值是否在选项内"""
        v = Choice(["red", "green", "blue"])
        self.assertTrue(v.validate("red"))
        with self.assertRaises(ValidationError):
            v.validate("yellow")

    def test_choice_none_passes(self):
        """Choice 对 None 放行"""
        self.assertTrue(Choice(["a"]).validate(None))

    def test_function_validator(self):
        """Function 使用自定义函数校验"""
        v = Function(lambda x: x > 10, message="必须大于10")
        self.assertTrue(v.validate(11))
        with self.assertRaises(ValidationError) as ctx:
            v.validate(5)
        self.assertEqual(str(ctx.exception), "必须大于10")


class TestField(unittest.TestCase):
    """测试表单字段"""

    def test_field_required_missing(self):
        """必填字段缺失时校验失败并记录错误"""
        field = Field(required=True)
        self.assertFalse(field.validate(None))
        self.assertEqual(len(field.errors), 1)

    def test_field_required_passes(self):
        """必填字段有值时校验通过"""
        field = Field(required=True)
        self.assertTrue(field.validate("hello"))
        self.assertEqual(field.value, "hello")

    def test_field_default_used_when_none(self):
        """值为 None 时使用默认值"""
        field = Field(default="fallback")
        self.assertTrue(field.validate(None))
        self.assertEqual(field.value, "fallback")

    def test_field_optional_empty_skips_validators(self):
        """非必填字段为空时跳过其他验证器"""
        field = Field(validators=[Length(min_length=100)])
        self.assertTrue(field.validate(""))
        self.assertTrue(field.validate(None))

    def test_field_collects_multiple_errors(self):
        """字段校验收集所有验证器错误而不中断"""
        field = Field(validators=[Length(min_length=5), Regex(r"^[a-z]+$")])
        self.assertFalse(field.validate("ab1"))
        self.assertEqual(len(field.errors), 2)

    def test_field_validator_error_messages_appended(self):
        """验证器错误消息被记录到 errors"""
        field = Field(validators=[Length(min_length=5)])
        field.validate("ab")
        self.assertTrue(field.errors)


class TestForm(unittest.TestCase):
    """测试表单基类"""

    def test_form_field_discovery(self):
        """Form 自动发现类属性中的 Field"""
        form = LoginForm()
        self.assertIn("username", form._fields)
        self.assertIn("password", form._fields)
        self.assertIn("email", form._fields)

    def test_form_valid_data(self):
        """合法数据校验通过且 data 返回字段值"""
        form = LoginForm(data={"username": "admin", "password": "secret123"})
        self.assertTrue(form.validate())
        self.assertEqual(form.errors, {})
        self.assertEqual(form.get("username"), "admin")

    def test_form_invalid_required(self):
        """必填字段缺失时校验失败"""
        form = LoginForm(data={"username": "", "password": ""})
        self.assertFalse(form.validate())
        self.assertIn("username", form.errors)
        self.assertIn("password", form.errors)

    def test_form_invalid_length(self):
        """字段长度不符合要求时校验失败"""
        form = LoginForm(data={"username": "ab", "password": "123"})
        self.assertFalse(form.validate())

    def test_form_optional_email_invalid(self):
        """非必填字段提供了非法值时校验失败"""
        form = LoginForm(
            data={"username": "admin", "password": "secret123", "email": "bad"}
        )
        self.assertFalse(form.validate())
        self.assertIn("email", form.errors)

    def test_form_get_missing_field(self):
        """get 不存在的字段返回默认值"""
        form = LoginForm()
        self.assertIsNone(form.get("nope"))
        self.assertEqual(form.get("nope", "dft"), "dft")

    def test_registration_form_password_mismatch(self):
        """注册表单密码确认不一致时校验失败"""
        form = RegistrationForm(data={
            "username": "admin_1",
            "email": "a@example.com",
            "password": "password123",
            "confirm_password": "different",
        })
        self.assertFalse(form.validate())
        self.assertIn("confirm_password", form.errors)
        self.assertEqual(form.errors["confirm_password"], ["Passwords do not match"])

    def test_registration_form_success(self):
        """注册表单合法数据（含年龄范围）校验通过"""
        form = RegistrationForm(data={
            "username": "admin_1",
            "email": "a@example.com",
            "password": "password123",
            "confirm_password": "password123",
            "age": "30",
        })
        self.assertTrue(form.validate())
        self.assertEqual(form.get("age"), "30")


if __name__ == "__main__":
    unittest.main()
