#!/usr/bin/env python
# coding: utf-8

"""
表单数据解析测试

覆盖 parse_header、parse_form（含缓存、数组/字典语法与冲突处理）
以及三种 multipart 解析器（WSGI / ASGI / 流式）。
"""

import io
import unittest

from litefs.exceptions import HttpError
from litefs.handlers.form import (
    parse_form,
    parse_header,
    parse_multipart_asgi,
    parse_multipart_stream,
    parse_multipart_wsgi,
)


class TestParseHeader(unittest.TestCase):
    """parse_header 头部参数解析"""

    def test_simple_content_type(self):
        """无参数时返回空参数字典"""
        mime_type, params = parse_header('text/html')
        self.assertEqual(mime_type, 'text/html')
        self.assertEqual(params, {})

    def test_content_type_with_params(self):
        """解析 charset 等参数"""
        mime_type, params = parse_header('text/html; charset=utf-8')
        self.assertEqual(mime_type, 'text/html')
        self.assertEqual(params.get('charset'), 'utf-8')


class TestParseForm(unittest.TestCase):
    """parse_form 表单解析"""

    def test_simple_pairs(self):
        """基本键值对解析"""
        self.assertEqual(parse_form('a=1&b=2'), {'a': '1', 'b': '2'})

    def test_bytes_input(self):
        """bytes 输入自动解码"""
        self.assertEqual(parse_form(b'a=1&b=2'), {'a': '1', 'b': '2'})

    def test_url_decoding(self):
        """URL 编码与 + 号解码"""
        form = parse_form('name=%E4%B8%AD%E6%96%87&city=New+York')
        self.assertEqual(form, {'name': '中文', 'city': 'New York'})

    def test_empty_segments_and_missing_value(self):
        """空片段跳过，缺等号的键值为空串"""
        self.assertEqual(parse_form('a=1&&b'), {'a': '1', 'b': ''})

    def test_repeated_key_becomes_list(self):
        """普通键重复出现合并为列表"""
        self.assertEqual(parse_form('tag=one&tag=two'), {'tag': ['one', 'two']})

    def test_array_suffix_appends(self):
        """k[] 语法收集为列表"""
        self.assertEqual(parse_form('tag[]=one&tag[]=two'), {'tag': ['one', 'two']})

    def test_array_suffix_after_scalar(self):
        """先普通后 [] 语法时合并为 [标量, 追加值]"""
        self.assertEqual(parse_form('tag=one&tag[]=two'), {'tag': ['one', 'two']})

    def test_dict_syntax(self):
        """k[sub] 语法解析为嵌套字典"""
        self.assertEqual(parse_form('user[name]=alice&user[age]=18'),
                         {'user': {'name': 'alice', 'age': '18'}})

    def test_dict_syntax_duplicate_sub_key(self):
        """嵌套字典重复子键合并为列表"""
        self.assertEqual(parse_form('user[tag]=a&user[tag]=b'),
                         {'user': {'tag': ['a', 'b']}})

    def test_scalar_conflicts_with_dict(self):
        """同名键先标量后字典语法抛 ValueError"""
        with self.assertRaises(ValueError):
            parse_form('user=alice&user[age]=18')

    def test_dict_conflicts_with_array(self):
        """同名键先字典后 [] 语法抛 ValueError"""
        with self.assertRaises(ValueError):
            parse_form('user[age]=18&user[]=alice')

    def test_array_suffix_then_scalar_appends(self):
        """先 [] 后普通键时标量追加进列表"""
        self.assertEqual(parse_form('tag[]=one&tag=two'), {'tag': ['one', 'two']})

    def test_array_suffix_conflicts_with_dict(self):
        """同名键先字典后 [] 语法抛 ValueError"""
        with self.assertRaises(ValueError):
            parse_form('user[age]=18&user[]=alice')

    def test_cache_hit_returns_same_object(self):
        """相同查询串命中缓存返回同一对象"""
        query = 'cache-test=unique-value-12345'
        first = parse_form(query)
        second = parse_form(query)
        self.assertIs(first, second)


