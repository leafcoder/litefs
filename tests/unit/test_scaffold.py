#!/usr/bin/env python
# coding: utf-8

"""
测试脚手架生成
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from litefs.cli import startproject


def test_scaffold_generation():
    """测试脚手架生成"""
    print("测试脚手架生成...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "testproject"
        
        # 生成项目
        startproject("testproject", str(tmpdir))
        
        # 检查目录结构
        expected_dirs = [
            "templates",
            "static",
            "static/css",
            "static/js",
            "static/images",
        ]
        
        for dir_path in expected_dirs:
            full_path = project_path / dir_path
            if not full_path.exists():
                print(f"  ✗ 目录不存在: {dir_path}")
                return False
            print(f"  ✓ 目录存在: {dir_path}")
        
        # 检查文件
        expected_files = [
            "app.py",
            "config.yaml",
            "requirements.txt",
            "README.md",
            ".gitignore",
            "templates/index.html",
            "templates/about.html",
            "static/css/style.css",
            "wsgi.py",
        ]
        
        for file_path in expected_files:
            full_path = project_path / file_path
            if not full_path.exists():
                print(f"  ✗ 文件不存在: {file_path}")
                return False
            print(f"  ✓ 文件存在: {file_path}")
        
        return True


if __name__ == "__main__":
    print("=" * 60)
    print("测试脚手架生成")
    print("=" * 60)
    
    if test_scaffold_generation():
        print("=" * 60)
        print("所有测试通过！")
        print("=" * 60)
    else:
        print("=" * 60)
        print("测试失败！")
        print("=" * 60)
        sys.exit(1)
