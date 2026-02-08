"""
交互模式检测器

Phase 4.1: 从交互历史中发现重复模式

核心流程:
1. 每次对话后提取 InteractionFingerprint
2. 持久化到 fingerprints/ 目录 + SQLite 索引
3. 定期检测：同类指纹 >= 3 次 → DetectedPattern
4. 通知用户，询问是否创建 Skill
"""

import json
import uuid
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class InteractionFingerprint:
    """
    交互指纹 — 一次对话的结构化摘要

    由 LLM 在对话结束后从上下文中提取。
    """

    id: str = field(default_factory=lambda: f"fp-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}")
    timestamp: datetime = field(default_factory=datetime.now)

    # 意图层
    intent: str = ""  # 用户意图摘要（如 "翻译 Markdown 文档"）
    domain: str = ""  # 领域标签（如 "translation", "blog", "code"）

    # 行为层
    tools_used: list[str] = field(default_factory=list)  # 使用的工具列表
    tool_chain: str = ""  # 工具调用链签名（如 "file_read→file_write"）

    # 特征层
    input_pattern: str = ""  # 输入特征（如 "markdown file"）
    output_pattern: str = ""  # 输出特征（如 "translated markdown"）

    # 结果层
    success: bool = True
    rounds: int = 1  # 对话轮数

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "intent": self.intent,
            "domain": self.domain,
            "tools_used": self.tools_used,
            "tool_chain": self.tool_chain,
            "input_pattern": self.input_pattern,
            "output_pattern": self.output_pattern,
            "success": self.success,
            "rounds": self.rounds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InteractionFingerprint":
        return cls(
            id=data.get("id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            intent=data.get("intent", ""),
            domain=data.get("domain", ""),
            tools_used=data.get("tools_used", []),
            tool_chain=data.get("tool_chain", ""),
            input_pattern=data.get("input_pattern", ""),
            output_pattern=data.get("output_pattern", ""),
            success=data.get("success", True),
            rounds=data.get("rounds", 1),
        )


@dataclass
class DetectedPattern:
    """
    检测到的交互模式

    当同类指纹累积 >= threshold 次时生成。
    """

    id: str = field(default_factory=lambda: f"pat-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}")
    name: str = ""  # LLM 起的模式名（如 "Markdown 文档翻译"）
    description: str = ""  # 模式描述
    frequency: int = 0  # 出现次数
    fingerprint_ids: list[str] = field(default_factory=list)  # 关联的指纹 ID
    typical_tool_chain: list[str] = field(default_factory=list)  # 典型工具链
    suggested_skill_name: str = ""  # 建议的 Skill 名称
    confidence: float = 0.0  # 0.0 ~ 1.0
    status: str = "detected"  # detected | proposed | accepted | rejected | covered
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "frequency": self.frequency,
            "fingerprint_ids": self.fingerprint_ids,
            "typical_tool_chain": self.typical_tool_chain,
            "suggested_skill_name": self.suggested_skill_name,
            "confidence": self.confidence,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DetectedPattern":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            frequency=data.get("frequency", 0),
            fingerprint_ids=data.get("fingerprint_ids", []),
            typical_tool_chain=data.get("typical_tool_chain", []),
            suggested_skill_name=data.get("suggested_skill_name", ""),
            confidence=data.get("confidence", 0.0),
            status=data.get("status", "detected"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
        )


class PatternDetector:
    """
    交互模式检测器

    职责:
    1. 记录交互指纹
    2. 检测重复模式（基于 LLM 语义聚类）
    3. 管理模式生命周期
    """

    # 触发 Skill 提议的最小重复次数
    PATTERN_THRESHOLD = 3
    # 检索指纹的时间窗口（天）
    LOOKBACK_DAYS = 30
    # 最大保留指纹数
    MAX_FINGERPRINTS = 500

    def __init__(self, jarvis_home: Path):
        self._home = jarvis_home
        self._fingerprints_dir = jarvis_home / "memory" / "fingerprints"
        self._patterns_path = jarvis_home / "evolution" / "patterns.json"

        # 确保目录存在
        self._fingerprints_dir.mkdir(parents=True, exist_ok=True)
        self._patterns_path.parent.mkdir(parents=True, exist_ok=True)

        # 加载已检测到的模式
        self._patterns: list[DetectedPattern] = self._load_patterns()

    # ── 指纹管理 ──────────────────────────────────────────

    def record(self, fingerprint: InteractionFingerprint) -> None:
        """记录一条交互指纹"""
        # 按月份分文件存储
        month_key = fingerprint.timestamp.strftime("%Y-%m")
        fp_path = self._fingerprints_dir / f"{month_key}.json"

        # 加载当月指纹
        fingerprints = self._load_fingerprints_file(fp_path)
        fingerprints.append(fingerprint.to_dict())

        # 限制单文件大小
        if len(fingerprints) > self.MAX_FINGERPRINTS:
            fingerprints = fingerprints[-self.MAX_FINGERPRINTS:]

        # 保存
        fp_path.write_text(
            json.dumps(fingerprints, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_recent_fingerprints(self, days: int = None) -> list[InteractionFingerprint]:
        """获取最近 N 天的指纹"""
        if days is None:
            days = self.LOOKBACK_DAYS

        cutoff = datetime.now() - timedelta(days=days)
        result = []

        # 扫描指纹文件
        for fp_path in sorted(self._fingerprints_dir.glob("*.json"), reverse=True):
            fingerprints = self._load_fingerprints_file(fp_path)
            for fp_data in fingerprints:
                fp = InteractionFingerprint.from_dict(fp_data)
                if fp.timestamp >= cutoff:
                    result.append(fp)

            # 如果文件日期早于截止日期，提前退出
            try:
                file_month = fp_path.stem  # "2026-02"
                file_date = datetime.strptime(file_month + "-01", "%Y-%m-%d")
                if file_date < cutoff:
                    break
            except ValueError:
                continue

        return sorted(result, key=lambda x: x.timestamp, reverse=True)

    def _load_fingerprints_file(self, path: Path) -> list[dict]:
        """加载指纹文件"""
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return []

    # ── 模式检测 ──────────────────────────────────────────

    def detect_patterns(self, fingerprints: list[InteractionFingerprint] = None) -> list[DetectedPattern]:
        """
        检测重复模式（规则版本，不依赖 LLM）

        策略：按 (domain, tool_chain) 分组，同组 >= PATTERN_THRESHOLD 则触发
        """
        if fingerprints is None:
            fingerprints = self.get_recent_fingerprints()

        if not fingerprints:
            return []

        # 按 (domain, tool_chain) 分组
        groups: dict[tuple[str, str], list[InteractionFingerprint]] = defaultdict(list)
        for fp in fingerprints:
            if fp.success and fp.domain and fp.tool_chain:
                key = (fp.domain, fp.tool_chain)
                groups[key].append(fp)

        new_patterns = []
        for (domain, tool_chain), fps in groups.items():
            if len(fps) < self.PATTERN_THRESHOLD:
                continue

            # 检查是否已有对应的模式
            if self._is_pattern_known(domain, tool_chain):
                continue

            # 从指纹中提炼模式
            pattern = DetectedPattern(
                name=f"{domain} ({tool_chain})",
                description=f"检测到你经常进行 {domain} 类型的任务，"
                            f"工具链为 {tool_chain}，"
                            f"已重复 {len(fps)} 次。",
                frequency=len(fps),
                fingerprint_ids=[fp.id for fp in fps],
                typical_tool_chain=tool_chain.split("→"),
                suggested_skill_name=self._suggest_skill_name(domain),
                confidence=min(len(fps) / 10.0, 1.0),
                status="detected",
            )
            new_patterns.append(pattern)
            self._patterns.append(pattern)

        if new_patterns:
            self._save_patterns()

        return new_patterns

    async def detect_patterns_llm(self, fingerprints: list[InteractionFingerprint], llm_call) -> list[DetectedPattern]:
        """
        用 LLM 做语义聚类检测模式（更智能）

        Args:
            fingerprints: 最近的指纹列表
            llm_call: async callable(prompt: str) -> str
        """
        if not fingerprints or len(fingerprints) < self.PATTERN_THRESHOLD:
            return []

        # 格式化指纹给 LLM
        fp_summaries = []
        for fp in fingerprints[:30]:  # 最多 30 条
            fp_summaries.append(
                f"- [{fp.timestamp.strftime('%m-%d %H:%M')}] "
                f"意图: {fp.intent} | 领域: {fp.domain} | "
                f"工具链: {fp.tool_chain} | 成功: {fp.success}"
            )

        prompt = f"""你是 Jarvis 的模式分析引擎。分析以下交互指纹，找出重复的行为模式。

交互指纹（最近 {self.LOOKBACK_DAYS} 天）:
{chr(10).join(fp_summaries)}

已有模式（避免重复检测）:
{chr(10).join(f"- {p.name} (状态: {p.status})" for p in self._patterns) or "无"}

要求:
1. 只报告出现 >= {self.PATTERN_THRESHOLD} 次的模式
2. 给出具体的 Skill 名称建议（英文、小写、连字符）
3. 不要重复已有模式

返回 JSON 数组（如果没有新模式返回空数组）:
[
  {{
    "name": "模式名称（中文）",
    "description": "描述",
    "frequency": 出现次数,
    "suggested_skill_name": "skill-name",
    "confidence": 0.0-1.0,
    "fingerprint_intents": ["匹配的 intent 列表"]
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

            new_patterns = []
            for item in data:
                # 匹配指纹 ID
                matched_ids = []
                intents = item.get("fingerprint_intents", [])
                for fp in fingerprints:
                    if fp.intent in intents or any(i in fp.intent for i in intents):
                        matched_ids.append(fp.id)

                pattern = DetectedPattern(
                    name=item.get("name", "未命名模式"),
                    description=item.get("description", ""),
                    frequency=item.get("frequency", 0),
                    fingerprint_ids=matched_ids,
                    suggested_skill_name=item.get("suggested_skill_name", ""),
                    confidence=item.get("confidence", 0.5),
                    status="detected",
                )
                new_patterns.append(pattern)
                self._patterns.append(pattern)

            if new_patterns:
                self._save_patterns()

            return new_patterns

        except (json.JSONDecodeError, Exception) as e:
            print(f"[PatternDetector] LLM 模式检测失败: {e}")
            # 降级到规则检测
            return self.detect_patterns(fingerprints)

    def _is_pattern_known(self, domain: str, tool_chain: str) -> bool:
        """检查模式是否已存在"""
        for p in self._patterns:
            if p.status in ("rejected",):
                continue
            # 比较 name 格式为 "domain (tool_chain)"
            expected_name = f"{domain} ({tool_chain})"
            if p.name == expected_name:
                return True
        return False

    def _suggest_skill_name(self, domain: str) -> str:
        """基于领域建议 Skill 名称"""
        name_map = {
            "translation": "auto-translator",
            "blog": "blog-assistant",
            "code": "code-helper",
            "document": "doc-processor",
            "data": "data-analyzer",
        }
        return name_map.get(domain, f"{domain}-assistant")

    # ── 模式生命周期 ──────────────────────────────────────

    def get_patterns(self, status: str = None) -> list[DetectedPattern]:
        """获取模式列表"""
        if status:
            return [p for p in self._patterns if p.status == status]
        return list(self._patterns)

    def get_actionable_patterns(self) -> list[DetectedPattern]:
        """获取可操作的模式（detected 且未被处理）"""
        return [p for p in self._patterns if p.status == "detected"]

    def update_pattern_status(self, pattern_id: str, status: str) -> bool:
        """更新模式状态"""
        for p in self._patterns:
            if p.id == pattern_id:
                p.status = status
                self._save_patterns()
                return True
        return False

    # ── 持久化 ────────────────────────────────────────────

    def _load_patterns(self) -> list[DetectedPattern]:
        """加载模式"""
        if not self._patterns_path.exists():
            return []
        try:
            data = json.loads(self._patterns_path.read_text(encoding="utf-8"))
            return [DetectedPattern.from_dict(p) for p in data]
        except (json.JSONDecodeError, IOError):
            return []

    def _save_patterns(self) -> None:
        """保存模式"""
        data = [p.to_dict() for p in self._patterns]
        self._patterns_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── LLM 辅助：从对话中提取指纹 ────────────────────────

    @staticmethod
    def build_extraction_prompt(messages: list[dict], tools_used: list[str]) -> str:
        """
        构建指纹提取 Prompt

        在对话结束后调用，由 LLM 从对话上下文中提取结构化指纹。
        """
        # 只取最近的对话（避免 token 过多）
        recent = messages[-10:] if len(messages) > 10 else messages
        conversation = "\n".join(
            f"[{m['role']}]: {m.get('content', '')[:200]}"
            for m in recent
            if m.get("role") in ("user", "assistant") and m.get("content")
        )

        tools_str = ", ".join(tools_used) if tools_used else "无"
        tool_chain = "→".join(tools_used) if tools_used else "无"

        return f"""分析以下对话，提取交互指纹。

对话:
{conversation}

使用的工具: {tools_str}
工具调用链: {tool_chain}

请提取:
{{
    "intent": "用户意图的一句话总结",
    "domain": "领域标签（translation/blog/code/document/data/system/other）",
    "input_pattern": "输入数据特征（如 markdown file, python script）",
    "output_pattern": "输出数据特征（如 translated text, new file）",
    "success": true/false
}}

只返回 JSON。"""
