#!/usr/bin/env python
# coding: utf-8

import sys
import os

# 添加 litefs 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from litefs import Litefs

# 创建 site 目录
os.makedirs("site", exist_ok=True)

# 创建 index.py 文件，返回 "Hello world"
with open("site/index.py", "w") as f:
    f.write("def handler(request, response):\n    return \"Hello world\"")

# 创建最简单的 litefs 应用
app = Litefs(webroot="./site", host="0.0.0.0", port=8000)

if __name__ == "__main__":
    app.run()
