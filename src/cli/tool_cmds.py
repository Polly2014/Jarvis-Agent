"""
Jarvis CLI — 工具管理命令
"""
import typer
from .common import console


def register(app: typer.Typer):
    """注册 tools 子命令"""

    tools_app = typer.Typer(
        name="tools",
        help="🔧 工具管理",
        invoke_without_command=True,
        no_args_is_help=False,
    )

    @tools_app.callback(invoke_without_command=True)
    def tools_default(ctx: typer.Context):
        """列出所有可用工具"""
        if ctx.invoked_subcommand is not None:
            return
        _show_tools()

    @tools_app.command("list")
    def tools_list():
        """列出所有可用工具"""
        _show_tools()

    @tools_app.command("info")
    def tools_info(name: str = typer.Argument(..., help="工具名称")):
        """查看工具详细信息"""
        from ..tools.registry import get_registry

        registry = get_registry()
        tool = registry.get(name)

        if not tool:
            console.print(f"[red]工具 '{name}' 不存在[/red]")
            console.print(f"[dim]可用工具: {', '.join(registry.list_names())}[/dim]")
            return

        import json
        console.print(f"\n[bold]🔧 {tool.name}[/bold]")
        console.print(f"  描述: {tool.description}")
        console.print(f"  参数:")
        params = tool.parameters.get("properties", {})
        required = tool.parameters.get("required", [])
        for p_name, p_info in params.items():
            req_mark = "*" if p_name in required else " "
            p_type = p_info.get("type", "any")
            p_desc = p_info.get("description", "")
            console.print(f"    {req_mark} [bold]{p_name}[/bold] ({p_type}): {p_desc}")
        console.print()

    app.add_typer(tools_app)


def _show_tools():
    """显示工具列表（复用 chat.py 中的逻辑）"""
    from ..tools.registry import get_registry

    registry = get_registry()
    tools = registry.list_all()

    if not tools:
        console.print("[dim]没有已注册的工具[/dim]")
        return

    console.print(f"\n[bold]🔧 可用工具[/bold] ({len(tools)} 个)\n")

    builtins = [t for t in tools if t.name in ("file_read", "file_write", "shell_exec", "http_request")]
    meta = [t for t in tools if t.name in ("create_skill", "create_tool", "create_mcp")]
    custom = [t for t in tools if t not in builtins and t not in meta]

    if builtins:
        console.print("[bold cyan]Layer 0 — 原子工具[/bold cyan]")
        for t in builtins:
            console.print(f"  🔹 [bold]{t.name}[/bold]  [dim]{t.description}[/dim]")
        console.print()

    if meta:
        console.print("[bold magenta]Layer 1 — 元工具[/bold magenta]")
        for t in meta:
            console.print(f"  🔸 [bold]{t.name}[/bold]  [dim]{t.description}[/dim]")
        console.print()

    if custom:
        console.print("[bold yellow]Custom — 自定义工具[/bold yellow]")
        for t in custom:
            console.print(f"  ⭐ [bold]{t.name}[/bold]  [dim]{t.description}[/dim]")
        console.print()