class TestParseMultipartWSGI(unittest.TestCase):
    """parse_multipart_wsgi 解析器"""

    @staticmethod
    def _body():
        return (
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'\r\n'
            b'hello world\r\n'
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="up"; filename="a.txt"\r\n'
            b'Content-Type: text/plain\r\n'
            b'\r\n'
            b'file-bytes\r\n'
            b'--BOUNDARY--\r\n'
        )

    def test_parses_fields_and_files(self):
        """解析普通字段与上传文件"""
        stream = io.BytesIO(self._body())
        posts, files = parse_multipart_wsgi(stream, 'BOUNDARY', stream.getbuffer().nbytes)
        self.assertEqual(posts, {'title': 'hello world'})
        self.assertIn('up', files)
        # 边界分隔符前的 CRLF 属于分隔符，不计入文件内容（RFC 2046）
        self.assertEqual(files['up'].read(), b'file-bytes')
        files['up'].close()

    def test_oversized_body_raises_413(self):
        """超过 max_upload_size 抛 413"""
        with self.assertRaises(HttpError) as ctx:
            parse_multipart_wsgi(io.BytesIO(b''), 'B', 100, max_upload_size=10)
        self.assertEqual(ctx.exception.status_code, 413)

    def test_part_without_headers_skipped(self):
        """缺少头部分隔的片段被跳过"""
        body = b'--BOUNDARY\r\n--BOUNDARY--\r\n'
        posts, files = parse_multipart_wsgi(io.BytesIO(body), 'BOUNDARY', len(body))
        self.assertEqual(posts, {})
        self.assertEqual(files, {})


class TestParseMultipartASGI(unittest.TestCase):
    """parse_multipart_asgi 解析器"""

    def test_parses_fields_and_files(self):
        """解析普通字段与上传文件"""
        body = (
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="note"\r\n'
            b'\r\n'
            b'memo text\r\n'
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="doc"; filename="d.bin"\r\n'
            b'\r\n'
            b'\x00\x01\x02\r\n'
            b'--BOUNDARY--\r\n'
        )
        posts, files = parse_multipart_asgi(body, 'BOUNDARY')
        self.assertEqual(posts, {'note': 'memo text'})
        # 边界分隔符前的 CRLF 属于分隔符，不计入文件内容（RFC 2046）
        self.assertEqual(files['doc'].read(), b'\x00\x01\x02')
        files['doc'].close()

    def test_oversized_body_raises_413(self):
        """超过 max_upload_size 抛 413"""
        with self.assertRaises(HttpError) as ctx:
            parse_multipart_asgi(b'x' * 20, 'B', max_upload_size=10)
        self.assertEqual(ctx.exception.status_code, 413)


class TestParseMultipartStream(unittest.TestCase):
    """parse_multipart_stream 流式解析器"""

    @staticmethod
    def _body():
        return (
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'\r\n'
            b'hello stream\r\n'
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="up"; filename="s.txt"\r\n'
            b'\r\n'
            b'stream-bytes\r\n'
            b'--BOUNDARY--\r\n'
        )

    def test_parses_fields_and_files(self):
        """流式解析普通字段与上传文件"""
        stream = io.BytesIO(self._body())
        posts, files = parse_multipart_stream(stream, 'BOUNDARY')
        self.assertEqual(posts, {'title': 'hello stream'})
        # 边界分隔符前的 CRLF 属于分隔符，不计入文件内容（RFC 2046）
        self.assertEqual(files['up'].read(), b'stream-bytes')
        files['up'].close()

    def test_unexpected_start_returns_empty(self):
        """起始边界不匹配时宽容返回空结果（与 WSGI/ASGI 路径行为一致）"""
        posts, files = parse_multipart_stream(io.BytesIO(b'not-boundary\r\n'), 'BOUNDARY')
        self.assertEqual(posts, {})
        self.assertEqual(files, {})


