"""
Jarvis CLI — Evolution 进化系统命令

子命令:
  reflect     🧠 触发元认知反思
  abilities   📊 查看五维能力雷达
  patterns    🔍 查看检测到的交互模式

Skill 子命令组:
  skill list     列出所有 Skill
  skill enable   启用 Skill
  skill disable  禁用 Skill
  skill delete   删除 Skill
  skill test     沙盒测试 Skill
"""
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from .common import console, JARVIS_HOME, ensure_jarvis_home, load_llm_config


# ── 内部实现 ──────────────────────────────────────────────

def _get_evolution_components():
    """延迟加载 Evolution 组件"""
    from ..evolution.pattern_detector import PatternDetector
    from ..evolution.skill_registry import SkillRegistry
    from ..evolution.preference_learner import PreferenceLearner
    from ..evolution.metacognition import Metacognition

    detector = PatternDetector(JARVIS_HOME)
    registry = SkillRegistry(JARVIS_HOME)
    learner = PreferenceLearner(JARVIS_HOME)
    meta = Metacognition(JARVIS_HOME, detector, registry, learner)

    return detector, registry, learner, meta


def _do_reflect():
    """执行元认知反思"""
    ensure_jarvis_home()
    detector, registry, learner, meta = _get_evolution_components()

    console.print("\n[bold cyan]🧠 正在进行元认知反思...[/bold cyan]\n")

    report = asyncio.run(meta.reflect())
    console.print(report.render())
    console.print()


def _do_abilities():
    """查看五维能力雷达"""
    ensure_jarvis_home()
    detector, registry, learner, meta = _get_evolution_components()

    fingerprints = detector.get_recent_fingerprints(days=30)
    patterns = detector.get_patterns()
    skills = registry.list_skills(include_disabled=True)
    preferences = learner.get_all_preferences()

    radar = meta.compute_ability_radar(
        fingerprint_count=len(fingerprints),
        pattern_count=len(patterns),
        skill_count=len(skills),
        preference_count=len(preferences),
    )

    radar_labels = {
        "perception": ("👁️", "感知"),
        "memory": ("🧠", "记忆"),
        "thinking": ("💭", "思考"),
        "action": ("🦾", "行动"),
        "evolution": ("🔄", "进化"),
    }

    console.print("\n[bold]📊 五维能力雷达[/bold]\n")
    for key, (emoji, label) in radar_labels.items():
        score = radar.get(key, 0.0)
        filled = int(score * 10)
        bar = "█" * filled + "░" * (10 - filled)
        pct = f"{score:.0%}"
        console.print(f"  {emoji} {label}  {bar} {pct}")

    console.print()
    console.print(f"  [dim]指纹: {len(fingerprints)} | 模式: {len(patterns)} | "
                  f"Skill: {len(skills)} | 偏好: {len(preferences)}[/dim]")
    console.print()


