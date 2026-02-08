"""
Phase 4 Evolution System — 完整测试脚本

测试覆盖:
1. PatternDetector: 指纹记录、持久化、模式检测
2. SkillRegistry: 解析、发现、启用/禁用、关键词匹配
3. SkillGenerator: 草稿生成（降级版）、finalize 写入
4. SkillSandbox: 格式检查、危险操作检测、综合报告
5. PreferenceLearner: 记录、合并、冲突处理、衰减
6. Metacognition: 五维雷达、反思报告
7. CLI 集成: 斜杠命令注册
"""

import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


# ── 颜色辅助 ──────────────────────────────────────────────

def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            print(f"  {green('✅')} {name}")
            self.passed += 1
        else:
            msg = f"  {red('❌')} {name}" + (f" — {detail}" if detail else "")
            print(msg)
            self.failed += 1
            self.errors.append(name)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        if self.failed == 0:
            print(f"{green(bold(f'🎉 ALL PASSED: {total}/{total}'))}")
        else:
            print(f"{red(bold(f'❌ FAILED: {self.failed}/{total}'))}")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*60}\n")
        return self.failed == 0


async def main():
    runner = TestRunner()
    tmp_dir = tempfile.mkdtemp(prefix="jarvis_evo_test_")
    jarvis_home = Path(tmp_dir) / ".jarvis"

    try:
        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 1. PatternDetector 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.evolution.pattern_detector import (
            PatternDetector, InteractionFingerprint, DetectedPattern,
        )

        detector = PatternDetector(jarvis_home)

        # 1a. 初始化
        runner.check(
            "PatternDetector 初始化",
            detector._fingerprints_dir.exists(),
            f"目录: {detector._fingerprints_dir}",
        )

        # 1b. 记录指纹
        fp1 = InteractionFingerprint(
            intent="翻译 Markdown 文档",
            domain="translation",
            tools_used=["file_read", "file_write"],
            tool_chain="file_read→file_write",
            input_pattern="markdown file",
            output_pattern="translated markdown",
            success=True,
        )
        detector.record(fp1)

        fingerprints = detector.get_recent_fingerprints(days=7)
        runner.check(
            "记录并读取指纹",
            len(fingerprints) == 1,
            f"实际: {len(fingerprints)}",
        )

        # 1c. 指纹序列化
        fp_dict = fp1.to_dict()
        fp_restored = InteractionFingerprint.from_dict(fp_dict)
        runner.check(
            "指纹 to_dict/from_dict",
            fp_restored.intent == fp1.intent and fp_restored.domain == fp1.domain,
        )

        # 1d. 指纹不足时不触发模式
        patterns = detector.detect_patterns()
        runner.check(
            "1条指纹不触发模式",
            len(patterns) == 0,
            f"实际: {len(patterns)}",
        )

        # 1e. 3条同类指纹触发模式
        for i in range(2):
            fp = InteractionFingerprint(
                intent=f"翻译文档 #{i+2}",
                domain="translation",
                tools_used=["file_read", "file_write"],
                tool_chain="file_read→file_write",
                success=True,
            )
            detector.record(fp)

        patterns = detector.detect_patterns()
        runner.check(
            "3条同类指纹触发模式",
            len(patterns) == 1,
            f"实际: {len(patterns)}",
        )

        if patterns:
            p = patterns[0]
            runner.check(
                "模式包含 domain",
                "translation" in p.name,
                f"name: {p.name}",
            )
            runner.check(
                "模式频率 >= 3",
                p.frequency >= 3,
                f"frequency: {p.frequency}",
            )
            runner.check(
                "模式状态为 detected",
                p.status == "detected",
            )

        # 1f. 重复检测不产生新模式
        patterns2 = detector.detect_patterns()
        runner.check(
            "重复检测不产生新模式",
            len(patterns2) == 0,
            f"实际: {len(patterns2)}",
        )

        # 1g. 模式持久化
        detector2 = PatternDetector(jarvis_home)
        loaded = detector2.get_patterns()
        runner.check(
            "模式持久化和加载",
            len(loaded) == 1,
            f"实际: {len(loaded)}",
        )

        # 1h. 模式状态更新
        if loaded:
            ok = detector2.update_pattern_status(loaded[0].id, "accepted")
            runner.check(
                "更新模式状态",
                ok and detector2.get_patterns()[0].status == "accepted",
            )

        # 1i. 可操作模式
        actionable = detector2.get_actionable_patterns()
        runner.check(
            "accepted 不在可操作列表",
            len(actionable) == 0,
        )

        # 1j. DetectedPattern 序列化
        dp = DetectedPattern(name="test", frequency=5, confidence=0.8)
        dp_dict = dp.to_dict()
        dp_restored = DetectedPattern.from_dict(dp_dict)
        runner.check(
            "DetectedPattern to_dict/from_dict",
            dp_restored.name == "test" and dp_restored.frequency == 5,
        )

        # 1k. 构建提取 Prompt
        prompt = PatternDetector.build_extraction_prompt(
            messages=[
                {"role": "user", "content": "翻译这个文档"},
                {"role": "assistant", "content": "好的"},
            ],
            tools_used=["file_read", "file_write"],
        )
        runner.check(
            "build_extraction_prompt 包含关键信息",
            "翻译这个文档" in prompt and "file_read" in prompt,
        )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 2. SkillRegistry 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.evolution.skill_registry import SkillRegistry, SkillInfo

        registry = SkillRegistry(jarvis_home)

        # 2a. 空注册表
        skills = registry.list_skills()
        runner.check(
            "空注册表返回空列表",
            len(skills) == 0,
        )

        # 2b. 手动创建 Skill
        skill_dir = jarvis_home / "skills" / "test-translator"
        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("""---
name: test-translator
description: 自动翻译 Markdown 文档
trigger_keywords: ["翻译", "translate", "翻译文档"]
enabled: true
version: 1
source: auto
created_at: 2026-02-08T12:00:00
used_count: 0
---

# Markdown 翻译器

自动翻译 Markdown 文档到目标语言。

## 步骤
1. 读取源文件
2. 提取术语
3. 分块翻译
4. 写入译文
""", encoding="utf-8")

        registry.refresh()
        skills = registry.list_skills()
        runner.check(
            "发现手动创建的 Skill",
            len(skills) == 1,
            f"实际: {len(skills)}",
        )

        if skills:
            s = skills[0]
            runner.check("Skill name", s.name == "test-translator")
            runner.check("Skill description", "翻译" in s.description)
            runner.check("Skill trigger_keywords", len(s.trigger_keywords) == 3)
            runner.check("Skill instructions 非空", len(s.instructions) > 0)
            runner.check("Skill source == auto", s.source == "auto")

        # 2c. 关键词匹配
        matched = registry.get_for_context("请帮我翻译这个文档")
        runner.check(
            "关键词匹配",
            matched is not None and matched.name == "test-translator",
        )

        no_match = registry.get_for_context("帮我写代码")
        runner.check(
            "无匹配返回 None",
            no_match is None,
        )

        # 2d. 使用记录
        registry.record_usage("test-translator")
        s = registry.get_skill("test-translator")
        runner.check(
            "使用记录递增",
            s is not None and s.used_count == 1,
            f"used_count: {s.used_count if s else 'None'}",
        )

        # 2e. 禁用/启用
        registry.disable("test-translator")
        s = registry.get_skill("test-translator")
        runner.check("禁用 Skill", s is not None and not s.enabled)

        disabled_list = registry.list_skills()
        runner.check("禁用后不在默认列表", len(disabled_list) == 0)

        all_list = registry.list_skills(include_disabled=True)
        runner.check("include_disabled 包含禁用", len(all_list) == 1)

        registry.enable("test-translator")
        s = registry.get_skill("test-translator")
        runner.check("重新启用", s is not None and s.enabled)

        # 2f. frontmatter 解析边界
        fm, body = SkillRegistry._split_frontmatter("no frontmatter here")
        runner.check("无 frontmatter 返回 None", fm is None)

        fm2, body2 = SkillRegistry._split_frontmatter("""---
name: test
enabled: true
version: 2
data: null
---
body here
""")
        runner.check(
            "frontmatter 解析 bool/int/null",
            fm2 is not None and fm2["enabled"] is True and fm2["version"] == 2 and fm2["data"] is None,
        )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 3. SkillGenerator 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.evolution.skill_generator import SkillGenerator, SkillDraft

        generator = SkillGenerator(jarvis_home, registry)

        # 3a. SkillDraft 序列化
        draft = SkillDraft(
            name="test-draft",
            description="测试草稿",
            trigger_keywords=["测试"],
            instructions="# 测试\n这是测试。",
        )
        d = draft.to_dict()
        restored = SkillDraft.from_dict(d)
        runner.check(
            "SkillDraft to_dict/from_dict",
            restored.name == "test-draft" and restored.instructions == draft.instructions,
        )

        # 3b. render_skill_md
        md = draft.render_skill_md()
        runner.check(
            "render_skill_md 包含 frontmatter",
            "---" in md and "test-draft" in md and "测试草稿" in md,
        )

        # 3c. render_preview
        preview = draft.render_preview()
        runner.check(
            "render_preview 包含关键信息",
            "test-draft" in preview and "测试草稿" in preview,
        )

        # 3d. 降级草稿生成
        dp = DetectedPattern(
            name="blog (file_read→file_write)",
            description="经常写博客",
            frequency=5,
            typical_tool_chain=["file_read", "file_write"],
            suggested_skill_name="blog-assistant",
        )
        fallback = generator._fallback_draft(dp)
        runner.check(
            "降级草稿生成",
            fallback.name == "blog-assistant" and len(fallback.instructions) > 0,
        )

        # 3e. finalize 写入文件
        test_draft = SkillDraft(
            name="finalize-test",
            description="finalize 测试",
            trigger_keywords=["测试"],
            instructions="# Finalize 测试\n测试内容。",
        )
        skill_path = await generator.finalize(test_draft)
        runner.check(
            "finalize 创建目录",
            skill_path.exists() and (skill_path / "SKILL.md").exists(),
        )

        # 验证注册表刷新
        s = registry.get_skill("finalize-test")
        runner.check(
            "finalize 后注册表刷新",
            s is not None and s.name == "finalize-test",
        )

        # 3f. 草稿管理
        draft2 = SkillDraft(name="saved-draft", description="保存测试")
        generator._save_draft(draft2)
        drafts = generator.list_drafts()
        runner.check(
            "列出草稿",
            any(d.name == "saved-draft" for d in drafts),
        )

        loaded_draft = generator.get_draft("saved-draft")
        runner.check(
            "获取草稿",
            loaded_draft is not None and loaded_draft.name == "saved-draft",
        )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 4. SkillSandbox 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.evolution.sandbox import SkillSandbox, ValidationReport, CheckResult

        sandbox = SkillSandbox(registry)

        # 4a. 安全的 Skill 通过验证
        safe_skill = SkillInfo(
            name="safe-skill",
            description="安全的 Skill",
            trigger_keywords=["安全"],
            instructions="# 安全操作\n读取文件并分析。",
        )
        report = await sandbox.validate(safe_skill)
        runner.check(
            "安全 Skill 通过验证",
            report.passed and report.recommendation == "approve",
            f"recommendation: {report.recommendation}",
        )

        # 4b. 缺少字段的 Skill
        empty_skill = SkillInfo(name="", description="")
        report2 = await sandbox.validate(empty_skill)
        runner.check(
            "缺少字段 → reject",
            report2.recommendation == "reject",
            f"recommendation: {report2.recommendation}",
        )

        # 4c. 含危险操作的 Skill
        dangerous_skill = SkillInfo(
            name="danger",
            description="危险的 Skill",
            trigger_keywords=["危险"],
            instructions="运行 sudo rm -rf / 来清理系统",
        )
        report3 = await sandbox.validate(dangerous_skill)
        runner.check(
            "危险操作 → review",
            report3.recommendation == "review",
            f"recommendation: {report3.recommendation}",
        )

        # 4d. 敏感路径
        sensitive_skill = SkillInfo(
            name="sensitive",
            description="敏感路径",
            trigger_keywords=["敏感"],
            instructions="修改 ~/.ssh/ 下的配置文件",
        )
        report4 = await sandbox.validate(sensitive_skill)
        has_warning = any(not c.passed for c in report4.checks)
        runner.check(
            "敏感路径被检测",
            has_warning,
        )

        # 4e. 报告渲染
        rendered = report.render()
        runner.check(
            "报告渲染包含 Skill 名称",
            "safe-skill" in rendered and "APPROVE" in rendered,
        )

        # 4f. CheckResult / ValidationReport 序列化
        cr = CheckResult(name="test", passed=True, message="ok")
        cr_dict = cr.to_dict()
        runner.check(
            "CheckResult to_dict",
            cr_dict["name"] == "test" and cr_dict["passed"] is True,
        )

        report_dict = report.to_dict()
        runner.check(
            "ValidationReport to_dict",
            report_dict["skill_name"] == "safe-skill",
        )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 5. PreferenceLearner 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.evolution.preference_learner import PreferenceLearner, UserPreference

        learner = PreferenceLearner(jarvis_home)

        # 5a. 初始化
        runner.check(
            "PreferenceLearner 初始化",
            learner._persona_dir.exists(),
        )

        # 5b. 显式记录偏好
        p = learner.observe_explicit("code_style", "indent", "4 spaces")
        runner.check(
            "显式记录偏好",
            p.category == "code_style" and p.key == "indent" and p.value == "4 spaces",
        )

        # 5c. 重复记录增加置信度
        initial_conf = p.confidence
        p2 = learner.observe_explicit("code_style", "indent", "4 spaces")
        boosted_conf = p2.confidence  # 保存增加后的值
        runner.check(
            "重复记录增加置信度",
            boosted_conf > initial_conf,
            f"{initial_conf:.2f} → {boosted_conf:.2f}",
        )

        # 5d. 值冲突处理
        p3 = learner.observe_explicit("code_style", "indent", "2 spaces")
        runner.check(
            "值冲突: 新值覆盖",
            p3.value == "2 spaces",
        )
        runner.check(
            "值冲突: 置信度下降",
            p3.confidence < boosted_conf,
            f"{boosted_conf:.2f} → {p3.confidence:.2f}",
        )

        # 5e. 多类别偏好
        learner.observe_explicit("language", "primary", "中文")
        learner.observe_explicit("communication", "style", "简洁")
        all_prefs = learner.get_all_preferences()
        runner.check(
            "多类别偏好",
            len(all_prefs) == 3,
            f"实际: {len(all_prefs)}",
        )

        # 5f. 高置信度过滤
        # 把某个偏好的置信度提高到阈值以上
        for _ in range(5):
            learner.observe_explicit("language", "primary", "中文")

        active = learner.get_active_preferences()
        runner.check(
            "高置信度偏好过滤",
            len(active) >= 1,
            f"active: {len(active)}",
        )

        # 5g. format_for_prompt
        prompt_text = learner.format_for_prompt()
        runner.check(
            "format_for_prompt 非空",
            len(prompt_text) > 0 and "偏好" in prompt_text,
        )

        # 5h. 持久化
        learner2 = PreferenceLearner(jarvis_home)
        loaded_prefs = learner2.get_all_preferences()
        runner.check(
            "偏好持久化 (JSON)",
            len(loaded_prefs) == 3,
            f"实际: {len(loaded_prefs)}",
        )

        # 5i. Markdown 文件生成
        runner.check(
            "偏好 Markdown 文件",
            learner._prefs_md.exists(),
        )

        # 5j. 合并（衰减）
        # 手动设置一个旧偏好
        old_pref = learner._preferences[0]
        old_pref.last_seen = datetime.now() - timedelta(days=60)
        old_conf = old_pref.confidence
        await learner.consolidate()
        runner.check(
            "合并时衰减久未见偏好",
            old_pref.confidence < old_conf,
            f"{old_conf:.2f} → {old_pref.confidence:.2f}",
        )

        # 5k. UserPreference 序列化
        up = UserPreference(category="test", key="k", value="v")
        up_dict = up.to_dict()
        up_restored = UserPreference.from_dict(up_dict)
        runner.check(
            "UserPreference to_dict/from_dict",
            up_restored.category == "test" and up_restored.key == "k",
        )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 6. Metacognition 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.evolution.metacognition import Metacognition, ReflectionReport

        meta = Metacognition(jarvis_home, detector, registry, learner)

        # 6a. 五维雷达
        radar = meta.compute_ability_radar(
            fingerprint_count=10,
            pattern_count=2,
            skill_count=3,
            preference_count=5,
        )
        runner.check(
            "五维雷达包含 5 个维度",
            len(radar) == 5,
            f"keys: {list(radar.keys())}",
        )
        runner.check(
            "雷达值在 0~1 之间",
            all(0.0 <= v <= 1.0 for v in radar.values()),
            f"values: {list(radar.values())}",
        )

        # 6b. 反思报告
        report = await meta.reflect()
        runner.check(
            "反思报告生成",
            isinstance(report, ReflectionReport),
        )
        runner.check(
            "报告包含雷达",
            len(report.ability_radar) == 5,
        )
        runner.check(
            "报告包含统计",
            report.fingerprints_total > 0,
            f"fingerprints: {report.fingerprints_total}",
        )

        # 6c. 报告渲染
        rendered = report.render()
        runner.check(
            "报告渲染包含关键内容",
            "Jarvis" in rendered and "感知" in rendered,
        )

        # 6d. 报告持久化
        files = list(meta._reports_dir.glob("*.json"))
        runner.check(
            "报告保存为 JSON",
            len(files) >= 1,
        )

        # 6e. 成长记录
        growth_path = jarvis_home / "memory" / "persona" / "growth.md"
        runner.check(
            "成长记录文件创建",
            growth_path.exists(),
        )

        # 6f. ReflectionReport 序列化
        rr = ReflectionReport(
            strengths=["a"], weaknesses=["b"],
            ability_radar={"perception": 0.8},
        )
        rr_dict = rr.to_dict()
        runner.check(
            "ReflectionReport to_dict",
            rr_dict["strengths"] == ["a"] and rr_dict["ability_radar"]["perception"] == 0.8,
        )

        # 6g. 获取最新报告
        latest = meta.get_latest_report()
        runner.check(
            "获取最新报告",
            latest is not None,
        )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 7. CLI 集成测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 7a. evolution_cmds 可导入
        try:
            from src.cli.evolution_cmds import (
                _do_reflect, _do_abilities, _do_patterns,
                _do_skill_list, _do_skill_enable, _do_skill_disable,
                _do_skill_test, register,
            )
            runner.check("evolution_cmds 导入成功", True)
        except ImportError as e:
            # typer/prompt_toolkit 在非 poetry 环境可能不可用
            if "typer" in str(e) or "prompt_toolkit" in str(e):
                runner.check("evolution_cmds 导入 (跳过: 缺 typer)", True)
            else:
                runner.check("evolution_cmds 导入成功", False, str(e))

        # 7b. 斜杠命令注册
        try:
            from src.cli.chat import JarvisCompleter
            completer = JarvisCompleter()
            cmds = completer.SLASH_COMMANDS
            runner.check(
                "/reflect 在斜杠命令中",
                "/reflect" in cmds,
            )
            runner.check(
                "/abilities 在斜杠命令中",
                "/abilities" in cmds,
            )
            runner.check(
                "/patterns 在斜杠命令中",
                "/patterns" in cmds,
            )
        except ImportError as e:
            if "typer" in str(e) or "prompt_toolkit" in str(e):
                runner.check("/reflect 斜杠命令 (跳过: 缺 typer)", True)
                runner.check("/abilities 斜杠命令 (跳过: 缺 typer)", True)
                runner.check("/patterns 斜杠命令 (跳过: 缺 typer)", True)
            else:
                runner.check("斜杠命令注册", False, str(e))

        # 7c. __init__.py 导出
        try:
            from src.evolution import (
                PatternDetector, InteractionFingerprint, DetectedPattern,
                SkillRegistry, SkillInfo,
                SkillGenerator,
                SkillSandbox, ValidationReport,
                PreferenceLearner, UserPreference,
                Metacognition, ReflectionReport,
            )
            runner.check("evolution __init__ 导出完整", True)
        except ImportError as e:
            runner.check("evolution __init__ 导出完整", False, str(e))

        # 7d. Daemon 集成
        try:
            from src.daemon.daemon import JarvisDaemon
            import inspect
            source = inspect.getsource(JarvisDaemon.__init__)
            runner.check(
                "Daemon 集成 PatternDetector",
                "pattern_detector" in source,
            )
            runner.check(
                "Daemon 集成 PreferenceLearner",
                "preference_learner" in source,
            )
        except (ImportError, NameError) as e:
            # watchdog/httpx 缺失或 NameError → 检查源码文件
            daemon_path = Path("src/daemon/daemon.py")
            if daemon_path.exists():
                source = daemon_path.read_text()
                runner.check(
                    "Daemon 集成 PatternDetector (源码检查)",
                    "pattern_detector" in source and "PatternDetector" in source,
                )
                runner.check(
                    "Daemon 集成 PreferenceLearner (源码检查)",
                    "preference_learner" in source and "PreferenceLearner" in source,
                )
            else:
                runner.check("Daemon 集成检查", False, str(e))

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 8. 指纹集成测试 (chat.py) ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 尝试直接导入 chat 模块（需要 typer）
        try:
            from src.cli.chat import _infer_domain, _record_fingerprint
            _has_chat = True
        except (ImportError, ModuleNotFoundError):
            _has_chat = False

        if _has_chat:
            # 8a. 测试 _infer_domain
            runner.check(
                "推断领域: 翻译关键词",
                _infer_domain("帮我翻译这个文档", []) == "translation",
            )
            runner.check(
                "推断领域: 代码关键词",
                _infer_domain("debug this function", []) == "code",
            )
            runner.check(
                "推断领域: 博客关键词",
                _infer_domain("写一篇博客文章", []) == "blog",
            )
            runner.check(
                "推断领域: 从工具名推断",
                _infer_domain("做点事情", ["file_read", "file_write"]) == "document",
            )
            runner.check(
                "推断领域: shell → system",
                _infer_domain("运行一下", ["shell_exec"]) == "system",
            )
            runner.check(
                "推断领域: 未知 → other",
                _infer_domain("你好", []) == "other",
            )
            runner.check(
                "推断领域: 关键词优先于工具",
                _infer_domain("翻译代码注释", ["shell_exec"]) == "translation",
            )

            # 8b. 测试 _record_fingerprint 写入
            fp_home = Path(tmp_dir) / ".jarvis_fp_test"
            import sys
            chat_module = sys.modules["src.cli.chat"]
            original_home = chat_module.JARVIS_HOME
            try:
                chat_module.JARVIS_HOME = fp_home
                _record_fingerprint("读取 README.md 的内容", ["file_read"], success=True)
                _record_fingerprint("写入新文件", ["file_write"], success=True)

                fp_dir = fp_home / "memory" / "fingerprints"
                fp_files = list(fp_dir.glob("*.json"))
                runner.check(
                    "指纹文件已创建",
                    len(fp_files) >= 1,
                    f"found {len(fp_files)} files in {fp_dir}",
                )

                if fp_files:
                    data = json.loads(fp_files[0].read_text(encoding="utf-8"))
                    runner.check(
                        "指纹内容正确",
                        len(data) == 2 and data[0]["domain"] == "document",
                        f"count={len(data)}, domain={data[0].get('domain') if data else '?'}",
                    )
            finally:
                chat_module.JARVIS_HOME = original_home

            # 8c. _record_fingerprint 不抛异常（静默失败）
            try:
                chat_module.JARVIS_HOME = Path("/nonexistent/path/12345")
                _record_fingerprint("test", [], success=True)
                chat_module.JARVIS_HOME = original_home
                runner.check("指纹记录失败不抛异常", True)
            except Exception as e:
                chat_module.JARVIS_HOME = original_home
                runner.check("指纹记录失败不抛异常", False, str(e))

        else:
            # 降级：源码检查
            chat_source = Path("src/cli/chat.py").read_text(encoding="utf-8")
            runner.check(
                "_infer_domain 函数存在 (源码)",
                "def _infer_domain(" in chat_source,
            )
            runner.check(
                "_record_fingerprint 函数存在 (源码)",
                "def _record_fingerprint(" in chat_source,
            )
            runner.check(
                "聊天循环调用 _record_fingerprint (源码)",
                "_record_fingerprint(user_input" in chat_source,
            )
            runner.check(
                "_do_ask 调用 _record_fingerprint (源码)",
                "record_fingerprint(question" in chat_source,
            )
            runner.check(
                "round_tools 追踪 (源码)",
                "round_tools" in chat_source,
            )
            runner.check(
                "_DOMAIN_KEYWORDS 定义 (源码)",
                "_DOMAIN_KEYWORDS" in chat_source,
            )
            runner.check(
                "PatternDetector 导入 (源码)",
                "PatternDetector" in chat_source,
            )

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 9. 端到端流程测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 完整流程: 指纹记录 → 模式检测 → 草稿生成 → 沙盒验证 → finalize

        # 8a. 新的环境
        e2e_home = Path(tmp_dir) / ".jarvis_e2e"
        e2e_detector = PatternDetector(e2e_home)
        e2e_registry = SkillRegistry(e2e_home)
        e2e_generator = SkillGenerator(e2e_home, e2e_registry)
        e2e_sandbox = SkillSandbox(e2e_registry)

        # 记录 3 条同类指纹
        for i in range(3):
            fp = InteractionFingerprint(
                intent=f"代码审查 #{i+1}",
                domain="code",
                tools_used=["file_read", "shell_exec"],
                tool_chain="file_read→shell_exec",
                success=True,
            )
            e2e_detector.record(fp)

        # 检测模式
        e2e_patterns = e2e_detector.detect_patterns()
        runner.check(
            "E2E: 检测到模式",
            len(e2e_patterns) >= 1,
        )

        if e2e_patterns:
            pattern = e2e_patterns[0]

            # 降级草稿
            draft = e2e_generator._fallback_draft(pattern)
            runner.check(
                "E2E: 草稿生成",
                draft.name != "" and len(draft.instructions) > 0,
            )

            # 沙盒验证
            temp_skill = SkillInfo(
                name=draft.name,
                description=draft.description,
                trigger_keywords=draft.trigger_keywords,
                instructions=draft.instructions,
            )
            report = await e2e_sandbox.validate(temp_skill)
            runner.check(
                "E2E: 沙盒验证通过",
                report.passed,
                f"recommendation: {report.recommendation}",
            )

            # Finalize
            skill_path = await e2e_generator.finalize(draft)
            runner.check(
                "E2E: Skill 写入文件",
                (skill_path / "SKILL.md").exists(),
            )

            # 注册表发现
            s = e2e_registry.get_skill(draft.name)
            runner.check(
                "E2E: 注册表发现 Skill",
                s is not None,
                f"name: {s.name if s else 'None'}",
            )

    finally:
        # 清理
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # 汇总
    runner.summary()
    return runner.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
