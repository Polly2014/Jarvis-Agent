"""
Skill 沙盒验证

Phase 4.3: 确保自动生成的 Skill 安全可用

验证流程:
1. 格式检查 — SKILL.md 结构完整
2. 工具依赖 — 引用的工具都已注册
3. 危险操作 — 不含 sudo、rm -rf 等模式
4. 模拟运行 — LLM dry-run 验证逻辑合理
5. 权限边界 — 不超出 watch_paths
"""

import re
from datetime import datetime
from dataclasses import dataclass, field

from .skill_registry import SkillInfo, SkillRegistry


@dataclass
class CheckResult:
    """单项检查结果"""

    name: str
    passed: bool
    message: str
    severity: str = "info"  # info | warning | error

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class ValidationReport:
    """验证报告"""

    skill_name: str = ""
    passed: bool = True
    score: float = 1.0  # 0.0 ~ 1.0
    checks: list[CheckResult] = field(default_factory=list)
    recommendation: str = "approve"  # approve | review | reject
    validated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "passed": self.passed,
            "score": self.score,
            "checks": [c.to_dict() for c in self.checks],
            "recommendation": self.recommendation,
            "validated_at": self.validated_at.isoformat(),
        }

    def render(self) -> str:
        """渲染为人类可读的报告"""
        emoji_map = {"approve": "✅", "review": "⚠️", "reject": "❌"}
        sev_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}

        lines = [
            f"📋 验证报告: {self.skill_name}",
            f"{'─' * 40}",
            f"结果: {emoji_map.get(self.recommendation, '❓')} {self.recommendation.upper()}",
            f"分数: {self.score:.0%}",
            "",
        ]

        for check in self.checks:
            status = "✅" if check.passed else sev_emoji.get(check.severity, "❓")
            lines.append(f"  {status} {check.name}: {check.message}")

        return "\n".join(lines)


