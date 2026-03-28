# 会话管理

Litefs 会话管理示例。

## 示例文件

- `session_example.py` - 会话管理示例主程序
- `site/session.py` - 会话处理器

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
