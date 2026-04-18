#!/usr/bin/env python
# coding: utf-8

"""
实时应用示例

展示 Litefs 的实时通信特性：
- WebSocket 连接
- 房间管理
- 消息广播
- 用户进入/离开通知
- 在线用户列表
"""

import sys
import os
import json
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get

APP_DIR = os.path.dirname(os.path.abspath(__file__))

app = Litefs(
    host='0.0.0.0',
    port=8084,
    debug=True,
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))

connected_users = {}
user_names = set()


@get('/', name='index')
def index(request):
    """首页 - 聊天室入口"""
    return request.render_template('index.html')


@app.websocket('/ws')
def chat_handler(ws):
    """WebSocket 聊天处理"""
    user_name = 'Anonymous'
    
    for message in ws:
        if isinstance(message, dict):
            msg_type = message.get('type', 'unknown')
            
            if msg_type == 'join':
                user_name = message.get('user', 'Anonymous')
                connected_users[id(ws)] = user_name
                user_names.add(user_name)
                ws.join('chat')
                
                ws.send({'type': 'welcome', 'message': f'欢迎 {user_name} 加入聊天室!'})
                ws.send({'type': 'user_list', 'users': list(user_names)})
                
                ws.to_room('chat', {
                    'type': 'join',
                    'user': user_name
                }, exclude_self=True)
                
                ws.to_room('chat', {
                    'type': 'user_list',
                    'users': list(user_names)
                }, exclude_self=False)
                
            elif msg_type == 'chat':
                user = message.get('user', 'Anonymous')
                ws.to_room('chat', {
                    'type': 'chat',
                    'user': user,
                    'message': message.get('message', '')
                }, exclude_self=False)
                
            elif msg_type == 'ping':
                ws.send({'type': 'pong'})
    
    if id(ws) in connected_users:
        del connected_users[id(ws)]
    
    if user_name in user_names:
        user_names.discard(user_name)
    
    ws.to_room('chat', {
        'type': 'leave',
        'user': user_name
    }, exclude_self=True)
    
    ws.to_room('chat', {
        'type': 'user_list',
        'users': list(user_names)
    }, exclude_self=False)
    
    ws.leave('chat')


app.register_routes(__name__)


def push_notifications():
    """后台推送通知"""
    while True:
        time.sleep(30)
        ws = app.get_websocket()
        if ws:
            ws.broadcast({
                'type': 'notification',
                'message': f'服务器时间: {time.strftime("%H:%M:%S")}'
            })


if __name__ == '__main__':
    print("=" * 60)
    print("Litefs 实时应用示例")
    print("=" * 60)
    print()
    print("展示特性:")
    print("  - WebSocket 连接")
    print("  - 房间管理")
    print("  - 消息广播")
    print("  - 用户进入/离开通知")
    print("  - 在线用户列表")
    print("  - 后台推送")
    print()
    print("HTTP: http://localhost:8084")
    print("WebSocket: ws://localhost:8084/ws")
    print("=" * 60)
    
    threading.Thread(target=push_notifications, daemon=True).start()
    app.run()
