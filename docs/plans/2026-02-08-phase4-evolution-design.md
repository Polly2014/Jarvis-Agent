# Phase 4: 进化与自生成 设计文档

> 📅 2026-02-08  
> 🎯 让 Jarvis 学会"长大"——从用工具到造工具，从听指令到懂你

---

## 1. 核心理念

**"能力应该从交互中涌现，而非预设。"**

Phase 1~3 让 Jarvis 拥有了感知、记忆、思考、行动的完整能力。但这些能力都是我们预设的——它会用 `file_read`，是因为我们写了这个工具。Phase 4 的目标是让 Jarvis **自己发现规律、提炼模式、创造新能力**。

这是从"工具"到"伙伴"的质变：

```
Phase 1~3:  人类造工具 → Agent 用工具 → 完成任务
Phase 4:    Agent 观察 → 发现模式 → 自己造工具 → 越来越懂你
```

### 数码宝贝式进化的核心

```
🥚 空白状态 (Phase 1)     → 有了眼睛和耳朵
🐣 初步成长 (Phase 2)     → 有了大脑和记忆
🦋 能力展开 (Phase 3)     → 有了手和工具
⭐ 自我进化 (Phase 4)     → 有了自我意识和学习能力
```

### 设计原则

1. **涌现 > 预设**：Skill 从真实交互中提炼，不凭空想象
2. **用户确认**：自动提议，但人类拍板——Agent 不能偷偷给自己加能力
3. **安全沙盒**：新能力必须通过验证才能启用
4. **渐进人格**：骨架（价值观）设计，肌肉（偏好/风格）涌现

---

## 2. 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                    Phase 4: Evolution                    │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐  │
│  │   4.1        │   │   4.2        │   │   4.3       │  │
│  │  Pattern     │──▶│  Skill       │──▶│  Sandbox    │  │
│  │  Detector    │   │  Generator   │   │  Validator  │  │
│  └──────┬───────┘   └──────────────┘   └──────┬──────┘  │
│         │                                      │         │
│         │           ┌──────────────┐            │         │
│         └──────────▶│   4.4        │◀───────────┘         │
│                     │  Preference  │                      │
│                     │  Learner     │                      │
│                     └──────┬───────┘                      │
│                            │                              │
│                     ┌──────▼───────┐                      │
│                     │   4.5        │                      │
│                     │  Meta-       │                      │
│                     │  cognition   │                      │
│                     └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
                            │
                   ┌────────▼────────┐
                   │  Existing Infra  │
                   │  Memory + Tools  │
                   │  + LLM + Daemon  │
                   └─────────────────┘
```

### 新增模块

```
src/evolution/
├── __init__.py              # 导出核心类
├── pattern_detector.py      # 4.1 交互模式检测
├── skill_generator.py       # 4.2 Skill 自动生成
├── sandbox.py               # 4.3 沙盒验证
├── preference_learner.py    # 4.4 偏好学习
└── metacognition.py         # 4.5 元认知
```

---

## 3. 模块 4.1：模式检测器 (PatternDetector)

> **核心问题**：怎么判断"用户在重复做同一类事"？

### 3.1 交互指纹

每次对话结束后，提取一个**交互指纹 (InteractionFingerprint)**：

```python
@dataclass
class InteractionFingerprint:
    """一次交互的结构化摘要"""
    id: str                          # 唯一标识
    timestamp: datetime
    intent: str                      # LLM 提取的用户意图（如 "翻译文档"）
    tools_used: list[str]            # 调用了哪些工具（如 ["file_read", "file_write"]）
    tool_chain: str                  # 工具调用链签名（如 "read→write"）
    domain: str                      # 领域标签（如 "translation", "blog", "code"）
    input_pattern: str               # 输入特征（如 "markdown file"）
    output_pattern: str              # 输出特征（如 "translated markdown"）
    success: bool                    # 任务是否完成
    user_satisfaction: Optional[int] # 用户反馈（1-5，可选）
```

**提取时机**：每次 `_do_ask()` 或聊天轮次结束时，由 LLM 从对话上下文中总结。

### 3.2 模式聚类

```python
class PatternDetector:
    """检测重复交互模式"""
    
    def __init__(self, memory_index: MemoryIndex):
        self._fingerprints: list[InteractionFingerprint]  # 最近 N 条指纹
        self._patterns: list[DetectedPattern]             # 已检测到的模式
    
    async def record(self, fingerprint: InteractionFingerprint):
        """记录一条交互指纹"""
        # 1. 持久化到 memory（type="fingerprint"）
        # 2. 触发模式检测
    
    async def detect(self) -> Optional[DetectedPattern]:
        """检测是否形成了新模式"""
        # 1. 获取最近 30 天的指纹
        # 2. 按 (intent, tool_chain, domain) 分组
        # 3. 同组 >= 3 次 → 形成模式
        # 4. 过滤已有 Skill 覆盖的模式
        # 5. 返回最强的未覆盖模式
    
    async def _cluster_fingerprints(self, fingerprints) -> list[FingerprintCluster]:
        """用 LLM 做语义聚类（不依赖精确匹配）"""
        # Prompt: "以下是最近的交互记录，请找出重复的模式..."
