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
│   │
│   ├── cli/                       # 🖥️ CLI 入口 (Phase 2.5 模块化)
│   │   ├── __init__.py            # app 定义 + main callback + 子命令注册
│   │   ├── common.py              # 常量、路径、状态查询、通用工具
│   │   ├── chat.py                # 聊天循环、补全器、streaming
│   │   ├── daemon_cmds.py         # daemon 生命周期 (start/rest/status)
│   │   ├── memory_cmds.py         # 记忆系统 (recall/think/insights)
│   │   ├── explore_cmds.py        # 探索与项目 (init/explore/projects/discoveries/skills)
│   │   └── evolution_cmds.py      # 进化系统 (reflect/abilities/patterns/skill)
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
│   │   ├── __init__.py            # 导出 MemoryWriter, MemoryIndex
│   │   ├── writer.py              # MemoryWriter (Markdown 写入)
│   │   └── index.py               # MemoryIndex (SQLite FTS5 索引)
│   │
│   ├── llm/                       # 💬 对话引擎 (Phase 3 ✅)
│   │   └── __init__.py            # JarvisLLMClient (streaming + function calling)
│   │
│   ├── tools/                     # 🔧 工具系统 (Phase 3 ✅)
│   │   ├── __init__.py            # 导出 Tool, ToolResult, ToolRegistry
│   │   ├── base.py                # Tool ABC + ToolResult
│   │   ├── registry.py            # ToolRegistry (自动发现 + 全局单例)
│   │   ├── builtins/              # Layer 0 — 原子工具
│   │   │   ├── file_read.py       # 读取文件
│   │   │   ├── file_write.py      # 写入文件
│   │   │   ├── shell_exec.py      # 执行 Shell 命令
│   │   │   └── http_request.py    # HTTP 请求
│   │   └── meta/                  # Layer 1 — 元工具
│   │       ├── create_skill.py    # 创建 Skill
│   │       ├── create_tool.py     # 创建自定义 Tool
│   │       └── create_mcp.py      # 创建 MCP Server 骨架
│   │
│   └── evolution/                 # 🔄 进化系统 (Phase 4 ✅)
│       ├── __init__.py            # 导出所有进化模块
│       ├── pattern_detector.py    # 交互指纹 + 模式检测
│       ├── skill_registry.py      # Skill 注册表 (发现/加载/匹配)
│       ├── skill_generator.py     # Skill 草稿生成 (LLM + fallback)
│       ├── sandbox.py             # 沙盒验证 (安全检查 + LLM 审计)
│       ├── preference_learner.py  # 偏好学习 (观察 + 衰减 + 合并)
│       └── metacognition.py       # 元认知 (五维雷达 + 反思报告)
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
| **CLI** | 命令行入口、聊天循环 | `cli/__init__.py`, `cli/chat.py` |
| **Daemon** | 后台守护、文件监控、心跳 | `daemon/daemon.py`, `daemon/discovery.py` |
| **Explorer** | 目录扫描、项目识别 | `explorer/scanner.py`, `explorer/signatures.py` |
| **Memory** | 混合记忆系统 (Markdown + SQLite) | `memory/writer.py`, `memory/index.py` |
| **LLM** | 对话引擎 (Streaming + Function Calling) | `llm/__init__.py` |
| **Tools** | 工具系统 (Layer 0 原子 + Layer 1 元工具) | `tools/base.py`, `tools/registry.py` |

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

# Phase 3 新增命令
jarvis tools                   # 列出所有可用工具

# Phase 4 新增命令
jarvis reflect                 # 触发元认知反思
jarvis abilities               # 查看五维能力雷达
jarvis patterns                # 查看已检测的交互模式
jarvis skill list [--all]      # 列出 Skills
jarvis skill enable <name>     # 启用 Skill
jarvis skill disable <name>    # 禁用 Skill
jarvis skill delete <name>     # 删除 Skill
jarvis skill test <name>       # 沙盒测试 Skill

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
/tools       # 列出可用工具
/reflect     # 元认知反思
/abilities   # 五维能力雷达
/patterns    # 交互模式检测
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
├── daemon.pid           # Daemon 进程 PID (Phase 2.5+)
├── discoveries.json     # 发现记录
├── chat_history         # 聊天历史 (prompt_toolkit)
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

### 🧹 Phase 2.5：代码质量 ✅

> **里程碑**：清理技术债务，模块化重构

| 改动 | 说明 | 状态 |
|------|------|------|
| 🔒 线程安全 | `JarvisEventHandler._recent_changes` 加 `threading.Lock` | ✅ |
| 🗑️ 清除死代码 | 删除 `main.py`, `config.py`, `proactive/`, `serve` 命令 | ✅ |
| 🗑️ 清理遗留模块 | 删除 `llm/client.py`, `memory/database.py`, `memory/models.py` | ✅ |
| 📦 CLI 模块化 | 1909 行 `cli.py` → `cli/` 包 (6 个模块) | ✅ |
| 📂 projects 命令 | 实现 `jarvis projects`（读取 discoveries.json） | ✅ |
| 🎭 persona 初始化 | `jarvis init` 自动调用 `MemoryWriter.init_persona()` | ✅ |
| 🔧 PID 管理 | `daemon.pid` + `SIGTERM` 优雅停止 | ✅ |

---

