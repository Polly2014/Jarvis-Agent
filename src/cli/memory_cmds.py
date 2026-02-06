"""
Jarvis CLI — 记忆相关命令
"""
import json
import re
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from .common import (
    console, JARVIS_HOME,
    get_config_path, ensure_jarvis_home, load_llm_config,
)


# ── 内部实现 ──────────────────────────────────────────────

def _do_recall(query: Optional[str] = None):
    """搜索记忆"""
    from ..memory import MemoryIndex

    index_path = JARVIS_HOME / "index.db"

    if not index_path.exists():
        console.print("[yellow]💭 记忆索引尚未创建[/yellow]")
        console.print("[dim]启动 daemon 后会自动记录发现到记忆中[/dim]")
        return

    index = MemoryIndex(index_path)

    if query is None:
        console.print("\n[bold]🧠 最近记忆:[/bold]")
        results = index.get_recent(limit=5)
        if not results:
            console.print("[yellow]暂无记忆[/yellow]")
            return

        for r in results:
            stars = "⭐" * r.importance
            console.print(f"  [{r.date}] [bold]{r.title}[/bold] {stars}")
            if r.summary:
                summary = r.summary[:60] + "..." if len(r.summary) > 60 else r.summary
                console.print(f"     [dim]{summary}[/dim]")
            if r.tags:
                tags_str = " ".join(f"[cyan]#{t}[/cyan]" for t in r.tags[:3])
                console.print(f"     {tags_str}")
    else:
        console.print(f"\n[bold]🔍 搜索: [cyan]{query}[/cyan][/bold]\n")
        results = index.recall(query, limit=10)

        if not results:
            console.print("[yellow]未找到相关记忆[/yellow]")
            console.print("[dim]试试其他关键词？[/dim]")
            return

        for i, r in enumerate(results, 1):
            stars = "⭐" * r.importance
            console.print(f"  {i}. [{r.date}] [bold]{r.title}[/bold] {stars}")
            if r.summary:
                summary = r.summary[:80] + "..." if len(r.summary) > 80 else r.summary
                console.print(f"      [dim]{summary}[/dim]")

        console.print(f"\n[dim]共 {len(results)} 条相关记忆[/dim]")