```

### 3.3 模式模型

```python
@dataclass
class DetectedPattern:
    """检测到的交互模式"""
    id: str
    name: str                         # LLM 起的名字（如 "Markdown 文档翻译"）
    description: str                  # 模式描述
    frequency: int                    # 出现次数
    fingerprints: list[str]           # 关联的指纹 ID
    typical_tool_chain: list[str]     # 典型工具链
    suggested_skill_name: str         # 建议的 Skill 名称
    confidence: float                 # 0.0 ~ 1.0
    status: str = "detected"          # detected | proposed | accepted | rejected
```

### 3.4 触发策略

```
交互完成
  ↓
提取 InteractionFingerprint (LLM)
  ↓
PatternDetector.record()
  ↓
detect() — 同类指纹 >= 3 条？
  ├─ No → 静默
  └─ Yes → DetectedPattern
         ↓
       Notifier: "我注意到你经常做 [X]，要不要创建一个 Skill？"
         ↓
       用户确认 → SkillGenerator
```

---

## 4. 模块 4.2：Skill 自动生成 (SkillGenerator)

> **核心问题**：怎么从一个"模式"变成一个可用的 Skill？

### 4.1 生成流程

```python
class SkillGenerator:
    """从检测到的模式生成 Skill"""
    
    async def propose(self, pattern: DetectedPattern) -> SkillDraft:
        """生成 Skill 草稿"""
        # 1. 收集该模式的所有历史对话（从 Memory 中检索）
        # 2. LLM 分析：提炼通用步骤、提取参数化模板
        # 3. 生成 SKILL.md 草稿
        # 4. 返回给用户审阅
    
    async def finalize(self, draft: SkillDraft, user_edits: str = None) -> Path:
        """用户确认后，正式创建 Skill"""
        # 1. 应用用户修改（如果有）
        # 2. 调用 create_skill 元工具写入文件
        # 3. 注册到 SkillRegistry
        # 4. 记录到 Memory（milestone 类型）
```

### 4.2 Skill 草稿

```python
@dataclass
class SkillDraft:
    """Skill 草稿——供用户审阅"""
    name: str
    description: str
    trigger_keywords: list[str]      # 触发关键词
    instructions: str                # SKILL.md 的 instructions 内容
    example_interactions: list[str]  # 示例对话
    required_tools: list[str]        # 依赖的工具
    source_pattern: str              # 来源模式 ID
```

### 4.3 用户确认交互

```
Jarvis: 🧬 我发现你经常做"将 Markdown 文档翻译成中文"这件事（最近 5 次）。
        
        我可以创建一个 Skill 来自动化这个流程：
        
        📝 Skill: markdown-translator
        🔑 触发词: "翻译", "translate", "翻译文档"
        📋 步骤:
           1. 读取源文件 (file_read)
           2. 提取术语 (LLM)
           3. 分块翻译 (LLM + 术语表)
           4. 写入译文 (file_write)
        
        [✅ 创建] [✏️ 修改] [❌ 跳过] [🔇 不再提醒]

你> ✅
Jarvis: ✅ Skill "markdown-translator" 已创建！
        下次你说"翻译这个文档"时，我会自动使用这个 Skill。
```

### 4.4 Skill 生命周期管理

```python
class SkillRegistry:
    """Skill 注册表"""
    
    skills_dir: Path = JARVIS_HOME / "skills"
    
    def list_skills(self) -> list[SkillInfo]
    def load_skill(self, name: str) -> SkillInfo
    def enable(self, name: str)
    def disable(self, name: str)
    def delete(self, name: str)
    def get_for_context(self, user_input: str) -> Optional[SkillInfo]:
        """根据用户输入匹配最佳 Skill（关键词 + LLM 语义匹配）"""
```

```python
@dataclass
class SkillInfo:
    name: str
    path: Path
    description: str
    trigger_keywords: list[str]
    instructions: str
    enabled: bool = True
    version: int = 1
    created_at: datetime
    used_count: int = 0              # 使用次数
    last_used: Optional[datetime]    # 最后使用时间
    source: str = "auto"             # "auto" | "manual" | "builtin"
