#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs


def main():
    """基础处理器示例"""
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='./examples/02-basic-handlers/site',
        debug=True
    )
    
    print("=" * 60)
    print("Litefs Basic Handlers Example")
    print("=" * 60)
    print("可用的处理器:")
    print("  /json - JSON 响应")
    print("  /json_complex - 复杂 JSON 响应")
    print("  /json_custom_header - 自定义头的 JSON 响应")
    print("  /json_error - JSON 错误响应")
    print("  /json_html - JSON 和 HTML 混合响应")
    print("  /html - HTML 响应")
    print("  /text - 文本响应")
    print("  /form - 表单处理")
    print("  /error - 错误处理")
    print("  /generator - 生成器响应")
    print("  /mixed - 混合响应")
    print("  /mixed_tuple - 元组混合响应")
    print("  /mixed_tuple_text - 元组文本混合响应")
    print("=" * 60)
    
    app.run()


if __name__ == '__main__':
    main()
