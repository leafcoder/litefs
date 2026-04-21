# WebSocket 支持

## 概述

Litefs 提供完整的 WebSocket 支持，包括：
- 独立的 WebSocket 服务器
- 连接管理
- 房间/频道管理
- 认证集成
- 心跳检测

## 快速开始

### 基本使用

```python
from litefs import Litefs

app = Litefs()

@app.websocket('/ws')
def ws_handler(ws):
    ws.send('欢迎连接!')
    
    for message in ws:
        ws.broadcast(message)
```

### 房间管理

```python
@app.websocket('/chat/{room_id}')
def chat_handler(ws, room_id):
    ws.join(room_id)
    
    for message in ws:
        ws.to_room(room_id, message)
```

### 认证集成

```python
from litefs.auth import Auth

auth = Auth(app, secret_key='your-secret-key')

def ws_auth_handler(ws):
    token = ws.query_params.get('token', [None])[0]
    if token:
        try:
            payload = auth._jwt.decode_token(token)
            ws.user_id = payload.get('sub')
            return True
        except:
            pass
    return False

@app.websocket('/ws', auth_required=True, auth_handler=ws_auth_handler)
def protected_ws(ws):
    ws.send(f'你好, 用户 {ws.user_id}!')
    
    for message in ws:
        ws.broadcast(message)
```

## API 参考

### WebSocket 连接对象

| 方法 | 说明 |
|------|------|
| `ws.send(data)` | 发送消息给当前连接 |
| `ws.broadcast(data)` | 广播给所有连接 |
| `ws.to_room(room, data)` | 发送到指定房间 |
| `ws.join(room)` | 加入房间 |
| `ws.leave(room)` | 离开房间 |
| `ws.close(code, reason)` | 关闭连接 |
| `ws.ping()` | 发送心跳 |
| `for msg in ws` | 消息迭代器 |

### 属性

| 属性 | 说明 |
|------|------|
| `ws.path` | WebSocket 路径 |
| `ws.query_params` | 查询参数（字典） |
| `ws.headers` | 请求头 |
| `ws.address` | 客户端地址 (host, port) |
| `ws.rooms` | 所属房间列表 |
| `ws.is_closed` | 连接是否已关闭 |
| `ws.user` | 用户对象（认证后） |

### 消息格式

WebSocket 自动处理消息格式：

- **发送 dict/list**：自动 JSON 序列化
- **发送 str**：作为文本消息发送
- **发送 bytes**：作为二进制消息发送
- **接收消息**：自动 JSON 解析（如果是 JSON）

```python
@app.websocket('/ws')
def handler(ws):
    # 发送 JSON
    ws.send({'type': 'greeting', 'message': 'Hello'})
    
    # 发送文本
    ws.send('Plain text message')
    
    # 发送二进制
    ws.send_bytes(b'\x00\x01\x02')
    
    for message in ws:
        # message 自动解析为 dict 或 str
        if isinstance(message, dict):
            print(f"JSON: {message}")
        else:
            print(f"Text: {message}")
```

## 完整示例

### 聊天室

```python
from litefs import Litefs

app = Litefs()

@app.route('/')
def index(request):
    return '''<!DOCTYPE html>
<html>
<head><title>聊天室</title></head>
<body>
    <div id="messages"></div>
    <input type="text" id="input">
    <button onclick="send()">发送</button>
    <script>
        const ws = new WebSocket('ws://localhost:8081/ws');
        ws.onmessage = e => {
            const div = document.createElement('div');
            div.textContent = e.data;
            document.getElementById('messages').appendChild(div);
        };
        function send() {
            const input = document.getElementById('input');
            ws.send(JSON.stringify({message: input.value}));
            input.value = '';
        }
    </script>
</body>
</html>'''

@app.websocket('/ws')
def chat(ws):
    ws.send('欢迎来到聊天室!')
    ws.join('chat')
    
    for message in ws:
        if isinstance(message, dict):
            ws.to_room('chat', {
                'type': 'chat',
                'message': message.get('message', '')
            })
    
    ws.leave('chat')

if __name__ == '__main__':
    app.run()
```

### 实时数据推送

```python
import time
import threading
from litefs import Litefs

app = Litefs()

def push_data():
    """后台线程推送数据"""
    while True:
        time.sleep(1)
        ws = app.get_websocket()
        if ws:
            ws.broadcast({
                'type': 'update',
                'timestamp': time.time(),
                'value': random.random()
            })

@app.websocket('/stream')
def stream(ws):
    ws.send({'type': 'connected'})
    
    for message in ws:
        pass  # 只接收，不处理

if __name__ == '__main__':
    threading.Thread(target=push_data, daemon=True).start()
    app.run()
```

## 配置选项

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `path` | str | '/ws' | WebSocket 路径 |
| `port` | int | HTTP端口+1 | WebSocket 服务器端口 |
| `auth_required` | bool | False | 是否需要认证 |
| `auth_handler` | Callable | None | 认证处理函数 |

## 协议支持

支持 RFC 6455 WebSocket 协议：

- 文本消息（Opcode 0x1）
- 二进制消息（Opcode 0x2）
- 关闭帧（Opcode 0x8）
- Ping/Pong 心跳（Opcode 0x9/0xA）

## 关闭码

| 码 | 说明 |
|----|------|
| 1000 | 正常关闭 |
| 1001 | 离开 |
| 1002 | 协议错误 |
| 1003 | 不支持的数据类型 |
| 4001 | 未授权（自定义） |

```python
from litefs.websocket import CloseCode

ws.close(CloseCode.NORMAL, 'Goodbye')
```

## 注意事项

1. WebSocket 服务器默认在 HTTP 端口 + 1 运行
2. 使用 `for message in ws` 循环会阻塞直到连接关闭
3. `ws.broadcast()` 会广播给所有连接（包括自己）
4. `ws.to_room()` 默认排除发送者，使用 `exclude_self=False` 包含
