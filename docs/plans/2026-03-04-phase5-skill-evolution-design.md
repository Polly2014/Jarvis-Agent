# Phase 5: Skill Evolution Observer

> **状态**: 📋 规划中  
> **预估**: ~2 周  
> **里程碑**: Agent 能监控 skill 执行后的人工修正，自动积累 Evolution Log，主动建议优化  
> **P0 验证**: ✅ 已通过 (2026-03-04)

## 核心目标

Phase 4 解决了"从 0 到 1 创建 skill"，Phase 5 解决"从 v1 到 v2 优化 skill"。合在一起 = **完整的 skill 生命周期管理**。

**P0 验证已通过**（2026-03-04）：手工对 blog-writer 和 memory-keeper 各收集 5 条 git diff 信号，分别产出 3 个有效 patch，skill-optimizer skill 按需触发即可。Phase 5 是将这个流程自动化到 Jarvis daemon。

## 架构设计

```
src/evolution/
├── pattern_detector.py      # Phase 4: 发现新 skill 需求 (0→1)
├── skill_generator.py       # Phase 4: 创建新 skill
├── skill_registry.py        # Phase 4: 管理 skill
├── sandbox.py               # Phase 4: 安全验证
├── preference_learner.py    # Phase 4: 偏好学习
├── metacognition.py         # Phase 4: 自我反思
└── skill_evolution.py       # 🆕 Phase 5: 优化已有 skill (v1→v2)
```

## P5.1: SkillEvolutionObserver — 静默采集（3-5 天）

复用 daemon 现有 think loop（不新增 watchdog），定期跑 `git log` 检测修正：

```python
@dataclass
class SkillOutput:
    skill_name: str
    output_files: list[str]
    commit_hash: str
    timestamp: datetime
    correction_window: int = 7200  # 2h 窗口

@dataclass
class CorrectionTrace:
    trace_id: str
    skill_name: str
    output_file: str
    original_commit: str
    correction_commit: str
    diff: str
    diff_summary: str         # LLM 生成的一句话摘要
    timestamp: datetime
```

存储：`~/.jarvis/evolution/correction-traces.jsonl` + Markdown 视图 `~/.jarvis/evolution/{skill-name}.md`

**daemon.py 改动**：
```python
# _think() 方法加一段：
corrections = await self.skill_evolution.check_corrections(changes)
for trace in corrections:
    self.skill_evolution.record_trace(trace)
```

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 👁️ **Correction 检测** | think loop 中检查 git diff vs skill 产出 | 📋 |
| 🧠 **Trace 记录** | CorrectionTrace 写入 JSONL + Markdown | 📋 |
| 🧠 **LLM 摘要** | 每条 correction diff 生成一句话摘要 | 📋 |

## P5.2: Evolution Report + 主动提醒（3-5 天）

```python
class SkillEvolutionObserver:
    OPTIMIZATION_THRESHOLD = 5

    async def check_and_notify(self):
        """在 daemon _self_reflect() 中调用"""
        for skill_name, traces in self.get_traces_by_skill().items():
            if len(traces) >= self.OPTIMIZATION_THRESHOLD:
                report = await self.generate_evolution_report(skill_name, traces)
                self.notifier.notify(
                    title=f"💡 {skill_name} 有 {len(traces)} 条修正信号",
                    message=f"建议运行 skill-optimizer。主要模式: {report.top_patterns}",
                )
```

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 📊 **聚合分析** | 按 skill 聚合 traces，LLM 聚类摘要 | 📋 |
| 🔔 **主动提醒** | 累积 ≥5 条信号时通过 notifier 通知 | 📋 |
| 💭 **Metacognition 整合** | 五维雷达加入 evolution depth 评分 | 📋 |

## P5.3: 闭环 — CLI 命令（2-3 天）

```bash
jarvis skill evolve blog-writer              # 查看 evolution report
jarvis skill evolve blog-writer --optimize   # 生成 patch 建议
```

自然语言也可触发：`"blog-writer 最近修正多吗？"`

| 能力维度 | 功能 | 状态 |
|---------|------|------|
| 🖥️ **CLI 命令** | `jarvis skill evolve` 子命令 | 📋 |
| 💬 **自然语言** | 聊天中询问 skill 修正状况 | 📋 |

## 配置新增

```json
{
  "skill_evolution": {
    "enabled": true,
    "correction_window_seconds": 7200,
    "optimization_threshold": 5,
    "skill_output_paths": {
      "blog-writer": "content/blog/",
      "paper-writer": "Master-Translator-MCP-Server/Paper/",
      "memory-keeper": "memory/"
    }
  }
}
```

**自动发现机制**：`skill_output_paths` 手动配置作为 override。同时 `SkillEvolutionObserver` 在 daemon 启动时扫描所有 SKILL.md，从 frontmatter 的 `output_paths` 字段自动提取产出路径作为 fallback。这样新增 skill 不需要手动更新配置。

## 存储新增

```
~/.jarvis/
├── evolution/                    # 🆕 Phase 5
│   ├── correction-traces.jsonl  # 机器可查询
│   ├── blog-writer.md           # 人可读 Markdown 视图
│   ├── memory-keeper.md
│   └── paper-writer.md
└── ...
```

## 改动清单

| 文件 | 改动 | 工作量 |
|------|------|--------|
| 🆕 `src/evolution/skill_evolution.py` | SkillEvolutionObserver 主模块 | 主力 |
| `src/daemon/daemon.py` | `_think()` 加 correction 检测 + `_self_reflect()` 加 evolution 检查 | 小改 |
| `src/cli/evolution_cmds.py` | 加 `skill evolve` 子命令 | 小改 |
| `src/evolution/__init__.py` | 导出新模块 | 一行 |
| `src/evolution/metacognition.py` | 五维雷达加 evolution depth | 小改 |

## 与 skill-optimizer skill 的协作

```
Jarvis daemon (自动采集)          skill-optimizer (按需触发)
        │                                │
        ▼                                │
  correction-traces.jsonl ──读取──→  Phase 2: 收集信号
        │                                │
        ▼                                ▼
  "有 7 条修正信号"              Phase 3-6: 生成 patch
  主动提醒用户                    人审批 → 合并
```

Jarvis 负责**静默采集 + 主动提醒**，skill-optimizer 负责**按需分析 + 生成 patch**。通过 evolution log 文件解耦。

## 验收标准

- [ ] daemon think loop 检测到 skill 产出后的人工修改，自动记录 CorrectionTrace
- [ ] `~/.jarvis/evolution/blog-writer.md` 显示人可读的修正历史
- [ ] `jarvis skill evolve blog-writer` 输出聚合 report
- [ ] 累积 ≥5 条信号后 daemon 主动提醒
- [ ] Metacognition 五维雷达反映 evolution depth
- [ ] 所有新增测试通过
- [ ] Phase 4 的 79/79 单元测试仍全部通过（无回归）
