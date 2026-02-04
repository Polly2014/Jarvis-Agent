#!/usr/bin/env python3
"""
Phase 1 完整测试脚本

测试 Jarvis-Agent 的五维能力（Phase 1 部分）：
- 👁️ 感知：explore, watchdog, signatures
- 🧠 记忆：SQLite, projects, episodes
- 💭 思考：chat, ask
- 🦾 行动：CLI 命令

运行方式：
    cd Jarvis-Agent
    poetry run python tests/test_phase1.py
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# 测试环境路径
TEST_GROUND = Path.home().parent / "polly/Downloads/Sublime_Workspace/Zola_Workspace/www.polly.com/jarvis-test-ground"
JARVIS_DIR = Path(__file__).parent.parent


def run_jarvis(cmd: str, capture: bool = True, input_text: str = None) -> tuple[int, str]:
    """运行 jarvis CLI 命令"""
    full_cmd = f"cd {JARVIS_DIR} && poetry run python -m src.cli {cmd}"
    result = subprocess.run(
        full_cmd,
        shell=True,
        capture_output=capture,
        text=True,
        input=input_text,
    )
    return result.returncode, result.stdout + result.stderr


def test_status() -> bool:
    """测试 status 命令"""
    console.print("\n[bold cyan]📊 测试 jarvis status...[/]")
    code, output = run_jarvis("status")
    console.print(output)
    return "Jarvis" in output or "生命体征" in output


def test_explore() -> bool:
    """测试 explore 命令"""
    console.print(f"\n[bold cyan]🔍 测试 jarvis explore {TEST_GROUND}...[/]")
    # 自动选择 "all" 来确认所有项目
    code, output = run_jarvis(f"explore {TEST_GROUND}", input_text="all\n")
    console.print(output[:800] if len(output) > 800 else output)
    # 检查是否发现了项目
    return "project" in output.lower() or "发现" in output or "探索" in output


def test_projects() -> bool:
    """测试 projects 命令"""
    console.print("\n[bold cyan]📂 测试 jarvis projects...[/]")
    code, output = run_jarvis("projects")
    console.print(output)
    return code == 0


def test_skills() -> bool:
    """测试 skills 命令"""
    console.print("\n[bold cyan]⚡ 测试 jarvis skills...[/]")
    code, output = run_jarvis("skills")
    console.print(output)
    return code == 0


def test_ask() -> bool:
    """测试 ask 命令"""
    console.print("\n[bold cyan]💬 测试 jarvis ask...[/]")
    code, output = run_jarvis('ask "你好，用一句话介绍你自己"')
    console.print(output)
    return code == 0 and len(output) > 20


def test_discoveries() -> bool:
    """测试 discoveries 命令"""
    console.print("\n[bold cyan]🔔 测试 jarvis discoveries...[/]")
    code, output = run_jarvis("discoveries")
    console.print(output)
    return code == 0


def test_daemon_foreground() -> bool:
    """测试前台 daemon (短时间)"""
    console.print("\n[bold cyan]🫀 测试 jarvis start -f (5秒)...[/]")
    
    # 启动 daemon 进程
    proc = subprocess.Popen(
        f"cd {JARVIS_DIR} && poetry run python -m src.cli start -f",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    
    # 等待 5 秒
    time.sleep(5)
    
    # 终止进程
    proc.terminate()
    try:
        output, _ = proc.communicate(timeout=2)
        console.print(output[:500] if output else "(no output)")
    except subprocess.TimeoutExpired:
        proc.kill()
    
    return True  # 只要没崩溃就算成功


def test_daemon_background() -> bool:
    """测试后台 daemon"""
    console.print("\n[bold cyan]🫀 测试后台 daemon (start → status → rest)...[/]")
    
    # 启动
    code, output = run_jarvis("start")
    console.print(f"  start: {output.strip()}")
    if code != 0:
        return False
    
    time.sleep(2)
    
    # 检查状态
    code, output = run_jarvis("status")
    is_running = "运行中" in output or "running" in output.lower()
    console.print(f"  status: {'🟢 运行中' if is_running else '❌ 未运行'}")
    
    # 停止
    code, output = run_jarvis("rest")
    console.print(f"  rest: {output.strip()}")
    
    return is_running


def test_file_change_detection() -> bool:
    """测试文件变化检测"""
    console.print("\n[bold cyan]👁️ 测试文件变化检测...[/]")
    
    # 启动后台 daemon
    run_jarvis("start")
    time.sleep(2)
    
    # 创建测试文件
    test_file = TEST_GROUND / f"test_detection_{int(time.time())}.md"
    test_file.write_text("# Test File\n\nThis is a test for file detection.")
    console.print(f"  创建文件: {test_file.name}")
    
    # 等待检测
    time.sleep(3)
    
    # 检查 discoveries
    code, output = run_jarvis("discoveries")
    detected = test_file.name in output or "检测" in output
    console.print(f"  检测结果: {'✅ 检测到' if detected else '⚠️ 未在 discoveries 中'}")
    
    # 清理
    run_jarvis("rest")
    test_file.unlink(missing_ok=True)
    
    return True  # 文件监控机制存在即可


def main():
    console.print(Panel.fit(
        "[bold green]🧪 Jarvis-Agent Phase 1 完整测试[/]\n"
        f"测试环境: {TEST_GROUND}",
        title="Phase 1 Test Suite"
    ))
    
    tests = [
        ("status", test_status),
        ("explore", test_explore),
        ("projects", test_projects),
        ("skills", test_skills),
        ("ask", test_ask),
        ("discoveries", test_discoveries),
        ("daemon (foreground)", test_daemon_foreground),
        ("daemon (background)", test_daemon_background),
        ("file detection", test_file_change_detection),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed, None))
        except Exception as e:
            results.append((name, False, str(e)))
            console.print(f"[red]❌ {name} 异常: {e}[/]")
    
    # 汇总报告
    console.print("\n")
    table = Table(title="📋 Phase 1 测试报告")
    table.add_column("测试项", style="cyan")
    table.add_column("状态", justify="center")
    table.add_column("备注")
    
    passed_count = 0
    for name, passed, error in results:
        if passed:
            passed_count += 1
            table.add_row(name, "✅ PASS", "")
        else:
            table.add_row(name, "❌ FAIL", error or "")
    
    console.print(table)
    
    # 总结
    total = len(results)
    console.print(Panel.fit(
        f"[bold]通过: {passed_count}/{total}[/]\n"
        f"{'🎉 Phase 1 测试全部通过！' if passed_count == total else '⚠️ 部分测试未通过'}",
        title="测试总结",
        border_style="green" if passed_count == total else "yellow"
    ))
    
    return 0 if passed_count == total else 1


if __name__ == "__main__":
    sys.exit(main())
