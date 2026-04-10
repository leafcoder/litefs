# Skill 开发指南

本指南帮助你创建高质量的 Trae Skill。

## Skill 开发流程

### 1. 理解需求

在创建 Skill 之前，明确：
- Skill 解决什么问题？
- 用户会如何触发此 Skill？
- 需要什么资源（脚本、文档、模板）？

### 2. 初始化 Skill

使用初始化脚本创建 Skill 骨架：

```bash
python scripts/init_trae_project.py --path /path/to/project --with-skill my-skill
```

### 3. 编写 SKILL.md

#### Frontmatter 规范

```yaml
---
name: my-skill
description: |
  Skill 功能描述。
  当用户需要：(1) 场景一 (2) 场景二 (3) 场景三 时使用此 Skill。
---
```

**关键点：**
- `name`: 使用 kebab-case 命名
- `description`: 必须包含触发条件

#### 正文结构

根据 Skill 类型选择合适的结构：

**工作流型 Skill：**
```markdown
# Skill Title

## Overview
简要说明

## Workflow
1. 步骤一
2. 步骤二

## Resources
- scripts/
- references/
```

**任务型 Skill：**
```markdown
# Skill Title

## Overview
简要说明

## Quick Start
快速开始示例

## Tasks
### Task 1
### Task 2
```

**参考型 Skill：**
```markdown
# Skill Title

## Overview
简要说明

## Guidelines
### 规范一
### 规范二
```

### 4. 添加资源文件

#### scripts/ 目录

存放可执行脚本：

```
scripts/
├── main_script.py      # 主脚本
├── helper.py           # 辅助脚本
└── utils/              # 工具目录
```

**脚本规范：**
- 添加 shebang (`#!/usr/bin/env python3`)
- 包含 docstring
- 添加使用说明
- 处理错误情况

#### references/ 目录

存放参考文档：

```
references/
├── api_reference.md    # API 参考
├── best_practices.md   # 最佳实践
└── examples.md         # 示例
```

**文档规范：**
- 使用清晰的标题层级
- 包含代码示例
- 添加目录（超过 100 行时）

#### assets/ 目录

存放资源文件：

```
assets/
├── templates/          # 模板文件
├── images/             # 图片
└── fonts/              # 字体
```

### 5. 创建 AGENTS.md（可选）

如果 Skill 需要定义 Agent 角色：

```markdown
---
name: my-agent
description: Agent 描述
---

# Agent Title

## 角色定义 (Persona)
*   **专长**: 描述
*   **风格**: 描述

## 核心能力
*   能力一
*   能力二

## 工作流程
1. 步骤一
2. 步骤二
```

### 6. 验证 Skill

运行验证脚本检查 Skill 格式：

```bash
python scripts/validate_trae_project.py --path /path/to/project
```

## 设计原则

### 1. 简洁优先

- SKILL.md 正文 < 500 行
- 只包含必要信息
- 详细内容移至 references/

### 2. 渐进式加载

```
Level 1: name + description (始终加载)
Level 2: SKILL.md 正文 (触发时加载)
Level 3: references/ (按需加载)
```

### 3. 清晰的触发条件

**好的 description：**
```yaml
description: |
  PDF 处理工具，支持合并、拆分、提取文本。
  当用户需要：(1) 合并多个 PDF (2) 拆分 PDF (3) 提取 PDF 文本 时使用此 Skill。
```

**不好的 description：**
```yaml
description: 处理 PDF 文件
```

### 4. 避免信息重复

- 每条信息只定义一次
- 使用引用而非复制
- 保持单一信息源

## 常见模式

### 决策树模式

```markdown
## Workflow

1. 确定任务类型：
   **创建新文件？** → 执行创建流程
   **编辑现有文件？** → 执行编辑流程

2. 创建流程: [步骤]
3. 编辑流程: [步骤]
```

### 示例驱动模式

```markdown
## Commit Message Format

遵循以下示例：

**Example 1:**
Input: 添加用户认证功能
Output:
```
feat(auth): implement user authentication

Add login endpoint and JWT validation
```
```

### 模板模式

```markdown
## Report Structure

使用以下模板结构：

# [分析标题]

## 执行摘要
[关键发现概述]

## 详细发现
- 发现一
- 发现二

## 建议
1. 建议一
2. 建议二
```

## 测试 Skill

### 1. 手动测试

- 验证触发条件
- 测试工作流程
- 检查输出质量

### 2. 脚本测试

```bash
# 运行脚本
python scripts/main_script.py --help

# 测试示例
python scripts/main_script.py --input example.txt
```

### 3. 验证配置

```bash
python scripts/validate_trae_project.py --path .
```

## 发布 Skill

### 1. 检查清单

- [ ] SKILL.md 格式正确
- [ ] description 包含触发条件
- [ ] 脚本可执行
- [ ] 文档完整
- [ ] 验证通过

### 2. 打包

```bash
# 如果有打包脚本
python scripts/package_skill.py .trae/Skills/my-skill
```

### 3. 迭代改进

根据实际使用反馈持续改进：
- 添加缺失的功能
- 优化工作流程
- 完善文档