```

---

## 5. 模块 4.3：沙盒验证 (Sandbox)

> **核心问题**：怎么确保新 Skill 不会搞破坏？

### 5.1 验证流程

```python
class SkillSandbox:
    """Skill 安全验证"""
    
    async def validate(self, skill: SkillInfo) -> ValidationReport:
        """验证一个 Skill"""
        checks = [
            self._check_syntax(),           # SKILL.md 格式正确
            self._check_tool_deps(),         # 依赖的工具都存在
            self._check_no_dangerous_ops(),  # 不含危险操作模式
            self._dry_run(),                 # 用模拟数据试运行
        ]
        return ValidationReport(checks)
    
    async def _dry_run(self, skill: SkillInfo) -> CheckResult:
        """模拟运行：用 LLM 模拟一次 Skill 执行"""
        # 1. 构造模拟输入
        # 2. 让 LLM 按 Skill instructions 规划步骤
        # 3. 检查步骤中是否有越权操作
        # 4. 不实际执行工具，只验证计划合理性
```

### 5.2 验证报告

```python
@dataclass
class ValidationReport:
    passed: bool
    score: float                     # 0.0 ~ 1.0
    checks: list[CheckResult]
    recommendation: str              # "approve" | "review" | "reject"
    
@dataclass
class CheckResult:
    name: str                        # 检查项名称
    passed: bool
    message: str
    severity: str = "info"           # info | warning | error
```

### 5.3 验证策略

| 检查项 | 说明 | 失败处理 |
|--------|------|---------|
| 格式检查 | SKILL.md 结构完整 | ❌ 阻止创建 |
| 工具依赖 | 所有引用的工具已注册 | ❌ 阻止创建 |
| 危险操作 | 不含 `sudo`、`rm -rf` 等模式 | ⚠️ 需人工确认 |
| 模拟运行 | LLM dry-run 无异常 | ⚠️ 需人工确认 |
| 权限边界 | 不超出已配置的 `watch_paths` | ❌ 阻止创建 |

---

## 6. 模块 4.4：偏好学习 (PreferenceLearner)

> **核心问题**：怎么让 Jarvis "越来越懂你"？

### 6.1 偏好模型

```python
@dataclass
class UserPreference:
    """用户偏好"""
    category: str                    # "code_style" | "language" | "workflow" | "schedule" | "communication"
    key: str                         # 具体项（如 "indent_style"）
    value: str                       # 偏好值（如 "4 spaces"）
    confidence: float                # 置信度 0.0 ~ 1.0（观察越多越高）
    evidence_count: int              # 支持该偏好的证据数量
    first_seen: datetime
    last_seen: datetime
```

### 6.2 提取策略

```python
class PreferenceLearner:
    """从交互中学习用户偏好"""
    
    preferences_path: Path = JARVIS_HOME / "memory" / "persona" / "preferences.md"
    
    async def observe(self, conversation: list[dict]):
        """从一次对话中提取偏好信号"""
        # LLM Prompt:
        # "分析以下对话，提取用户的偏好和习惯。
        #  只记录有明确证据的偏好，不要猜测。
        #  输出格式: [{category, key, value, evidence}]"
    
    async def consolidate(self):
        """定期合并偏好（由 Daemon self_reflect 触发）"""
        # 1. 读取所有 raw 偏好信号
        # 2. 合并重复项，更新 confidence
        # 3. 冲突的偏好：保留最新 + 降低旧的 confidence
        # 4. 写入 preferences.md
    
    def get_active_preferences(self) -> list[UserPreference]:
        """获取高置信度偏好（用于注入 System Prompt）"""
        # confidence >= 0.6 的偏好
```

### 6.3 Persona 动态更新

```
~/.jarvis/memory/persona/
├── self.md                  # 核心人格（骨架，少变）
├── preferences.md           # 用户偏好（肌肉，常变）
└── growth.md                # 成长记录（里程碑）
```

**System Prompt 注入**：
```python
def build_system_prompt(self) -> str:
    base = self._load_persona()                    # 核心人格
    prefs = self.preference_learner.get_active()   # 用户偏好
    skills = self.skill_registry.list_enabled()     # 可用 Skill
    
    return f"""
{base}

## 你了解到的用户偏好
{self._format_preferences(prefs)}

## 你掌握的专属 Skill
{self._format_skills(skills)}
"""
```

---

## 7. 模块 4.5：元认知 (Metacognition)

> **核心问题**：Agent 能不能"知道自己不知道什么"？

### 7.1 能力边界感知

```python
class Metacognition:
    """元认知——自我反思能力"""
    
    async def reflect(self) -> ReflectionReport:
        """触发元认知反思"""
        # 1. 收集：所有 Skill、工具、偏好、模式
        # 2. 分析：
        #    - 哪些领域能力强？（高频 + 高成功率）
        #    - 哪些领域能力弱？（低频 or 失败率高）
        #    - 哪些领域完全没覆盖？
        # 3. 输出 ReflectionReport
    
    async def suggest_growth(self) -> list[GrowthSuggestion]:
        """建议下一步应该学什么"""
        # 基于能力盲区 + 用户最近的需求趋势
