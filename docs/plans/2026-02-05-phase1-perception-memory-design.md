# Phase 1: 感知与记忆 设计文档

> 📅 2026-02-05  
> 🎯 让 Jarvis 拥有"眼睛"和"耳朵"——感知世界，记住经历

---

## 1. 核心理念

**"Agent 不是被动工具，是有心跳的生命体。"**

传统 CLI 工具只在被调用时存在。Jarvis 不同——它有一个 Daemon 常驻后台，像心跳一样持续感知周围的变化。这不是技术炫技，而是 Agent 的本质需求：**无感知则无智能，无记忆则无进化**。

### Agent 四大内核

```
🌉 遇水搭桥 — 遇到新任务时，自主创建 Skill/MCP
💪 肌肉涌现 — 能力从交互中自然生长，非预设
🎭 渐进性格 — 骨架（价值观）设计 + 肌肉（偏好）涌现
🧠 记忆迭代 — 无记忆则无进化
```

### 设计原则

1. **真挂机**：Daemon 必须真正常驻后台，不能作假
2. **LLM 驱动发现**：用 LLM 智能分析，而非 if-else 规则
3. **特征指纹匹配**：项目识别通过签名系统，可扩展
4. **最小可用**：只做感知和记忆，不做多余的事

---

## 2. Daemon 心跳进程

### 2.1 配置模型

```python
@dataclass
class DaemonConfig:
    think_interval_seconds: int = 60          # 思考间隔
    self_reflect_interval_seconds: int = 3600 # 自省间隔
    watch_paths: list[str]                    # 监控路径
    llm_provider: str = "openai"
    llm_base_url: str = "http://localhost:23335/api/openai"
    llm_model: str = "claude-sonnet-4"
```

### 2.2 生命体征

```python
@dataclass
class LifeSigns:
    status: str = "running"       # running | resting | stopped
    last_heartbeat: datetime
    discoveries_today: int
    important_discoveries_today: int
```

### 2.3 核心类

```python
class JarvisDaemon:
    async def start(self)                         # 启动心跳循环
    async def stop(self)                          # 优雅停止
    async def _think_loop(self)                   # 核心思考循环（见下文）
    async def _think(self, changes) -> Discovery  # LLM 分析文件变化
    async def _self_reflect(self) -> Discovery    # 无变化时自省
    def _process_discovery(self, discovery)        # 发现处理管线
    def _fallback_analysis(self, changes)          # LLM 不可用时的规则后备
```

### 2.4 Think Loop 架构

```
┌─────────────────────────────────────────┐
│           _think_loop()                 │
│                                         │
│  while alive:                           │
│    1. 更新心跳 (LifeSigns)              │
│    2. 收集文件变化 (get_and_clear)       │
│    3. if 有变化:                        │
│         → _think(changes)  # LLM 分析   │
│       elif 超时:                        │
│         → _self_reflect()  # LLM 自省   │
│    4. if discovery:                     │
│         → _process_discovery()          │
│           ├─ DiscoveryStore.add()        │
│           └─ Notifier.notify()          │
│    5. sleep(think_interval)             │
└─────────────────────────────────────────┘
```

**双模式思考**：
- **有变化** → `_think(changes)`：将文件变化交给 LLM 分析，提炼为有意义的 Discovery
- **无变化超时** → `_self_reflect()`：LLM 自省，回顾最近的发现和状态

### 2.5 文件监控

```python
class JarvisEventHandler(FileSystemEventHandler):
    """watchdog 事件处理器"""
    _recent_changes: list[dict]
    _lock: threading.Lock                  # Phase 2.5 修复的线程安全

    def on_modified(self, event)            # 文件修改事件
    def on_created(self, event)             # 文件创建事件
    def get_and_clear_changes(self) -> list[dict]  # 原子读取+清空
```

关键设计：watchdog 在子线程中收集事件，主循环在 asyncio 中读取。需要 `threading.Lock` 保护共享的 `_recent_changes` 列表。

---

## 3. Explorer 感知模块

### 3.1 目录扫描器

```python
# src/explorer/scanner.py

def scan_directory(
    root_path: Path,
    max_depth: int = 2,
    ignore_patterns: List[str] = None
) -> List[ProjectMeta]:
```

- **DFS 遍历** + 深度限制（默认 2 层）
- **智能忽略**：`.git`、`node_modules`、`__pycache__`、`venv`、`dist`、`build`、`public`
- 在每个目录调用 `match_signatures()` 进行特征匹配

### 3.2 特征指纹库

```python
# src/explorer/signatures.py

class ProjectType(str, Enum):
    ZOLA_BLOG
    ACADEMIC_PAPER
    MCP_SERVER
    VSCODE_EXTENSION
    PYTHON_PROJECT
    BOOK_TRANSLATION
    UNKNOWN

@dataclass
class ProjectSignature:
    type: ProjectType
    description: str
    required_files: List[str]           # 必须存在的文件/目录
    optional_files: List[str]           # 可选文件（加分项）
    pattern_in_file: Dict[str, str]     # 文件内容正则匹配
    skill_template: str                 # 对应的 Skill 模板
    priority: int                       # 匹配优先级（越高越优先）
```

**已内置 6 种项目签名**：

| 类型 | 必要文件 | 内容匹配 | 优先级 |
|------|---------|---------|--------|
| Zola Blog | `config.toml`, `content/`, `templates/` | — | 10 |
| MCP Server | `pyproject.toml` | 含 `fastmcp` | 9 |
| VS Code Extension | `package.json`, `src/extension.ts` | — | 9 |
| Academic Paper | `*.tex` | — | 8 |
| Python Project | `pyproject.toml` | — | 5 |
| Book Translation | `*.md`, `terminology*.json` | — | 3 |

