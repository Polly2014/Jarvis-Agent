"""
Jarvis-Agent CLI 入口

拆分自原始 cli.py (1900+ 行) → 模块化 cli/ 包

模块划分:
  common.py       — 常量、路径、状态查询、通用工具
  daemon_cmds.py  — daemon 生命周期 (start/rest/status)
  memory_cmds.py  — 记忆系统 (recall/think/insights)
  explore_cmds.py — 探索与项目 (init/explore/projects/discoveries/skills)
  chat.py         — 聊天循环、补全器、streaming
"""
import typer
from typing import Optional

from .common import (
    console, JARVIS_HOME, VERSION,
    ensure_jarvis_home,
)
from .chat import show_welcome_banner, run_chat_loop, _do_ask
from .daemon_cmds import _do_start_daemon, _do_rest, _do_status
from .explore_cmds import _do_discoveries, _do_skills, _do_init
from .memory_cmds import _do_recall, _do_think, _do_insights


# ── Typer App ─────────────────────────────────────────────

app = typer.Typer(
    name="jarvis",
    help="🥚 数码宝贝式 AI Agent —— 从空白开始，探索进化，成为你的专属伙伴",
    invoke_without_command=True,
    no_args_is_help=False,
)


# ── 注册子命令模块 ─────────────────────────────────────────

from . import daemon_cmds, memory_cmds, explore_cmds, evolution_cmds

daemon_cmds.register(app)
memory_cmds.register(app)
explore_cmds.register(app)
evolution_cmds.register(app)


# ── 主入口 callback ────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    daemon: bool = typer.Option(False, "--daemon", "-d", help="启动 daemon 后退出"),
    rest_daemon: bool = typer.Option(False, "--rest", "-r", help="停止 daemon"),
    show_status: bool = typer.Option(False, "--status", "-s", help="显示状态"),
    question: Optional[str] = typer.Argument(None, help="单次提问（不进入聊天）"),
):
    """
    🥚 Jarvis - 你的 AI 伙伴

    直接运行进入聊天，或使用参数快捷操作：

      jarvis          进入聊天模式
      jarvis "问题"   单次提问
      jarvis -d       启动 daemon
      jarvis -s       查看状态
      jarvis -r       停止 daemon
    """
    if ctx.invoked_subcommand is not None:
        return

    # 子命令名误传为 question 参数时的分发
    KNOWN_COMMANDS = {
        "start", "rest", "status", "discoveries", "init",
        "explore", "projects", "recall", "chat", "ask", "skills",
        "think", "insights", "tools",
        "reflect", "abilities", "patterns", "skill",
    }
    if question and question.lower() in KNOWN_COMMANDS:
        cmd_map = {
            "start": _do_start_daemon,
            "rest": _do_rest,
            "status": _do_status,
            "discoveries": _do_discoveries,
            "init": _do_init,
            "explore": lambda: from_explore_cmds_do_explore(None),
            "projects": lambda: from_explore_cmds_do_projects(),
            "recall": lambda: _do_recall(None),
            "think": _do_think,
            "insights": _do_insights,
            "chat": run_chat_loop,
            "skills": _do_skills,
            "tools": lambda: from_tool_cmds_show_tools(),
            "reflect": lambda: from_evolution_cmds("reflect"),
            "abilities": lambda: from_evolution_cmds("abilities"),
            "patterns": lambda: from_evolution_cmds("patterns"),
        }
        handler = cmd_map.get(question.lower())
        if handler:
            handler()
        else:
            console.print(f"[yellow]请使用: jarvis {question} [参数][/yellow]")
        return

    ensure_jarvis_home()

    if show_status:
        _do_status()
        return

    if daemon:
        _do_start_daemon()
        return

    if rest_daemon:
        _do_rest()
        return

    if question:
        _do_ask(question)
        return

    # 默认：显示欢迎并进入聊天
    show_welcome_banner()
    run_chat_loop()


# lazy imports for cmd_map lambdas
def from_explore_cmds_do_explore(path):
    from .explore_cmds import _do_explore
    _do_explore(path)

def from_explore_cmds_do_projects():
    from .explore_cmds import _do_projects
    _do_projects()

def from_tool_cmds_show_tools():
    from .tool_cmds import _show_tools
    _show_tools()

def from_evolution_cmds(cmd: str):
    from .evolution_cmds import _do_reflect, _do_abilities, _do_patterns
    {"reflect": _do_reflect, "abilities": _do_abilities, "patterns": _do_patterns}[cmd]()


# ── 兼容 chat / ask 子命令 ─────────────────────────────────

@app.command()
def chat():
    """💬 进入对话模式"""
    run_chat_loop()


@app.command()
def ask(question: str = typer.Argument(..., help="你的问题")):
    """❓ 单次提问"""
    _do_ask(question)
