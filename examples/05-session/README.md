# 会话管理

Litefs 会话管理示例，包括与新路由系统的集成。

## 示例文件

- `session_example.py` - 会话管理示例主程序（使用新的路由系统）

## 运行示例

```bash
python session_example.py
```

访问 http://localhost:8080/session 查看会话管理示例。

## 会话操作

### 设置会话

```python
def handler(self):
    self.session['username'] = '张三'
    self.session['user_id'] = '1001'
    return "会话已设置"
```

### 获取会话

```python
def handler(self):
    username = self.session.get('username', 'Guest')
    return f"Hello, {username}!"
```

### 删除会话

```python
def handler(self):
    if 'username' in self.session:
        del self.session['username']
    return "会话已删除"
```

### 清除所有会话

```python
def handler(self):
    self.session.clear()
    return "所有会话已清除"
```

### 检查会话存在

```python
def handler(self):
    if 'user_id' in self.session:
        return "用户已登录"
    return "用户未登录"
```

## 会话应用场景

### 1. 用户登录状态

```python
def login_handler(self):
    if self.method == 'POST':
        username = self.post.get('username')
        password = self.post.get('password')
        
        if authenticate(username, password):
            self.session['user_id'] = get_user_id(username)
            self.session['username'] = username
            self.session['login_time'] = datetime.now()
            return "登录成功"
        
        return "登录失败"
    
    return '<form method="post">...</form>'
```

### 2. 购物车

```python
def add_to_cart_handler(self):
    product_id = self.get.get('product_id')
    quantity = int(self.get.get('quantity', 1))
    
    cart = self.session.get('cart', [])
    cart.append({'product_id': product_id, 'quantity': quantity})
    self.session['cart'] = cart
    
    return "商品已添加到购物车"
```

### 3. 用户偏好

```python
def set_preference_handler(self):
    theme = self.get.get('theme', 'light')
    language = self.get.get('language', 'zh-CN')
    
    self.session['theme'] = theme
    self.session['language'] = language
    
    return "偏好设置已保存"
```

### 4. 访问计数

```python
def page_handler(self):
    count = self.session.get('visit_count', 0)
    self.session['visit_count'] = count + 1
    return f"您已访问此页面 {self.session['visit_count']} 次"
```

## 会话特性

- 自动管理会话 ID
- 支持任意 Python 对象存储
- 自动过期处理
- 线程安全
- 支持分布式存储（通过 Redis）

## 与新路由系统集成

使用新的路由系统定义会话相关的路由：

```python
from litefs import Litefs
from litefs.routing import get, post

app = Litefs(
    session_backend='database',
    session_expiration_time=3600
)

@get('/session')
def session_handler(self):
    # 获取会话数据
    username = self.session.get('username', 'Guest')
    visit_count = self.session.get('visit_count', 0)
    
    # 更新访问计数
    self.session['visit_count'] = visit_count + 1
    
    # 生成响应
    return f"Hello, {username}! You've visited {self.session['visit_count']} times."

@post('/login')
def login_handler(self):
    # 获取表单数据
    username = self.post.get('username')
    password = self.post.get('password')
    
    # 验证用户（这里简化处理）
    if username and password:
        # 设置会话
        self.session['username'] = username
        self.session['user_id'] = 123
        return "Login successful!"
    
    return "Login failed!"

@get('/logout')
def logout_handler(self):
    # 清除会话
    self.session.clear()
    return "Logged out successfully!"

# 注册路由
app.register_routes(session_handler)
app.register_routes(login_handler)
app.register_routes(logout_handler)

app.run()
```

### 访问端点

- **会话信息**：http://localhost:8080/session
- **登录**：POST http://localhost:8080/login
- **登出**：http://localhost:8080/logout
