#!/usr/bin/env python
# coding: utf-8

"""
WebSocket 示例

本示例展示如何使用 Litefs 的 WebSocket 功能：
- 基本 WebSocket 连接
- 消息收发
- 房间管理
- 广播消息

测试步骤：
1. 启动服务器
2. 使用 WebSocket 客户端连接 ws://localhost:8081/ws
3. 发送消息测试
"""

import sys
import os

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
    """首页 - 返回 WebSocket 测试页面"""
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket 测试</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        .chat-box { border: 1px solid #ccc; height: 300px; overflow-y: auto; padding: 10px; margin: 10px 0; }
        .message { margin: 5px 0; padding: 5px; border-radius: 5px; }
        .message.sent { background: #e3f2fd; text-align: right; }
        .message.received { background: #f5f5f5; }
        .message.system { background: #fff3e0; text-align: center; color: #666; }
        .input-box { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px; }
        button { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #1976d2; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .status.connected { background: #e8f5e9; color: #2e7d32; }
        .status.disconnected { background: #ffebee; color: #c62828; }
    </style>
</head>
<body>
    <h1>WebSocket 测试</h1>
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
                addMessage('已连接到服务器', 'system');
                updateStatus(true);
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'chat') {
                        addMessage(data.user + ': ' + data.message, 'received');
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
            
            ws.onerror = function(error) {
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
    return html


@app.websocket('/ws')
def ws_handler(ws):
    """WebSocket 处理函数"""
    ws.send({'type': 'welcome', 'message': '欢迎连接 WebSocket 服务器!'})
    ws.join('broadcast')
    
    for message in ws:
        if isinstance(message, dict):
            msg_type = message.get('type', 'unknown')
            
            if msg_type == 'chat':
                ws.to_room('broadcast', {
                    'type': 'chat',
                    'user': 'Anonymous',
                    'message': message.get('message', '')
                }, exclude_self=False)
            elif msg_type == 'ping':
                ws.send({'type': 'pong'})
            else:
                ws.broadcast(message)
        else:
            ws.broadcast({'type': 'message', 'data': str(message)})
    
    ws.leave('broadcast')


app.register_routes(__name__)


if __name__ == '__main__':
    print("=" * 60)
    print("WebSocket 示例")
    print("=" * 60)
    print()
    print("HTTP 服务器: http://localhost:8080")
    print("WebSocket 服务器: ws://localhost:8081/ws")
    print()
    print("测试步骤:")
    print("1. 浏览器访问 http://localhost:8080")
    print("2. 点击 '连接' 按钮")
    print("3. 输入消息并发送")
    print()
    print("服务器启动中...")
    print("=" * 60)
    
    app.run()
