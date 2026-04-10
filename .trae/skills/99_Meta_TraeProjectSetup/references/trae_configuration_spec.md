# Trae 配置规范

本文档详细说明 Trae 的配置文件规范和最佳实践。

## 目录结构

```
项目根目录/
├── .trae/
│   ├── USER_PREFERENCES.md    # 用户偏好设置
│   ├── rules/
│   │   └── project_rules.md   # 项目规则
│   └── Skills/                # 自定义 Skill 目录
│       └── skill-name/
│           ├── SKILL.md       # Skill 主文件
│           ├── AGENTS.md      # Agent 定义 (可选)
│           ├── scripts/       # 脚本目录 (可选)
│           ├── references/    # 参考文档 (可选)
│           └── assets/        # 资源文件 (可选)
```

## USER_PREFERENCES.md 规范

### 文件位置

`.trae/USER_PREFERENCES.md`

### 必需章节

1. **技术栈偏好 (Tech Stack)**
   - 定义项目使用的技术栈
   - Trae 会优先使用指定的技术

2. **交互风格 (Communication Style)**
   - 定义回复语言
   - 定义详细程度
   - 定义是否使用 Emoji

3. **角色覆盖 (Role Overrides)**
   - 覆盖特定角色的行为
   - 定义角色特定的偏好

4. **禁令 (Constraints)**
   - 定义禁止事项
   - Trae 会严格遵守这些约束

### 示例

```markdown
# User Preferences

## 1. 技术栈偏好 (Tech Stack)
*   **CSS Framework**: Tailwind CSS
*   **State Management**: Zustand
*   **Language**: TypeScript (Strict Mode)

## 2. 交互风格 (Communication Style)
*   **Language**: 中文回复，技术术语保留英文
*   **Detail Level**: 资深开发者模式
*   **Emoji**: 禁用

## 3. 角色覆盖 (Role Overrides)
*   **@Backend Developer**: 优先使用 FastAPI

## 4. 禁令 (Constraints)
*   严禁使用 `any` 类型
```

## project_rules.md 规范

### 文件位置

`.trae/rules/project_rules.md`

### 必需章节

1. **构建与验证命令**
   - Lint 命令
   - TypeCheck 命令
   - Test 命令
   - Build 命令

2. **代码规范**
   - 注释规范
   - 命名规范
   - 代码风格

3. **Git 规范**
   - Commit 规范
   - 分支规范

### 示例

```markdown
# Project Rules

## 构建与验证命令
*   **Lint**: npm run lint
*   **TypeCheck**: npm run typecheck
*   **Test**: npm run test
*   **Build**: npm run build

## 代码规范
*   **函数注释**: 必须添加函数级注释
*   **语言**: 中文注释

## Git 规范
*   **Commit**: 遵循 Conventional Commits
```

## SKILL.md 规范

### 文件位置

`.trae/Skills/<skill-name>/SKILL.md`

### YAML Frontmatter

```yaml
---
name: skill-name
description: Skill 描述，包含触发条件和使用场景
---
```

**必需字段：**
- `name`: Skill 名称（小写字母、数字、连字符）
- `description`: Skill 描述（包含 WHEN to use）

### 命名规范

- 只能包含小写字母、数字和连字符
- 长度不超过 40 个字符
- 不能以连字符开头或结尾
- 不能包含连续连字符

### 目录命名约定

推荐使用以下前缀组织 Skill：

| 前缀 | 分类 |
|-----|------|
| `00_Meta_` | 元技能 |
| `01_Discovery_` | 发现类 |
| `02_Designer_` | 设计类 |
| `03_Developer_` | 开发类 |
| `04_Tester_` | 测试类 |
| `05_Backend_` | 后端类 |
| `05_DevOps_` | DevOps 类 |
| `06_Office_` | 办公类 |
| `07_Security_` | 安全类 |
| `08_AI_` | AI 类 |
| `09_Operations_` | 运营类 |
| `99_Meta_` | 元技能 |

## AGENTS.md 规范

### 文件位置

`.trae/Skills/<skill-name>/AGENTS.md`

### YAML Frontmatter

```yaml
---
name: agent-name
description: Agent 描述
---
```

### 必需章节

1. **角色定义 (Persona)**
   - 专长
   - 风格
   - 背景

2. **核心能力**
   - 列出 Agent 的核心能力

3. **工作流程**
   - 定义工作步骤

## 最佳实践

### 1. 保持简洁

- SKILL.md 正文保持在 500 行以内
- 将详细内容移至 references/ 目录

### 2. 渐进式加载

- 核心内容放在 SKILL.md
- 详细文档放在 references/
- 脚本放在 scripts/

### 3. 清晰的触发条件

在 description 中明确说明：
- 何时使用此 Skill
- 处理什么类型的任务
- 支持什么文件格式

### 4. 避免重复

- 信息只在一个地方定义
- 使用引用而非复制

### 5. 测试脚本

- 所有脚本必须可执行
- 添加适当的错误处理
- 包含使用说明
