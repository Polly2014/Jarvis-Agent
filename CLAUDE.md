# Jarvis-Agent

> 🥚 数码宝贝式 AI Agent —— 从空白开始，探索进化，成为你的专属伙伴

## 项目愿景

Jarvis-Agent 是一个探索式进化的个人 AI 助手：
- 🥚 **空白开始**：初始形态是通用的 Jarvis
- 🔍 **主动探索**：扫描用户目录，发现项目和任务
- ⚡ **能力生成**：通过交互动态创建专属 skill
- 🦋 **持续进化**：从通用助手进化成专属伙伴

## 快速开始

```bash
# 安装
cd Jarvis-Agent
poetry install

# 初始化
jarvis init

# 探索你的项目目录
jarvis explore ~/projects/

# 开始对话
jarvis chat
```

## 项目结构

```
Jarvis-Agent/
├── CLAUDE.md                      # 项目文档（本文件）
├── pyproject.toml                 # Poetry 配置
├── .env.example                   # 环境变量模板
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── cli.py                     # CLI 入口 (Typer + Rich)
│   ├── config.py                  # 配置管理 (~/.jarvis/)
│   ├── main.py                    # 模块入口
│   │
│   ├── daemon/                    # 🫀 守护进程
│   │   ├── __init__.py
│   │   ├── daemon.py              # 核心心跳循环 + 文件监控
│   │   ├── discovery.py           # 发现事件模型
│   │   └── notifier.py            # 通知系统
│   │
│   ├── explorer/                  # �️ 感知模块
│   │   ├── __init__.py
│   │   ├── scanner.py             # 目录扫描
│   │   ├── signatures.py          # 特征指纹库
│   │   ├── models.py              # 项目模型
│   │   └── context_extractor.py   # CLAUDE.md 解析
│   │
│   ├── memory/                    # 🧠 记忆系统 (Phase 2 混合架构)
│   │   ├── __init__.py
│   │   ├── writer.py              # MemoryWriter (Markdown 写入)
│   │   ├── index.py               # MemoryIndex (SQLite FTS5 索引)
│   │   ├── database.py            # SQLite 操作 (legacy)
│   │   └── models.py              # 数据模型
│   │
│   ├── llm/                       # 💬 对话引擎
│   │   ├── __init__.py
│   │   └── client.py              # Agent Maestro / Claude API
│   │
│   └── proactive/                 # ⏰ 调度系统
│       ├── __init__.py
│       └── scheduler.py           # APScheduler 调度
│
└── scripts/                       # 部署脚本
    ├── deploy.sh
    ├── install_daemon.sh          # macOS/Linux 安装
    ├── uninstall_daemon.sh
    ├── com.polly.jarvis.plist     # macOS launchd
    └── jarvis-agent.service       # Linux systemd
```

## 核心模块

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| **Daemon** | 后台守护、文件监控、心跳 | `daemon.py`, `discovery.py` |
| **Explorer** | 目录扫描、项目识别 | `scanner.py`, `signatures.py` |
| **Memory** | 混合记忆系统 (Markdown + SQLite) | `writer.py`, `index.py` |
| **LLM** | 对话引擎 (Agent Maestro) | `client.py` |
| **Proactive** | 调度系统 | `scheduler.py` |

## 命令

```bash
# 主入口 (Phase 2 ✅)
jarvis                         # 直接进入聊天模式
jarvis "问题"                  # 单次提问
jarvis -d                      # 启动 daemon
jarvis -s                      # 查看状态
jarvis -r                      # 停止 daemon

# Phase 2 新增命令
jarvis recall "关键词"         # 搜索记忆
jarvis think                   # 手动触发思考
jarvis insights                # 查看最近洞察

# 斜杠命令 (聊天中使用)
/start       # 启动 daemon
/rest        # 停止 daemon
/status      # 查看状态
/discoveries # 查看发现
/recall      # 搜索记忆
/think       # 触发思考
/insights    # 查看洞察
/explore     # 探索目录
/projects    # 列出项目
/skills      # 列出 skills
/init        # 初始化
/help        # 帮助
/exit /quit  # 退出聊天

# 自然语言控制 (聊天中使用)
"帮我挂机"                     # → 启动 daemon
"休息"                         # → 停止 daemon
"你在干嘛"                     # → 查看状态

# 传统子命令 (仍可用)
jarvis init                    # 交互式初始化
jarvis start                   # 启动后台守护进程
jarvis start -f                # 前台运行（调试）
jarvis status                  # 查看生命体征

# 开发
poetry install                 # 安装依赖
poetry run python -m src.cli   # 运行 CLI
pipx install .                 # 全局安装 jarvis 命令
```

