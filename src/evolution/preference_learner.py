"""
偏好学习器

Phase 4.4: 从交互中学习用户偏好，让 Jarvis "越来越懂你"

偏好类别:
- code_style: 代码风格（缩进、命名、语言偏好）
- language: 自然语言偏好（中/英、语气、详细度）
- workflow: 工作流偏好（文件组织、工具使用）
- schedule: 时间相关偏好（工作时间、提醒频率）
- communication: 沟通偏好（详细解释 vs 简洁、是否要 emoji）

存储: ~/.jarvis/memory/persona/preferences.json
可读版: ~/.jarvis/memory/persona/preferences.md
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class UserPreference:
    """用户偏好"""

    category: str  # code_style | language | workflow | schedule | communication
    key: str  # 具体项（如 "indent_style"）
    value: str  # 偏好值（如 "4 spaces"）
    confidence: float = 0.3  # 初始置信度
    evidence_count: int = 1  # 支持该偏好的证据数量
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "key": self.key,
            "value": self.value,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserPreference":
        return cls(
            category=data.get("category", ""),
            key=data.get("key", ""),
            value=data.get("value", ""),
            confidence=data.get("confidence", 0.3),
            evidence_count=data.get("evidence_count", 1),
            first_seen=datetime.fromisoformat(data["first_seen"]) if "first_seen" in data else datetime.now(),
            last_seen=datetime.fromisoformat(data["last_seen"]) if "last_seen" in data else datetime.now(),
        )


class PreferenceLearner:
    """
    偏好学习器

    职责:
    1. 从对话中提取偏好信号
    2. 合并、去重、冲突解决
    3. 输出高置信度偏好供 System Prompt 注入
    """

    # 置信度阈值（低于此值不注入 System Prompt）
    ACTIVE_THRESHOLD = 0.6
    # 每次新观察增加的置信度
    CONFIDENCE_INCREMENT = 0.15
    # 置信度上限
    MAX_CONFIDENCE = 0.95
    # 最大偏好数量
    MAX_PREFERENCES = 100

    def __init__(self, jarvis_home: Path):
        self._home = jarvis_home
        self._persona_dir = jarvis_home / "memory" / "persona"
        self._persona_dir.mkdir(parents=True, exist_ok=True)

        self._prefs_json = self._persona_dir / "preferences.json"
        self._prefs_md = self._persona_dir / "preferences.md"

        self._preferences: list[UserPreference] = self._load()

    # ── 观察 ──────────────────────────────────────────────

    async def observe(self, conversation: list[dict], llm_call) -> list[UserPreference]:
        """
        从一次对话中提取偏好信号

        Args:
            conversation: 对话消息列表
            llm_call: async callable(prompt: str) -> str

        Returns:
            新发现的偏好列表
        """
        # 只取最近的消息
        recent = conversation[-8:] if len(conversation) > 8 else conversation
        conv_text = "\n".join(
            f"[{m['role']}]: {m.get('content', '')[:300]}"
            for m in recent
            if m.get("role") in ("user", "assistant") and m.get("content")
        )

        if not conv_text.strip():
            return []

        prompt = f"""分析以下对话，提取用户的偏好和习惯。
只记录有明确证据的偏好，不要猜测。

对话:
{conv_text}

已有偏好（避免重复）:
{self._format_existing_prefs()}

返回 JSON 数组（如果没有新发现返回空数组）:
[
  {{
    "category": "code_style|language|workflow|schedule|communication",
    "key": "具体项名称",
    "value": "偏好值",
    "evidence": "对话中的证据"
  }}
]