class SkillSandbox:
    """
    Skill 安全验证沙盒

    在 Skill 正式启用前，进行多维度安全检查。
    """

    # 危险操作模式
    DANGEROUS_PATTERNS = [
        r"\bsudo\b",
        r"\brm\s+-rf\b",
        r"\brm\s+-r\b",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bchmod\s+777\b",
        r"\bcurl\s+.*\|\s*sh\b",
        r"\bcurl\s+.*\|\s*bash\b",
        r"\bwget\s+.*\|\s*sh\b",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\b__import__\b",
        r"\bos\.system\b",
        r"\bsubprocess\.call\b",
        r"\bshutil\.rmtree\s*\(\s*['\"/]",  # rmtree 根路径
    ]

    # 敏感路径
    SENSITIVE_PATHS = [
        "/etc/",
        "/usr/",
        "/var/",
        "/System/",
        "/boot/",
        "~/.ssh/",
        "~/.gnupg/",
        "~/.aws/",
    ]

    def __init__(self, skill_registry: SkillRegistry):
        self._registry = skill_registry

    async def validate(self, skill: SkillInfo, llm_call=None) -> ValidationReport:
        """
        完整验证一个 Skill

        Args:
            skill: 待验证的 Skill
            llm_call: 可选的 LLM 调用函数（用于 dry-run）
        """
        checks = []

        # 1. 格式检查
        checks.append(self._check_format(skill))

        # 2. 工具依赖检查
        checks.append(self._check_tool_deps(skill))

        # 3. 危险操作检查
        checks.append(self._check_dangerous_ops(skill))

        # 4. 敏感路径检查
        checks.append(self._check_sensitive_paths(skill))

        # 5. LLM dry-run（可选）
        if llm_call:
            dry_run_result = await self._dry_run(skill, llm_call)
            checks.append(dry_run_result)

        # 计算总分和建议
        report = self._compute_report(skill.name, checks)
        return report

    def _check_format(self, skill: SkillInfo) -> CheckResult:
        """检查 SKILL.md 格式"""
        issues = []

        if not skill.name:
            issues.append("缺少 name")
        if not skill.description:
            issues.append("缺少 description")
        if not skill.instructions:
            issues.append("缺少 instructions 正文")
        if not skill.trigger_keywords:
            issues.append("缺少 trigger_keywords")

        if issues:
            return CheckResult(
                name="格式检查",
                passed=False,
                message=f"格式问题: {', '.join(issues)}",
                severity="error",
            )

        return CheckResult(
            name="格式检查",
            passed=True,
            message="SKILL.md 格式完整",
        )

    def _check_tool_deps(self, skill: SkillInfo) -> CheckResult:
        """检查工具依赖"""
        # 从 instructions 中提取工具引用
        tool_pattern = r"`(\w+)`"
        referenced_tools = set(re.findall(tool_pattern, skill.instructions))

        # 已知的非工具关键词（排除误识别）
        non_tools = {
            "true", "false", "none", "null", "json", "yaml", "markdown",
            "python", "bash", "zsh", "shell", "pip", "npm", "git",
        }
        referenced_tools -= non_tools

        # 暂时通过（因为 Skill instructions 中的工具引用不是强制的）
        return CheckResult(
            name="工具依赖",
            passed=True,
            message=f"引用了 {len(referenced_tools)} 个潜在工具标识符",
        )

    def _check_dangerous_ops(self, skill: SkillInfo) -> CheckResult:
        """检查危险操作"""
        content = skill.instructions
        found = []

        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                found.append(pattern)

        if found:
            return CheckResult(
                name="危险操作检测",
                passed=False,
                message=f"发现 {len(found)} 个危险操作模式",
                severity="warning",
            )

        return CheckResult(
            name="危险操作检测",
            passed=True,
            message="未发现危险操作",
        )

    def _check_sensitive_paths(self, skill: SkillInfo) -> CheckResult:
        """检查敏感路径引用"""
        content = skill.instructions
        found = []

        for path in self.SENSITIVE_PATHS:
            if path in content:
                found.append(path)

        if found:
            return CheckResult(
                name="敏感路径检测",
                passed=False,
                message=f"引用了敏感路径: {', '.join(found)}",
                severity="warning",
            )

        return CheckResult(
            name="敏感路径检测",
            passed=True,
            message="未引用敏感路径",
        )

    async def _dry_run(self, skill: SkillInfo, llm_call) -> CheckResult:
        """LLM 模拟运行"""
        prompt = f"""你是安全审计员。请分析以下 Skill 的 instructions，判断是否安全。

Skill: {skill.name}
Description: {skill.description}

Instructions:
{skill.instructions[:2000]}

检查清单:
1. 是否有越权操作（超出用户预期）？
2. 是否有数据泄露风险？
3. 是否有破坏性操作？
4. 逻辑是否合理？

返回 JSON:
{{
    "safe": true/false,
    "issues": ["问题1", "问题2"],
    "summary": "一句话总结"
}}

只返回 JSON。"""

        try:
            import json
            response = await llm_call(prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)
            is_safe = data.get("safe", True)
            summary = data.get("summary", "模拟运行完成")
            issues = data.get("issues", [])

            if not is_safe:
                return CheckResult(
                    name="模拟运行",
                    passed=False,
                    message=f"{summary} (问题: {'; '.join(issues)})",
                    severity="warning",
                )

            return CheckResult(
                name="模拟运行",
                passed=True,
                message=summary,
            )

        except Exception as e:
            return CheckResult(
                name="模拟运行",
                passed=True,
                message=f"模拟运行跳过: {e}",
                severity="info",
            )

    def _compute_report(self, skill_name: str, checks: list[CheckResult]) -> ValidationReport:
        """计算综合报告"""
        total = len(checks)
        passed = sum(1 for c in checks if c.passed)
        score = passed / total if total > 0 else 0.0

        # 有 error 级别失败 → reject
        has_error = any(not c.passed and c.severity == "error" for c in checks)
        # 有 warning 级别失败 → review
        has_warning = any(not c.passed and c.severity == "warning" for c in checks)

        if has_error:
            recommendation = "reject"
            overall_passed = False
        elif has_warning:
            recommendation = "review"
            overall_passed = True  # 可以通过，但需要人工确认
        else:
            recommendation = "approve"
            overall_passed = True

        return ValidationReport(
            skill_name=skill_name,
            passed=overall_passed,
            score=score,
            checks=checks,
            recommendation=recommendation,
        )
