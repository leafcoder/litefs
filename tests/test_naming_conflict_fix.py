#!/usr/bin/env python
# coding: utf-8

"""
命名冲突修复验证测试

验证 EmailValidator 和 URLValidator 的命名冲突已修复
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from litefs import (
    EmailValidator,
    URLValidator,
    EmailFieldValidator,
    URLFieldValidator
)


def test_import_no_conflict():
    """测试导入无命名冲突"""
    # 验证 EmailValidator 来自 validators 模块
    assert EmailValidator.__module__ == 'litefs.validators', \
        f"EmailValidator 应该来自 litefs.validators，实际来自 {EmailValidator.__module__}"
    
    # 验证 URLValidator 来自 validators 模块
    assert URLValidator.__module__ == 'litefs.validators', \
        f"URLValidator 应该来自 litefs.validators，实际来自 {URLValidator.__module__}"
    
    # 验证 EmailFieldValidator 来自 forms 模块
    assert EmailFieldValidator.__module__ == 'litefs.forms', \
        f"EmailFieldValidator 应该来自 litefs.forms，实际来自 {EmailFieldValidator.__module__}"
    
    # 验证 URLFieldValidator 来自 forms 模块
    assert URLFieldValidator.__module__ == 'litefs.forms', \
        f"URLFieldValidator 应该来自 litefs.forms，实际来自 {URLFieldValidator.__module__}"
    
    print("✅ 所有导入验证通过！")
    print(f"  EmailValidator: {EmailValidator.__module__}")
    print(f"  URLValidator: {URLValidator.__module__}")
    print(f"  EmailFieldValidator: {EmailFieldValidator.__module__}")
    print(f"  URLFieldValidator: {URLFieldValidator.__module__}")


def test_validators_are_different():
    """测试验证器是不同的类"""
    # 验证 EmailValidator 和 EmailFieldValidator 是不同的类
    assert EmailValidator != EmailFieldValidator, \
        "EmailValidator 和 EmailFieldValidator 应该是不同的类"
    
    # 验证 URLValidator 和 URLFieldValidator 是不同的类
    assert URLValidator != URLFieldValidator, \
        "URLValidator 和 URLFieldValidator 应该是不同的类"
    
    print("✅ 验证器类区分验证通过！")


def test_validators_work_correctly():
    """测试验证器工作正常"""
    # 测试 EmailValidator
    email_validator = EmailValidator()
    assert email_validator.validate('test@example.com'), \
        "EmailValidator 应该验证有效的邮箱地址"
    
    # 测试 EmailFieldValidator
    email_field_validator = EmailFieldValidator()
    assert email_field_validator.validate('test@example.com'), \
        "EmailFieldValidator 应该验证有效的邮箱地址"
    
    # 测试 URLValidator
    url_validator = URLValidator()
    assert url_validator.validate('http://example.com'), \
        "URLValidator 应该验证有效的 URL"
    
    # 测试 URLFieldValidator
    url_field_validator = URLFieldValidator()
    assert url_field_validator.validate('http://example.com'), \
        "URLFieldValidator 应该验证有效的 URL"
    
    print("✅ 验证器功能验证通过！")


if __name__ == '__main__':
    print("=" * 60)
    print("命名冲突修复验证测试")
    print("=" * 60)
    print()
    
    test_import_no_conflict()
    print()
    
    test_validators_are_different()
    print()
    
    test_validators_work_correctly()
    print()
    
    print("=" * 60)
    print("所有测试通过！命名冲突已成功修复。")
    print("=" * 60)
