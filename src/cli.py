"""
Jarvis-Agent CLI 入口
"""
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from pathlib import Path
from typing import Optional
from datetime import datetime
import json
import os
import subprocess
import sys

app = typer.Typer(
    name="jarvis",
    help="🥚 数码宝贝式 AI Agent —— 从空白开始，探索进化，成为你的专属伙伴",
    invoke_without_command=True,
    no_args_is_help=False
)
console = Console()

# 版本号
VERSION = "0.1.0"

# Jarvis 家目录
JARVIS_HOME = Path.home() / ".jarvis"


def get_config_path() -> Path:
    return JARVIS_HOME / "config.json"


def get_state_path() -> Path:
    return JARVIS_HOME / "state.json"


def get_discoveries_path() -> Path:
    return JARVIS_HOME / "discoveries.json"


def ensure_jarvis_home():
    """确保 Jarvis 家目录存在"""
    JARVIS_HOME.mkdir(parents=True, exist_ok=True)
    (JARVIS_HOME / "logs").mkdir(exist_ok=True)
    (JARVIS_HOME / "memory").mkdir(exist_ok=True)
    (JARVIS_HOME / "skills").mkdir(exist_ok=True)


def get_status_summary() -> tuple[str, str, int]:
    """
    获取状态摘要
    Returns: (status_emoji, status_text, unread_count)
    """
    state_path = get_state_path()
    discoveries_path = get_discoveries_path()
    
    # 检查 daemon 状态
    if not state_path.exists():
        return "⚪", "未启动", 0
    
    try:
        with open(state_path, "r") as f:
            state = json.load(f)
        
        status = state.get("status", "unknown")
        last_hb = state.get("last_heartbeat")
        
        if status == "running" and last_hb:
            last_heartbeat = datetime.fromisoformat(last_hb)
            if (datetime.now() - last_heartbeat).total_seconds() < 120:
                status_emoji, status_text = "🟢", "运行中"
            else:
                status_emoji, status_text = "🔴", "无响应"
        elif status == "resting":
            status_emoji, status_text = "😴", "休眠中"
        else:
            status_emoji, status_text = "⚪", "已停止"
    except (json.JSONDecodeError, KeyError):
        status_emoji, status_text = "⚪", "未知"
    
    # 统计未读发现
    unread_count = 0
    if discoveries_path.exists():
        try:
            with open(discoveries_path, "r") as f:
                data = json.load(f)
            unread_count = sum(
                1 for d in data.get("discoveries", [])
                if not d.get("acknowledged")
            )
        except (json.JSONDecodeError, KeyError):
            pass
    
    return status_emoji, status_text, unread_count


def is_first_run() -> bool:
    """检查是否首次运行"""
    config_path = get_config_path()
    return not config_path.exists()


def detect_natural_intent(text: str) -> Optional[str]:
    """
    检测自然语言中的控制意图
    Returns: 'start', 'rest', 'status' 或 None
    """
    text_lower = text.lower()
    
    # 启动意图
    start_triggers = [
        "帮我挂机", "开始挂机", "上线", "启动", "start",
        "帮我守着", "开始监控", "wake up", "后台运行"
    ]
    if any(t in text_lower for t in start_triggers):
        return "start"
    
    # 休眠意图
    rest_triggers = [
        "休息", "下线", "停止", "休眠", "stop", "rest",
        "不用守了", "停止监控", "go to sleep"
    ]
    if any(t in text_lower for t in rest_triggers):
        return "rest"
    
    # 状态查询意图
    status_triggers = [
        "你在干嘛", "什么状态", "怎么样了", "status",
        "在运行吗", "你好吗", "how are you"
    ]
    if any(t in text_lower for t in status_triggers):
        return "status"
    
    return None


def show_welcome_banner():
    """显示欢迎横幅和状态"""
    status_emoji, status_text, unread = get_status_summary()
    
    # 构建状态行
    status_line = f"状态: {status_emoji} {status_text}"
    if unread > 0:
        status_line += f" | 未读: [yellow]{unread}[/yellow] 条发现"
    
    console.print(Panel(
        f"[bold cyan]🥚 Jarvis[/bold cyan] v{VERSION}\n{status_line}",
        border_style="cyan",
        padding=(0, 1)
    ))


