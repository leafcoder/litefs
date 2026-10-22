#!/usr/bin/env python
# coding: utf-8

"""
JSON 序列化抽象层测试

覆盖 :mod:`litefs._json` 的对外契约：

- ``dumps`` 返回 UTF-8 字节串，``dumps_str`` 返回字符串
- 与标准库 ``json`` 的行为对齐（非字符串字典键、``default=str`` 语义）
- 异常类型保持可捕获（``JSONDecodeError`` / ``JSONEncodeError``）
- 文件级 ``dump`` / ``load`` 的二进制读写
"""

import io
import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime

from litefs._json import (
    JSONDecodeError,
    JSONEncodeError,
    dump,
    dumps,
    dumps_ascii,
    dumps_str,
    load,
    loads,
)


@dataclass
class Sample:
    """用于验证 dataclass 序列化语义的样本类型"""

    a: int
    b: str


class TestDumps(unittest.TestCase):
    """序列化出口"""

    def test_dumps_returns_bytes(self):
        """dumps 返回 UTF-8 字节串"""
        result = dumps({"a": 1})
        self.assertIsInstance(result, bytes)
        self.assertEqual(result, b'{"a":1}')

    def test_dumps_str_returns_str(self):
        """dumps_str 返回字符串，且与 dumps 内容一致"""
        payload = {"a": 1, "b": "x"}
        self.assertIsInstance(dumps_str(payload), str)
        self.assertEqual(dumps_str(payload), dumps(payload).decode("utf-8"))

    def test_non_ascii_kept_unescaped(self):
        """非 ASCII 字符不转义，与标准库 ensure_ascii=False 语义一致"""
        result = dumps_str({"k": "中文"})
        self.assertEqual(result, '{"k":"中文"}')
        self.assertNotIn("\\u", result)
        self.assertEqual(
            loads(result),
            json.loads(json.dumps({"k": "中文"}, ensure_ascii=False)),
        )

    def test_non_str_keys_converted_like_stdlib(self):
        """非字符串字典键转字符串，与标准库默认行为一致"""
        payload = {1: "a", 2.5: "b", True: "c", None: "d"}
        self.assertEqual(
            loads(dumps(payload)),
            json.loads(json.dumps(payload)),
        )

    def test_datetime_uses_default_callback(self):
        """datetime 交由 default 回调处理，输出格式与标准库一致"""
        value = datetime(2026, 10, 22, 12, 30, 0)
        result = dumps_str({"d": value}, default=str)
        self.assertEqual(result, '{"d":"2026-10-22 12:30:00"}')
        self.assertEqual(
            loads(result),
            json.loads(json.dumps({"d": value}, default=str, ensure_ascii=False)),
        )

    def test_datetime_without_default_raises(self):
        """未提供 default 时 datetime 不可序列化，行为与标准库一致"""
        with self.assertRaises(TypeError):
            dumps({"d": datetime(2026, 10, 22, 12, 30, 0)})

    def test_dataclass_uses_default_callback(self):
        """dataclass 交由 default 回调处理，输出格式与标准库一致"""
        self.assertEqual(dumps_str({"x": Sample(1, "y")}, default=str), '{"x":"Sample(a=1, b=\'y\')"}')

    def test_set_uses_default_callback(self):
        """set 交由 default 回调处理"""
        self.assertEqual(loads(dumps({"s": {1, 2}}, default=str)), {"s": "{1, 2}"})

    def test_unserializable_raises_type_error(self):
        """不可序列化对象抛出 TypeError"""
        with self.assertRaises(TypeError):
            dumps({"s": {1, 2}})


