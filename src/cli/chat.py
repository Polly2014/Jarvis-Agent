"""
Jarvis CLI — 聊天循环与补全器
"""
import asyncio
import json
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from .common import (
    console, JARVIS_HOME, VERSION,
    get_status_summary, get_unread_discoveries, format_discovery_time,
    is_first_run, detect_natural_intent, load_llm_config,
    ensure_jarvis_home,
)
from .daemon_cmds import _do_start_daemon, _do_rest, _do_status
from .memory_cmds import _do_recall, _do_think, _do_insights
from .explore_cmds import _do_discoveries, _do_explore, _do_projects, _do_skills, _do_init

from rich.panel import Panel


# ── 斜杠命令补全器 ─────────────────────────────────────────

class JarvisCompleter(Completer):
    """Jarvis 斜杠命令补全器"""

    SLASH_COMMANDS = {
        "/start": "启动 daemon 后台监控",
        "/rest": "停止 daemon",
        "/status": "查看状态",
        "/discoveries": "查看发现记录",
        "/recall": "搜索记忆 (用法: /recall 关键词)",
        "/think": "触发一次思考",
        "/insights": "查看最近洞察",
        "/explore": "探索目录",
        "/projects": "列出已发现项目",
        "/skills": "列出 skills",
        "/tools": "列出可用工具",
        "/init": "初始化配置",
        "/help": "显示帮助",
        "/exit": "退出聊天",
        "/quit": "退出聊天",
    }

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        if text.startswith("/"):
            word = text.lower()
            for cmd, desc in self.SLASH_COMMANDS.items():
                if cmd.startswith(word):
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=f"{cmd}",
                        display_meta=desc,
                    )


# ── 辅助 ──────────────────────────────────────────────────

def show_welcome_banner():
    """显示欢迎横幅和状态"""
    status_emoji, status_text, unread = get_status_summary()

    header = f"[bold cyan]🥚 Jarvis[/bold cyan] v{VERSION}  {status_emoji} {status_text}"
    console.print(Panel(header, border_style="cyan", padding=(0, 1)))

    if unread > 0:
        discoveries = get_unread_discoveries(limit=3)
        if discoveries:
            console.print()
            console.print(f"[bold yellow]📋 最近发现[/bold yellow] [dim]({unread}条未读)[/dim]")

            for d in discoveries:
                importance = d.get("importance", 3)
                stars = "⭐" * min(importance, 5)
                time_str = format_discovery_time(d.get("timestamp", ""))
                title = d.get("title", "未知发现")
                if len(title) > 40:
                    title = title[:37] + "..."
                console.print(f"  {stars} [dim][{time_str}][/dim] {title}")

            console.print(f"  [dim]└─ /discoveries 查看全部 · /discoveries --ack 标记已读[/dim]")
            console.print()


def show_slash_help():
    """显示斜杠命令帮助"""
    help_text = """
[bold]斜杠命令:[/bold]
  /start       启动 daemon 后台监控
  /rest        停止 daemon
  /status      查看状态
  /discoveries 查看发现记录
  /recall      搜索记忆 (用法: /recall 关键词)
  /think       触发一次思考
  /insights    查看最近洞察
  /explore     探索目录
  /projects    列出已发现项目
  /skills      列出 skills
  /tools       列出可用工具
  /init        初始化配置
  /help        显示本帮助
  /exit /quit  退出聊天

[dim]也可以直接用自然语言："帮我挂机"、"休息"、"你在干嘛"[/dim]
"""
    console.print(help_text)


def handle_slash_command(cmd: str) -> bool:
    """
    处理斜杠命令
    Returns: True 表示已处理，False 表示需要退出
    """
    cmd = cmd.strip().lower()
    parts = cmd.split(maxsplit=1)
    command = parts[0]
    args = parts[1] if len(parts) > 1 else None

    if command in ("/exit", "/quit", "/q"):
        console.print("\n[dim]再见！随时呼唤我。[/dim] 👋")
        return False

    elif command == "/help":
        show_slash_help()
    elif command == "/status":
        _do_status()
    elif command == "/start":
        _do_start_daemon()
    elif command == "/rest":
        _do_rest()
    elif command == "/discoveries":
        _do_discoveries()
    elif command == "/recall":
        _do_recall(args)
    elif command == "/think":
        _do_think()
    elif command == "/insights":
        _do_insights()
    elif command == "/explore":
        _do_explore(args)
    elif command == "/projects":
        _do_projects()
    elif command == "/skills":
        _do_skills()
    elif command == "/tools":
        _do_tools()
    elif command == "/init":
        _do_init()
    else:
        console.print(f"[red]未知命令: {command}[/red]")
        console.print("[dim]输入 /help 查看可用命令[/dim]")

    return True


