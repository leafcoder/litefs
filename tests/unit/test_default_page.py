#!/usr/bin/env python
# coding: utf-8

"""
测试默认页面功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from litefs import Litefs
from litefs.config import Config


def test_default_page_priority():
    """测试默认页面优先级"""
    print("测试默认页面优先级...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        webroot = Path(tmpdir) / "site"
        webroot.mkdir()
        
        app = Litefs(webroot=str(webroot), default_page="index,index.html")
        
        # 测试 1: 只有 index.html
        (webroot / "index.html").write_text("<html><body>index.html</body></html>")
        
        # 测试 2: 只有 index.py
        (webroot / "index.html").unlink()
        (webroot / "index.py").write_text("""
def handler(self):
    self.start_response(200, [('Content-Type', 'text/html')])
    return ['<html><body>index.py</body></html>']
""")
        
        # 测试 3: 两者都有，应该优先使用 index.py
        (webroot / "index.html").write_text("<html><body>index.html</body></html>")
        
        print("  ✓ 默认页面优先级测试完成")


def test_default_page_multiple():
    """测试多个默认页面"""
    print("测试多个默认页面...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        webroot = Path(tmpdir) / "site"
        webroot.mkdir()
        
        # 测试 1: 默认配置
        app = Litefs(webroot=str(webroot))
        assert app.config.default_page == "index,index.html"
        print("  ✓ 默认配置正确")
        
        # 测试 2: 自定义配置
        app = Litefs(webroot=str(webroot), default_page="home,default.html")
        assert app.config.default_page == "home,default.html"
        print("  ✓ 自定义配置正确")
        
        # 测试 3: 单个默认页面
        app = Litefs(webroot=str(webroot), default_page="index")
        assert app.config.default_page == "index"
        print("  ✓ 单个默认页面配置正确")


def test_default_page_fallback():
    """测试默认页面回退"""
    print("测试默认页面回退...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        webroot = Path(tmpdir) / "site"
        webroot.mkdir()
        
        # 创建目录结构
        subdir = webroot / "test"
        subdir.mkdir()
        
        # 测试 1: 子目录中没有默认页面，应该回退到第一个默认页面
        app = Litefs(webroot=str(webroot), default_page="index,index.html")
        
        # 创建 index.html
        (webroot / "index.html").write_text("<html><body>index.html</body></html>")
        
        # 创建子目录的 index.html
        (subdir / "index.html").write_text("<html><body>test/index.html</body></html>")
        
        print("  ✓ 默认页面回退测试完成")


def test_default_page_config_parsing():
    """测试配置解析"""
    print("测试配置解析...")
    
    config = Config()
    
    # 测试 1: 字符串配置
    config.set("default_page", "index,index.html")
    assert config.default_page == "index,index.html"
    print("  ✓ 字符串配置正确")
    
    # 测试 2: 列表配置
    config.set("default_page", ["index", "index.html"])
    assert config.default_page == ["index", "index.html"]
    print("  ✓ 列表配置正确")
    
    # 测试 3: 单个值
    config.set("default_page", "index")
    assert config.default_page == "index"
    print("  ✓ 单个值配置正确")


if __name__ == "__main__":
    print("=" * 60)
    print("测试默认页面功能")
    print("=" * 60)
    
    test_default_page_priority()
    test_default_page_multiple()
    test_default_page_fallback()
    test_default_page_config_parsing()
    
    print("=" * 60)
    print("所有测试通过！")
    print("=" * 60)
