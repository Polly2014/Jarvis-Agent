"""
元认知引擎

Phase 4.5: 让 Jarvis "知道自己知道什么，不知道什么"

核心能力:
1. 五维能力雷达: 感知/记忆/思考/行动/进化
2. 能力边界感知: 强项/弱项/盲区
3. 成长建议: 基于盲区 + 用户需求趋势

触发时机:
- jarvis reflect 手动命令
- Daemon _self_reflect 周期性触发
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field

from .pattern_detector import PatternDetector
from .skill_registry import SkillRegistry
from .preference_learner import PreferenceLearner


@dataclass
class ReflectionReport:
    """元认知反思报告"""

    timestamp: datetime = field(default_factory=datetime.now)
    strengths: list[str] = field(default_factory=list)  # 擅长的领域
    weaknesses: list[str] = field(default_factory=list)  # 薄弱的领域
    blind_spots: list[str] = field(default_factory=list)  # 完全未覆盖
    growth_suggestions: list[str] = field(default_factory=list)
    ability_radar: dict[str, float] = field(default_factory=dict)  # 五维 0.0~1.0
    skills_summary: dict = field(default_factory=dict)  # Skill 使用统计
    fingerprints_total: int = 0
    patterns_total: int = 0
    preferences_total: int = 0

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "blind_spots": self.blind_spots,
            "growth_suggestions": self.growth_suggestions,
            "ability_radar": self.ability_radar,
            "skills_summary": self.skills_summary,
            "fingerprints_total": self.fingerprints_total,
            "patterns_total": self.patterns_total,
            "preferences_total": self.preferences_total,
        }

    def render(self) -> str:
        """渲染为 Rich 友好的文本"""
        lines = [
            f"🧠 Jarvis 元认知报告 ({self.timestamp.strftime('%Y-%m-%d %H:%M')})",
            "━" * 45,
            "",
            "  五维能力:",
        ]

        radar_labels = {
            "perception": "👁️ 感知",
            "memory": "🧠 记忆",
            "thinking": "💭 思考",
            "action": "🦾 行动",
            "evolution": "🔄 进化",
        }

        for key, label in radar_labels.items():
            score = self.ability_radar.get(key, 0.0)
            filled = int(score * 10)
            bar = "█" * filled + "░" * (10 - filled)
            pct = f"{score:.0%}"
            hint = ""
            if score < 0.3:
                hint = "  ← 需要加强！"
            elif score >= 0.8:
                hint = "  ← 很强！"
            lines.append(f"    {label}  {bar} {pct}{hint}")

        lines.append("")

        if self.strengths:
            lines.append(f"  💪 擅长: {', '.join(self.strengths)}")
        if self.weaknesses:
            lines.append(f"  📉 薄弱: {', '.join(self.weaknesses)}")
        if self.blind_spots:
            lines.append(f"  🫥 盲区: {', '.join(self.blind_spots)}")

        lines.append("")

        if self.growth_suggestions:
            lines.append("  💡 成长建议:")
            for i, suggestion in enumerate(self.growth_suggestions, 1):
                lines.append(f"    {i}. {suggestion}")

        lines.append("")
        lines.append(
            f"  📊 统计: {self.fingerprints_total} 指纹 | "
            f"{self.patterns_total} 模式 | "
            f"{self.preferences_total} 偏好 | "
            f"{len(self.skills_summary)} Skills"
        )

        return "\n".join(lines)


class Metacognition:
    """
    元认知引擎

    整合 PatternDetector + SkillRegistry + PreferenceLearner 的数据，
    进行自我能力评估。
    """

    # 已知的能力领域
    ALL_DOMAINS = [
        "translation", "blog", "code", "document", "data",
        "system", "testing", "design", "research", "devops",
    ]

    def __init__(
        self,
        jarvis_home: Path,
        pattern_detector: PatternDetector,
        skill_registry: SkillRegistry,
        preference_learner: PreferenceLearner,
    ):
        self._home = jarvis_home
        self._detector = pattern_detector
        self._registry = skill_registry
        self._learner = preference_learner
        self._reports_dir = jarvis_home / "evolution" / "reflections"
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    async def reflect(self, llm_call=None) -> ReflectionReport:
        """
        执行元认知反思

        Args:
            llm_call: 可选，用于 LLM 增强分析
        """
        # 收集数据
        fingerprints = self._detector.get_recent_fingerprints(days=30)
        patterns = self._detector.get_patterns()
        skills = self._registry.list_skills(include_disabled=True)
        preferences = self._learner.get_all_preferences()

        # 计算五维雷达
        radar = self.compute_ability_radar(
            fingerprint_count=len(fingerprints),
            pattern_count=len(patterns),
            skill_count=len(skills),
            preference_count=len(preferences),
        )

        # 分析强弱项
        domain_stats = self._analyze_domains(fingerprints)
        strengths = [d for d, s in domain_stats.items() if s["success_rate"] > 0.7 and s["count"] >= 3]
        weaknesses = [d for d, s in domain_stats.items() if s["success_rate"] < 0.5 and s["count"] >= 2]
        active_domains = set(domain_stats.keys())
        blind_spots = [d for d in self.ALL_DOMAINS if d not in active_domains]

        # Skill 统计
        skills_summary = {
            s.name: {
                "enabled": s.enabled,
                "used_count": s.used_count,
                "source": s.source,
            }
            for s in skills
        }

        # 成长建议
        suggestions = self._generate_suggestions(strengths, weaknesses, blind_spots, skills)

        # LLM 增强分析（可选）
        if llm_call and fingerprints:
            llm_suggestions = await self._llm_enhanced_reflect(
                fingerprints, patterns, skills, preferences, llm_call
            )
            if llm_suggestions:
                suggestions = llm_suggestions

        report = ReflectionReport(
            strengths=strengths,
            weaknesses=weaknesses,
            blind_spots=blind_spots,
            growth_suggestions=suggestions,
            ability_radar=radar,
            skills_summary=skills_summary,
            fingerprints_total=len(fingerprints),
            patterns_total=len(patterns),
            preferences_total=len(preferences),
        )

        # 保存报告
        self._save_report(report)

        return report

    def compute_ability_radar(
        self,
        fingerprint_count: int = 0,
        pattern_count: int = 0,
        skill_count: int = 0,
        preference_count: int = 0,
    ) -> dict[str, float]:
        """
        计算五维能力分数 (0.0 ~ 1.0)

        各维度评分标准:
        - 感知: 项目覆盖率、指纹数量
        - 记忆: 记忆条目数
        - 思考: 模式检测 + 偏好学习
        - 行动: 指纹中的工具使用
        - 进化: Skill 数量 + 偏好覆盖度
        """
        return {
            "perception": self._score_perception(fingerprint_count),
            "memory": self._score_memory(),
            "thinking": self._score_thinking(pattern_count, preference_count),
            "action": self._score_action(fingerprint_count),
            "evolution": self._score_evolution(skill_count, preference_count),
        }

    def _score_perception(self, fingerprint_count: int) -> float:
        """感知能力分数"""
        # 基于交互指纹数量（越多说明感知越活跃）
        # 30 个指纹 = 满分
        return min(fingerprint_count / 30.0, 1.0)

    def _score_memory(self) -> float:
        """记忆能力分数"""
        # 检查记忆目录中的文件数量
        memory_dir = self._home / "memory"
        if not memory_dir.exists():
            return 0.0
        
        file_count = sum(1 for _ in memory_dir.rglob("*.md"))
        # 20 个文件 = 满分
        return min(file_count / 20.0, 1.0)

    def _score_thinking(self, pattern_count: int, preference_count: int) -> float:
        """思考能力分数"""
        # 模式检测 + 偏好学习 = 思考能力
        pattern_score = min(pattern_count / 5.0, 0.5)
        pref_score = min(preference_count / 10.0, 0.5)
        return pattern_score + pref_score

    def _score_action(self, fingerprint_count: int) -> float:
        """行动能力分数"""
        # 基于成功完成的交互数
        fingerprints = self._detector.get_recent_fingerprints(days=30)
        if not fingerprints:
            return 0.0
        success_count = sum(1 for fp in fingerprints if fp.success)
        return min(success_count / 20.0, 1.0)

    def _score_evolution(self, skill_count: int, preference_count: int) -> float:
        """进化能力分数"""
        # Skill 数量 + 偏好覆盖度
        skill_score = min(skill_count / 5.0, 0.5)
        pref_score = min(preference_count / 10.0, 0.5)
        return skill_score + pref_score

    # ── 领域分析 ──────────────────────────────────────────

    def _analyze_domains(self, fingerprints) -> dict[str, dict]:
        """按领域分析交互统计"""
        stats: dict[str, dict] = {}
        for fp in fingerprints:
            domain = fp.domain or "other"
            if domain not in stats:
                stats[domain] = {"count": 0, "success": 0}
            stats[domain]["count"] += 1
            if fp.success:
                stats[domain]["success"] += 1

        # 计算成功率
        for domain, s in stats.items():
            s["success_rate"] = s["success"] / s["count"] if s["count"] > 0 else 0.0

        return stats

    def _generate_suggestions(
        self,
        strengths: list[str],
        weaknesses: list[str],
        blind_spots: list[str],
        skills: list,
    ) -> list[str]:
        """基于规则生成成长建议"""
        suggestions = []

        if weaknesses:
            suggestions.append(
                f"多练习 {', '.join(weaknesses[:2])} 类型的任务，提升成功率"
            )

        if blind_spots:
            suggestions.append(
                f"尝试 {', '.join(blind_spots[:2])} 领域的任务，扩展能力边界"
            )

        auto_skills = [s for s in skills if s.source == "auto"]
        if len(auto_skills) == 0:
            suggestions.append("积累更多交互指纹，让模式检测器发现可自动化的任务")

        if not suggestions:
            suggestions.append("继续保持！当前能力均衡发展")

        return suggestions

    async def _llm_enhanced_reflect(
        self, fingerprints, patterns, skills, preferences, llm_call
    ) -> list[str]:
        """LLM 增强反思分析"""
        fp_summary = "\n".join(
            f"- [{fp.domain}] {fp.intent} ({'✅' if fp.success else '❌'})"
            for fp in fingerprints[:15]
        )

        skill_summary = "\n".join(
            f"- {s.name} (使用 {s.used_count} 次, {'启用' if s.enabled else '禁用'})"
            for s in skills
        ) or "无"

        prompt = f"""你是 Jarvis 的元认知引擎。基于以下数据进行自我反思。