def _do_patterns():
    """查看检测到的交互模式"""
    ensure_jarvis_home()
    from ..evolution.pattern_detector import PatternDetector

    detector = PatternDetector(JARVIS_HOME)
    patterns = detector.get_patterns()

    if not patterns:
        console.print("\n[dim]暂无检测到的模式。使用更多对话后，模式会自动浮现。[/dim]\n")
        return

    console.print(f"\n[bold]🔍 检测到的模式[/bold] ({len(patterns)} 个)\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("状态", width=8)
    table.add_column("模式", min_width=20)
    table.add_column("频率", width=6, justify="center")
    table.add_column("置信度", width=8, justify="center")
    table.add_column("建议 Skill", min_width=15)

    status_emoji = {
        "detected": "🔵",
        "proposed": "🟡",
        "accepted": "🟢",
        "rejected": "🔴",
        "covered": "✅",
    }

    for p in patterns:
        emoji = status_emoji.get(p.status, "❓")
        conf = f"{p.confidence:.0%}"
        table.add_row(
            f"{emoji} {p.status}",
            p.name,
            str(p.frequency),
            conf,
            p.suggested_skill_name,
        )

    console.print(table)
    console.print()


def _do_skill_list(include_disabled: bool = False):
    """列出所有 Skill"""
    ensure_jarvis_home()
    from ..evolution.skill_registry import SkillRegistry

    registry = SkillRegistry(JARVIS_HOME)
    skills = registry.list_skills(include_disabled=include_disabled)

    if not skills:
        console.print("\n[dim]暂无 Skill。Jarvis 会在检测到重复模式时自动提议创建。[/dim]\n")
        return

    console.print(f"\n[bold]🧬 Skill 列表[/bold] ({len(skills)} 个)\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("名称", min_width=20)
    table.add_column("来源", width=8)
    table.add_column("状态", width=8)
    table.add_column("使用次数", width=8, justify="center")
    table.add_column("描述", min_width=25)

    for s in skills:
        status = "✅ 启用" if s.enabled else "⏸️ 禁用"
        source_emoji = {"auto": "🤖", "manual": "👤", "builtin": "📦"}.get(s.source, "❓")
        table.add_row(
            s.name,
            f"{source_emoji} {s.source}",
            status,
            str(s.used_count),
            s.description[:40] + ("..." if len(s.description) > 40 else ""),
        )

    console.print(table)
    console.print()


def _do_skill_enable(name: str):
    """启用 Skill"""
    from ..evolution.skill_registry import SkillRegistry
    registry = SkillRegistry(JARVIS_HOME)
    if registry.enable(name):
        console.print(f"[green]✅ Skill '{name}' 已启用[/green]")
    else:
        console.print(f"[red]❌ 找不到 Skill '{name}'[/red]")


def _do_skill_disable(name: str):
    """禁用 Skill"""
    from ..evolution.skill_registry import SkillRegistry
    registry = SkillRegistry(JARVIS_HOME)
    if registry.disable(name):
        console.print(f"[yellow]⏸️ Skill '{name}' 已禁用[/yellow]")
    else:
        console.print(f"[red]❌ 找不到 Skill '{name}'[/red]")


def _do_skill_delete(name: str):
    """删除 Skill"""
    from ..evolution.skill_registry import SkillRegistry
    registry = SkillRegistry(JARVIS_HOME)
    if registry.delete(name):
        console.print(f"[red]🗑️ Skill '{name}' 已删除（已移到 .trash）[/red]")
    else:
        console.print(f"[red]❌ 找不到 Skill '{name}'[/red]")


def _do_skill_test(name: str):
    """沙盒测试 Skill"""
    from ..evolution.skill_registry import SkillRegistry
    from ..evolution.sandbox import SkillSandbox

    registry = SkillRegistry(JARVIS_HOME)
    skill = registry.get_skill(name)

    if not skill:
        console.print(f"[red]❌ 找不到 Skill '{name}'[/red]")
        return

    sandbox = SkillSandbox(registry)

    console.print(f"\n[bold]🧪 沙盒测试: {name}[/bold]\n")
    report = asyncio.run(sandbox.validate(skill))
    console.print(report.render())
    console.print()


# ── Typer 子命令 ──────────────────────────────────────────

# Skill 子命令组
skill_app = typer.Typer(
    name="skill",
    help="🧬 Skill 管理（列出、启用、禁用、测试、删除）",
    invoke_without_command=True,
    no_args_is_help=True,
)


@skill_app.command("list")
def skill_list(
    all: bool = typer.Option(False, "--all", "-a", help="包括已禁用的 Skill"),
):
    """📋 列出所有 Skill"""
    _do_skill_list(include_disabled=all)


@skill_app.command("enable")
def skill_enable(name: str = typer.Argument(..., help="Skill 名称")):
    """✅ 启用 Skill"""
    _do_skill_enable(name)


@skill_app.command("disable")
def skill_disable(name: str = typer.Argument(..., help="Skill 名称")):
    """⏸️ 禁用 Skill"""
    _do_skill_disable(name)


@skill_app.command("delete")
def skill_delete(
    name: str = typer.Argument(..., help="Skill 名称"),
    force: bool = typer.Option(False, "--force", "-f", help="不确认直接删除"),
):
    """🗑️ 删除 Skill"""
    if not force:
        confirm = typer.confirm(f"确定删除 Skill '{name}'？")
        if not confirm:
            console.print("[dim]已取消[/dim]")
            return
    _do_skill_delete(name)


@skill_app.command("test")
def skill_test(name: str = typer.Argument(..., help="Skill 名称")):
    """🧪 沙盒测试 Skill"""
    _do_skill_test(name)


def register(app: typer.Typer):
    """注册 evolution 相关子命令到 app"""

    @app.command()
    def reflect():
        """🧠 元认知反思 — 查看 Jarvis 的自我认知"""
        _do_reflect()

    @app.command()
    def abilities():
        """📊 五维能力雷达 — 感知/记忆/思考/行动/进化"""
        _do_abilities()

    @app.command()
    def patterns():
        """🔍 查看检测到的交互模式"""
        _do_patterns()

    # 注册 skill 子命令组
    app.add_typer(skill_app, name="skill")