def _do_think():
    """触发一次思考"""
    import httpx
    from ..memory import MemoryIndex, MemoryWriter, MemoryEntry, IndexEntry

    config_path = get_config_path()
    if not config_path.exists():
        console.print("[red]请先运行 /init 初始化配置[/red]")
        return

    llm = load_llm_config()
    base_url = llm.get("base_url", "http://localhost:23335/api/openai")
    model = llm.get("model", "claude-sonnet-4")
    auth_token = llm.get("auth_token", "")

    console.print("\n[bold cyan]💭 Jarvis 正在思考...[/bold cyan]\n")

    index_path = JARVIS_HOME / "index.db"
    memory_path = JARVIS_HOME / "memory"

    recent_context = ""
    if index_path.exists():
        index = MemoryIndex(index_path)
        recent = index.get_recent(days=3, limit=10)
        if recent:
            recent_context = "最近的记忆：\n" + "\n".join([
                f"- [{r.date}] {r.title}: {r.summary[:100] if r.summary else ''}" for r in recent
            ])

    prompt = f"""你是 Jarvis，Polly 的 AI 助手。现在是主动思考时间。

{recent_context}

请思考：
1. 最近有什么有意义的模式或趋势？
2. 是否有什么事情需要提醒 Polly？
3. 有没有什么建议或洞察？

如果没有特别重要的事情，可以返回 null。

如果有洞察，请用以下 JSON 格式回复：
{{
    "title": "简短标题（10字以内）",
    "content": "详细内容（2-3句话）",
    "importance": 1-5,
    "suggested_action": "建议的行动（可选）"
}}

只返回 JSON 或 null。"""

    try:
        with httpx.Client(timeout=60.0, trust_env=False) as client:
            response = client.post(
                f"{base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data["choices"][0]["message"]["content"].strip()

            if result.lower() == "null":
                console.print("[dim]💤 没有特别的洞察，一切安好[/dim]")
                return

            json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
            if json_match:
                insight = json.loads(json_match.group())

                stars = "⭐" * insight.get("importance", 3)
                console.print(Panel(
                    f"[bold]{insight.get('title', '洞察')}[/bold] {stars}\n\n"
                    f"{insight.get('content', '')}\n\n"
                    f"[dim]建议: {insight.get('suggested_action', '无')}[/dim]",
                    title="💡 Jarvis 的洞察",
                    border_style="cyan",
                ))

                writer = MemoryWriter(memory_path)
                entry = MemoryEntry(
                    timestamp=datetime.now(),
                    title=insight.get("title", "思考"),
                    content=insight.get("content", ""),
                    importance=insight.get("importance", 3),
                    entry_type="insight",
                )
                file_path = writer.append_to_daily(entry)

                if index_path.exists():
                    index = MemoryIndex(index_path)
                    index_entry = IndexEntry(
                        id=f"i-{datetime.now().strftime('%Y%m%d')}-{hash(insight.get('title', ''))%10000:04d}",
                        entry_type="insight",
                        file_path=str(file_path),
                        date=datetime.now().date().isoformat(),
                        title=insight.get("title", "思考"),
                        tags=[],
                        importance=insight.get("importance", 3),
                        summary=insight.get("content", "")[:200],
                    )
                    index.add(index_entry)

                console.print(f"\n[dim]已记录到: {file_path.name}[/dim]")
            else:
                console.print(f"[dim]思考结果: {result}[/dim]")

    except Exception as e:
        console.print(f"[red]思考失败: {e}[/red]")


def _do_insights():
    """查看最近洞察"""
    from ..memory import MemoryIndex
    from ..memory.index import date as date_type

    index_path = JARVIS_HOME / "index.db"

    if not index_path.exists():
        console.print("[yellow]💭 还没有任何洞察[/yellow]")
        console.print("[dim]使用 /think 触发思考，或启动 daemon 自动生成[/dim]")
        return

    index = MemoryIndex(index_path)

    date_from = date_type.today() - timedelta(days=7)
    results = index.search(date_from=date_from, limit=10)

    if not results:
        console.print("[yellow]最近 7 天没有洞察记录[/yellow]")
        return

    console.print("\n[bold]💡 最近 7 天的洞察:[/bold]\n")

    for r in results:
        stars = "⭐" * r.importance
        type_emoji = "💭" if r.entry_type == "insight" else "🔍"
        console.print(f"  {type_emoji} [{r.date}] [bold]{r.title}[/bold] {stars}")
        if r.summary:
            summary = r.summary[:60] + "..." if len(r.summary) > 60 else r.summary
            console.print(f"      [dim]{summary}[/dim]")

    console.print(f"\n[dim]共 {len(results)} 条记录[/dim]")


# ── Typer 子命令 ──────────────────────────────────────────

def register(app: typer.Typer):
    """注册记忆相关子命令"""

    @app.command()
    def recall(
        query: Optional[str] = typer.Argument(None, help="搜索关键词"),
        limit: int = typer.Option(10, "-n", "--limit", help="结果数量"),
        important: bool = typer.Option(False, "-i", "--important", help="只显示重要记忆(⭐⭐⭐+)"),
    ):
        """🧠 搜索记忆"""
        from ..memory import MemoryIndex

        ensure_jarvis_home()
        index_path = JARVIS_HOME / "index.db"

        if not index_path.exists():
            console.print("[yellow]💭 记忆索引尚未创建[/yellow]")
            raise typer.Exit(0)

        index = MemoryIndex(index_path)

        if query:
            console.print(f"\n[bold]🔍 搜索: [cyan]{query}[/cyan][/bold]\n")
            results = index.recall(query, limit=limit)
        elif important:
            console.print("\n[bold]⭐ 重要记忆:[/bold]\n")
            results = index.get_important(min_importance=3, limit=limit)
        else:
            console.print("\n[bold]🧠 最近记忆:[/bold]\n")
            results = index.get_recent(limit=limit)

        if not results:
            console.print("[yellow]暂无匹配的记忆[/yellow]")
            raise typer.Exit(0)

        table = Table(box=None, padding=(0, 1))
        table.add_column("日期", style="dim")
        table.add_column("标题", style="bold")
        table.add_column("重要性")
        table.add_column("摘要", style="dim")

        for r in results:
            stars = "⭐" * r.importance
            summary = r.summary[:40] + "..." if r.summary and len(r.summary) > 40 else (r.summary or "")
            table.add_row(r.date, r.title, stars, summary)

        console.print(table)
        console.print(f"\n[dim]共 {len(results)} 条记忆[/dim]")

    @app.command()
    def think():
        """💭 手动触发一次思考"""
        ensure_jarvis_home()
        _do_think()

    @app.command()
    def insights(
        days: int = typer.Option(7, "-d", "--days", help="查看最近 N 天"),
        limit: int = typer.Option(10, "-n", "--limit", help="结果数量"),
    ):
        """💡 查看最近的洞察"""
        from ..memory import MemoryIndex
        from ..memory.index import date as date_type

        ensure_jarvis_home()
        index_path = JARVIS_HOME / "index.db"

        if not index_path.exists():
            console.print("[yellow]💭 还没有任何洞察[/yellow]")
            raise typer.Exit(0)

        index = MemoryIndex(index_path)
        date_from = date_type.today() - timedelta(days=days)
        results = index.search(date_from=date_from, limit=limit)

        if not results:
            console.print(f"[yellow]最近 {days} 天没有洞察记录[/yellow]")
            raise typer.Exit(0)

        console.print(f"\n[bold]💡 最近 {days} 天的洞察:[/bold]\n")
        for r in results:
            stars = "⭐" * r.importance
            type_emoji = "💭" if r.entry_type == "insight" else "🔍"
            console.print(f"  {type_emoji} [{r.date}] [bold]{r.title}[/bold] {stars}")
            if r.summary:
                summary = r.summary[:80] + "..." if len(r.summary) > 80 else r.summary
                console.print(f"      [dim]{summary}[/dim]")

        console.print(f"\n[dim]共 {len(results)} 条记录[/dim]")