## 记忆系统架构 (Phase 2)

**核心理念**: "Markdown 存内容，SQLite 做索引"

```
~/.jarvis/memory/
├── daily/           # 📅 编年体日志 (2026-02-05.md)
│   └── 发现/对话/决策/里程碑
├── topics/          # 📚 纪传体主题
└── persona.md       # 🎭 人格定义
```

| 组件 | 用途 | 特点 |
|------|------|------|
| **MemoryWriter** | Markdown 写入 | LLM-native，人类可读，Git 友好 |
| **MemoryIndex** | SQLite FTS5 索引 | 毫秒级搜索，标签/日期/重要性过滤 |

### 四层记忆模型

| 层次 | 内容 | 说明 |
|------|------|------|
| 📅 **Episodes** | 事件记忆 | 对话摘要、决策、里程碑 |
| 📂 **Projects** | 项目记忆 | Explorer 发现的项目及状态 |
| 🧠 **Knowledge** | 知识记忆 | 偏好、关系、系统配置 |
| 🎭 **Persona** | 人格记忆 | 骨架（设计）+ 肌肉（涌现） |

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| CLI | Typer + Rich + prompt_toolkit |
| Memory | Markdown + SQLite FTS5 |
| File Watch | watchdog |
| Scheduler | APScheduler |
| HTTP | httpx (trust_env=False) |
| LLM | Agent Maestro (OpenAI-compatible) |

## 配置

运行时配置存储在 `~/.jarvis/`:

```
~/.jarvis/
├── config.json          # 主配置
├── index.db             # SQLite FTS5 索引
├── state.json           # 心跳状态
├── discoveries.json     # 发现记录
├── memory/              # Markdown 记忆
│   ├── daily/           # 编年体
│   ├── topics/          # 纪传体
│   └── persona.md       # 人格
└── logs/
    └── daemon.log       # 守护进程日志
```

**config.json 示例**:
```json
{
  "llm": {
    "provider": "openai",
    "base_url": "http://localhost:23335/api/openai",
    "model": "claude-sonnet-4"
  },
  "watch_paths": ["/path/to/your/projects"],
  "think_interval": 300
}
```

## 相关文档

- [设计文档](../docs/plans/2026-02-04-polly-agent-design.md)
- [博客：注意力工程](../content/blog/20260205-Attention-Engineering-Insight/index.md)
- [博客：Jarvis 的诞生](../content/blog/20260205-Jarvis-Agent-Genesis/index.md)

---

## 🧬 进化路线图

### 设计原则

```
核心理念：一点不多，一点不少
目标用户：开发者（打造 Agent 本身）
进化方向：从"能对话"到"能进化"
```

### 五维能力模型

| 维度 | 能力 | 核心问题 |
|------|------|---------|
| 👁️ **感知** | 探索、监控 | Agent 如何发现世界？ |
| 🧠 **记忆** | 存储、检索、关联 | Agent 如何记住经历？ |
| 💭 **思考** | 推理、规划、决策 | Agent 如何形成判断？ |
| 🦾 **行动** | 执行、工具调用 | Agent 如何改变世界？ |
| 🔄 **进化** | 自学习、Skill 生成 | Agent 如何提升自己？ |

---

### 🥚 Phase 1：感知与记忆 ✅

> **里程碑**：Agent 能感知环境，记住交互

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 👁️ 感知 | 目录扫描 (`explore`) | ✅ |
| 👁️ 感知 | 文件监控 (`watchdog`) | ✅ |
| 👁️ 感知 | 项目特征识别 (`signatures`) | ✅ |
| 🧠 记忆 | SQLite 存储 | ✅ |
| 🧠 记忆 | 项目记忆 (projects) | ✅ |
| 🧠 记忆 | 事件记忆 (episodes) | ✅ |
| 💭 思考 | LLM 对话 (chat/ask) | ✅ |
| 🦾 行动 | CLI 命令执行 | ✅ |

**验证标准**：
- [x] `jarvis explore` 能发现项目
- [x] `jarvis chat` 能正常对话
- [x] `jarvis start` 守护进程持续运行

---

### 🐣 Phase 2：思考与推理 ✅

> **里程碑**：Agent 能主动思考，形成判断

