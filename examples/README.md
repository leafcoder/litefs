# Litefs 示例

本目录包含 Litefs 框架的示例代码，展示框架的各种功能。

## 示例列表

### 1. 基本示例 (`basic.py`)

展示 Litefs 框架的基本使用，包括：
- 创建应用实例
- 添加路由（GET 和 POST）
- 运行服务器

### 2. 高级示例 (`advanced.py`)

展示 Litefs 框架的高级功能，包括：
- 响应对象的使用（JSON 响应）
- 配置管理
- 插件系统
- 安全特性（CSRF 保护）

### 3. 经典示例目录

#### 3.1 Hello World (`01-hello-world/`)

最简单的 Litefs 应用，展示基本的路由和响应。

#### 3.2 路由示例 (`02-routing/`)

展示 Litefs 框架的路由系统，包括：
- 基本路由
- 带参数的路由
- 正则表达式路由

#### 3.3 博客示例 (`03-blog/`)

展示 Litefs 框架的完整功能，包括：
- 路由系统
- 模板渲染
- 静态文件服务

#### 3.4 API 服务示例 (`04-api-service/`)

展示如何使用 Litefs 框架创建 RESTful API 服务。

#### 3.5 全栈示例 (`05-fullstack/`)

展示 Litefs 框架与前端技术的集成，包括：
- 后端 API
- 前端 JavaScript
- 静态文件服务

#### 3.6 SQLAlchemy 示例 (`06-sqlalchemy/`)

展示 Litefs 框架与 SQLAlchemy ORM 的集成，包括：
- 数据库模型定义
- 数据库操作
- 模板渲染
- 表单处理

## 运行示例

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行基本示例

```bash
python examples/basic.py
```

然后访问：http://localhost:9090

### 3. 运行高级示例

```bash
python examples/advanced.py
```

然后访问：http://localhost:9090

### 4. 运行经典示例

#### 4.1 运行 Hello World 示例

```bash
cd examples/01-hello-world
python app.py
```

然后访问：http://localhost:8080

#### 4.2 运行路由示例

```bash
cd examples/02-routing
python app.py
```

然后访问：http://localhost:8080

#### 4.3 运行博客示例

```bash
cd examples/03-blog
python app.py
```

然后访问：http://localhost:8080

#### 4.4 运行 API 服务示例

```bash
cd examples/04-api-service
python app.py
```

然后访问：http://localhost:8080

#### 4.5 运行全栈示例

```bash
cd examples/05-fullstack
python app.py
```

然后访问：http://localhost:8080

#### 4.6 运行 SQLAlchemy 示例

```bash
cd examples/06-sqlalchemy
python app.py
```

然后访问：http://localhost:8080

## 功能说明

### 基本示例路由

- GET `/` - 首页，返回 "Hello, Litefs!"
- GET `/user/{id}` - 获取用户信息，返回用户 ID
- POST `/user` - 创建用户，返回创建的用户名

### 高级示例路由

- GET `/` - 首页，返回 JSON 响应，包含框架信息
- GET `/config` - 获取配置信息，返回当前配置
- GET `/plugins` - 获取插件信息，返回已加载的插件
- POST `/form` - 表单提交，展示 CSRF 保护

## 注意事项

- 示例代码仅用于演示，实际生产环境中需要根据具体需求进行修改
- 高级示例中的插件需要在运行前确保插件目录结构正确
- CSRF 保护需要在表单中包含 CSRF 令牌
