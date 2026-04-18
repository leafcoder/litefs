#!/usr/bin/env python
# coding: utf-8

"""
实时应用示例

展示 Litefs 的实时通信特性：
- WebSocket 连接
- 房间管理
- 消息广播
- 认证集成
"""

import sys
import os
import json
import threading
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get

app = Litefs(
    host='0.0.0.0',
    port=8080,
    debug=True,
)


@get('/', name='index')
def index(request):
    """首页 - 聊天室入口"""
    return '''<!DOCTYPE html>
<html>
<head>
    <title>Litefs 实时聊天</title>
    <style>
        body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #2196f3; }
        .chat-box { border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 10px; margin: 10px 0; background: #f9f9f9; }
        .message { margin: 5px 0; padding: 8px; border-radius: 5px; }
        .message.sent { background: #e3f2fd; text-align: right; }
        .message.received { background: #fff; }
        .message.system { background: #fff3e0; text-align: center; color: #666; font-size: 12px; }
        .input-box { display: flex; gap: 10px; }
        input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #1976d2; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; text-align: center; }
        .status.connected { background: #e8f5e9; color: #2e7d32; }
        .status.disconnected { background: #ffebee; color: #c62828; }
    </style>
</head>
<body>
    <h1>Litefs 实时聊天室</h1>
    <div id="status" class="status disconnected">未连接</div>
    <div id="chat-box" class="chat-box"></div>
    <div class="input-box">
        <input type="text" id="message-input" placeholder="输入消息..." disabled>
        <button id="send-btn" disabled>发送</button>
        <button id="connect-btn">连接</button>
    </div>
    
    <script>
        let ws = null;
        const chatBox = document.getElementById('chat-box');
        const messageInput = document.getElementById('message-input');
        const sendBtn = document.getElementById('send-btn');
        const connectBtn = document.getElementById('connect-btn');
        const statusDiv = document.getElementById('status');
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        }
        
        function updateStatus(connected) {
            if (connected) {
                statusDiv.textContent = '已连接';
                statusDiv.className = 'status connected';
                messageInput.disabled = false;
                sendBtn.disabled = false;
                connectBtn.textContent = '断开';
            } else {
                statusDiv.textContent = '未连接';
                statusDiv.className = 'status disconnected';
                messageInput.disabled = true;
                sendBtn.disabled = true;
                connectBtn.textContent = '连接';
            }
        }
        
        function connect() {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.close();
                return;
            }
            
            ws = new WebSocket('ws://localhost:8081/ws');
            
            ws.onopen = function() {
                addMessage('已连接到聊天室', 'system');
                updateStatus(true);
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'chat') {
                        addMessage(data.user + ': ' + data.message, 'received');
                    } else if (data.type === 'welcome') {
                        addMessage(data.message, 'system');
                    } else if (data.type === 'notification') {
                        addMessage('[系统] ' + data.message, 'system');
                    } else {
                        addMessage(JSON.stringify(data), 'received');
                    }
                } catch (e) {
                    addMessage(event.data, 'received');
                }
            };
            
            ws.onclose = function() {
                addMessage('连接已断开', 'system');
                updateStatus(false);
            };
            
            ws.onerror = function() {
                addMessage('连接错误', 'system');
                updateStatus(false);
            };
        }
        
        function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'chat', message: message }));
                addMessage('我: ' + message, 'sent');
                messageInput.value = '';
            }
        }
        
        connectBtn.addEventListener('click', connect);
        sendBtn.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''


@app.websocket('/ws')
def chat_handler(ws):
    """WebSocket 聊天处理"""
    ws.send({'type': 'welcome', 'message': '欢迎加入聊天室!'})
    ws.join('chat')
    
    for message in ws:
        if isinstance(message, dict):
            msg_type = message.get('type', 'unknown')
            
            if msg_type == 'chat':
                ws.to_room('chat', {
                    'type': 'chat',
                    'user': 'Anonymous',
                    'message': message.get('message', '')
                }, exclude_self=False)
            elif msg_type == 'ping':
                ws.send({'type': 'pong'})
    
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
    print("  - 后台推送")
    print()
    print("HTTP: http://localhost:8080")
    print("WebSocket: ws://localhost:8081/ws")
    print("=" * 60)
    
    threading.Thread(target=push_notifications, daemon=True).start()
    app.run()