**匹配逻辑**：按优先级从高到低尝试，`required_files` 全部存在则命中，计算 `confidence` 分数。

### 3.3 项目模型

```python
# src/explorer/models.py

@dataclass
class ProjectMeta:
    name: str                        # 项目名（目录名）
    path: Path                       # 绝对路径
    type: ProjectType                # 项目类型
    description: str = ""            # 描述
    status: str = ""                 # 状态
    confidence: float = 0.0          # 匹配置信度
    context: dict = field(...)       # 提取的上下文信息
    suggested_skill: str = ""        # 建议创建的 Skill

    @property
    def icon(self) -> str:           # 类型图标映射
        # ZOLA_BLOG → ✍️, ACADEMIC_PAPER → 📄, MCP_SERVER → 📦, ...
```

---

## 4. Discovery 发现系统

### 4.1 发现模型

```python
# src/daemon/discovery.py

class DiscoveryType(Enum):
    FILE_INSIGHT      # 文件变化洞察
    PROJECT_UPDATE    # 项目状态更新
    REMINDER          # 提醒
    SELF_REFLECT      # 自省
    SUGGESTION        # 建议

@dataclass
class Discovery:
    title: str
    content: str
    importance: int                    # 1-5 (5=最重要)
    type: DiscoveryType
    id: str                            # "d-20260205-abc123" 格式
    source_files: list[str]
    suggested_action: Optional[str]
    acknowledged: bool = False
```

### 4.2 持久化

```python
class DiscoveryStore:
    """JSON 持久化 → ~/.jarvis/discoveries.json"""

    def add(self, discovery: Discovery)     # 最新在前，保留最近 100 条
    def get_recent(self, count: int = 10)
    def get_today(self) -> list[Discovery]
    def get_unacknowledged(self) -> list
    def acknowledge(self, id: str)
```

### 4.3 通知系统

```python
# src/daemon/notifier.py

class Notifier:
    def notify(self, title, message, importance, subtitle)
    def _terminal_notify(...)       # Rich 彩色终端输出
    def _macos_notify(...)          # osascript display notification
```

**重要性 → 颜色映射**：`1=灰 2=白 3=黄 4=紫 5=红`
**重要性阈值**：低于 `min_importance` 的发现不发通知

---

## 5. CLI 命令

```bash
jarvis                         # 进入聊天模式
jarvis "问题"                  # 单次提问
jarvis -d / jarvis start       # 启动 Daemon
jarvis -r / jarvis rest        # 停止 Daemon
jarvis -s / jarvis status      # 查看状态（生命体征）
jarvis init                    # 交互式初始化
jarvis explore <path>          # 扫描目录，发现项目
jarvis discoveries             # 查看最近发现
jarvis projects                # 列出已识别项目
jarvis skills                  # 列出已有 Skills
```

**聊天模式支持**：
- `prompt_toolkit` 交互式输入 + FileHistory
- 斜杠命令补全（Tab）
- 自然语言意图检测：`"帮我挂机"` → 启动 daemon

---

## 6. 文件结构

```
src/
├── cli/                       # CLI 入口
│   ├── __init__.py            # Typer app + main callback
│   ├── common.py              # 常量、路径、状态查询
│   ├── chat.py                # 聊天循环 + streaming
│   ├── daemon_cmds.py         # start/rest/status
│   └── explore_cmds.py        # init/explore/projects/discoveries/skills
│
├── daemon/                    # Daemon 心跳
│   ├── daemon.py              # JarvisDaemon + Think Loop
│   ├── discovery.py           # Discovery + DiscoveryStore
│   └── notifier.py            # 通知系统
│
└── explorer/                  # 感知模块
    ├── scanner.py             # 目录扫描
    ├── signatures.py          # 特征指纹库
    ├── models.py              # ProjectMeta
    └── context_extractor.py   # CLAUDE.md 解析
```

---

## 7. 运行时存储

```
~/.jarvis/
├── config.json          # 主配置（LLM、监控路径、间隔）
├── state.json           # Daemon 心跳状态
├── discoveries.json     # 发现记录（最近 100 条）
├── chat_history         # 聊天命令历史
└── logs/
    └── daemon.log       # Daemon 日志
```

---

## 8. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 进程模型 | Daemon（常驻） vs Cron（定时） | Daemon 更"活"，有状态、实时监控、支持自省 |
| 发现引擎 | LLM 分析 vs 规则匹配 | LLM 提供智能洞察，不是机械报告 |
| 项目识别 | 签名指纹 vs 目录名 | 签名更准确，支持内容匹配 |
| HTTP 客户端 | httpx (trust_env=False) | 禁用系统代理，避免 Clash 拦截本地请求 |
| CLI 框架 | Typer + Rich | 开箱即用的类型安全 + 美化输出 |
| 部署 | macOS launchd | KeepAlive + RunAtLoad，系统级守护 |

---

## 9. 验证标准

- [x] `jarvis explore <path>` 能发现并正确分类项目
- [x] `jarvis start` 守护进程持续运行，定期产生心跳
- [x] Daemon 能检测文件变化并通过 LLM 分析生成 Discovery
- [x] `jarvis chat` 能正常流式对话
- [x] `jarvis discoveries` 显示最近的发现记录
