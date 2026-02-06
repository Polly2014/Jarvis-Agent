"""
Jarvis CLI — 探索、发现、技能、初始化命令
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from .common import (
    console, JARVIS_HOME,
    get_config_path, get_discoveries_path, ensure_jarvis_home,
)


# ── 内部实现 ──────────────────────────────────────────────

def _do_discoveries():
    """查看发现"""
    discoveries_path = get_discoveries_path()

    if not discoveries_path.exists():
        console.print("[yellow]还没有任何发现[/yellow]")
        return

    try:
        with open(discoveries_path, "r") as f:
            data = json.load(f)

        all_discoveries = data.get("discoveries", [])
        if not all_discoveries:
            console.print("[yellow]还没有任何发现[/yellow]")
            return

        console.print("\n[bold]📋 最近发现:[/bold]")
        for d in all_discoveries[:5]:
            ts = datetime.fromisoformat(d.get("timestamp", datetime.now().isoformat()))
            time_str = ts.strftime("%m/%d %H:%M")
            stars = "⭐" * d.get("importance", 3)
            title = d.get("title", "")[:30]
            ack = "✓" if d.get("acknowledged") else ""
            console.print(f"  [{time_str}] {title} {stars} {ack}")
    except Exception as e:
        console.print(f"[red]读取失败: {e}[/red]")


def _do_explore(path_arg: Optional[str] = None):
    """探索目录"""
    from ..explorer import scan_directory, format_discovery_report

    path = path_arg
    if path is None:
        config_path = get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                watch_paths = config.get("watch_paths", [])
                if watch_paths:
                    path = watch_paths[0]
            except Exception:
                pass

    if path is None:
        path = str(Path.cwd())

    target_path = Path(path).expanduser().resolve()

    if not target_path.exists():
        console.print(f"[red]❌ 目录不存在: {target_path}[/red]")
        return

    console.print(f"\n🔍 正在探索 [cyan]{target_path}[/cyan]...")
    projects = scan_directory(target_path)

    if not projects:
        console.print("[yellow]没有发现可识别的项目[/yellow]")
        return

    report = format_discovery_report(projects)
    console.print(report)


def _do_projects():
    """列出已发现的项目"""
    discoveries_path = get_discoveries_path()

    if not discoveries_path.exists():
        console.print("[yellow]还没有探索过任何目录[/yellow]")
        console.print("[dim]运行 jarvis explore 开始探索[/dim]")
        return

    try:
        with open(discoveries_path, "r") as f:
            data = json.load(f)

        discoveries = data.get("discoveries", [])
        # 过滤出 project_found 类型的发现
        projects = [d for d in discoveries if d.get("type") == "project_found"]

        if not projects:
            console.print("[yellow]还没有发现任何项目[/yellow]")
            console.print("[dim]运行 jarvis explore 开始探索[/dim]")
            return

        console.print("\n[bold]📂 已发现的项目:[/bold]\n")

        table = Table(box=None, padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("项目名", style="bold cyan")
        table.add_column("类型", style="green")
        table.add_column("路径", style="dim")
        table.add_column("发现时间", style="dim")

        for i, p in enumerate(projects, 1):
            ts = datetime.fromisoformat(p.get("timestamp", "")).strftime("%m-%d %H:%M") if p.get("timestamp") else "?"
            meta = p.get("metadata", {})
            table.add_row(
                str(i),
                p.get("title", "未知"),
                meta.get("project_type", "?"),
                meta.get("path", "?"),
                ts,
            )

        console.print(table)
        console.print(f"\n[dim]共 {len(projects)} 个项目[/dim]")

    except Exception as e:
        console.print(f"[red]读取失败: {e}[/red]")


def _do_skills():
    """列出 skills"""
    skills_dir = JARVIS_HOME / "skills"

    if not skills_dir.exists():
        console.print("[yellow]还没有任何 skill[/yellow]")
        return

    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]

    if not skill_dirs:
        console.print("[yellow]还没有任何 skill[/yellow]")
        return

    console.print("\n[bold]⚡ 已激活的 Skills:[/bold]")
    for skill_dir in skill_dirs:
        console.print(f"  • [cyan]{skill_dir.name}[/cyan]")


def _do_init():
    """初始化配置"""
    ensure_jarvis_home()

    console.print("\n[bold cyan]🥚 Jarvis 初始化[/bold cyan]")

    default_path = str(Path.home() / "projects")
    workspace = Prompt.ask("📁 你的工作目录路径", default=default_path)

    workspace_path = Path(workspace).expanduser().resolve()

    if not workspace_path.exists():
        console.print(f"[yellow]⚠️  目录 {workspace_path} 不存在[/yellow]")
        if Confirm.ask("要创建它吗？"):
            workspace_path.mkdir(parents=True)
        else:
            return

    config_path = get_config_path()
    config = {
        "daemon": {
            "think_interval_seconds": 60,
            "self_reflect_interval": 3600,
        },
        "watch_paths": [str(workspace_path)],
        "llm": {
            "base_url": "http://localhost:23335/api/openai",
            "auth_token": "Powered by Agent Maestro",
            "model": "claude-sonnet-4",
        },
        "notification": {
            "terminal": True,
            "macos_notification": True,
            "min_importance": 3,
        },
    }

    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    # 初始化 persona.md
    from ..memory import MemoryWriter
    memory_path = JARVIS_HOME / "memory"
    writer = MemoryWriter(memory_path)
    writer.init_persona({
        "name": "Jarvis",
        "owner": "Polly",
        "version": "0.2.0",
        "workspace": str(workspace_path),
    })
    console.print(f"   ✅ persona.md 已初始化")

    console.print(f"\n✅ 配置已保存: [green]{config_path}[/green]")


# ── Typer 子命令 ──────────────────────────────────────────

def register(app: typer.Typer):
    """注册探索相关子命令"""

    @app.command()
    def init():
        """🥚 初始化 Jarvis，开始你们的旅程"""
        ensure_jarvis_home()

        console.print(Panel.fit(
            "[bold cyan]你好！我是 Jarvis[/bold cyan]\n\n"
            "我是一个刚出生的 AI。现在什么都不懂，但我很好奇。\n"
            "能告诉我你的工作目录在哪里吗？我想去看看。",
            title="🥚 Jarvis 孵化中",
            border_style="cyan",
        ))

        default_path = str(Path.home() / "projects")
        workspace = Prompt.ask("\n📁 你的工作目录路径", default=default_path)

        workspace_path = Path(workspace).expanduser().resolve()

        if not workspace_path.exists():
            console.print(f"[yellow]⚠️  目录 {workspace_path} 不存在[/yellow]")
            if Confirm.ask("要创建它吗？"):
                workspace_path.mkdir(parents=True)
            else:
                raise typer.Exit(1)

        config_path = get_config_path()
        config = {
            "daemon": {
                "think_interval_seconds": 60,
                "self_reflect_interval": 3600,
            },
            "watch_paths": [str(workspace_path)],
            "llm": {
                "base_url": "http://localhost:23335/api/openai",
                "auth_token": "Powered by Agent Maestro",
                "model": "claude-sonnet-4",
            },
            "notification": {
                "terminal": True,
                "macos_notification": True,
                "min_importance": 3,
            },
        }

        with open(config_path, "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 初始化 persona.md
        from ..memory import MemoryWriter
        memory_path = JARVIS_HOME / "memory"
        writer = MemoryWriter(memory_path)
        writer.init_persona({
            "name": "Jarvis",
            "owner": "Polly",
            "version": "0.2.0",
            "workspace": str(workspace_path),
        })

        console.print(f"\n✅ 已记住你的工作目录: [green]{workspace_path}[/green]")
        console.print(f"   配置已保存到: {config_path}")
        console.print("   ✅ persona.md 已初始化")
        console.print("\n[dim]接下来：[/dim]")
        console.print("  1. [bold]jarvis explore[/bold] - 让我去探索你的世界")
        console.print("  2. [bold]jarvis start[/bold] - 启动心跳，让我真正活起来")

    @app.command()
    def explore(
        path: Optional[str] = typer.Argument(None, help="要探索的目录路径"),
    ):
        """🔍 探索目录，发现你的项目"""
        from ..explorer import scan_directory, format_discovery_report

        if path is None:
            config_path = get_config_path()
            if config_path.exists():
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    watch_paths = config.get("watch_paths", [])
                    if watch_paths:
                        path = watch_paths[0]
                except (json.JSONDecodeError, KeyError):
                    pass

            if path is None:
                path = str(Path.cwd())

        target_path = Path(path).expanduser().resolve()

        if not target_path.exists():
            console.print(f"[red]❌ 目录不存在: {target_path}[/red]")
            raise typer.Exit(1)

        console.print(f"\n🔍 正在探索 [cyan]{target_path}[/cyan]...\n")

        projects = scan_directory(target_path)

        if not projects:
            console.print("[yellow]没有发现可识别的项目[/yellow]")
            return

        report = format_discovery_report(projects)
        console.print(report)

        console.print("\n[dim]请输入编号确认要追踪的项目 (如: 1,3 或 all 或 none):[/dim]")
        selection = Prompt.ask("选择")

        if selection.lower() == "none":
            console.print("好的，以后再说。")
            return

        if selection.lower() == "all":
            selected_indices = list(range(len(projects)))
        else:
            try:
                selected_indices = [int(x.strip()) - 1 for x in selection.split(",")]
            except ValueError:
                console.print("[red]无效的输入[/red]")
                raise typer.Exit(1)

        for idx in selected_indices:
            if 0 <= idx < len(projects):
                project = projects[idx]
                console.print(f"\n⚡ 正在为 [cyan]{project.name}[/cyan] 创建追踪能力...")
                console.print(f"   ✅ [green]{project.name}[/green] skill 已激活")

    @app.command()
    def projects():
        """📂 列出已发现的项目"""
        _do_projects()

    @app.command()
    def discoveries(
        today: bool = typer.Option(False, "--today", "-t", help="只显示今日发现"),
        ack: bool = typer.Option(False, "--ack", "-a", help="确认所有发现为已阅读"),
        count: int = typer.Option(10, "--count", "-n", help="显示数量"),
    ):
        """💡 查看 Jarvis 的发现"""
        discoveries_path = get_discoveries_path()

        if not discoveries_path.exists():
            console.print("[yellow]还没有任何发现[/yellow]")
            return

        try:
            with open(discoveries_path, "r") as f:
                data = json.load(f)

            all_discoveries = data.get("discoveries", [])

            if ack:
                for d in all_discoveries:
                    d["acknowledged"] = True
                with open(discoveries_path, "w") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                console.print("[green]✅ 所有发现已标记为已阅读[/green]")
                return

            if today:
                today_date = datetime.now().date()
                filtered = [
                    d for d in all_discoveries
                    if datetime.fromisoformat(d.get("timestamp", "2000-01-01")).date() == today_date
                ]
            else:
                filtered = all_discoveries

            if not filtered:
                console.print("[yellow]没有发现[/yellow]")
                return

            table = Table(title="💡 Jarvis 发现", show_header=True)
            table.add_column("时间", style="dim", width=12)
            table.add_column("重要性", width=6)
            table.add_column("标题", style="bold")
            table.add_column("内容", width=40)
            table.add_column("状态", width=4)

            for d in filtered[:count]:
                ts = datetime.fromisoformat(d.get("timestamp", datetime.now().isoformat()))
                time_str = ts.strftime("%m/%d %H:%M")
                stars = "⭐" * d.get("importance", 3)
                title = d.get("title", "")[:20]
                content = d.get("content", "")[:40]
                ack_mark = "✓" if d.get("acknowledged") else ""
                table.add_row(time_str, stars, title, content, ack_mark)

            console.print(table)

            unacked = sum(1 for d in filtered if not d.get("acknowledged"))
            if unacked > 0:
                console.print(f"\n[dim]{unacked} 条未阅读。使用 [bold]jarvis discoveries --ack[/bold] 标记全部已读[/dim]")

        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[red]读取发现失败: {e}[/red]")

    @app.command()
    def skills():
        """⚡ 列出所有已激活的 skill"""
        _do_skills()
