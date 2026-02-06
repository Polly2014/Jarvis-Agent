# Phase 2: 记忆与推理 设计文档

> 📅 2026-02-05 ~ 2026-02-06  
> 🎯 让 Jarvis 拥有"大脑"——Markdown 存内容，SQLite 做索引

---

## 1. 核心理念

**"记忆不是 CRUD，而是思维的延续。"**

Phase 1 让 Jarvis 有了感知能力，但发现的东西转瞬即逝——只存在 JSON 里，搜不到、串不起来。Phase 2 要给 Jarvis 一套**双轨记忆系统**：

```
┌─────────────────────────────────────────────┐
│              双轨记忆架构                     │
│                                              │
│   📝 Markdown 文件 — 内容存储层               │
│      ├── daily/     编年体（按日记录）         │
│      ├── topics/    纪传体（按主题追踪）       │
│      └── persona/   自我认知                  │
│                                              │
│   🔍 SQLite + FTS5 — 索引检索层              │
│      └── memory.db  全文搜索 + 元数据查询      │
│                                              │
│   设计哲学：                                  │
│   "Markdown 是人类友好的，SQLite 是机器友好的" │
│   "两者协同，缺一不可"                        │
└─────────────────────────────────────────────┘
```

### 设计原则

1. **Markdown 为王**：记忆内容存于 Markdown，人可直接阅读和编辑
2. **SQLite 索引**：FTS5 全文搜索，亚秒级 recall
3. **双写不可省**：每次写入同时更新 Markdown + SQLite
4. **四层记忆**：daily → topics → persona → index，由细到粗

---

## 2. 记忆数据模型

### 2.1 记忆条目

```python
# src/memory/writer.py

@dataclass
class MemoryEntry:
    timestamp: datetime              # 写入时间
    title: str                       # 标题
    content: str                     # 内容（Markdown 格式）
    importance: int = 3              # 重要性 1-5
    tags: list[str] = field(...)     # 标签
    entry_type: str = "observation"  # observation | decision | insight | milestone
```

### 2.2 索引条目

```python
# src/memory/index.py

@dataclass
class IndexEntry:
    id: Optional[int]                # SQLite rowid（自增）
    type: str                        # "daily" | "topic" | "discovery"
    file_path: str                   # 对应的 Markdown 文件路径
    date: str                        # "2026-02-05" 格式
    title: str                       # 标题
    tags: str                        # 逗号分隔的标签
    importance: int                  # 1-5
    summary: str                     # 内容摘要
    content: str                     # 完整内容
```

---

## 3. MemoryWriter — 内容存储层

```python
class MemoryWriter:
    def __init__(self, memory_root: Path)
```

### 3.1 编年体 · Daily

```python
def append_to_daily(self, entry: MemoryEntry) -> Path:
    """追加到当日日记 → memory/daily/2026/02/05.md"""
```

**文件结构**：
```markdown
# 📅 2026-02-05 日记

## 🕐 14:30 [决策] 选择双轨记忆架构
> 重要性: ⭐⭐⭐⭐ | 标签: #jarvis-agent, #architecture

Markdown存内容 + SQLite做索引，两者协同...

---

## 🕐 16:45 [洞察] FTS5 比 LIKE 快 100 倍
> 重要性: ⭐⭐⭐ | 标签: #sqlite, #performance

在 1000 条记忆中搜索，FTS5 耗时 < 1ms...
```

### 3.2 纪传体 · Topics

```python
def update_topic(self, topic: str, entry: MemoryEntry) -> Path:
    """更新主题文件 → memory/topics/{topic}/README.md"""
```

**自动创建**目录和 README.md，如果主题不存在。追加模式，不覆盖已有内容。

### 3.3 自我认知 · Persona

```python
def init_persona(self, persona_data: dict) -> Path:
    """初始化人格档案 → memory/persona/self.md"""
```

记录 Jarvis 的身份、性格、价值观。这是 Phase 1 `config.json` 中 persona 字段的结构化扩展。

### 3.4 辅助方法

```python
def read_daily(self, date: str) -> Optional[str]
    """读取指定日期的日记"""

def read_recent_dailies(self, days: int = 7) -> list[tuple[str, str]]
    """读取最近 N 天的日记，返回 [(date, content), ...]"""
```

