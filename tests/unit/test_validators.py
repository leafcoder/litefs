#!/usr/bin/env python
# coding: utf-8

"""
表单验证功能测试
"""

import unittest

from litefs.validators import (
    ValidationError,
    RequiredValidator,
    TypeValidator,
    StringValidator,
    NumberValidator,
    EmailValidator,
    URLValidator,
    ChoiceValidator,
    RegexValidator,
    FormValidator,
    required,
    string_type,
    number_type,
    email,
    url,
    choice,
    regex,
)


class TestRequiredValidator(unittest.TestCase):
    """测试必填验证器"""

    def test_valid_value(self):
        """测试有效值"""
        validator = RequiredValidator()
        result = validator.validate("test", "field")
        self.assertEqual(result, "test")

    def test_empty_string(self):
        """测试空字符串"""
        validator = RequiredValidator()
        with self.assertRaises(ValidationError):
            validator.validate("", "field")

    def test_none_value(self):
        """测试 None 值"""
        validator = RequiredValidator()
        with self.assertRaises(ValidationError):
            validator.validate(None, "field")


class TestStringValidator(unittest.TestCase):
    """测试字符串验证器"""

    def test_valid_string(self):
        """测试有效字符串"""
        validator = StringValidator(min_length=3, max_length=10)
        result = validator.validate("hello", "field")
        self.assertEqual(result, "hello")

    def test_too_short(self):
        """测试字符串过短"""
        validator = StringValidator(min_length=5)
        with self.assertRaises(ValidationError):
            validator.validate("abc", "field")

    def test_too_long(self):
        """测试字符串过长"""
        validator = StringValidator(max_length=5)
        with self.assertRaises(ValidationError):
            validator.validate("abcdef", "field")

    def test_pattern_match(self):
        """测试正则匹配"""
        validator = StringValidator(pattern=r"^\d+$")
        with self.assertRaises(ValidationError):
            validator.validate("abc", "field")

    def test_pattern_success(self):
        """测试正则成功"""
        validator = StringValidator(pattern=r"^\d+$")
        result = validator.validate("123", "field")
        self.assertEqual(result, "123")


class TestNumberValidator(unittest.TestCase):
    """测试数字验证器"""

    def test_valid_number(self):
        """测试有效数字"""
        validator = NumberValidator(min_value=0, max_value=100)
        result = validator.validate(50, "field")
        self.assertEqual(result, 50)

    def test_too_small(self):
        """测试数字过小"""
        validator = NumberValidator(min_value=10)
        with self.assertRaises(ValidationError):
            validator.validate(5, "field")

    def test_too_large(self):
        """测试数字过大"""
        validator = NumberValidator(max_value=100)
        with self.assertRaises(ValidationError):
            validator.validate(150, "field")

    def test_float_value(self):
        """测试浮点数"""
        validator = NumberValidator()
        result = validator.validate(3.14, "field")
        self.assertEqual(result, 3.14)


class TestEmailValidator(unittest.TestCase):
    """测试邮箱验证器"""

    def test_valid_email(self):
        """测试有效邮箱"""
        validator = EmailValidator()
        result = validator.validate("test@example.com", "field")
        self.assertEqual(result, "test@example.com")

    def test_invalid_email(self):
        """测试无效邮箱"""
        validator = EmailValidator()
        with self.assertRaises(ValidationError):
            validator.validate("invalid-email", "field")


class TestURLValidator(unittest.TestCase):
    """测试 URL 验证器"""

    def test_valid_url(self):
        """测试有效 URL"""
        validator = URLValidator()
        result = validator.validate("https://example.com", "field")
        self.assertEqual(result, "https://example.com")

    def test_invalid_url(self):
        """测试无效 URL"""
        validator = URLValidator()
        with self.assertRaises(ValidationError):
            validator.validate("not-a-url", "field")


class TestChoiceValidator(unittest.TestCase):
    """测试选择验证器"""

    def test_valid_choice(self):
        """测试有效选择"""
        validator = ChoiceValidator(choices=["a", "b", "c"])
        result = validator.validate("b", "field")
        self.assertEqual(result, "b")

    def test_invalid_choice(self):
        """测试无效选择"""
        validator = ChoiceValidator(choices=["a", "b", "c"])
        with self.assertRaises(ValidationError):
            validator.validate("d", "field")


class TestRegexValidator(unittest.TestCase):
    """测试正则表达式验证器"""

    def test_valid_pattern(self):
        """测试有效模式"""
        validator = RegexValidator(pattern=r"^\d{4}$")
        result = validator.validate("1234", "field")
        self.assertEqual(result, "1234")

    def test_invalid_pattern(self):
        """测试无效模式"""
        validator = RegexValidator(pattern=r"^\d{4}$")
        with self.assertRaises(ValidationError):
            validator.validate("abc", "field")


class TestFormValidator(unittest.TestCase):
    """测试表单验证器"""

    def test_valid_form(self):
        """测试有效表单"""
        validator = FormValidator()
        validator.add_field("username", [string_type(min_length=3, max_length=20)])
        validator.add_field("age", [number_type(min_value=0, max_value=120)])
        validator.add_field("email", [email()])

        data = {
            "username": "john",
            "age": 25,
            "email": "john@example.com",
        }

        is_valid, errors = validator.validate(data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_invalid_form(self):
        """测试无效表单"""
        validator = FormValidator()
        validator.add_field("username", [string_type(min_length=3, max_length=20)])
        validator.add_field("age", [number_type(min_value=0, max_value=120)])
        validator.add_field("email", [email()])

        data = {
            "username": "jo",
            "age": 150,
            "email": "invalid-email",
        }

        is_valid, errors = validator.validate(data)
        self.assertFalse(is_valid)
        self.assertIn("username", errors)
        self.assertIn("age", errors)
        self.assertIn("email", errors)

    def test_missing_required_field(self):
        """测试缺少必填字段"""
        validator = FormValidator()
        validator.add_field("username", [required()])

        data = {}

        is_valid, errors = validator.validate(data)
        self.assertFalse(is_valid)
        self.assertIn("username", errors)


class TestShortcutFunctions(unittest.TestCase):
    """测试快捷函数"""

    def test_required_shortcut(self):
        """测试必填快捷函数"""
        validator = required()
        self.assertIsInstance(validator, RequiredValidator)

    def test_string_shortcut(self):
        """测试字符串快捷函数"""
        validator = string_type(min_length=5, max_length=10)
        self.assertIsInstance(validator, StringValidator)
        self.assertEqual(validator.min_length, 5)
        self.assertEqual(validator.max_length, 10)

    def test_number_shortcut(self):
        """测试数字快捷函数"""
        validator = number_type(min_value=0, max_value=100)
        self.assertIsInstance(validator, NumberValidator)
        self.assertEqual(validator.min_value, 0)
        self.assertEqual(validator.max_value, 100)

    def test_email_shortcut(self):
        """测试邮箱快捷函数"""
        validator = email()
        self.assertIsInstance(validator, EmailValidator)

    def test_url_shortcut(self):
        """测试 URL 快捷函数"""
        validator = url()
        self.assertIsInstance(validator, URLValidator)

    def test_choice_shortcut(self):
        """测试选择快捷函数"""
        validator = choice(["a", "b", "c"])
        self.assertIsInstance(validator, ChoiceValidator)
        self.assertEqual(validator.choices, ["a", "b", "c"])

    def test_regex_shortcut(self):
        """测试正则快捷函数"""
        validator = regex(r"^\d+$")
        self.assertIsInstance(validator, RegexValidator)


if __name__ == '__main__':
    unittest.main()
