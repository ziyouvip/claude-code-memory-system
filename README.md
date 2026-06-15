# Claude Code Memory System

让 Claude Code 拥有自我进化和记忆系统。

## 背景

每次打开 Claude Code 开始新对话，它都是一张白纸。昨天你花了 10 分钟解释的项目架构、你反复纠正的代码风格偏好、你建立的特殊开发规范——全部归零。

这套系统为 Claude Code 装上"长期记忆"，更进一步，不只是被动记忆，而是主动学习：观察你的行为模式、项目架构，提炼行为规律、项目知识，下次自动应用。

## 系统架构

整个系统由三个核心子系统构成：

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code Memory System                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐ │
│  │  Observation  │   │   Instinct    │   │    Memory     │ │
│  │    Engine     │──▶│    Engine     │──▶│    Engine     │ │
│  │  行为观测层   │   │   模式提炼层   │   │   记忆注入层   │ │
│  └───────────────┘   └───────────────┘   └───────────────┘ │
│         │                   │                   │          │
│         ▼                   ▼                   ▼          │
│  observations.jsonl   instincts/*.md      memories/*.md    │
│                                              auto-evolved.md│
└─────────────────────────────────────────────────────────────┘
```

### 1. 行为观测层 (Observation Engine)

通过 Hook 机制 100% 捕获每次工具调用，写入 JSONL 观测流。

### 2. 模式提炼层 (Instinct Engine)

会话结束时自动分析观测数据，提炼行为模式为原子化 Instinct 规则，置信度动态演化。

- **路径 A：统计模式检测** - 硬编码检测器识别高频模式
- **路径 B：AI 语义分析** - 调用 Claude API 分析深层规律

### 3. 记忆注入层 (Memory Engine)

提炼完成的规则写入规则文件，下次会话启动时自动加载。使用向量检索实现语义召回。

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/claude-code-memory-system.git
cd claude-code-memory-system
```

### 2. 安装依赖

```bash
pip install qdrant-client sentence-transformers
```

### 3. 复制文件到 Claude Code 目录

```bash
# 创建目录
mkdir -p ~/.claude/hooks ~/.claude/bin
mkdir -p ~/.claude/observations ~/.claude/homunculus/instincts/personal
mkdir -p ~/.claude/memory/memories ~/.claude/memory/qdrant
mkdir -p ~/.claude/rules

# 复制脚本
cp hooks/observe.py ~/.claude/hooks/
cp bin/*.py ~/.claude/bin/
```

### 4. 配置 Hooks

编辑 `~/.claude/settings.json`，添加 hooks 配置：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python ~/.claude/hooks/observe.py pre" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          { "type": "command", "command": "python ~/.claude/hooks/observe.py post" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python ~/.claude/bin/auto-analyze-instincts.py && python ~/.claude/bin/auto-evolve.py" }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "python ~/.claude/bin/inject_memory_context.py" }
        ]
      }
    ]
  }
}
```

## 目录结构

```
~/.claude/
├── settings.json              # Hooks 配置
├── hooks/
│   └── observe.py            # 观测采集脚本
├── bin/
│   ├── auto-analyze-instincts.py  # Instinct 分析
│   ├── auto-evolve.py        # Instinct 聚合
│   ├── inject_memory_context.py   # 记忆注入
│   └── observations_rotate.py     # 数据归档
├── observations/
│   └── observations.jsonl    # 观测数据
├── homunculus/
│   └── instincts/
│       └── personal/         # 个人 Instinct 存储
├── memory/
│   ├── memories/             # 记忆文件存储
│   └── qdrant/               # 向量数据库
└── rules/
    └── auto-evolved.md      # 自动演化规则
```

## 记忆类型

| 类型 | 用途 | 示例 |
|------|------|------|
| `user` | 用户偏好、身份认知 | "用户是 Java 专家，TypeScript 中级" |
| `feedback` | 纠正和指导 | "改完代码不主动提交，等用户确认" |
| `project` | 项目上下文 | "当前项目使用 Vitest 做单元测试" |
| `reference` | 外部资源引用 | 文档链接、API 端点 |

## 创建记忆

在 `~/.claude/memory/memories/` 目录下创建 Markdown 文件：

```markdown
---
name: my-preferences
description: 我的编码偏好
metadata:
  type: user
---

## 代码风格
- 使用 2 空格缩进
- 变量命名使用 camelCase
- 函数必须有 JSDoc 注释

## Why
统一的代码风格提高可读性，减少 code review 时间。

## How to apply
在生成代码时自动应用这些风格规则。
```

## 内置模式检测

系统会自动检测以下行为模式：

| 模式 | 触发条件 | 动作 |
|------|----------|------|
| `read-before-edit` | 编辑未读取的文件 | 先读取文件内容 |
| `test-after-change` | 代码修改后 | 运行测试验证 |
| `git-status-check` | Git 操作前 | 检查当前状态 |
| `install-before-use` | 使用 CLI 工具前 | 检查是否安装 |
| `context-gather` | 大规模修改前 | 收集上下文信息 |

## 置信度演化

- 首次发现：confidence = 0.5
- 重复验证：confidence += 0.05（上限 0.9）
- 长期未触发：confidence -= 0.05（低于 0.55 标记为 deprecated）

## 防膨胀机制

- **Observations**：超 5MB 或 8000 行自动按月归档
- **Instinct**：低置信度标记 deprecated
- **Memory**：按类型 TTL 管理
- **auto-evolved.md**：每次覆盖重写

## 实际收益

- **上下文冷启动**：10分钟 → 30秒
- **Token 消耗降低**：约 78%
- **错误重复率下降**：80%
- **知识复利效应**：随时间指数增长

## 参考

- [得物技术：让 Claude Code 拥有自我进化和记忆系统](https://mp.weixin.qq.com/s/PGT49KORSVZYpJxykWnwOw)

## License

MIT License