def _do_tools():
    """显示可用工具列表"""
    from ..tools.registry import get_registry

    registry = get_registry()
    tools = registry.list_all()

    if not tools:
        console.print("[dim]没有已注册的工具[/dim]")
        return

    console.print(f"\n[bold]🔧 可用工具[/bold] ({len(tools)} 个)\n")

    # 分组显示
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


# ── 聊天循环 ──────────────────────────────────────────────

def create_prompt_session() -> PromptSession:
    """创建带补全的 PromptSession"""
    style = Style.from_dict({
        'prompt': 'bold #00ff00',
        'completion-menu.completion': 'bg:#333333 #ffffff',
        'completion-menu.completion.current': 'bg:#00aa00 #ffffff',
        'completion-menu.meta.completion': 'bg:#333333 #888888',
        'completion-menu.meta.completion.current': 'bg:#00aa00 #ffffff',
    })

    history_path = JARVIS_HOME / "chat_history"

    return PromptSession(
        completer=JarvisCompleter(),
        style=style,
        history=FileHistory(str(history_path)),
        complete_while_typing=False,
    )


def _do_ask(question: str):
    """单次提问（带工具调用）"""
    from ..llm import JarvisLLMClient

    llm_config = load_llm_config()
    client = JarvisLLMClient(
        base_url=llm_config.get("base_url", "http://localhost:23335/api/openai"),
        model=llm_config.get("model", "claude-sonnet-4"),
        auth_token=llm_config.get("auth_token", ""),
    )

    console.print(f"\n[bold green]你[/bold green]: {question}")
    console.print("\n[bold cyan]Jarvis[/bold cyan]: ", end="")

    def on_content(text: str):
        print(text, end="", flush=True)

    def on_tool_start(name: str, args: dict):
        args_short = str(args)[:80]
        console.print(f"\n  [dim]🔧 {name}({args_short})[/dim]", end="")

    def on_tool_end(name: str, result):
        status = "✅" if result.success else "❌"
        console.print(f" {status}")

    try:
        asyncio.run(client.chat_with_tools(
            messages=[{"role": "user", "content": question}],
            on_content=on_content,
            on_tool_start=on_tool_start,
            on_tool_end=on_tool_end,
        ))
        print("\n")
    except Exception as e:
        console.print(f"\n[red]错误: {e}[/red]")


def run_chat_loop():
    """统一的聊天循环：斜杠命令补全 + 自然语言控制 + LLM 对话 (with tool calling)"""
    from ..llm import JarvisLLMClient

    if is_first_run():
        console.print("\n[yellow]🥚 首次运行！让我们先初始化配置。[/yellow]")
        console.print("[dim]输入 /init 开始初始化，或直接开始聊天[/dim]\n")

    llm_config = load_llm_config()
    client = JarvisLLMClient(
        base_url=llm_config.get("base_url", "http://localhost:23335/api/openai"),
        model=llm_config.get("model", "claude-sonnet-4"),
        auth_token=llm_config.get("auth_token", ""),
    )

    # 显示工具数量
    tool_count = len(client.registry)
    if tool_count > 0:
        console.print(f"[dim]🔧 已加载 {tool_count} 个工具 (输入 /tools 查看)[/dim]")

    messages: list[dict] = []
    session = create_prompt_session()

    console.print("[dim]输入 / 后按 Tab 补全命令，↑↓ 查看历史[/dim]\n")

    def on_content(text: str):
        print(text, end="", flush=True)

    def on_tool_start(name: str, args: dict):
        args_short = str(args)[:80]
        console.print(f"\n  [dim]🔧 {name}({args_short})[/dim]", end="")

    def on_tool_end(name: str, result):
        status = "✅" if result.success else "❌"
        console.print(f" {status}")

    while True:
        try:
            user_input = session.prompt("你> ").strip()

            if not user_input:
                continue

            # 斜杠命令
            if user_input.startswith("/"):
                if not handle_slash_command(user_input):
                    break
                continue

            # 退出兼容
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[dim]再见！随时呼唤我。[/dim] 👋")
                break

            # 自然语言意图
            intent = detect_natural_intent(user_input)
            if intent == "start":
                _do_start_daemon()
                continue
            elif intent == "rest":
                _do_rest()
                continue
            elif intent == "status":
                _do_status()
                continue

            # LLM 对话 (with tool calling)
            messages.append({"role": "user", "content": user_input})

            console.print("\n[bold cyan]Jarvis[/bold cyan]: ", end="")

            try:
                reply = asyncio.run(client.chat_with_tools(
                    messages=messages,
                    on_content=on_content,
                    on_tool_start=on_tool_start,
                    on_tool_end=on_tool_end,
                ))
                print("\n")

            except Exception as e:
                console.print(f"\n[red]连接错误: {e}[/red]\n")

        except KeyboardInterrupt:
            console.print("\n[dim]再见！(daemon 仍在后台运行)[/dim] 👋")
            break
