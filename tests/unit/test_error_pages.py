#!/usr/bin/env python
# coding: utf-8

"""
错误页面功能测试
"""

import unittest
import tempfile
import os

from litefs.error_pages import ErrorPageRenderer


class TestErrorPageRenderer(unittest.TestCase):
    """测试错误页面渲染器"""

    def test_render_400_error(self):
        """测试渲染 400 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(400)
        self.assertIn("400", content)
        self.assertIn("错误的请求", content)
        self.assertIn("Bad Request", content)

    def test_render_403_error(self):
        """测试渲染 403 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(403)
        self.assertIn("403", content)
        self.assertIn("禁止访问", content)
        self.assertIn("Forbidden", content)

    def test_render_404_error(self):
        """测试渲染 404 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(404)
        self.assertIn("404", content)
        self.assertIn("页面未找到", content)
        self.assertIn("Not Found", content)

    def test_render_500_error(self):
        """测试渲染 500 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(500)
        self.assertIn("500", content)
        self.assertIn("服务器内部错误", content)
        self.assertIn("Internal Server Error", content)

    def test_render_502_error(self):
        """测试渲染 502 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(502)
        self.assertIn("502", content)
        self.assertIn("网关错误", content)
        self.assertIn("Bad Gateway", content)

    def test_render_503_error(self):
        """测试渲染 503 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(503)
        self.assertIn("503", content)
        self.assertIn("服务不可用", content)
        self.assertIn("Service Unavailable", content)

    def test_render_504_error(self):
        """测试渲染 504 错误页面"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(504)
        self.assertIn("504", content)
        self.assertIn("网关超时", content)
        self.assertIn("Gateway Timeout", content)

    def test_render_unknown_error(self):
        """测试渲染未知错误（默认 500）"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(418)
        self.assertIn("500", content)
        self.assertIn("服务器内部错误", content)

    def test_render_with_custom_message(self):
        """测试使用自定义消息"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(500, message="自定义错误消息")
        self.assertIn("自定义错误消息", content)

    def test_render_with_custom_detail(self):
        """测试使用自定义详情"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(500, detail="自定义错误详情")
        self.assertIn("自定义错误详情", content)

    def test_get_error_page(self):
        """测试获取错误页面"""
        renderer = ErrorPageRenderer()
        status_code, content_type, content = renderer.get_error_page(404)
        self.assertEqual(status_code, 404)
        self.assertEqual(content_type, "text/html; charset=utf-8")
        self.assertIn("404", content)

    def test_custom_error_dir(self):
        """测试自定义错误页面目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            error_file = os.path.join(temp_dir, "404.html")
            with open(error_file, "w", encoding="utf-8") as f:
                f.write("<html><body>自定义 404 页面</body></html>")

            renderer = ErrorPageRenderer(temp_dir)
            content = renderer.render_error_page(404)
            self.assertIn("自定义 404 页面", content)

    def test_custom_error_dir_nonexistent(self):
        """测试不存在的自定义错误页面目录"""
        renderer = ErrorPageRenderer("/nonexistent/directory")
        content = renderer.render_error_page(404)
        self.assertIn("404", content)
        self.assertIn("页面未找到", content)

    def test_html_structure(self):
        """测试 HTML 结构"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(404)
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<html", content)
        self.assertIn("</html>", content)
        self.assertIn("<head>", content)
        self.assertIn("<body>", content)

    def test_responsive_design(self):
        """测试响应式设计"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(404)
        self.assertIn("viewport", content)
        self.assertIn("width=device-width", content)

    def test_styling(self):
        """测试样式"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(404)
        self.assertIn("<style>", content)
        self.assertIn("background:", content)
        self.assertIn("border-radius:", content)

    def test_return_home_button(self):
        """测试返回首页按钮"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(404)
        self.assertIn('href="/"', content)
        self.assertIn("返回首页", content)

    def test_error_icon(self):
        """测试错误图标"""
        renderer = ErrorPageRenderer()
        content = renderer.render_error_page(404)
        self.assertIn("error-icon", content)


if __name__ == '__main__':
    unittest.main()
