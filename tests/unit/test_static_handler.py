#!/usr/bin/env python
# coding: utf-8

"""
静态文件处理器测试

覆盖 litefs.static_handler 模块：路径安全、缓存、ETag、条件请求、Gzip 压缩。
"""

import gzip
import os
import tempfile
import unittest
from pathlib import Path

from litefs.static_handler import StaticFileHandler, create_static_handler


class StaticFileTestCase(unittest.TestCase):
    """静态文件测试基类：创建临时目录与示例文件"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.handler = StaticFileHandler(self.tmpdir)

        # 小文件（不触发压缩）
        self.small_path = Path(self.tmpdir) / "small.txt"
        self.small_path.write_text("hello litefs", encoding="utf-8")

        # 大文件（>1KB 且为可压缩类型，触发 Gzip）
        self.big_path = Path(self.tmpdir) / "big.html"
        self.big_path.write_text("<html>" + "x" * 4096 + "</html>", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def get_header(self, headers, name):
        """从响应头列表取值"""
        for key, value in headers:
            if key == name:
                return value
        return None


class TestInitAndConvenience(StaticFileTestCase):
    """测试初始化与便捷函数"""

    def test_nonexistent_directory_raises(self):
        """目录不存在时抛 ValueError"""
        with self.assertRaises(ValueError):
            StaticFileHandler("/nonexistent/path/for/litefs/test")

    def test_default_options(self):
        """默认配置正确"""
        h = self.handler
        self.assertEqual(h.max_age, StaticFileHandler.DEFAULT_MAX_AGE)
        self.assertTrue(h.enable_gzip)
        self.assertTrue(h.enable_etag)
        self.assertTrue(h.enable_range)

    def test_create_static_handler(self):
        """create_static_handler 返回配置好的实例"""
        h = create_static_handler(self.tmpdir, max_age=60, enable_gzip=False)
        self.assertIsInstance(h, StaticFileHandler)
        self.assertEqual(h.max_age, 60)
        self.assertFalse(h.enable_gzip)


class TestPathSecurity(StaticFileTestCase):
    """测试路径安全"""

    def test_normal_file_served(self):
        """正常文件返回 200 与正确内容"""
        status, headers, content = self.handler.serve("small.txt")
        self.assertEqual(status, 200)
        self.assertEqual(content, b"hello litefs")
        self.assertEqual(
            self.get_header(headers, "Content-Type"), "text/plain"
        )

    def test_leading_slash_allowed(self):
        """开头的斜杠被移除后正常服务"""
        status, _, content = self.handler.serve("/small.txt")
        self.assertEqual(status, 200)
        self.assertEqual(content, b"hello litefs")

    def test_path_traversal_blocked(self):
        """路径遍历攻击返回 403"""
        evil = os.path.join(self.tmpdir, "secret.txt")
        Path(evil).write_text("secret", encoding="utf-8")
        status, _, content = self.handler.serve("../secret.txt")
        self.assertEqual(status, 403)
        self.assertEqual(content, b"Forbidden")

    def test_missing_file_404(self):
        """不存在的文件返回 404"""
        status, _, content = self.handler.serve("no-such-file.txt")
        self.assertEqual(status, 404)
        self.assertEqual(content, b"Not Found")

    def test_directory_request_403(self):
        """请求目录（非文件）返回 403"""
        subdir = Path(self.tmpdir) / "sub"
        subdir.mkdir()
        status, _, content = self.handler.serve("sub")
        self.assertEqual(status, 403)
        self.assertEqual(content, b"Forbidden")


class TestCaching(StaticFileTestCase):
    """测试文件缓存"""

    def test_second_serve_uses_cache(self):
        """第二次请求命中内存缓存，内容一致"""
        status1, _, content1 = self.handler.serve("small.txt")
        info = self.handler.get_cache_info()
        self.assertEqual(info["cache_size"], 1)
        self.assertIn(str(self.small_path), info["cached_files"])

        status2, _, content2 = self.handler.serve("small.txt")
        self.assertEqual(status1, status2)
        self.assertEqual(content1, content2)

    def test_clear_cache(self):
        """clear_cache 清空缓存"""
        self.handler.serve("small.txt")
        self.handler.clear_cache()
        self.assertEqual(self.handler.get_cache_info()["cache_size"], 0)

    def test_cache_size_limit(self):
        """达到 cache_size 上限后不再缓存新文件"""
        h = StaticFileHandler(self.tmpdir, cache_size=1)
        h.serve("small.txt")
        h.serve("big.html")
        info = h.get_cache_info()
        self.assertEqual(info["cache_size"], 1)
        self.assertEqual(info["cached_files"], [str(self.small_path)])


class TestConditionalRequests(StaticFileTestCase):
    """测试条件请求"""

    def test_etag_generated_and_304(self):
        """ETag 生成后 If-None-Match 匹配返回 304"""
        _, headers, _ = self.handler.serve("small.txt")
        etag = self.get_header(headers, "ETag")
        self.assertIsNotNone(etag)

        status, _, content = self.handler.serve(
            "small.txt", {"If-None-Match": etag}
        )
        self.assertEqual(status, 304)
        self.assertEqual(content, b"")

    def test_etag_disabled(self):
        """关闭 ETag 时不生成 ETag 头"""
        h = StaticFileHandler(self.tmpdir, enable_etag=False)
        _, headers, _ = h.serve("small.txt")
        self.assertIsNone(self.get_header(headers, "ETag"))

    def test_if_modified_since_not_modified(self):
        """If-Modified-Since 晚于文件修改时间返回 304"""
        future = "Mon, 01 Jan 2035 00:00:00 GMT"
        status, _, _ = self.handler.serve("small.txt", {"If-Modified-Since": future})
        self.assertEqual(status, 304)

    def test_if_modified_since_modified(self):
        """If-Modified-Since 早于文件修改时间返回 200"""
        past = "Mon, 01 Jan 1990 00:00:00 GMT"
        status, _, _ = self.handler.serve("small.txt", {"If-Modified-Since": past})
        self.assertEqual(status, 200)

    def test_invalid_if_modified_since_ignored(self):
        """非法的 If-Modified-Since 被忽略，返回 200"""
        status, _, _ = self.handler.serve("small.txt", {"If-Modified-Since": "garbage"})
        self.assertEqual(status, 200)


class TestGzipCompression(StaticFileTestCase):
    """测试 Gzip 压缩"""

    def test_compressible_large_file_gzipped(self):
        """大体积可压缩类型被 Gzip 压缩"""
        status, headers, content = self.handler.serve("big.html")
        self.assertEqual(status, 200)
        self.assertEqual(self.get_header(headers, "Content-Encoding"), "gzip")
        self.assertEqual(
            int(self.get_header(headers, "Content-Length")), len(content)
        )
        self.assertEqual(gzip.decompress(content), self.big_path.read_bytes())

    def test_gzip_disabled(self):
        """关闭 Gzip 后返回原始内容"""
        h = StaticFileHandler(self.tmpdir, enable_gzip=False)
        _, headers, content = h.serve("big.html")
        self.assertIsNone(self.get_header(headers, "Content-Encoding"))
        self.assertEqual(content, self.big_path.read_bytes())

    def test_small_file_not_compressed(self):
        """小于最小压缩阈值的文件不压缩"""
        _, headers, content = self.handler.serve("small.txt")
        self.assertIsNone(self.get_header(headers, "Content-Encoding"))
        self.assertEqual(content, b"hello litefs")


class TestResponseHeaders(StaticFileTestCase):
    """测试响应头构建"""

    def test_cache_control_and_expires(self):
        """默认 max_age>0 时生成 Cache-Control 与 Expires"""
        _, headers, _ = self.handler.serve("small.txt")
        self.assertEqual(
            self.get_header(headers, "Cache-Control"),
            f"public, max-age={StaticFileHandler.DEFAULT_MAX_AGE}",
        )
        self.assertIsNotNone(self.get_header(headers, "Expires"))

    def test_accept_ranges(self):
        """启用 Range 时生成 Accept-Ranges 头"""
        _, headers, _ = self.handler.serve("small.txt")
        self.assertEqual(self.get_header(headers, "Accept-Ranges"), "bytes")

    def test_last_modified_present(self):
        """Last-Modified 头存在"""
        _, headers, _ = self.handler.serve("small.txt")
        self.assertIsNotNone(self.get_header(headers, "Last-Modified"))


class TestFileSizeLimit(StaticFileTestCase):
    """测试文件大小限制"""

    def test_oversized_file_413(self):
        """超过 max_file_size 的文件返回 413"""
        big = Path(self.tmpdir) / "huge.bin"
        big.write_bytes(b"\0" * 2048)
        h = StaticFileHandler(self.tmpdir, max_file_size=1024)
        status, _, content = h.serve("huge.bin")
        self.assertEqual(status, 413)
        self.assertEqual(content, b"Payload Too Large")


if __name__ == "__main__":
    unittest.main()
