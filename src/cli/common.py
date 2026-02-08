"""
Jarvis CLI — 公共常量与工具函数
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel

# ── 全局单例 ──────────────────────────────────────────────
console = Console()

# 版本号
VERSION = "0.4.0"

# Jarvis 家目录
JARVIS_HOME = Path.home() / ".jarvis"


# ── 路径辅助 ──────────────────────────────────────────────

def get_config_path() -> Path:
    return JARVIS_HOME / "config.json"


def get_state_path() -> Path:
    return JARVIS_HOME / "state.json"


def get_discoveries_path() -> Path:
    return JARVIS_HOME / "discoveries.json"


def get_pid_path() -> Path:
    return JARVIS_HOME / "daemon.pid"


def ensure_jarvis_home():
    """确保 Jarvis 家目录存在"""
    JARVIS_HOME.mkdir(parents=True, exist_ok=True)
    (JARVIS_HOME / "logs").mkdir(exist_ok=True)
    (JARVIS_HOME / "memory").mkdir(exist_ok=True)
    (JARVIS_HOME / "skills").mkdir(exist_ok=True)


# ── 状态查询 ──────────────────────────────────────────────

def get_status_summary() -> tuple[str, str, int]:
    """
    获取状态摘要
    Returns: (status_emoji, status_text, unread_count)
    """
    state_path = get_state_path()
    discoveries_path = get_discoveries_path()

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


def get_unread_discoveries(limit: int = 3) -> list[dict]:
    """获取未读发现列表（按重要性排序）"""
    discoveries_path = get_discoveries_path()
    if not discoveries_path.exists():
        return []

    try:
        with open(discoveries_path, "r") as f:
            data = json.load(f)

        unread = [
            d for d in data.get("discoveries", [])
            if not d.get("acknowledged")
        ]
        unread.sort(key=lambda x: x.get("importance", 3), reverse=True)
        return unread[:limit]
    except (json.JSONDecodeError, KeyError):
        return []


def format_discovery_time(iso_timestamp: str) -> str:
    """格式化发现时间为友好显示"""
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now()
        if dt.date() == now.date():
            return dt.strftime("%H:%M")
        elif (now.date() - dt.date()).days == 1:
            return "昨天"
        else:
            return dt.strftime("%m-%d")
    except (ValueError, TypeError):
        return "?"


def is_first_run() -> bool:
    """检查是否首次运行"""
    return not get_config_path().exists()


def detect_natural_intent(text: str) -> Optional[str]:
    """
    检测自然语言中的控制意图
    Returns: 'start', 'rest', 'status' 或 None
    """
    text_lower = text.lower()

    start_triggers = [
        "帮我挂机", "开始挂机", "上线", "启动", "start",
        "帮我守着", "开始监控", "wake up", "后台运行"
    ]
    if any(t in text_lower for t in start_triggers):
        return "start"

    rest_triggers = [
        "休息", "下线", "停止", "休眠", "stop", "rest",
        "不用守了", "停止监控", "go to sleep"
    ]
    if any(t in text_lower for t in rest_triggers):
        return "rest"

    status_triggers = [
        "你在干嘛", "什么状态", "怎么样了", "status",
        "在运行吗", "你好吗", "how are you"
    ]
    if any(t in text_lower for t in status_triggers):
        return "status"

    return None


def load_llm_config() -> dict:
    """加载 LLM 配置，返回 {base_url, model, auth_token}"""
    config_path = get_config_path()
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config.get("llm", {})
    return {
        "base_url": "http://localhost:23335/api/openai",
        "model": "claude-sonnet-4",
        "auth_token": "",
    }
