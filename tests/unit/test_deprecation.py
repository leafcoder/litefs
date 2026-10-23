#!/usr/bin/env python
# coding: utf-8

"""
弃用机制测试

覆盖 :mod:`litefs.deprecation` 的消息格式化、告警发出、
装饰器行为，以及与 :mod:`litefs._stable` 废弃登记表的联动。
"""

import unittest
import warnings

from litefs.deprecation import (
    LitefsDeprecationWarning,
    deprecated,
    format_deprecation_message,
    warn_deprecated,
)


class TestDeprecationMessage(unittest.TestCase):
    """告警消息格式"""

    def test_message_contains_all_four_elements(self):
        """消息包含宣告版本、移除版本、替代符号与原因"""
        message = format_deprecation_message(
            "litefs.core:Litefs.session",
            since="0.10.0",
            removal="1.3.0",
            replacement="Litefs.db_session",
            reason="命名冲突",
        )
        self.assertIn("litefs.core:Litefs.session", message)
        self.assertIn("0.10.0", message)
        self.assertIn("1.3.0", message)
        self.assertIn("Litefs.db_session", message)
        self.assertIn("命名冲突", message)

    def test_message_without_optional_elements(self):
        """缺省信息时消息仍然合法"""
        message = format_deprecation_message("litefs.x:y")
        self.assertIn("litefs.x:y", message)
        self.assertTrue(message.endswith("。"))


class TestWarnDeprecated(unittest.TestCase):
    """告警发出"""

    def test_emits_warning(self):
        """调用时抛出 LitefsDeprecationWarning"""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warn_deprecated(
                "litefs.test:func",
                since="0.10.0",
                removal="1.3.0",
                replacement="litefs.test:new_func",
            )
        self.assertEqual(len(caught), 1)
        self.assertTrue(issubclass(caught[0].category, LitefsDeprecationWarning))

    def test_falls_back_to_registry(self):
        """未显式给出的信息从废弃登记表回填"""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warn_deprecated("litefs.core:Litefs.session")
        self.assertEqual(len(caught), 1)
        message = str(caught[0].message)
        self.assertIn("0.10.0", message)
        self.assertIn("1.3.0", message)
        self.assertIn("Litefs.db_session", message)

    def test_warning_is_deprecation_warning_subclass(self):
        """自定义告警继承自标准库 DeprecationWarning"""
        self.assertTrue(issubclass(LitefsDeprecationWarning, DeprecationWarning))


class TestDeprecatedDecorator(unittest.TestCase):
    """装饰器行为"""

    def test_emits_warning_on_call(self):
        """被装饰函数被调用时发出告警"""
        calls = []

        @deprecated(since="0.10.0", removal="1.3.0", replacement="new_func")
        def old_func(value):
            calls.append(value)
            return value * 2

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = old_func(3)
        self.assertEqual(result, 6)
        self.assertEqual(calls, [3])
        self.assertEqual(len(caught), 1)
        self.assertIn("new_func", str(caught[0].message))

    def test_preserves_metadata(self):
        """装饰器保留原函数元数据"""
        @deprecated(since="0.10.0")
        def documented_func():
            """原始文档字符串"""
            return 1

        self.assertEqual(documented_func.__name__, "documented_func")
        self.assertEqual(documented_func.__doc__, "原始文档字符串")
        self.assertTrue(documented_func.__deprecated__)
        self.assertTrue(
            documented_func.__deprecation_target__.endswith(":documented_func"),
            documented_func.__deprecation_target__,
        )

    def test_no_warning_at_import_time(self):
        """导入期不告警，仅调用时告警"""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")

            @deprecated(since="0.10.0")
            def another_func():
                return 2

        self.assertEqual(len(caught), 0)


class TestRegisteredDeprecations(unittest.TestCase):
    """与废弃登记表联动"""

    def test_litefs_session_method_is_deprecated(self):
        """Litefs.session() 已接入统一的弃用机制"""
        from litefs.core import Litefs

        self.assertTrue(getattr(Litefs.session, "__deprecated__", False))
        self.assertEqual(
            getattr(Litefs.session, "__deprecation_target__", None),
            "litefs.core:Litefs.session",
        )

    def test_litefs_session_emits_warning(self):
        """调用已废弃方法时发出带替代方案的告警"""
        from litefs.core import Litefs

        app = Litefs(debug=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                app.session("default")
            except Exception:
                # 无数据库连接时业务异常可接受，此处只校验告警已发出
                pass
        messages = [str(item.message) for item in caught]
        self.assertTrue(
            any("Litefs.db_session" in message for message in messages),
            "未产生包含替代方案的弃用告警: %s" % messages,
        )


if __name__ == "__main__":
    unittest.main()
