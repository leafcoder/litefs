# SQLAlchemy 示例

这个示例演示了如何在 Litefs 中使用 SQLAlchemy 进行数据库操作。

## 功能特性

- ✅ 使用 SQLAlchemy 作为 ORM
- ✅ 数据库模型定义
- ✅ 路由和视图函数
- ✅ 模板渲染
- ✅ 完整的 CRUD 操作

## 环境准备

1. 安装依赖：

```bash
pip install sqlalchemy
```

2. 启动应用：

```bash
python app.py
```

3. 访问地址：

```
http://localhost:8080
```

## 项目结构

```
06-sqlalchemy/
├── app.py          # 主应用文件
├── models.py       # 数据库模型定义
├── templates/      # 模板目录
│   ├── base.html   # 基础模板
│   ├── index.html  # 首页模板
│   ├── create.html # 创建文章模板
│   ├── edit.html   # 编辑文章模板
│   └── view.html   # 查看文章模板
└── README.md       # 说明文档
```

## 数据库模型

本示例使用 SQLite 数据库，定义了以下模型：

- `Post` - 博客文章模型

## 路由

- `GET /` - 首页，显示所有文章
- `GET /create` - 创建文章页面
- `POST /create` - 创建文章
- `GET /edit/{id}` - 编辑文章页面
- `POST /edit/{id}` - 更新文章
- `GET /view/{id}` - 查看文章详情
- `GET /delete/{id}` - 删除文章

## 技术栈

- Litefs Web 框架
- SQLAlchemy ORM
- SQLite 数据库
- Mako 模板引擎