---

## 4. MemoryIndex — 索引检索层

### 4.1 数据库结构

```python
class MemoryIndex:
    def __init__(self, db_path: Path):
        """初始化 SQLite 数据库，自动创建表和触发器"""
```

**主表**：
```sql
CREATE TABLE IF NOT EXISTS memory_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,           -- "daily" / "topic" / "discovery"
    file_path TEXT,               -- Markdown 文件路径
    date TEXT NOT NULL,           -- "2026-02-05"
    title TEXT NOT NULL,
    tags TEXT DEFAULT '',         -- "jarvis-agent,architecture"
    importance INTEGER DEFAULT 3,
    summary TEXT DEFAULT '',
    content TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**FTS5 虚拟表**（全文搜索加速）：
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title,
    tags,
    summary,
    content,
    content='memory_entries',
    content_rowid='id'
);
```

### 4.2 三触发器自动同步

```sql
-- INSERT 触发器：主表写入时同步到 FTS5
CREATE TRIGGER memory_ai AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, title, tags, summary, content)
    VALUES (new.id, new.title, new.tags, new.summary, new.content);
END;

-- DELETE 触发器：主表删除时同步删除 FTS5
CREATE TRIGGER memory_ad AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, tags, summary, content)
    VALUES ('delete', old.id, old.title, old.tags, old.summary, old.content);
END;

-- UPDATE 触发器：主表更新时同步更新 FTS5
CREATE TRIGGER memory_au AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, title, tags, summary, content)
    VALUES ('delete', old.id, old.title, old.tags, old.summary, old.content);
    INSERT INTO memory_fts(rowid, title, tags, summary, content)
    VALUES (new.id, new.title, new.tags, new.summary, new.content);
END;
```

### 4.3 检索接口

```python
def add(self, entry: IndexEntry) -> int:
    """写入索引，返回 id"""

def search(self, query: str, limit: int = 20) -> list[IndexEntry]:
    """FTS5 全文搜索（前缀匹配 + BM25 排序）"""
    # 使用 memory_fts MATCH '{query}*'

def recall(self, query: str, days: int = 30, limit: int = 20) -> list[IndexEntry]:
    """回忆 = 搜索 + 时间范围过滤"""
    # FTS5 MATCH + date >= N天前

def get_recent(self, count: int = 20) -> list[IndexEntry]:
    """获取最近 N 条记忆（按时间倒序）"""

def get_important(self, min_importance: int = 4, limit: int = 20) -> list[IndexEntry]:
    """获取重要记忆（importance >= 阈值）"""
```

---

## 5. Think Loop 增强

Phase 2 让 Daemon 的发现不再只存 JSON，而是同时写入三个目的地：

```
Discovery 产生
    │
    ├─→ 1. discoveries.json     (Phase 1 原有，保持兼容)
    │
    ├─→ 2. memory/daily/        (Markdown 日记)
    │      └─ MemoryWriter.append_to_daily()
    │
    └─→ 3. memory.db            (SQLite 索引)
           └─ MemoryIndex.add()
```

```python
# daemon.py 中的 _process_discovery 增强

def _process_discovery(self, discovery: Discovery):
    # Phase 1: 存到 JSON
    self.discovery_store.add(discovery)

    # Phase 2 增强: 写入双轨记忆
    entry = MemoryEntry(
        title=discovery.title,
        content=discovery.content,
        importance=discovery.importance,
        tags=self._extract_tags(discovery),
        entry_type=discovery.type.value,
    )
    self.memory_writer.append_to_daily(entry)    # → Markdown
    self.memory_index.add(IndexEntry(...))         # → SQLite

    # 通知
    self.notifier.notify(...)
```

---

## 6. CLI 增强

### 6.1 新增命令

```bash
jarvis recall "关键词"          # FTS5 搜索记忆
jarvis think                   # 手动触发一次思考
jarvis insights                # 查看重要洞察 (importance >= 4)
```

### 6.2 聊天中的斜杠命令

