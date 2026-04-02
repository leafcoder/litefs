# Litefs 示例

本目录包含 Litefs Web 框架的精选示例，通过可视化的项目展示框架的各种功能。

## 示例列表

| 示例 | 描述 | 主要特性 |
|------|------|----------|
| [01-hello-world](./01-hello-world/) | 入门示例 | 基础应用、JSON响应 |
| [02-routing](./02-routing/) | 路由系统 | 装饰器路由、方法链、路径参数、查询参数 |
| [03-blog](./03-blog/) | 博客系统 | HTML模板、静态文件、会话管理、表单处理 |
| [04-api-service](./04-api-service/) | RESTful API | API设计、认证授权、CRUD操作、分页过滤 |
| [05-fullstack](./05-fullstack/) | 全栈应用 | 综合展示所有功能、中间件、缓存、健康检查 |

## 快速开始

### 1. Hello World (入门)

最简单的 Litefs 应用，适合初学者：

```bash
cd 01-hello-world
python app.py
```

访问 http://localhost:8080

### 2. 路由系统 (进阶)

学习 Litefs 的路由系统：

```bash
cd 02-routing
python app.py
```

### 3. 博客系统 (可视化)

一个完整的博客 Web 应用：

```bash
cd 03-blog
python app.py
```

默认账号: `admin` / `admin123`

### 4. API 服务 (后端)

RESTful API 服务示例：

```bash
cd 04-api-service
python app.py
```

### 5. 全栈应用 (综合)

展示 Litefs 所有功能的完整应用：

```bash
cd 05-fullstack
python app.py
```

## 学习路径

```
初学者 → 01-hello-world → 02-routing → 03-blog
                                      ↓
后端开发 ← 04-api-service ← 05-fullstack
```

## 示例详情

### 01-hello-world

**适合**: 初次接触 Litefs

展示内容:
- 创建应用实例
- 定义路由
- 返回 JSON 数据
- 启动服务器

### 02-routing

**适合**: 学习路由系统

展示内容:
- 装饰器路由定义
- 方法链路由定义
- 路径参数
- 查询参数
- 多种 HTTP 方法

### 03-blog

**适合**: 学习 Web 应用开发

展示内容:
- HTML 页面渲染
- 静态文件服务
- 会话管理（登录/登出）
- 表单处理
- 响应式 CSS 设计

### 04-api-service

**适合**: 学习 API 开发

展示内容:
- RESTful API 设计
- Token + Session 认证
- 权限控制（角色）
- CRUD 操作
- 分页和过滤
- 统一的响应格式

### 05-fullstack

**适合**: 了解 Litefs 全部功能

展示内容:
- 现代路由系统（装饰器 + 方法链）
- 会话管理（用户认证）
- 缓存使用（内存缓存）
- 中间件集成:
  - 日志中间件
  - 安全中间件
  - CORS 中间件
  - 限流中间件
  - 健康检查
- 静态文件服务
- API 接口
- 错误处理
