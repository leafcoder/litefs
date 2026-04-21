const elements = {
    connectBtn: document.getElementById('connect-btn'),
    sendBtn: document.getElementById('send-btn'),
    messageInput: document.getElementById('message-input'),
    usernameInput: document.getElementById('username-input'),
    messagesContainer: document.getElementById('messages-container'),
    connectionStatus: document.getElementById('connection-status'),
    onlineCount: document.getElementById('online-count'),
    userList: document.getElementById('user-list')
};

let ws = null;
let isConnected = false;
let onlineUsers = [];
let currentUsername = '';

function updateConnectionStatus(connected) {
    isConnected = connected;
    const statusDot = elements.connectionStatus.querySelector('.status-dot');
    const statusText = elements.connectionStatus.querySelector('.status-text');
    
    if (connected) {
        statusDot.className = 'status-dot connected';
        statusText.textContent = '已连接';
        elements.connectBtn.innerHTML = '<span class="btn-icon">🔴</span> 断开连接';
        elements.messageInput.disabled = false;
        elements.sendBtn.disabled = false;
        elements.usernameInput.disabled = true;
        elements.messageInput.focus();
    } else {
        statusDot.className = 'status-dot disconnected';
        statusText.textContent = '未连接';
        elements.connectBtn.innerHTML = '<span class="btn-icon">🔌</span> 连接服务器';
        elements.messageInput.disabled = true;
        elements.sendBtn.disabled = true;
        elements.usernameInput.disabled = false;
    }
}

function updateUserList() {
    if (onlineUsers.length === 0) {
        elements.userList.innerHTML = '<li class="empty-hint">暂无在线用户</li>';
    } else {
        elements.userList.innerHTML = onlineUsers.map(user => {
            const isCurrentUser = user === currentUsername;
            const avatar = user.charAt(0).toUpperCase();
            return `<li class="${isCurrentUser ? 'current-user' : ''}">
                <span class="user-avatar">${avatar}</span>
                <span>${user}${isCurrentUser ? ' (我)' : ''}</span>
            </li>`;
        }).join('');
    }
    elements.onlineCount.textContent = onlineUsers.length;
}

function addMessage(data) {
    const messagesHtml = elements.messagesContainer.innerHTML;
    if (messagesHtml.includes('welcome-message')) {
        elements.messagesContainer.innerHTML = '';
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    
    switch (data.type) {
        case 'chat':
            messageDiv.classList.add('chat-message');
            const avatar = data.user ? data.user.charAt(0).toUpperCase() : 'A';
            const user = data.user || 'Anonymous';
            const isCurrentUser = data.user === currentUsername;
            if (isCurrentUser) {
                messageDiv.classList.add('sent');
                messageDiv.innerHTML = `
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-user">我</span>
                            <span class="message-time">${time}</span>
                        </div>
                        <div class="message-text">${escapeHtml(data.message)}</div>
                    </div>
                `;
            } else {
                messageDiv.innerHTML = `
                    <div class="message-avatar">${avatar}</div>
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-user">${user}</span>
                            <span class="message-time">${time}</span>
                        </div>
                        <div class="message-text">${escapeHtml(data.message)}</div>
                    </div>
                `;
            }
            break;
            
        case 'join':
            messageDiv.classList.add('system-message');
            messageDiv.innerHTML = `
                <span class="system-icon">👋</span>
                <span class="system-text">${escapeHtml(data.user)} 进入房间</span>
            `;
            if (!onlineUsers.includes(data.user)) {
                onlineUsers.push(data.user);
                updateUserList();
            }
            break;
            
        case 'leave':
            messageDiv.classList.add('system-message');
            messageDiv.innerHTML = `
                <span class="system-icon">👋</span>
                <span class="system-text">${escapeHtml(data.user)} 离开房间</span>
            `;
            onlineUsers = onlineUsers.filter(u => u !== data.user);
            updateUserList();
            break;
            
        case 'user_list':
            onlineUsers = data.users || [];
            updateUserList();
            return;
            
        case 'system':
            messageDiv.classList.add('system-message');
            messageDiv.innerHTML = `
                <span class="system-icon">ℹ️</span>
                <span class="system-text">${escapeHtml(data.message)}</span>
            `;
            break;
            
        case 'notification':
            messageDiv.classList.add('notification-message');
            messageDiv.innerHTML = `
                <span class="notification-icon">🔔</span>
                <span class="notification-text">${escapeHtml(data.message)}</span>
            `;
            break;
            
        case 'welcome':
            messageDiv.classList.add('system-message');
            messageDiv.innerHTML = `
                <span class="system-icon">🎉</span>
                <span class="system-text">${escapeHtml(data.message)}</span>
            `;
            if (!onlineUsers.includes(currentUsername)) {
                onlineUsers.push(currentUsername);
                updateUserList();
            }
            break;
            
        default:
            messageDiv.classList.add('system-message');
            messageDiv.innerHTML = `<span class="system-text">${escapeHtml(JSON.stringify(data))}</span>`;
    }
    
    elements.messagesContainer.appendChild(messageDiv);
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        return;
    }
    
    currentUsername = elements.usernameInput.value.trim();
    if (!currentUsername) {
        currentUsername = '访客' + Math.floor(Math.random() * 1000);
    }
    
    ws = new WebSocket('ws://localhost:8081/ws');
    
    ws.onopen = function() {
        updateConnectionStatus(true);
        addMessage({ type: 'system', message: '已连接到服务器' });
        ws.send(JSON.stringify({ type: 'join', user: currentUsername }));
    };
    
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            addMessage(data);
        } catch (e) {
            addMessage({ type: 'system', message: event.data });
        }
    };
    
    ws.onclose = function() {
        updateConnectionStatus(false);
        addMessage({ type: 'system', message: '连接已断开' });
        onlineUsers = [];
        updateUserList();
    };
    
    ws.onerror = function() {
        updateConnectionStatus(false);
        addMessage({ type: 'system', message: '连接发生错误' });
    };
}

function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || !isConnected) return;
    
    ws.send(JSON.stringify({ type: 'chat', user: currentUsername, message: message }));
    elements.messageInput.value = '';
}

elements.connectBtn.addEventListener('click', connect);
elements.sendBtn.addEventListener('click', sendMessage);
elements.messageInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
elements.usernameInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        connect();
    }
});