最近 30 天交互 ({len(fingerprints)} 条):
{fp_summary}

检测到的模式: {len(patterns)} 个
已有 Skill: 
{skill_summary}
用户偏好: {len(preferences)} 条

请给出 3-5 条具体的成长建议。
每条建议应该具体、可操作。

返回 JSON 数组:
["建议1", "建议2", "建议3"]

只返回 JSON 数组。"""

        try:
            response = await llm_call(prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            data = json.loads(response)
            if isinstance(data, list) and all(isinstance(s, str) for s in data):
                return data
        except Exception:
            pass

        return []

    # ── 持久化 ────────────────────────────────────────────

    def _save_report(self, report: ReflectionReport) -> None:
        """保存反思报告"""
        filename = f"{report.timestamp.strftime('%Y-%m-%d_%H%M')}.json"
        path = self._reports_dir / filename
        path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 同时写入 growth.md（追加模式）
        growth_path = self._home / "memory" / "persona" / "growth.md"
        self._append_to_growth(growth_path, report)

    def _append_to_growth(self, path: Path, report: ReflectionReport) -> None:
        """追加到成长记录"""
        path.parent.mkdir(parents=True, exist_ok=True)

        entry = f"""
## {report.timestamp.strftime('%Y-%m-%d %H:%M')} 反思

