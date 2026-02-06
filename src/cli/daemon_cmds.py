"""
Jarvis CLI — Daemon 生命周期命令
"""
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from .common import (
    console, JARVIS_HOME, VERSION,
    get_config_path, get_state_path, get_discoveries_path, get_pid_path,
    ensure_jarvis_home, get_status_summary,
)


# ── 内部实现 ──────────────────────────────────────────────

def _do_status():
    """查看 Jarvis 状态"""
    status_emoji, status_text, unread = get_status_summary()

    state_path = get_state_path()
    hb_str = "无"
    if state_path.exists():
        try:
            with open(state_path, "r") as f:
                state = json.load(f)
            last_hb = state.get("last_heartbeat")
            if last_hb:
                time_since = (datetime.now() - datetime.fromisoformat(last_hb)).total_seconds()
                hb_str = f"{int(time_since)} 秒前" if time_since < 60 else f"{int(time_since // 60)} 分钟前"
        except (json.JSONDecodeError, KeyError):
            pass

    console.print(f"\n{status_emoji} 状态: [bold]{status_text}[/bold]")
    console.print(f"   心跳: {hb_str}")
    if unread > 0:
        console.print(f"   未读: [yellow]{unread}[/yellow] 条发现")


def _do_start_daemon():
    """启动 daemon 后台进程"""
    pid_path = get_pid_path()

    # 检查是否已有进程在运行
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, 0)  # 不发送信号，只检查存活
            console.print(f"[yellow]⚠️  已经在运行中 (PID: {pid})[/yellow]")
            return
        except (ProcessLookupError, ValueError):
            pid_path.unlink(missing_ok=True)
        except PermissionError:
            console.print("[yellow]⚠️  无法检查进程状态[/yellow]")
            return

    console.print("[cyan]🫀 启动 Jarvis Daemon...[/cyan]")

    log_path = JARVIS_HOME / "logs" / "daemon.log"

    daemon_code = (
        'import asyncio\n'
        'from src.daemon.daemon import run_daemon\n'
        'asyncio.run(run_daemon())\n'
    )
    cmd = [sys.executable, "-c", daemon_code]

    # 项目根目录
    project_root = Path(__file__).parent.parent.parent
    if not (project_root / "src").exists():
        config_path = get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                project_root = Path(config.get("project_root", project_root))
            except Exception:
                pass

    with open(log_path, "a") as log_file:
        log_file.write(f"\n{'='*50}\n")
        log_file.write(f"[{datetime.now().isoformat()}] Starting daemon...\n")
        log_file.write(f"Project root: {project_root}\n")
        log_file.flush()

        proc = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=log_file,
            cwd=str(project_root),
            start_new_session=True,
        )

    pid_path.write_text(str(proc.pid))
    console.print(f"[green]✅ 已在后台启动 (PID: {proc.pid})[/green]")


def _do_rest():
    """停止 daemon 进程"""
    pid_path = get_pid_path()
    state_path = get_state_path()

    if not pid_path.exists():
        # 检查残留状态
        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
                if state.get("status") == "running":
                    console.print("[yellow]⚠️  发现残留状态，正在清理...[/yellow]")
                    state["status"] = "stopped"
                    with open(state_path, "w") as f:
                        json.dump(state, f, indent=2)
                    console.print("[green]✅ 状态已清理[/green]")
                    return
            except Exception:
                pass
        console.print("[yellow]Jarvis 似乎没有在运行[/yellow]")
        return

    try:
        pid = int(pid_path.read_text().strip())
        console.print(f"[cyan]🛑 正在停止 Jarvis (PID: {pid})...[/cyan]")

        try:
            os.kill(pid, signal.SIGTERM)

            for _ in range(50):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except ProcessLookupError:
                    break
            else:
                console.print("[yellow]进程未响应，强制终止...[/yellow]")
                os.kill(pid, signal.SIGKILL)

            console.print("[green]😴 Jarvis 已休眠[/green]")
        except ProcessLookupError:
            console.print("[yellow]进程已不存在[/yellow]")

        pid_path.unlink(missing_ok=True)

        if state_path.exists():
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
                state["status"] = "stopped"
                with open(state_path, "w") as f:
                    json.dump(state, f, indent=2)
            except Exception:
                pass

    except ValueError:
        console.print("[red]PID 文件格式错误[/red]")
        pid_path.unlink(missing_ok=True)
    except PermissionError:
        console.print("[red]没有权限终止进程[/red]")
    except Exception as e:
        console.print(f"[red]操作失败: {e}[/red]")


# ── Typer 子命令 ──────────────────────────────────────────

def register(app: typer.Typer):
    """注册 daemon 相关子命令到 app"""

    @app.command()
    def start(
        foreground: bool = typer.Option(False, "--foreground", "-f", help="前台运行（调试用）"),
    ):
        """🫀 启动 Jarvis 心跳进程"""
        ensure_jarvis_home()

        # 前台运行时直接在当前进程执行
        if foreground:
            console.print("[cyan]🫀 前台启动 Jarvis Daemon...[/cyan]")
            console.print("[dim]按 Ctrl+C 停止[/dim]\n")
            import asyncio
            from ..daemon import run_daemon
            asyncio.run(run_daemon())
        else:
            _do_start_daemon()

    @app.command()
    def rest():
        """😴 让 Jarvis 休眠（保留记忆）"""
        _do_rest()

    @app.command()
    def status():
        """💓 查看 Jarvis 生命体征"""
        state_path = get_state_path()

        if not state_path.exists():
            console.print(Panel(
                "[yellow]Jarvis 尚未启动[/yellow]\n\n"
                "运行 [bold]jarvis start[/bold] 唤醒它",
                title="💤 休眠中",
                border_style="dim",
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

            time_since_heartbeat = (datetime.now() - last_heartbeat).total_seconds()
            if status_text == "running" and time_since_heartbeat > 120:
                actual_status, status_color = "🔴 无响应", "red"
            elif status_text == "running":
                actual_status, status_color = "🟢 运行中", "green"
            elif status_text == "resting":
                actual_status, status_color = "😴 休眠中", "yellow"
            else:
                actual_status, status_color = "⚪ 已停止", "dim"

            uptime = datetime.now() - started_at
            uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

            if time_since_heartbeat < 60:
                heartbeat_str = f"{int(time_since_heartbeat)} 秒前"
            elif time_since_heartbeat < 3600:
                heartbeat_str = f"{int(time_since_heartbeat // 60)} 分钟前"
            else:
                heartbeat_str = last_heartbeat.strftime("%H:%M:%S")

            content = (
                f"[{status_color}]状态: {actual_status}[/{status_color}]\n"
                f"上次心跳: {heartbeat_str}\n"
                f"运行时间: {uptime_str}\n"
                f"今日发现: {discoveries_today} 条（{important_today} 条重要）\n"
            )

            console.print(Panel(content, title="🫀 Jarvis 生命体征", border_style=status_color))

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
                            stars = "⭐" * d.get("importance", 3)
                            title = d.get("title", "未知")
                            ts = datetime.fromisoformat(d.get("timestamp", datetime.now().isoformat()))
                            ack = "✓" if d.get("acknowledged") else ""
                            console.print(f"  • [{ts.strftime('%H:%M')}] {title} {stars} {ack}")
                        console.print("\n[dim]使用 [bold]jarvis discoveries[/bold] 查看更多[/dim]")
                except (json.JSONDecodeError, KeyError):
                    pass

        except (json.JSONDecodeError, KeyError) as e:
            console.print(f"[red]读取状态失败: {e}[/red]")