```python
# src/cli/chat.py

class JarvisCompleter(Completer):
    """15 个斜杠命令补全"""

    COMMANDS = [
        "/help", "/quit", "/exit",
        "/status", "/start", "/rest",
        "/explore", "/projects", "/discoveries",
        "/skills", "/recall", "/think",
        "/insights", "/clear", "/history"
    ]
```

集成 `prompt_toolkit`：
- **FileHistory**：命令历史持久化到 `~/.jarvis/chat_history`
- **Tab 补全**：斜杠命令 + 路径补全
- **自然语言意图检测**：`"查一下之前关于..."` → 自动调用 recall

### 6.3 Streaming 对话

```python
async def _chat_streaming(self, message: str):
    """SSE 流式输出"""
    async with httpx.AsyncClient(trust_env=False) as client:
        async with client.stream("POST", url, json=payload) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0]["delta"]
                    if "content" in delta:
                        console.print(delta["content"], end="")
```

---

## 7. 文件结构

### 7.1 代码新增

```
src/
├── memory/                    # 🆕 Phase 2 新增模块
│   ├── __init__.py
│   ├── writer.py              # MemoryWriter（Markdown 存储）
│   └── index.py               # MemoryIndex（SQLite + FTS5）
│
├── cli/
│   ├── chat.py                # 🔄 增强：斜杠命令 + prompt_toolkit
│   └── explore_cmds.py        # 🔄 增强：recall, think, insights
│
└── daemon/
    └── daemon.py              # 🔄 增强：_process_discovery 双写
```

### 7.2 运行时存储新增

```
~/.jarvis/
├── memory/                    # 🆕 记忆存储
│   ├── daily/                 # 编年体
│   │   └── 2026/
│   │       └── 02/
│   │           ├── 05.md
│   │           └── 06.md
│   ├── topics/                # 纪传体
│   │   └── jarvis-agent/
│   │       └── README.md
│   └── persona/               # 自我认知
│       └── self.md
│
└── memory.db                  # 🆕 SQLite 索引数据库
```

---

## 8. Phase 2.5 补丁：线程安全

在 Phase 2 测试中发现一个隐藏的竞态条件 Bug：

**问题**：watchdog 事件处理器在子线程中写入 `_recent_changes`，而 `_think_loop` 在 asyncio 主线程中读取，没有锁保护。

**修复**：
```python
class JarvisEventHandler(FileSystemEventHandler):
    def __init__(self):
        self._recent_changes = []
        self._lock = threading.Lock()      # 🔧 添加互斥锁

    def on_modified(self, event):
        with self._lock:                   # 🔧 写入加锁
            self._recent_changes.append({...})

    def get_and_clear_changes(self):
        with self._lock:                   # 🔧 读取+清空加锁
            changes = self._recent_changes.copy()
            self._recent_changes.clear()
            return changes
```

这个修复被单独记为 Phase 2.5，因为它虽然只有几行代码，但揭示了"异步 + 多线程混合架构"的经典陷阱。

---

## 9. 关键设计决策

| 决策 | 选择 | 替代方案 | 理由 |
|------|------|---------|------|
| 记忆存储 | Markdown 文件 | JSON / SQLite only | 人类可读、可编辑、Git 友好 |
| 检索引擎 | SQLite FTS5 | Elasticsearch / Vector DB | 零依赖，够用，亚毫秒级 |
| 同步策略 | 触发器自动同步 | 应用层手动同步 | 原子性保证，减少 Bug |
| 记忆分类 | entry_type 字段 | 独立的表 | 灵活，不过度设计 |
| 聊天框架 | prompt_toolkit | readline / click | 历史记录、补全、美化 |
| 搜索模式 | 前缀匹配 `query*` | 精确匹配 | 更容错，支持模糊搜索 |

---

## 10. 验证标准

- [x] `MemoryWriter.append_to_daily()` 生成正确格式的 Markdown 日记
- [x] `MemoryIndex.search("jarvis")` 返回相关记忆
- [x] `MemoryIndex.recall("tool", days=7)` 按时间+相关性排序
- [x] Daemon 发现自动写入 Markdown + SQLite（双写）
- [x] 斜杠命令补全正常工作
- [x] 线程安全：watchdog 事件处理器和 Think Loop 无竞态
