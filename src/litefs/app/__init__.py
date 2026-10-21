#!/usr/bin/env python
# coding: utf-8

"""
Litefs 应用层子包

存放从 core.py 拆分出的应用组装逻辑：

- helpers          响应序列化、配置与服务器创建辅助函数
- protocol_mixin   WSGI / ASGI 协议适配与错误处理
- routing_mixin    路由注册与 WebSocket 入口
- extension_mixin  中间件、插件、健康检查与数据库扩展方法
- server_mixin     服务器启动、关闭与热重载生命周期
- server_cli       内置测试服务器命令行入口

`litefs.core.Litefs` 通过 Mixin 组合以上能力，对外接口保持不变。
"""
