"""
Skill 自动生成器

Phase 4.2: 从检测到的模式自动生成 Skill 草稿

流程:
1. PatternDetector 检出重复模式
2. SkillGenerator.propose() 生成草稿
3. 用户审阅 → 确认/修改/拒绝
4. SkillGenerator.finalize() 写入文件
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .pattern_detector import DetectedPattern
from .skill_registry import SkillRegistry


@dataclass
class SkillDraft:
    """
    Skill 草稿 — 供用户审阅

    在用户确认前的中间态。
    """

    name: str = ""
    description: str = ""
    trigger_keywords: list[str] = field(default_factory=list)
    instructions: str = ""  # SKILL.md 正文内容
    example_interactions: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    source_pattern_id: str = ""  # 来源模式 ID
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "trigger_keywords": self.trigger_keywords,
            "instructions": self.instructions,
            "example_interactions": self.example_interactions,
            "required_tools": self.required_tools,
            "source_pattern_id": self.source_pattern_id,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillDraft":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            trigger_keywords=data.get("trigger_keywords", []),
            instructions=data.get("instructions", ""),
            example_interactions=data.get("example_interactions", []),
            required_tools=data.get("required_tools", []),
            source_pattern_id=data.get("source_pattern_id", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )

    def render_skill_md(self) -> str:
        """渲染为 SKILL.md 内容"""
        keywords_json = json.dumps(self.trigger_keywords, ensure_ascii=False)
        now_str = self.created_at.isoformat()

        return f"""---
name: {self.name}
description: {self.description}
trigger_keywords: {keywords_json}
enabled: true
version: 1
source: auto
created_at: {now_str}
used_count: 0
---

{self.instructions}
"""

    def render_preview(self) -> str:
        """渲染预览（给用户看的可读版本）"""
        keywords = ", ".join(f'"{k}"' for k in self.trigger_keywords)
        tools = ", ".join(self.required_tools) if self.required_tools else "无特定工具"

        lines = [
            f"📝 Skill: {self.name}",
            f"📖 描述: {self.description}",
            f"🔑 触发词: {keywords}",
            f"🔧 工具链: {tools}",
            "",
            "📋 指导内容:",
        ]

        # 截取 instructions 前几行
        instr_lines = self.instructions.split("\n")[:10]
        for line in instr_lines:
            lines.append(f"   {line}")
        if len(self.instructions.split("\n")) > 10:
            lines.append("   ...")

        return "\n".join(lines)


class SkillGenerator:
    """
    Skill 自动生成器

    从 DetectedPattern → SkillDraft → SKILL.md
    """

    def __init__(self, jarvis_home: Path, skill_registry: SkillRegistry):
        self._home = jarvis_home
        self._registry = skill_registry
        self._drafts_dir = jarvis_home / "evolution" / "drafts"
        self._drafts_dir.mkdir(parents=True, exist_ok=True)

    async def propose(self, pattern: DetectedPattern, llm_call) -> SkillDraft:
        """
        从检测到的模式生成 Skill 草稿

        Args:
            pattern: 检测到的模式
            llm_call: async callable(prompt: str) -> str
        """
        prompt = f"""你是 Jarvis 的 Skill 生成引擎。根据以下交互模式，生成一个 Skill 定义。

检测到的模式:
- 名称: {pattern.name}
- 描述: {pattern.description}
- 出现次数: {pattern.frequency}
- 典型工具链: {" → ".join(pattern.typical_tool_chain)}
- 建议名称: {pattern.suggested_skill_name}

请生成:
{{
    "name": "skill-name (英文、小写、连字符)",
    "description": "一句话描述 Skill 的用途",
    "trigger_keywords": ["关键词1", "关键词2", "keyword3"],
    "instructions": "详细的 Skill 使用指导（Markdown 格式，200-500 字）\\n包含: 目标、步骤、注意事项",
    "required_tools": ["tool1", "tool2"],
    "example_interactions": ["用户可能说的话1", "用户可能说的话2"]
}}

要求:
1. name 使用英文小写 + 连字符
2. trigger_keywords 同时包含中英文
3. instructions 详细但不冗余
4. 只返回 JSON

只返回 JSON。"""

        try:
            response = await llm_call(prompt)
            response = response.strip()

            # 清理 Markdown code block
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            draft = SkillDraft(
                name=data.get("name", pattern.suggested_skill_name),
                description=data.get("description", pattern.description),
                trigger_keywords=data.get("trigger_keywords", []),
                instructions=data.get("instructions", ""),
                example_interactions=data.get("example_interactions", []),
                required_tools=data.get("required_tools", []),
                source_pattern_id=pattern.id,
            )

            # 保存草稿
            self._save_draft(draft)
            return draft

        except (json.JSONDecodeError, Exception) as e:
            # 降级：基于模式信息手动构建
            return self._fallback_draft(pattern)

    def _fallback_draft(self, pattern: DetectedPattern) -> SkillDraft:
        """降级策略：不依赖 LLM 直接从模式构建草稿"""
        name = pattern.suggested_skill_name or "auto-skill"
        domain = pattern.name.split("(")[0].strip() if "(" in pattern.name else pattern.name

        instructions = f"""# {domain} 自动化

## 目标
自动执行 {domain} 类型的任务。

## 工具链
{' → '.join(pattern.typical_tool_chain)}

## 步骤
1. 读取用户输入
2. 按照工具链顺序执行
3. 验证输出结果

## 注意事项
- 这是一个自动生成的 Skill，可能需要手动调整
- 请验证输出的正确性
"""
        return SkillDraft(
            name=name,
            description=pattern.description,
            trigger_keywords=[domain],
            instructions=instructions,
            required_tools=pattern.typical_tool_chain,
            source_pattern_id=pattern.id,
        )

    async def finalize(self, draft: SkillDraft, user_edits: Optional[str] = None) -> Path:
        """
        用户确认后，正式创建 Skill

        Args:
            draft: Skill 草稿
            user_edits: 用户的修改内容（如果有，替换 instructions）

        Returns:
            创建的 Skill 目录路径
        """
        if user_edits:
            draft.instructions = user_edits

        # 创建 Skill 目录
        skill_dir = self._home / "skills" / draft.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 写入 SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(draft.render_skill_md(), encoding="utf-8")

        # 创建 scripts 目录
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)

        # 刷新注册表
        self._registry.refresh()

        # 清理草稿
        self._remove_draft(draft.name)

        return skill_dir

    # ── 草稿管理 ──────────────────────────────────────────

    def _save_draft(self, draft: SkillDraft) -> None:
        """保存草稿"""
        path = self._drafts_dir / f"{draft.name}.json"
        path.write_text(
            json.dumps(draft.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _remove_draft(self, name: str) -> None:
        """删除草稿"""
        path = self._drafts_dir / f"{name}.json"
        if path.exists():
            path.unlink()

    def list_drafts(self) -> list[SkillDraft]:
        """列出所有待审阅的草稿"""
        drafts = []
        for path in self._drafts_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                drafts.append(SkillDraft.from_dict(data))
            except (json.JSONDecodeError, IOError):
                continue
        return drafts

    def get_draft(self, name: str) -> Optional[SkillDraft]:
        """获取指定草稿"""
        path = self._drafts_dir / f"{name}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return SkillDraft.from_dict(data)
        except (json.JSONDecodeError, IOError):
            return None