class TestMultipartHardening(unittest.TestCase):
    """multipart 解析加固（对应代码审计 4.4 节 0.12-⭐1，D4）"""

    @staticmethod
    def _field_body(value_bytes):
        return (
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="title"\r\n'
            b'\r\n' + value_bytes + b'\r\n'
            b'--BOUNDARY--\r\n'
        )

    def test_content_with_boundary_like_sequence(self):
        """文件内容包含类边界字节序列不破坏解析（CRLF 前缀校验，D4-2）"""
        body = (
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="up"; filename="a.bin"\r\n'
            b'\r\n'
            b'EMBED--BOUNDARY-INSIDE\r\n'
            b'--BOUNDARY--\r\n'
        )
        posts, files = parse_multipart_asgi(body, 'BOUNDARY')
        self.assertEqual(posts, {})
        self.assertEqual(files['up'].read(), b'EMBED--BOUNDARY-INSIDE')
        files['up'].close()

    def test_field_value_whitespace_preserved(self):
        """字段值保留合法前后空白（不再 strip，D4-3）"""
        posts, files = parse_multipart_asgi(self._field_body(b'  spaced value  '), 'BOUNDARY')
        self.assertEqual(posts, {'title': '  spaced value  '})
        self.assertEqual(files, {})

    def test_multiline_field_value(self):
        """多行字段值完整保留"""
        posts, files = parse_multipart_asgi(
            self._field_body(b'line1\r\nline2'), 'BOUNDARY'
        )
        self.assertEqual(posts, {'title': 'line1\r\nline2'})
        self.assertEqual(files, {})

    def test_repeated_field_becomes_list(self):
        """同名多值字段与 urlencoded 语义对齐转为列表（D4-4）"""
        body = (
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="tag"\r\n'
            b'\r\none\r\n'
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="tag"\r\n'
            b'\r\ntwo\r\n'
            b'--BOUNDARY\r\n'
            b'Content-Disposition: form-data; name="tag"\r\n'
            b'\r\nthree\r\n'
            b'--BOUNDARY--\r\n'
        )
        posts, files = parse_multipart_asgi(body, 'BOUNDARY')
        self.assertEqual(posts, {'tag': ['one', 'two', 'three']})
        self.assertEqual(files, {})

    def test_repeated_file_becomes_list(self):
        """同名多文件上传转为列表（D4-4）"""
        def part(content):
            return (
                b'--BOUNDARY\r\n'
                b'Content-Disposition: form-data; name="up"; filename="a.txt"\r\n'
                b'\r\n' + content + b'\r\n'
            )

        body = part(b'first') + part(b'second') + b'--BOUNDARY--\r\n'
        _, files = parse_multipart_asgi(body, 'BOUNDARY')
        self.assertIsInstance(files['up'], list)
        self.assertEqual([fp.read() for fp in files['up']], [b'first', b'second'])
        for fp in files['up']:
            fp.close()

    def test_wsgi_tiny_chunk_streaming(self):
        """WSGI 路径逐块读取请求体，不整包一次性读入内存（D4-1）"""

        class TinyChunkStream:
            """每次 read 最多返回 cap 字节的流，模拟分片到达的请求体"""

            def __init__(self, data, cap=7):
                self._fp = io.BytesIO(data)
                self.cap = cap
                self.max_read_request = 0

            def read(self, n=-1):
                if n is None or n < 0:
                    return self._fp.read(self.cap)
                self.max_read_request = max(self.max_read_request, n)
                return self._fp.read(min(n, self.cap))

        body = self._field_body(b'streaming works')
        stream = TinyChunkStream(body)
        posts, files = parse_multipart_wsgi(stream, 'BOUNDARY', len(body))
        self.assertEqual(posts, {'title': 'streaming works'})
        self.assertEqual(files, {})
        # 单次读取请求不大于解析器 chunk_size（流式，而非整包 read(content_length)）
        self.assertLessEqual(stream.max_read_request, 65536)

    def test_stream_actual_read_size_enforced(self):
        """流式路径按实际读取字节数强制限制（修复流式解析器忽略 max_upload_size）"""
        body = self._field_body(b'x' * 100)
        with self.assertRaises(HttpError) as ctx:
            parse_multipart_stream(io.BytesIO(body), 'BOUNDARY', max_upload_size=50)
        self.assertEqual(ctx.exception.status_code, 413)


if __name__ == '__main__':
    unittest.main()