def show_slash_help():
    """显示斜杠命令帮助"""
    help_text = """
[bold]斜杠命令:[/bold]
  /start       启动 daemon 后台监控
  /rest        停止 daemon
  /status      查看状态
  /discoveries 查看发现记录
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
    
    elif command == "/explore":
        _do_explore(args)
    
    elif command == "/projects":
        console.print("[yellow]📂 功能开发中...[/yellow]")
    
    elif command == "/skills":
        _do_skills()
    
    elif command == "/init":
        _do_init()
    
    else:
        console.print(f"[red]未知命令: {command}[/red]")
        console.print("[dim]输入 /help 查看可用命令[/dim]")
    
    return True


def _do_status():
    """内部：执行状态查看"""
    status_emoji, status_text, unread = get_status_summary()
    
    state_path = get_state_path()
    if state_path.exists():
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
            last_hb = state.get("last_heartbeat")
            if last_hb:
                last_heartbeat = datetime.fromisoformat(last_hb)
                time_since = (datetime.now() - last_heartbeat).total_seconds()
                if time_since < 60:
                    hb_str = f"{int(time_since)} 秒前"
                else:
                    hb_str = f"{int(time_since // 60)} 分钟前"
            else:
                hb_str = "无"
        except:
            hb_str = "无"
    else:
        hb_str = "无"
    
    console.print(f"\n{status_emoji} 状态: [bold]{status_text}[/bold]")
    console.print(f"   心跳: {hb_str}")
    if unread > 0:
        console.print(f"   未读: [yellow]{unread}[/yellow] 条发现")


def _do_start_daemon():
    """内部：启动 daemon"""
    status_emoji, status_text, _ = get_status_summary()
    
    if status_emoji == "🟢":
        console.print("[yellow]⚠️  已经在运行中[/yellow]")
        return
    
    console.print("[cyan]🫀 启动 Jarvis Daemon...[/cyan]")
    
    python_path = sys.executable
    log_path = JARVIS_HOME / "logs" / "daemon.log"
    
    cmd = f'nohup {python_path} -m src.daemon.daemon > {log_path} 2>&1 &'
    subprocess.Popen(cmd, shell=True, cwd=Path(__file__).parent.parent)
    
    console.print("[green]✅ 已在后台启动[/green]")


def _do_rest():
    """内部：停止 daemon"""
    state_path = get_state_path()
    
    if not state_path.exists():
        console.print("[yellow]Jarvis 似乎没有在运行[/yellow]")
        return
    
    try:
        with open(state_path, "r") as f:
            state = json.load(f)
        
        state["status"] = "resting"
        state["last_heartbeat"] = datetime.now().isoformat()
        
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        
        console.print("[cyan]😴 Jarvis 正在休眠...[/cyan]")
    except Exception as e:
        console.print(f"[red]操作失败: {e}[/red]")


def _do_discoveries():
    """内部：查看发现"""
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
    """内部：探索目录"""
    from .explorer import scan_directory, format_discovery_report
    
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
            except:
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


def _do_skills():
    """内部：列出 skills"""
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
    """内部：初始化"""
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
            "self_reflect_interval": 3600
        },
        "watch_paths": [str(workspace_path)],
        "llm": {
            "base_url": "http://localhost:23335/api/openai",
            "auth_token": "Powered by Agent Maestro",
            "model": "claude-sonnet-4"
        },
        "notification": {
            "terminal": True,
            "macos_notification": True,
            "min_importance": 3
        }
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n✅ 配置已保存: [green]{config_path}[/green]")


# ============================================================
# 智能补全
# ============================================================

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style


class JarvisCompleter(Completer):
    """Jarvis 斜杠命令补全器"""
    
    SLASH_COMMANDS = {
        "/start": "启动 daemon 后台监控",
        "/rest": "停止 daemon",
        "/status": "查看状态",
        "/discoveries": "查看发现记录",
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
        
        # 只在输入 / 开头时补全
        if text.startswith("/"):
            # 提取已输入的命令部分
            word = text.lower()
            
            for cmd, desc in self.SLASH_COMMANDS.items():
                if cmd.startswith(word):
                    # 计算需要补全的部分
                    yield Completion(
                        cmd,
                        start_position=-len(word),
                        display=f"{cmd}",
                        display_meta=desc
                    )


def create_prompt_session() -> PromptSession:
    """创建带补全的 PromptSession"""
    
    # 自定义样式
    style = Style.from_dict({
        'prompt': 'bold #00ff00',  # 绿色加粗
        'completion-menu.completion': 'bg:#333333 #ffffff',
        'completion-menu.completion.current': 'bg:#00aa00 #ffffff',
        'completion-menu.meta.completion': 'bg:#333333 #888888',
        'completion-menu.meta.completion.current': 'bg:#00aa00 #ffffff',
    })
    
    # 历史记录
    history_path = JARVIS_HOME / "chat_history"
    
    return PromptSession(
        completer=JarvisCompleter(),
        style=style,
        history=FileHistory(str(history_path)),
        complete_while_typing=False,  # 只在按 Tab 时补全
    )


def run_chat_loop():
    """
    统一的聊天循环
    支持：斜杠命令补全、自然语言控制、LLM 对话
    """
    import httpx
    
    # 首次运行检测
    if is_first_run():
        console.print("\n[yellow]🥚 首次运行！让我们先初始化配置。[/yellow]")
        console.print("[dim]输入 /init 开始初始化，或直接开始聊天[/dim]\n")
    
    # 加载 LLM 配置
    config_path = JARVIS_HOME / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        llm_config = config.get("llm", {})
    else:
        llm_config = {
            "base_url": "http://localhost:23335/api/openai",
            "model": "claude-sonnet-4",
            "auth_token": ""
        }
    
    base_url = llm_config.get("base_url", "http://localhost:23335/api/openai")
    model = llm_config.get("model", "claude-sonnet-4")
    auth_token = llm_config.get("auth_token", "")
    
    messages = []
    
    # 创建带补全的 session
    session = create_prompt_session()
    
    console.print("[dim]输入 / 后按 Tab 补全命令，↑↓ 查看历史[/dim]\n")
    
    while True:
        try:
            # 使用 prompt_toolkit 获取输入（支持补全和历史）
            user_input = session.prompt("你> ").strip()
            
            if not user_input.strip():
                continue
            
            # 检查斜杠命令
            if user_input.startswith("/"):
                if not handle_slash_command(user_input):
                    break
                continue
            
            # 检查退出命令（兼容旧版）
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[dim]再见！随时呼唤我。[/dim] 👋")
                break
            
            # 检查自然语言意图
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
            
            # 正常 LLM 对话
            messages.append({"role": "user", "content": user_input})
            
            with console.status("[bold cyan]Jarvis 思考中...[/bold cyan]"):
                try:
                    with httpx.Client(timeout=60.0, trust_env=False) as client:
                        resp = client.post(
                            f"{base_url}/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {auth_token}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": model,
                                "max_tokens": 2000,
                                "messages": [
                                    {"role": "system", "content": "你是 Jarvis，Polly 的私人 AI 助手。简洁、有帮助、可以用 emoji。"},
                                    *messages[-10:]
                                ]
                            }
                        )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        reply = data["choices"][0]["message"]["content"]
                        messages.append({"role": "assistant", "content": reply})
                        console.print(f"\n[bold cyan]Jarvis[/bold cyan]: {reply}\n")
                    else:
                        console.print(f"\n[red]API 错误: {resp.status_code}[/red]\n")
                        
                except Exception as e:
                    console.print(f"\n[red]连接错误: {e}[/red]\n")
        
        except KeyboardInterrupt:
            console.print("\n[dim]再见！(daemon 仍在后台运行)[/dim] 👋")
            break


# ============================================================
# 默认入口 (callback)
# ============================================================

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    daemon: bool = typer.Option(False, "--daemon", "-d", help="启动 daemon 后退出"),
    rest_daemon: bool = typer.Option(False, "--rest", "-r", help="停止 daemon"),
    show_status: bool = typer.Option(False, "--status", "-s", help="显示状态"),
    question: Optional[str] = typer.Argument(None, help="单次提问（不进入聊天）")
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
    # 如果有子命令，不执行默认行为
    if ctx.invoked_subcommand is not None:
        return
    
    ensure_jarvis_home()
    
    # 快捷参数处理
    if show_status:
        _do_status()
        return
    
    if daemon:
        _do_start_daemon()
        return
    
    if rest_daemon:
        _do_rest()
        return
    
    # 单次提问
    if question:
        _do_ask(question)
        return
    
    # 默认：显示欢迎并进入聊天
    show_welcome_banner()
    run_chat_loop()


def _do_ask(question: str):
    """内部：单次提问"""
    import httpx
    
    config_path = JARVIS_HOME / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        llm_config = config.get("llm", {})
    else:
        llm_config = {}
    
    base_url = llm_config.get("base_url", "http://localhost:23335/api/openai")
    model = llm_config.get("model", "claude-sonnet-4")
    auth_token = llm_config.get("auth_token", "")
    
    console.print(f"\n[bold green]你[/bold green]: {question}")
    
    with console.status("[bold cyan]Jarvis 思考中...[/bold cyan]"):
        try:
            with httpx.Client(timeout=60.0, trust_env=False) as client:
                resp = client.post(
                    f"{base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "max_tokens": 2000,
                        "messages": [
                            {"role": "system", "content": "你是 Jarvis，Polly 的私人 AI 助手。简洁、有帮助、可以用 emoji。"},
                            {"role": "user", "content": question}
                        ]
                    }
                )
            
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                console.print(f"\n[bold cyan]Jarvis[/bold cyan]: {reply}")
            else:
                console.print(f"\n[red]API 错误: {resp.status_code}[/red]")
                
        except Exception as e:
            console.print(f"\n[red]连接错误: {e}[/red]")


# ============================================================
# 生命周期命令
# ============================================================

@app.command()
def start(
    foreground: bool = typer.Option(False, "--foreground", "-f", help="前台运行（调试用）")
):
    """🫀 启动 Jarvis 心跳进程"""
    ensure_jarvis_home()
    
    # 检查是否已经运行
    state_path = get_state_path()
    if state_path.exists():
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
            if state.get("status") == "running":
                # 检查心跳时间
                last_heartbeat = datetime.fromisoformat(state.get("last_heartbeat", "2000-01-01"))
                if (datetime.now() - last_heartbeat).total_seconds() < 120:
                    console.print("[yellow]⚠️  Jarvis 已经在运行中[/yellow]")
                    console.print(f"   上次心跳: {last_heartbeat.strftime('%H:%M:%S')}")
                    return
        except (json.JSONDecodeError, KeyError):
            pass
    
    if foreground:
        # 前台运行
        console.print("[cyan]🫀 前台启动 Jarvis Daemon...[/cyan]")
        console.print("[dim]按 Ctrl+C 停止[/dim]\n")
        
        import asyncio
        from .daemon import run_daemon
        asyncio.run(run_daemon())
    else:
        # 后台运行
        console.print("[cyan]🫀 启动 Jarvis Daemon...[/cyan]")
        
        # 使用 nohup 启动后台进程
        python_path = sys.executable
        daemon_script = Path(__file__).parent / "daemon" / "daemon.py"
        log_path = JARVIS_HOME / "logs" / "daemon.log"
        
        cmd = f'nohup {python_path} -m src.daemon.daemon > {log_path} 2>&1 &'
        subprocess.Popen(cmd, shell=True, cwd=Path(__file__).parent.parent)
        
        console.print("[green]✅ Jarvis 已在后台启动[/green]")
        console.print(f"   日志: {log_path}")
        console.print("\n[dim]使用 [bold]jarvis status[/bold] 查看状态[/dim]")


@app.command()
def rest():
    """😴 让 Jarvis 休眠（保留记忆）"""
    state_path = get_state_path()
    
    if not state_path.exists():
        console.print("[yellow]Jarvis 似乎没有在运行[/yellow]")
        return
    
    # 更新状态为休眠
    try:
        with open(state_path, "r") as f:
            state = json.load(f)
        
        state["status"] = "resting"
        state["last_heartbeat"] = datetime.now().isoformat()
        
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)
        
        console.print("[cyan]😴 Jarvis 正在休眠...[/cyan]")
        console.print("[dim]记忆已保存，随时可以唤醒[/dim]")
        
        # TODO: 实际停止 daemon 进程
        # 可以通过 PID 文件或发送信号
        
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[red]读取状态失败: {e}[/red]")


@app.command()
def status():
    """💓 查看 Jarvis 生命体征"""
    state_path = get_state_path()
    
    if not state_path.exists():
        console.print(Panel(
            "[yellow]Jarvis 尚未启动[/yellow]\n\n"
            "运行 [bold]jarvis start[/bold] 唤醒它",
            title="💤 休眠中",
            border_style="dim"
        ))
        return
    
    try:
        with open(state_path, "r") as f:
            state = json.load(f)
        
        status_text = state.get("status", "unknown")
        last_heartbeat = datetime.fromisoformat(state.get("last_heartbeat", datetime.now().isoformat()))
        started_at = datetime.fromisoformat(state.get("started_at", datetime.now().isoformat()))
        discoveries_today = state.get("discoveries_today", 0)
        important_today = state.get("important_discoveries_today", 0)
        
        # 判断实际状态
        time_since_heartbeat = (datetime.now() - last_heartbeat).total_seconds()
        if status_text == "running" and time_since_heartbeat > 120:
            actual_status = "🔴 无响应"
            status_color = "red"
        elif status_text == "running":
            actual_status = "🟢 运行中"
            status_color = "green"
        elif status_text == "resting":
            actual_status = "😴 休眠中"
            status_color = "yellow"
        else:
            actual_status = "⚪ 已停止"
            status_color = "dim"
        
        # 计算运行时间
        uptime = datetime.now() - started_at
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"
        
        # 格式化心跳时间
        if time_since_heartbeat < 60:
            heartbeat_str = f"{int(time_since_heartbeat)} 秒前"
        elif time_since_heartbeat < 3600:
            heartbeat_str = f"{int(time_since_heartbeat // 60)} 分钟前"
        else:
            heartbeat_str = last_heartbeat.strftime("%H:%M:%S")
        
        content = f"""[{status_color}]状态: {actual_status}[/{status_color}]