```

### 7.2 反思报告

```python
@dataclass
class ReflectionReport:
    timestamp: datetime
    strengths: list[str]              # 擅长的领域
    weaknesses: list[str]             # 薄弱的领域
    blind_spots: list[str]            # 完全未覆盖的领域
    growth_suggestions: list[str]     # 成长建议
    ability_radar: dict[str, float]   # 五维能力雷达 {感知, 记忆, 思考, 行动, 进化}
    skills_summary: dict              # Skill 使用统计
```

### 7.3 五维能力雷达

```python
def compute_ability_radar(self) -> dict[str, float]:
    """计算五维能力分数（0.0 ~ 1.0）"""
    return {
        "perception": self._score_perception(),   # 项目覆盖率、发现频率
        "memory":     self._score_memory(),       # 记忆条目数、检索成功率
        "thinking":   self._score_thinking(),     # 自省频率、洞察质量
        "action":     self._score_action(),       # 工具使用频率、成功率
        "evolution":  self._score_evolution(),     # Skill 数量、偏好覆盖度
    }
```

**CLI 展示**（Rich 雷达图）：
```
jarvis reflect

🧠 Jarvis 元认知报告 (2026-02-15)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  五维能力:
    👁️ 感知  ████████░░ 80%
    🧠 记忆  ███████░░░ 70%
    💭 思考  ██████░░░░ 60%
    🦾 行动  █████████░ 90%
    🔄 进化  ███░░░░░░░ 30%  ← 刚起步！

  💪 擅长: 文件操作、项目扫描、文档翻译
  📉 薄弱: 代码生成、测试编写
  🫥 盲区: 数据库操作、CI/CD

  💡 成长建议:
    1. 多练习代码生成任务，提升行动维度
    2. 考虑创建 "代码审查" Skill
```

---

## 8. 与现有模块的集成

### 8.1 Daemon 集成

```python
# daemon.py 修改

async def _think(self, changes):
    discovery = ...  # 原有逻辑
    
    # Phase 4 新增：记录交互指纹
    if self.pattern_detector:
        fingerprint = await self._extract_fingerprint(changes)
        await self.pattern_detector.record(fingerprint)

async def _self_reflect(self):
    reflection = ...  # 原有逻辑
    
    # Phase 4 新增：偏好合并 + 元认知
    if self.preference_learner:
        await self.preference_learner.consolidate()
    if self.metacognition:
        report = await self.metacognition.reflect()
        # 写入 memory/persona/growth.md
```

### 8.2 Chat 集成

```python
# chat.py 修改

async def _do_ask(self, message):
    # 0. Skill 匹配：查看是否有匹配的 Skill
    matched_skill = self.skill_registry.get_for_context(message)
    if matched_skill:
        system_prompt += f"\n\n## 专属 Skill 指导\n{matched_skill.instructions}"
    
    # 1. 原有对话逻辑...
    result = await self.llm_client.chat(messages, tools)
    
    # 2. Phase 4 新增：对话后提取指纹
    fingerprint = await self.pattern_detector.extract_from_conversation(messages)
    await self.pattern_detector.record(fingerprint)
    
    # 3. Phase 4 新增：检查是否有新模式
    pattern = await self.pattern_detector.detect()
    if pattern:
        await self._propose_skill(pattern)
```

### 8.3 CLI 新增命令

```python
# cli/evolution_cmds.py

@app.command()
def reflect():
    """🧠 触发元认知反思"""

@app.command()  
def abilities():
    """📊 查看五维能力雷达"""

@app.command()
def patterns():
    """🔍 查看检测到的交互模式"""

# skill 子命令组
skill_app = typer.Typer()

@skill_app.command("list")
def skill_list():
    """列出所有 Skill"""

@skill_app.command("create")
def skill_create(name: str):
    """手动创建 Skill"""

@skill_app.command("test")
def skill_test(name: str):
    """在沙盒中测试 Skill"""

@skill_app.command("enable")
def skill_enable(name: str):
    """启用 Skill"""

