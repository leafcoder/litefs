#!/usr/bin/env python
"""LiteFS 性能测试套件 - 统一入口"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from litefs import Litefs

__version__ = "1.0.0"

# 导出主要组件
__all__ = ["Litefs"]