### 能力雷达
"""
        radar_labels = {
            "perception": "感知",
            "memory": "记忆",
            "thinking": "思考",
            "action": "行动",
            "evolution": "进化",
        }
        for key, label in radar_labels.items():
            score = report.ability_radar.get(key, 0.0)
            entry += f"- {label}: {score:.0%}\n"

        if report.strengths:
            entry += f"\n**擅长**: {', '.join(report.strengths)}\n"
        if report.weaknesses:
            entry += f"**薄弱**: {', '.join(report.weaknesses)}\n"
        if report.growth_suggestions:
            entry += "\n**建议**:\n"
            for s in report.growth_suggestions:
                entry += f"- {s}\n"

        entry += "\n---\n"

        # 如果文件不存在，写入标题
        if not path.exists():
            header = "# Jarvis 成长记录\n\n> 记录每次元认知反思的结果\n\n---\n"
            path.write_text(header + entry, encoding="utf-8")
        else:
            with open(path, "a", encoding="utf-8") as f:
                f.write(entry)

    def get_latest_report(self) -> ReflectionReport | None:
        """获取最近的反思报告"""
        files = sorted(self._reports_dir.glob("*.json"), reverse=True)
        if not files:
            return None
        try:
            data = json.loads(files[0].read_text(encoding="utf-8"))
            report = ReflectionReport()
            report.timestamp = datetime.fromisoformat(data.get("timestamp", ""))
            report.strengths = data.get("strengths", [])
            report.weaknesses = data.get("weaknesses", [])
            report.blind_spots = data.get("blind_spots", [])
            report.growth_suggestions = data.get("growth_suggestions", [])
            report.ability_radar = data.get("ability_radar", {})
            report.skills_summary = data.get("skills_summary", {})
            report.fingerprints_total = data.get("fingerprints_total", 0)
            report.patterns_total = data.get("patterns_total", 0)
            report.preferences_total = data.get("preferences_total", 0)
            return report
        except (json.JSONDecodeError, IOError):
            return None
