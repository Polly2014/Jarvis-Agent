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
│
├── src/
│   ├── __init__.py
│   ├── cli.py                     # CLI 入口 (typer)
│   ├── config.py                  # 配置管理
│   │
│   ├── explorer/                  # 🔍 探索器模块
│   │   ├── __init__.py
│   │   ├── scanner.py             # 目录扫描
│   │   ├── signatures.py          # 特征指纹库
│   │   └── context_extractor.py   # CLAUDE.md 解析
│   │
│   ├── memory/                    # 🧠 记忆系统
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite 操作
│   │   └── models.py              # 数据模型
│   │
│   ├── skills/                    # ⚡ 能力工厂
│   │   ├── __init__.py
│   │   ├── factory.py             # Skill 生成器
│   │   ├── registry.py            # Skill 注册表
│   │   └── templates/             # Skill 模板
│   │       ├── paper-tracker.md
│   │       ├── blog-tracker.md
│   │       └── mcp-monitor.md
│   │
│   ├── llm/                       # 💬 对话引擎
│   │   ├── __init__.py
│   │   └── client.py              # Claude/DeepSeek
│   │
│   ├── wechat/                    # 📱 微信 Bot
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── handlers.py
│   │
│   ├── proactive/                 # ⏰ 主动能力
│   │   ├── __init__.py
│   │   ├── scheduler.py
│   │   └── reminders.py
│   │
│   └── server.py                  # FastAPI 服务
│
├── scripts/
│   ├── deploy.sh
│   └── jarvis-agent.service
│
└── tests/
```

## 核心模块

| 模块 | 职责 | 关键文件 |
|------|------|---------|
| **Explorer** | 目录扫描、项目识别 | `scanner.py`, `signatures.py` |
| **Memory** | 四层记忆系统 | `database.py`, `models.py` |
| **Skills** | Skill 生成与注册 | `factory.py`, `registry.py` |
| **LLM** | 对话引擎 | `client.py` |
| **WeChat** | 企业微信 Bot | `client.py`, `handlers.py` |
| **Proactive** | 主动提醒 | `scheduler.py`, `reminders.py` |

## 命令

```bash
# CLI 命令
jarvis init                    # 交互式初始化
jarvis explore <path>          # 扫描目录发现项目
jarvis projects                # 列出已发现项目
jarvis chat                    # 进入对话模式
jarvis ask "问题"              # 单次提问
jarvis skills                  # 列出所有 skill
jarvis serve                   # 启动 API 服务

# 开发
poetry install                 # 安装依赖
poetry run pytest              # 运行测试
poetry run jarvis              # 运行 CLI
```

## 四层记忆系统

| 层次 | 内容 | 说明 |
|------|------|------|
| 📅 **Episodes** | 事件记忆 | 对话摘要、决策、里程碑 |
| 📂 **Projects** | 项目记忆 | Explorer 发现的项目及状态 |
| 🧠 **Knowledge** | 知识记忆 | 偏好、关系、系统配置 |
| 🎭 **Persona** | 人格记忆 | 骨架（设计）+ 肌肉（涌现） |

## 技术栈

| 组件 | 技术选型 |
|------|---------|
| CLI | Typer |
| Web | FastAPI |
| Database | SQLite + aiosqlite |
| Scheduler | APScheduler |
| WeChat | 企业微信 API |
| LLM | Claude API / DeepSeek API |

## 相关文档

- [设计文档](../docs/plans/2026-02-04-polly-agent-design.md)
- [博客：注意力工程](../content/blog/20260205-Attention-Engineering-Insight/index.md)
- [博客：Jarvis 的诞生](../content/blog/20260205-Jarvis-Agent-Genesis/index.md)

## 进化路线

```
🥚 孵化期 → 🐣 成长期 → 🦋 成熟期 → ⭐ 专属期

Phase 1: CLI 对话 + 目录探索 + 项目发现 + 手动 Skill 确认
Phase 2: 微信集成 + 主动提醒 + 日历/论文追踪
Phase 3: Skill 自生成 + 偏好自学习 + 沙盒验证
Phase 4: 多 Agent 协作 + 语音交互
```