### 🦋 Phase 3：行动与工具 ✅

> **里程碑**：Agent 能调用工具，执行任务

**核心目标**：从"只能说"到"能做事"——两层工具架构

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 🔧 **Tool 基础框架** | Tool ABC + ToolResult + ToolRegistry | ✅ |
| 🔹 **Layer 0 原子工具** | file_read, file_write, shell_exec, http_request | ✅ |
| 🔸 **Layer 1 元工具** | create_skill, create_tool, create_mcp | ✅ |
| 💬 **LLM Function Calling** | JarvisLLMClient (streaming + tool_calls) | ✅ |
| 🖥️ **CLI 命令** | `jarvis tools` + `/tools` 斜杠命令 | ✅ |
| 🔒 **安全控制** | 路径白名单、危险命令拦截、超时保护 | ✅ |

**架构设计**：
```
Layer 0 (Atomic)  — 不可再分: file_read, file_write, shell_exec, http_request
Layer 1 (Meta)    — 构造新能力: create_skill, create_tool, create_mcp
Layer 2 (Emergent)— Jarvis 自己创造 (Phase 4)
```

**验证标准**：
- [x] `jarvis tools` 显示 7 个工具
- [x] `jarvis chat` 中 LLM 能通过 function calling 调用工具
- [x] 危险 shell 命令被拦截
- [x] 系统路径写入被阻止

---

### ⭐ Phase 4：进化与自生成 ✅

> **里程碑**：Agent 能自己创建新能力

**核心目标**：从"用别人的工具"到"创造自己的工具"

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 🔄 **模式检测** | InteractionFingerprint + PatternDetector | ✅ |
| 🔄 **Skill 注册表** | SkillRegistry (发现/加载/启禁/匹配) | ✅ |
| 🔄 **Skill 自生成** | SkillGenerator (LLM 提议 + fallback) | ✅ |
| 🔄 **沙盒验证** | SkillSandbox (5 项安全检查 + LLM 审计) | ✅ |
| 🔄 **偏好学习** | PreferenceLearner (观察 + 衰减 + 合并) | ✅ |
| 💭 **元认知** | Metacognition (五维雷达 + 反思报告) | ✅ |
| 🖥️ **CLI 集成** | reflect/abilities/patterns + skill 子命令 | ✅ |
| 🫀 **Daemon 集成** | 定期模式检测 + 偏好合并 | ✅ |

**架构设计**：
```
InteractionFingerprint → PatternDetector → SkillGenerator → SkillSandbox → SkillRegistry
                                                                              ↕
UserPreference ← PreferenceLearner                              Metacognition (五维雷达)
```

**验证标准**：
- [x] 重复 3 次类似任务后，自动提议创建 Skill
- [x] `jarvis skill list` 显示自生成的 Skill
- [x] Skill 验证失败时不会被启用
- [x] `jarvis reflect` 输出完整反思报告
- [x] 79/79 单元测试全部通过

---

### 进化全景图

```
                    ┌─────────────────────────────────────────────────────┐
                    │                Phase 5: Skill Evolution 📋            │
                    │  👁️ Correction Observer → 📊 Evolution Report → 🔄    │
                    └─────────────────────────────────────────────────────┘
                                              ▲
                    ┌─────────────────────────────────────────────────────┐
                    │                   Phase 4: 进化 ✅                    │
                    │    🔄 模式检测 → Skill 生成 → 偏好学习 → 元认知        │
                    └─────────────────────────────────────────────────────┘
                                              ▲
                    ┌─────────────────────────────────────────────────────┐
                    │                   Phase 3: 行动 ✅                    │
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
| Phase 2.5 | ✅ 完成 | 代码质量清理 + CLI 模块化 + PID 管理 |
| Phase 3 | ✅ 完成 | Tool Registry + 工具调用 + 安全控制 |
| Phase 4 | ✅ 完成 | 模式检测 + Skill 自生成 + 偏好学习 + 元认知 |
| Phase 4.5 | ✅ 完成 | Context Window 管理（token-aware 截取 + LLM 压缩 + fallback） |
| Phase 5 | 📋 ~2 周 | Skill Evolution Observer + 主动提醒 + 闭环优化 |

---

### 🧬 Phase 5: Skill Evolution Observer 📋

> **里程碑**：Agent 能监控 skill 执行后的人工修正，自动积累 Evolution Log，主动建议优化

**核心目标**：Phase 4 = 创建 skill (0→1)，Phase 5 = 优化 skill (v1→v2)。完整的 skill 生命周期管理。

**P0 验证已通过** (2026-03-04)：手工对 blog-writer 和 memory-keeper 各收集 5 条 git diff 信号，分别产出 3 个有效 patch。

| 子阶段 | 内容 | 预估 |
|--------|------|------|
| P5.1 | SkillEvolutionObserver — 静默采集 (复用 daemon think loop + git log) | 3-5 天 |
| P5.2 | Evolution Report + 主动提醒 (累积 ≥5 条信号通知) | 3-5 天 |
| P5.3 | CLI 闭环 (`jarvis skill evolve <name>`) | 2-3 天 |

**新增模块**：`src/evolution/skill_evolution.py`（不重写，加一层）

→ 完整规划详见 [Phase 5 设计文档](docs/plans/2026-03-04-phase5-skill-evolution-design.md)