**核心目标**：从"被动问答"到"主动思考"

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 💭 Think Loop | 守护进程定期"思考" | ✅ |
| 💭 手动思考 | `jarvis think` 命令 | ✅ |
| 🧠 混合记忆 | Markdown + SQLite FTS5 | ✅ |
| 🧠 记忆检索 | `jarvis recall` 全文搜索 | ✅ |
| 🧠 洞察查看 | `jarvis insights` 命令 | ✅ |
| 👁️ 变化检测 | 文件监控 + LLM 分析 | ✅ |

**新增命令**：
```bash
jarvis recall "关键词"    # 检索记忆 ✅
jarvis think              # 手动触发思考 ✅
jarvis insights           # 查看最近洞察 ✅
```

**验证标准**：
- [x] 守护进程能定期产生"思考日志"
- [x] 检测到重要变化时，记录到 Markdown
- [x] `jarvis recall` 能检索相关记忆

---

### 🦋 Phase 3：行动与工具（2-3 周）

> **里程碑**：Agent 能调用工具，执行任务

**核心目标**：从"只能说"到"能做事"

| 能力维度 | 功能 | 说明 |
|---------|------|------|
| 🦾 **Tool Registry** | 工具注册表 | 发现、注册、调用 |
| 🦾 **内置工具** | 文件/Shell/HTTP | 基础操作能力 |
| 🦾 **MCP 集成** | 复用 MCP Server | 扩展工具生态 |
| 💭 **任务规划** | 分解复杂任务 | 多步骤执行 |
| 💭 **执行决策** | 自动/确认判断 | 安全控制 |

**新增命令**：
```bash
jarvis tools              # 列出可用工具
jarvis run <tool> <args>  # 手动调用工具
```

**验证标准**：
- [ ] `jarvis chat` 中能调用工具完成任务
- [ ] 危险操作前能请求确认
- [ ] 能连接现有 MCP Server

---

### ⭐ Phase 4：进化与自生成（3-4 周）

> **里程碑**：Agent 能自己创建新能力

**核心目标**：从"用别人的工具"到"创造自己的工具"

| 能力维度 | 功能 | 说明 |
|---------|------|------|
| 🔄 **Skill 自生成** | 从交互提炼模式 | 创建可复用 Skill |
| 🔄 **偏好自学习** | 记录用户偏好 | 个性化适应 |
| 🔄 **沙盒验证** | 安全测试新能力 | 防止错误 |
| 🧠 **Persona 进化** | 动态更新人格 | 成为专属伙伴 |
| 💭 **元认知** | 反思能力边界 | 知道自己不知道什么 |

**新增命令**：
```bash
jarvis skill create       # 手动创建 Skill
jarvis skill test <name>  # 测试 Skill
jarvis reflect            # 触发元认知反思
```

**验证标准**：
- [ ] 重复 3 次类似任务后，自动提议创建 Skill
- [ ] `jarvis skills` 显示自生成的 Skill
- [ ] Skill 验证失败时不会被启用

---

### 进化全景图

```
                    ┌─────────────────────────────────────────────────────┐
                    │                   Phase 4: 进化                      │
                    │        🔄 Skill 自生成 → 偏好学习 → 元认知            │
                    └─────────────────────────────────────────────────────┘
                                              ▲
                    ┌─────────────────────────────────────────────────────┐
                    │                   Phase 3: 行动                      │
                    │        🦾 Tool Registry → MCP → 任务执行             │
                    └─────────────────────────────────────────────────────┘
                                              ▲
                    ┌─────────────────────────────────────────────────────┐
                    │                Phase 2: 思考 ✅                       │
                    │   💭 Think Loop → 🧠 Markdown+FTS5 → 📊 Insights    │
                    └─────────────────────────────────────────────────────┘
                                              ▲
                    ┌─────────────────────────────────────────────────────┐
                    │                Phase 1: 感知与记忆 ✅                 │
                    │        👁️ Explorer → 🧠 Memory → 💬 Chat             │
                    └─────────────────────────────────────────────────────┘
```

### 时间线

| Phase | 预估时间 | 核心交付 |
|-------|---------|---------|
| Phase 1 | ✅ 完成 | 感知 + 记忆 + 对话 |
| Phase 2 | ✅ 完成 | Think Loop + 混合记忆 + 检索 |
| Phase 3 | 2-3 周 | Tool Registry + 工具调用 |
| Phase 4 | 3-4 周 | Skill 自生成 + 验证 |