只返回 JSON 数组。"""

        try:
            response = await llm_call(prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)
            if not isinstance(data, list):
                return []

            new_prefs = []
            for item in data:
                pref = self._merge_preference(
                    category=item.get("category", ""),
                    key=item.get("key", ""),
                    value=item.get("value", ""),
                )
                if pref:
                    new_prefs.append(pref)

            if new_prefs:
                self._save()

            return new_prefs

        except (json.JSONDecodeError, Exception):
            return []

    def observe_explicit(self, category: str, key: str, value: str) -> UserPreference:
        """直接记录一条明确的偏好（无需 LLM）"""
        pref = self._merge_preference(category, key, value)
        self._save()
        return pref

    # ── 合并与冲突 ────────────────────────────────────────

    def _merge_preference(self, category: str, key: str, value: str) -> Optional[UserPreference]:
        """合并新偏好到已有列表"""
        if not category or not key or not value:
            return None

        # 查找已有偏好
        existing = self._find_preference(category, key)
        if existing:
            if existing.value == value:
                # 同值：增加置信度
                existing.confidence = min(
                    existing.confidence + self.CONFIDENCE_INCREMENT,
                    self.MAX_CONFIDENCE,
                )
                existing.evidence_count += 1
                existing.last_seen = datetime.now()
                return existing
            else:
                # 值冲突：新值覆盖，但降低置信度
                existing.value = value
                existing.confidence = max(existing.confidence - 0.1, 0.3)
                existing.evidence_count += 1
                existing.last_seen = datetime.now()
                return existing
        else:
            # 全新偏好
            pref = UserPreference(
                category=category,
                key=key,
                value=value,
            )
            self._preferences.append(pref)

            # 限制总数
            if len(self._preferences) > self.MAX_PREFERENCES:
                # 移除最低置信度的
                self._preferences.sort(key=lambda p: p.confidence)
                self._preferences = self._preferences[-self.MAX_PREFERENCES:]

            return pref

    def _find_preference(self, category: str, key: str) -> Optional[UserPreference]:
        """查找已有偏好"""
        for pref in self._preferences:
            if pref.category == category and pref.key == key:
                return pref
        return None

    # ── 合并（由 Daemon 定期调用）──────────────────────────

    async def consolidate(self) -> None:
        """
        定期合并偏好

        由 Daemon 的 _self_reflect 触发。
        1. 合并重复项
        2. 衰减久未出现的偏好
        3. 重写 preferences.md
        """
        now = datetime.now()

        # 衰减 30 天未观察到的偏好
        for pref in self._preferences:
            days_since = (now - pref.last_seen).days
            if days_since > 30:
                pref.confidence *= 0.9  # 每次合并衰减 10%

        # 移除置信度太低的偏好
        self._preferences = [p for p in self._preferences if p.confidence >= 0.1]

        self._save()

    # ── 读取接口 ──────────────────────────────────────────

    def get_active_preferences(self) -> list[UserPreference]:
        """获取高置信度偏好（用于 System Prompt 注入）"""
        return [p for p in self._preferences if p.confidence >= self.ACTIVE_THRESHOLD]

    def get_all_preferences(self) -> list[UserPreference]:
        """获取所有偏好"""
        return list(self._preferences)

    def format_for_prompt(self) -> str:
        """格式化高置信度偏好为 System Prompt 片段"""
        active = self.get_active_preferences()
        if not active:
            return ""

        # 按类别分组
        by_category: dict[str, list[UserPreference]] = {}
        for pref in active:
            by_category.setdefault(pref.category, []).append(pref)

        category_names = {
            "code_style": "代码风格",
            "language": "语言偏好",
            "workflow": "工作流",
            "schedule": "时间习惯",
            "communication": "沟通偏好",
        }

        lines = ["## 你了解到的用户偏好\n"]
        for category, prefs in by_category.items():
            name = category_names.get(category, category)
            lines.append(f"### {name}")
            for pref in prefs:
                lines.append(f"- {pref.key}: {pref.value}")
            lines.append("")

        return "\n".join(lines)

    # ── 持久化 ────────────────────────────────────────────

    def _load(self) -> list[UserPreference]:
        """加载偏好"""
        if not self._prefs_json.exists():
            return []
        try:
            data = json.loads(self._prefs_json.read_text(encoding="utf-8"))
            return [UserPreference.from_dict(p) for p in data]
        except (json.JSONDecodeError, IOError):
            return []

    def _save(self) -> None:
        """保存偏好（JSON + Markdown 双写）"""
        # JSON
        data = [p.to_dict() for p in self._preferences]
        self._prefs_json.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Markdown 可读版
        self._write_markdown()

    def _write_markdown(self) -> None:
        """写入人类可读的 Markdown 偏好文件"""
        lines = [
            "# 用户偏好档案",
            "",
            f"> 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 总计: {len(self._preferences)} 条偏好",
            "",
        ]

        # 按类别分组
        by_category: dict[str, list[UserPreference]] = {}
        for pref in sorted(self._preferences, key=lambda p: -p.confidence):
            by_category.setdefault(pref.category, []).append(pref)

        category_names = {
            "code_style": "🎨 代码风格",
            "language": "🌐 语言偏好",
            "workflow": "⚙️ 工作流",
            "schedule": "🕐 时间习惯",
            "communication": "💬 沟通偏好",
        }

        for category, prefs in by_category.items():
            name = category_names.get(category, f"📁 {category}")
            lines.append(f"## {name}")
            lines.append("")
            for pref in prefs:
                confidence_bar = "█" * int(pref.confidence * 10) + "░" * (10 - int(pref.confidence * 10))
                active = " ✅" if pref.confidence >= self.ACTIVE_THRESHOLD else ""
                lines.append(
                    f"- **{pref.key}**: {pref.value} "
                    f"({confidence_bar} {pref.confidence:.0%}, "
                    f"证据×{pref.evidence_count}){active}"
                )
            lines.append("")

        self._prefs_md.write_text("\n".join(lines), encoding="utf-8")

    def _format_existing_prefs(self) -> str:
        """格式化已有偏好给 LLM Prompt"""
        if not self._preferences:
            return "无"
        lines = []
        for p in self._preferences[:20]:
            lines.append(f"- [{p.category}] {p.key} = {p.value} (置信度: {p.confidence:.0%})")
        return "\n".join(lines)
