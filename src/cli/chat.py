"""
Jarvis CLI — 聊天循环与补全器
"""
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
    elif command == "/init":
        _do_init()
    else:
        console.print(f"[red]未知命令: {command}[/red]")
        console.print("[dim]输入 /help 查看可用命令[/dim]")

    return True


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
    """单次提问（streaming）"""
    import httpx

    llm = load_llm_config()
    base_url = llm.get("base_url", "http://localhost:23335/api/openai")
    model = llm.get("model", "claude-sonnet-4")
    auth_token = llm.get("auth_token", "")

    console.print(f"\n[bold green]你[/bold green]: {question}")
    console.print("\n[bold cyan]Jarvis[/bold cyan]: ", end="")

    try:
        with httpx.Client(timeout=120.0, trust_env=False) as client:
            with client.stream(
                "POST",
                f"{base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 2000,
                    "stream": True,
                    "messages": [
                        {"role": "system", "content": "你是 Jarvis，Polly 的私人 AI 助手。简洁、有帮助、可以用 emoji。"},
                        {"role": "user", "content": question},
                    ],
                },
            ) as response:
                if response.status_code != 200:
                    console.print(f"[red]API 错误: {response.status_code}[/red]")
                    return

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            print(content, end="", flush=True)
                    except json.JSONDecodeError:
                        continue

        print("\n")

    except Exception as e:
        console.print(f"\n[red]连接错误: {e}[/red]")


def run_chat_loop():
    """统一的聊天循环：斜杠命令补全 + 自然语言控制 + LLM 对话"""
    import httpx

    if is_first_run():
        console.print("\n[yellow]🥚 首次运行！让我们先初始化配置。[/yellow]")
        console.print("[dim]输入 /init 开始初始化，或直接开始聊天[/dim]\n")

    llm = load_llm_config()
    base_url = llm.get("base_url", "http://localhost:23335/api/openai")
    model = llm.get("model", "claude-sonnet-4")
    auth_token = llm.get("auth_token", "")

    messages: list[dict] = []
    session = create_prompt_session()

    console.print("[dim]输入 / 后按 Tab 补全命令，↑↓ 查看历史[/dim]\n")

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

            # LLM 对话 (streaming)
            messages.append({"role": "user", "content": user_input})

            console.print("\n[bold cyan]Jarvis[/bold cyan]: ", end="")
            full_reply = ""

            try:
                with httpx.Client(timeout=120.0, trust_env=False) as client:
                    with client.stream(
                        "POST",
                        f"{base_url}/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {auth_token}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": model,
                            "max_tokens": 2000,
                            "stream": True,
                            "messages": [
                                {"role": "system", "content": "你是 Jarvis，Polly 的私人 AI 助手。简洁、有帮助、可以用 emoji。"},
                                *messages[-10:],
                            ],
                        },
                    ) as response:
                        if response.status_code != 200:
                            console.print(f"[red]API 错误: {response.status_code}[/red]\n")
                            continue

                        for line in response.iter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content:
                                    print(content, end="", flush=True)
                                    full_reply += content
                            except json.JSONDecodeError:
                                continue

                print("\n")
                messages.append({"role": "assistant", "content": full_reply})

            except Exception as e:
                console.print(f"\n[red]连接错误: {e}[/red]\n")

        except KeyboardInterrupt:
            console.print("\n[dim]再见！(daemon 仍在后台运行)[/dim] 👋")
            break
