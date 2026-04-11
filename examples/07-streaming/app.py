#!/usr/bin/env python
# coding: utf-8

"""
流式响应示例

这个示例展示如何使用 Litefs 的流式响应功能，包括：
1. 文本流 - 动态生成文本数据
2. 文件流 - 流式返回大文件
3. 进度流 - 实时返回任务进度（Server-Sent Events）
"""

from litefs import Litefs, Response
import time
import os

app = Litefs()


@app.add_get('/stream/text')
def stream_text(request):
    """流式返回文本数据"""
    
    def generate_text():
        for i in range(10):
            yield f"Line {i+1}\n"
            time.sleep(0.5)  # 模拟延迟
    
    return Response.stream(generate_text())


@app.add_get('/stream/file')
def stream_file(request):
    """流式返回大文件"""
    
    # 创建一个测试大文件
    file_path = 'test_large_file.txt'
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            for i in range(10000):
                f.write(f"Line {i+1}: This is a test line for large file streaming\n")
    
    # 使用简化的 file_stream 方法
    return Response.file_stream(file_path)


@app.add_get('/stream/progress')
def stream_progress(request):
    """流式返回任务进度"""
    
    def generate_progress():
        total = 100
        for i in range(total + 1):
            progress = i / total * 100
            # 使用 Server-Sent Events 格式
            yield f"data: {{\"progress\": {progress:.1f}}}\n\n"
            time.sleep(0.1)  # 模拟任务执行
    
    # 使用简化的 sse 方法
    return Response.sse(generate_progress())


if __name__ == '__main__':
    # 运行服务器
    app.run()
    print("流式响应示例已启动，请访问以下地址:")
    print("1. 文本流: http://localhost:9090/stream/text")
    print("2. 文件流: http://localhost:9090/stream/file")
    print("3. 进度流: http://localhost:9090/stream/progress")