@skill_app.command("disable")
def skill_disable(name: str):
    """禁用 Skill"""
```

---

## 9. 文件结构

```
src/
├── evolution/                     # 🆕 Phase 4 新模块
│   ├── __init__.py                # 导出 PatternDetector, SkillGenerator, etc.
│   ├── pattern_detector.py        # 交互模式检测
│   ├── skill_generator.py         # Skill 自动生成
│   ├── skill_registry.py          # Skill 注册表与生命周期
│   ├── sandbox.py                 # 沙盒验证
│   ├── preference_learner.py      # 偏好学习
│   └── metacognition.py           # 元认知
│
├── cli/
│   ├── evolution_cmds.py          # 🆕 reflect, abilities, patterns, skill 子命令
│   └── chat.py                    # 🔄 集成 Skill 匹配 + 指纹提取
│
├── daemon/
│   └── daemon.py                  # 🔄 集成 PatternDetector + PreferenceLearner
│
└── llm/
    └── __init__.py                # 🔄 System Prompt 注入偏好和 Skill
```

### 运行时存储新增

```
~/.jarvis/
├── skills/                        # 🆕 自动生成的 Skill
│   ├── markdown-translator/
│   │   └── SKILL.md
│   └── blog-draft/
│       └── SKILL.md
│
├── memory/
│   ├── persona/
│   │   ├── self.md                # 原有
│   │   ├── preferences.md         # 🆕 用户偏好
│   │   └── growth.md              # 🆕 成长记录
│   └── fingerprints/              # 🆕 交互指纹
│       └── 2026-02.json
│
└── evolution.db                   # 🆕 模式+Skill 元数据（SQLite）
```

---

## 10. 实施计划

| 子阶段 | 预估 | 核心交付 | 依赖 |
|--------|------|---------|------|
| **4.1 模式检测器** | 1 周 | PatternDetector + InteractionFingerprint | Memory, LLM |
| **4.2 Skill 自生成** | 1 周 | SkillGenerator + SkillRegistry + 用户确认流 | 4.1, create_skill |
| **4.3 沙盒验证** | 3 天 | SkillSandbox + ValidationReport | 4.2 |
| **4.4 偏好学习** | 1 周 | PreferenceLearner + Persona 动态更新 | Memory, Daemon |
| **4.5 元认知** | 3 天 | Metacognition + 五维雷达 + reflect 命令 | 4.1~4.4 |

### 建议实施顺序

```
Week 1:  4.1 PatternDetector (地基)
Week 2:  4.2 SkillGenerator  (核心价值)
Week 3:  4.3 Sandbox + 4.4 PreferenceLearner (安全 + 个性化)
Week 4:  4.5 Metacognition + 集成测试 + 文档
```

---

## 11. 关键设计决策

| 决策 | 选择 | 替代方案 | 理由 |
|------|------|---------|------|
| 模式检测 | LLM 语义聚类 | 精确字符串匹配 | 理解意图，不是匹配文字 |
| 聚类阈值 | 3 次同类 | 5 次 / 动态 | 够快触发，不过度打扰 |
| Skill 创建 | 必须用户确认 | 全自动 | 安全第一，人类拍板 |
| 偏好存储 | Markdown + LLM 提取 | 结构化 DB | 人类可读 + 可编辑 |
| 元认知频率 | 自省时 + 手动 | 每次对话 | 不浪费 token |
| Skill 格式 | `.claude/skills/` 兼容 | 自定义格式 | 与 Claude Code 生态兼容 |

---

## 12. 验证标准

### 4.1 模式检测
- [ ] 重复 3 次"翻译 Markdown"后，PatternDetector 检出模式
- [ ] 指纹正确记录到 memory
- [ ] 不同类型的任务不会被错误聚类

### 4.2 Skill 自生成
- [ ] 检出模式后自动弹出 Skill 提议
- [ ] 用户确认后 Skill 写入 `~/.jarvis/skills/`
- [ ] `jarvis skills` 列出自生成的 Skill
- [ ] 下次相同任务自动匹配已有 Skill

### 4.3 沙盒验证
- [ ] 含危险操作的 Skill 被标记为需要人工审核
- [ ] 格式错误的 Skill 被阻止创建
- [ ] 验证报告清晰可读

### 4.4 偏好学习
- [ ] 用 Python 时偏好 4 空格缩进 → 被记录
- [ ] 偏好注入 System Prompt 后，Jarvis 行为有变化
- [ ] `preferences.md` 人类可读

### 4.5 元认知
- [ ] `jarvis reflect` 输出五维能力雷达
- [ ] 能力盲区识别准确
- [ ] 成长建议具有可操作性
