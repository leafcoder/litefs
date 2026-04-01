#!/usr/bin/env python
# coding: utf-8

"""
多进程服务器示例

这个示例演示了如何使用 LiteFS 的多进程服务器功能，提高并发处理能力。
"""

from litefs import Litefs


def main():
    """主函数"""
    # 创建 LiteFS 应用
    app = Litefs(webroot="./site")
    
    # 打印帮助信息
    print("LiteFS 多进程服务器示例")
    print("=" * 60)
    print("使用 4 个进程运行服务器")
    print("访问地址: http://localhost:9090")
    print("=" * 60)
    
    # 启动多进程服务器
    # processes 参数指定进程数
    app.run(processes=4)


if __name__ == '__main__':
    main()