上次心跳: {heartbeat_str}
运行时间: {uptime_str}
今日发现: {discoveries_today} 条（{important_today} 条重要）
"""
        
        console.print(Panel(
            content,
            title="🫀 Jarvis 生命体征",
            border_style=status_color
        ))
        
        # 显示最近发现
        discoveries_path = get_discoveries_path()
        if discoveries_path.exists():
            try:
                with open(discoveries_path, "r") as f:
                    data = json.load(f)
                discoveries = data.get("discoveries", [])[:3]
                
                if discoveries:
                    console.print("\n[bold]📋 最近发现:[/bold]")
                    for d in discoveries:
                        importance = d.get("importance", 3)
                        stars = "⭐" * importance
                        title = d.get("title", "未知")
                        ts = datetime.fromisoformat(d.get("timestamp", datetime.now().isoformat()))
                        time_str = ts.strftime("%H:%M")
                        ack = "✓" if d.get("acknowledged") else ""
                        console.print(f"  • [{time_str}] {title} {stars} {ack}")
                    
                    console.print("\n[dim]使用 [bold]jarvis discoveries[/bold] 查看更多[/dim]")
            except (json.JSONDecodeError, KeyError):
                pass
        
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[red]读取状态失败: {e}[/red]")


@app.command()
def discoveries(
    today: bool = typer.Option(False, "--today", "-t", help="只显示今日发现"),
    ack: bool = typer.Option(False, "--ack", "-a", help="确认所有发现为已阅读"),
    count: int = typer.Option(10, "--count", "-n", help="显示数量")
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
            # 确认所有为已阅读
            for d in all_discoveries:
                d["acknowledged"] = True
            with open(discoveries_path, "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            console.print("[green]✅ 所有发现已标记为已阅读[/green]")
            return
        
        # 过滤
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
        
        # 显示表格
        table = Table(title="💡 Jarvis 发现", show_header=True)
        table.add_column("时间", style="dim", width=12)
        table.add_column("重要性", width=6)
        table.add_column("标题", style="bold")
        table.add_column("内容", width=40)
        table.add_column("状态", width=4)
        
        for d in filtered[:count]:
            ts = datetime.fromisoformat(d.get("timestamp", datetime.now().isoformat()))
            time_str = ts.strftime("%m/%d %H:%M")
            importance = d.get("importance", 3)
            stars = "⭐" * importance
            title = d.get("title", "")[:20]
            content = d.get("content", "")[:40]
            ack_mark = "✓" if d.get("acknowledged") else ""
            
            table.add_row(time_str, stars, title, content, ack_mark)
        
        console.print(table)
        
        # 统计
        unacked = sum(1 for d in filtered if not d.get("acknowledged"))
        if unacked > 0:
            console.print(f"\n[dim]{unacked} 条未阅读。使用 [bold]jarvis discoveries --ack[/bold] 标记全部已读[/dim]")
        
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[red]读取发现失败: {e}[/red]")


# ============================================================
# 原有命令
# ============================================================

@app.command()
def init():
    """🥚 初始化 Jarvis，开始你们的旅程"""
    ensure_jarvis_home()
    
    console.print(Panel.fit(
        "[bold cyan]你好！我是 Jarvis[/bold cyan]\n\n"
        "我是一个刚出生的 AI。现在什么都不懂，但我很好奇。\n"
        "能告诉我你的工作目录在哪里吗？我想去看看。",
        title="🥚 Jarvis 孵化中",
        border_style="cyan"
    ))
    
    # 获取工作目录
    default_path = str(Path.home() / "projects")
    workspace = Prompt.ask(
        "\n📁 你的工作目录路径",
        default=default_path
    )
    
    workspace_path = Path(workspace).expanduser().resolve()
    
    if not workspace_path.exists():
        console.print(f"[yellow]⚠️  目录 {workspace_path} 不存在[/yellow]")
        if Confirm.ask("要创建它吗？"):
            workspace_path.mkdir(parents=True)
        else:
            raise typer.Exit(1)
    
    # 保存配置
    config_path = get_config_path()
    config = {
        "daemon": {
            "think_interval_seconds": 60,
            "self_reflect_interval": 3600
        },
        "watch_paths": [str(workspace_path)],
        "llm": {
            "base_url": "http://localhost:23335/api/anthropic",
            "auth_token": "Powered by Agent Maestro",
            "model": "claude-sonnet-4"
        },
        "notification": {
            "terminal": True,
            "macos_notification": True,
            "min_importance": 3
        }
    }
    
    with open(config_path, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    console.print(f"\n✅ 已记住你的工作目录: [green]{workspace_path}[/green]")
    console.print(f"   配置已保存到: {config_path}")
    console.print("\n[dim]接下来：[/dim]")
    console.print("  1. [bold]jarvis explore[/bold] - 让我去探索你的世界")
    console.print("  2. [bold]jarvis start[/bold] - 启动心跳，让我真正活起来")


@app.command()
def explore(
    path: Optional[str] = typer.Argument(None, help="要探索的目录路径")
):
    """🔍 探索目录，发现你的项目"""
    from .explorer import scan_directory, format_discovery_report
    
    if path is None:
        # 从配置读取默认工作目录
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
    
    # 扫描目录
    projects = scan_directory(target_path)
    
    if not projects:
        console.print("[yellow]没有发现可识别的项目[/yellow]")
        return
    
    # 显示发现报告
    report = format_discovery_report(projects)
    console.print(report)
    
    # 让用户选择
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
    
    # 为选中的项目创建 skill
    for idx in selected_indices:
        if 0 <= idx < len(projects):
            project = projects[idx]
            console.print(f"\n⚡ 正在为 [cyan]{project.name}[/cyan] 创建追踪能力...")
            # TODO: 调用 Skill Factory
            console.print(f"   ✅ [green]{project.name}[/green] skill 已激活")


@app.command()
def projects():
    """📂 列出已发现的项目"""
    # TODO: 从数据库读取
    console.print("[yellow]功能开发中...[/yellow]")


@app.command()
def chat():
    """💬 进入对话模式"""
    import httpx
    import json
    
    # 加载配置
    config_path = JARVIS_HOME / "config.json"
    if not config_path.exists():
        console.print("[red]请先运行 jarvis init 初始化配置[/red]")
        raise typer.Exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    llm_config = config.get("llm", {})
    base_url = llm_config.get("base_url", "http://localhost:23335/api/openai")
    model = llm_config.get("model", "claude-sonnet-4")
    auth_token = llm_config.get("auth_token", "")
    
    console.print(Panel.fit(
        "[bold cyan]Jarvis 对话模式[/bold cyan]\n\n"
        f"模型: [green]{model}[/green]\n"
        "输入你的问题，我会尽力帮助你。\n"
        "输入 [bold]exit[/bold] 或 [bold]quit[/bold] 退出。",
        border_style="cyan"
    ))
    
    messages = []
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold green]你[/bold green]")
            
            if user_input.lower() in ("exit", "quit", "q"):
                console.print("\n[dim]再见！随时呼唤我。[/dim] 👋")
                break
            
            if not user_input.strip():
                continue
            
            messages.append({"role": "user", "content": user_input})
            
            # 调用 LLM
            with console.status("[bold cyan]Jarvis 思考中...[/bold cyan]"):
                try:
                    with httpx.Client(timeout=60.0, trust_env=False) as client:
                        resp = client.post(
                            f"{base_url}/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {auth_token}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": model,
                                "max_tokens": 2000,
                                "messages": [
                                    {"role": "system", "content": "你是 Jarvis，Polly 的私人 AI 助手。简洁、有帮助、可以用 emoji。"},
                                    *messages[-10:]  # 保留最近 10 轮对话
                                ]
                            }
                        )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        reply = data["choices"][0]["message"]["content"]
                        messages.append({"role": "assistant", "content": reply})
                        console.print(f"\n[bold cyan]Jarvis[/bold cyan]: {reply}")
                    else:
                        console.print(f"\n[red]API 错误: {resp.status_code}[/red]")
                        
                except Exception as e:
                    console.print(f"\n[red]连接错误: {e}[/red]")
            
        except KeyboardInterrupt:
            console.print("\n[dim]再见！[/dim]")
            break


@app.command()
def ask(question: str = typer.Argument(..., help="你的问题")):
    """❓ 单次提问"""
    import httpx
    import json
    
    # 加载配置
    config_path = JARVIS_HOME / "config.json"
    if not config_path.exists():
        console.print("[red]请先运行 jarvis init 初始化配置[/red]")
        raise typer.Exit(1)
    
    with open(config_path) as f:
        config = json.load(f)
    
    llm_config = config.get("llm", {})
    base_url = llm_config.get("base_url", "http://localhost:23335/api/openai")
    model = llm_config.get("model", "claude-sonnet-4")
    auth_token = llm_config.get("auth_token", "")
    
    console.print(f"\n[bold green]你[/bold green]: {question}")
    
    with console.status("[bold cyan]Jarvis 思考中...[/bold cyan]"):
        try:
            with httpx.Client(timeout=60.0, trust_env=False) as client:
                resp = client.post(
                    f"{base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "max_tokens": 2000,
                        "messages": [
                            {"role": "system", "content": "你是 Jarvis，Polly 的私人 AI 助手。简洁、有帮助、可以用 emoji。"},
                            {"role": "user", "content": question}
                        ]
                    }
                )
            
            if resp.status_code == 200:
                data = resp.json()
                reply = data["choices"][0]["message"]["content"]
                console.print(f"\n[bold cyan]Jarvis[/bold cyan]: {reply}")
            else:
                console.print(f"\n[red]API 错误: {resp.status_code}[/red]")
                
        except Exception as e:
            console.print(f"\n[red]连接错误: {e}[/red]")


@app.command()
def skills():
    """⚡ 列出所有已激活的 skill"""
    skills_dir = JARVIS_HOME / "skills"
    
    if not skills_dir.exists():
        console.print("[yellow]还没有任何 skill[/yellow]")
        return
    
    skill_dirs = [d for d in skills_dir.iterdir() if d.is_dir()]
    
    if not skill_dirs:
        console.print("[yellow]还没有任何 skill[/yellow]")
        return
    
    console.print("[bold]⚡ 已激活的 Skills:[/bold]\n")
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            console.print(f"  • [cyan]{skill_dir.name}[/cyan]")
        else:
            console.print(f"  • [dim]{skill_dir.name}[/dim] (无 SKILL.md)")


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="服务地址"),
    port: int = typer.Option(50207, help="服务端口")
):
    """🚀 启动 API 服务"""
    import uvicorn
    console.print(f"\n🚀 启动 Jarvis API 服务: http://{host}:{port}")
    uvicorn.run("src.server:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    app()