class TestDumpsAscii(unittest.TestCase):
    """ASCII 安全序列化出口"""

    def test_output_is_pure_ascii(self):
        """输出不含任何非 ASCII 字符"""
        result = dumps_ascii({"chinese": "中文测试", "emoji": "😀"})
        self.assertTrue(result.isascii())

    def test_matches_stdlib_ensure_ascii(self):
        """与标准库 ensure_ascii=True 逐字节一致"""
        payload = {"chinese": "中文测试", "emoji": "😀😁", "s": "!@#$%^&*()"}
        self.assertEqual(
            dumps_ascii(payload),
            json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
        )

    def test_round_trip_preserves_content(self):
        """转义后仍可正确还原原始内容"""
        payload = {"chinese": "中文测试", "emoji": "😀😁😂"}
        self.assertEqual(loads(dumps_ascii(payload)), payload)

    def test_ascii_payload_unchanged(self):
        """纯 ASCII 输入不做多余转义"""
        self.assertEqual(dumps_ascii({"a": 1, "b": "x"}), '{"a":1,"b":"x"}')

    def test_control_characters_escaped(self):
        """控制符与 DEL 均转义为 \\uXXXX"""
        result = dumps_ascii({"c": "\x00\x1f\x7f"})
        self.assertEqual(result, '{"c":"\\u0000\\u001f\\u007f"}')
        self.assertEqual(loads(result), {"c": "\x00\x1f\x7f"})

    def test_astral_char_uses_surrogate_pair(self):
        """星平面字符转义为 UTF-16 代理对"""
        result = dumps_ascii({"e": "\U0001F600"})
        self.assertEqual(result, '{"e":"\\ud83d\\ude00"}')
        self.assertEqual(loads(result), {"e": "\U0001F600"})

    def test_escaped_backslash_not_double_escaped(self):
        """JSON 自身的转义序列不被二次转义"""
        result = dumps_ascii({"k": 'a\\b"c\nd'})
        self.assertEqual(loads(result), {"k": 'a\\b"c\nd'})


class TestLoads(unittest.TestCase):
    """反序列化出口"""

    def test_loads_accepts_bytes(self):
        """loads 接受字节串"""
        self.assertEqual(loads(b'{"a":1}'), {"a": 1})

    def test_loads_accepts_str(self):
        """loads 接受字符串"""
        self.assertEqual(loads('{"a":1}'), {"a": 1})

    def test_loads_accepts_bytearray(self):
        """loads 接受 bytearray"""
        self.assertEqual(loads(bytearray(b'{"a":1}')), {"a": 1})

    def test_loads_top_level_scalar(self):
        """loads 支持顶层标量"""
        self.assertEqual(loads(b"123"), 123)
        self.assertIsNone(loads(b"null"))

    def test_invalid_json_raises_decode_error(self):
        """非法 JSON 抛出 JSONDecodeError"""
        with self.assertRaises(JSONDecodeError):
            loads(b"{invalid}")


class TestExceptionCompatibility(unittest.TestCase):
    """异常类型与标准库的兼容关系"""

    def test_decode_error_is_stdlib_subclass(self):
        """JSONDecodeError 继承自标准库 json.JSONDecodeError"""
        self.assertTrue(issubclass(JSONDecodeError, json.JSONDecodeError))
        self.assertTrue(issubclass(JSONDecodeError, ValueError))

    def test_encode_error_is_type_error_subclass(self):
        """JSONEncodeError 继承自 TypeError"""
        self.assertTrue(issubclass(JSONEncodeError, TypeError))

    def test_stdlib_except_chain_still_works(self):
        """既有 except (TypeError, ValueError) 捕获链不受影响"""
        try:
            dumps({"s": {1, 2}})
        except (TypeError, ValueError) as e:
            self.assertIsInstance(e, TypeError)
        else:
            self.fail("应当抛出 TypeError")


class TestFileApi(unittest.TestCase):
    """文件级读写"""

    def test_dump_and_load_round_trip(self):
        """dump 写入的文件可被 load 读回"""
        payload = {"name": "tom", "age": 18, "tags": ["a", "b"]}
        buffer = io.BytesIO()
        dump(payload, buffer)
        buffer.seek(0)
        self.assertEqual(load(buffer), payload)

    def test_dump_writes_utf8_without_escaping(self):
        """dump 写入的是 UTF-8 原字符"""
        buffer = io.BytesIO()
        dump({"k": "中文"}, buffer)
        self.assertEqual(buffer.getvalue(), '{"k":"中文"}'.encode("utf-8"))

    def test_file_round_trip_on_disk(self):
        """磁盘文件读写往返一致"""
        payload = {"k": "中文", "n": 1}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "data.json")
            with open(path, "wb") as f:
                dump(payload, f)
            with open(path, "rb") as f:
                self.assertEqual(load(f), payload)


if __name__ == "__main__":
    unittest.main()
