# 投票系统示例

本示例展示了如何使用 Litefs 框架构建一个完整的投票系统。

## 功能特性

- ✅ 创建投票活动
- ✅ 添加多个投票选项
- ✅ 投票功能
- ✅ 实时投票结果统计
- ✅ 可视化进度条展示
- ✅ 数据持久化（SQLite）
- ✅ 响应式设计

## 技术栈

- **框架**: Litefs
- **数据库**: SQLite + SQLAlchemy ORM
- **模板引擎**: Mako
- **前端**: HTML5 + CSS3 + JavaScript

## 项目结构

```
11-voting/
├── app.py              # 主应用文件
├── models.py           # 数据库模型
├── README.md           # 项目文档
├── templates/          # HTML 模板
│   ├── base.html       # 基础模板
│   ├── index.html      # 首页
│   ├── poll_detail.html # 投票详情
│   ├── result.html     # 投票结果
│   └── create_poll.html # 创建投票表单
└── static/
    └── style.css       # 样式文件
```

## 数据模型

### Poll（投票主题）
- `id`: 主键
- `title`: 投票标题
- `description`: 投票描述
- `created_at`: 创建时间
- `updated_at`: 更新时间

### Option（投票选项）
- `id`: 主键
- `poll_id`: 所属投票ID
- `text`: 选项文本
- `created_at`: 创建时间

### Vote（投票记录）
- `id`: 主键
- `poll_id`: 所属投票ID
- `option_id`: 所选选项ID
- `ip_address`: 投票者IP地址
- `user_agent`: 用户代理
- `created_at`: 投票时间

## 运行示例

### 1. 进入示例目录

```bash
cd examples/11-voting
```

### 2. 初始化数据库

首次运行需要初始化数据库表：

```bash
python app.py
```

然后访问 `http://localhost:8080/init` 初始化数据库。

### 3. 访问应用

访问 `http://localhost:8080` 查看投票列表。

## 使用流程

### 创建投票

1. 点击"创建新投票"按钮
2. 填写投票标题和描述
3. 添加至少两个选项
4. 点击"创建投票"

### 投票

1. 在首页查看所有投票活动
2. 点击"查看"按钮进入投票详情
3. 选择一个选项
4. 点击"投票"按钮

### 查看结果

投票后可以立即查看结果，系统会显示：
- 每个选项的得票数
- 得票百分比
- 总投票数
- 可视化进度条

## 示例数据

系统会自动创建一些示例投票数据，您可以直接体验投票功能。

## 自定义开发

### 添加新功能

- **用户认证**: 可以添加用户系统，防止重复投票
- **投票有效期**: 可以设置投票的开始和结束时间
- **匿名投票**: 可以选择是否记录IP地址
- **多选投票**: 可以修改为多选模式

### 数据库迁移

如果需要修改数据模型，可以使用 SQLAlchemy 的迁移工具：

```python
from alembic import op
import sqlalchemy as sa
```

## 注意事项

- 示例代码仅用于演示，实际生产环境中需要根据具体需求进行修改
- 当前实现使用 SQLite 数据库，适合小规模应用
- 生产环境建议使用 MySQL 或 PostgreSQL
- 建议添加用户认证防止重复投票
- 可以添加验证码防止恶意投票

## 相关链接

- [Litefs 官方文档](https://github.com/leafcoder/litefs)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [Mako 模板文档](https://www.makotemplates.org/)

## 许可证

MIT License
