"""
JarvisDaemon 心跳进程

🫀 Jarvis 的核心生命模块

功能：
- 实时监控文件变化（watchdog）
- 定时调用 Claude 进行智能分析
- 自动发送通知
- 管理生命体征状态
"""
import asyncio
import json
import os
import sys
import signal
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# 第三方依赖
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    print("[Daemon] 警告: watchdog 未安装，文件监控功能将不可用")

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False
    print("[Daemon] 警告: httpx 未安装，LLM 调用功能将不可用")

from .discovery import Discovery, DiscoveryType, DiscoveryStore
from .notifier import Notifier, NotificationConfig
from ..memory import MemoryWriter, MemoryEntry, MemoryIndex, IndexEntry


@dataclass
class DaemonConfig:
    """Daemon 配置"""
    # 思考间隔
    think_interval_seconds: int = 60       # 测试：1分钟
    self_reflect_interval_seconds: int = 3600  # 无变化时自省：1小时
    
    # 监控路径
    watch_paths: list[str] = field(default_factory=list)
    
    # LLM 配置
    llm_provider: str = "openai"  # "openai" or "anthropic"
    llm_base_url: str = "http://localhost:23335/api/openai"
    llm_auth_token: str = "Powered by Agent Maestro"
    llm_model: str = "claude-sonnet-4"
    
    # 通知配置
    notification_terminal: bool = True
    notification_macos: bool = True
    notification_min_importance: int = 3
    
    # 存储路径
    jarvis_home: str = field(default_factory=lambda: os.path.expanduser("~/.jarvis"))
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "DaemonConfig":
        """从配置文件加载"""
        if config_path is None:
            config_path = os.path.expanduser("~/.jarvis/config.json")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            return cls(
                think_interval_seconds=data.get("daemon", {}).get("think_interval_seconds", 60),
                self_reflect_interval_seconds=data.get("daemon", {}).get("self_reflect_interval", 3600),
                watch_paths=data.get("watch_paths", []),
                llm_provider=data.get("llm", {}).get("provider", "openai"),
                llm_base_url=data.get("llm", {}).get("base_url", "http://localhost:23335/api/openai"),
                llm_auth_token=data.get("llm", {}).get("auth_token", "Powered by Agent Maestro"),
                llm_model=data.get("llm", {}).get("model", "claude-sonnet-4"),
                notification_terminal=data.get("notification", {}).get("terminal", True),
                notification_macos=data.get("notification", {}).get("macos_notification", True),
                notification_min_importance=data.get("notification", {}).get("min_importance", 3),
            )
        except FileNotFoundError:
            return cls()
        except json.JSONDecodeError:
            return cls()
    
    def save(self, config_path: Optional[str] = None):
        """保存配置文件"""
        if config_path is None:
            config_path = os.path.join(self.jarvis_home, "config.json")
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        data = {
            "daemon": {
                "think_interval_seconds": self.think_interval_seconds,
                "self_reflect_interval": self.self_reflect_interval_seconds,
            },
            "watch_paths": self.watch_paths,
            "llm": {
                "base_url": self.llm_base_url,
                "auth_token": self.llm_auth_token,
                "model": self.llm_model,
            },
            "notification": {
                "terminal": self.notification_terminal,
                "macos_notification": self.notification_macos,
                "min_importance": self.notification_min_importance,
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


@dataclass
class LifeSigns:
    """生命体征"""
    status: str = "running"  # running, resting, stopped
    last_heartbeat: datetime = field(default_factory=datetime.now)
    discoveries_today: int = 0
    important_discoveries_today: int = 0
    active_skills: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "discoveries_today": self.discoveries_today,
            "important_discoveries_today": self.important_discoveries_today,
            "active_skills": self.active_skills,
            "started_at": self.started_at.isoformat(),
        }
    
    def save(self, path: str):
        """保存状态"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    @classmethod
    def load(cls, path: str) -> "LifeSigns":
        """加载状态"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                status=data.get("status", "stopped"),
                last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
                discoveries_today=data.get("discoveries_today", 0),
                important_discoveries_today=data.get("important_discoveries_today", 0),
                active_skills=data.get("active_skills", 0),
                started_at=datetime.fromisoformat(data.get("started_at", datetime.now().isoformat())),
            )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return cls()


class JarvisEventHandler(FileSystemEventHandler):
    """文件系统事件处理器"""
    
    def __init__(self, daemon: "JarvisDaemon"):
        super().__init__()
        self.daemon = daemon
        self._recent_changes: list[dict] = []
        self._ignore_patterns = [
            ".git", "__pycache__", ".DS_Store", "node_modules",
            ".pyc", ".pyo", ".swp", ".swo", "~"
        ]
    
    def _should_ignore(self, path: str) -> bool:
        """检查是否应该忽略"""
        for pattern in self._ignore_patterns:
            if pattern in path:
                return True
        return False
    
    def on_modified(self, event: "FileSystemEvent"):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._record_change("modified", event.src_path)
    
    def on_created(self, event: "FileSystemEvent"):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._record_change("created", event.src_path)
    
    def on_deleted(self, event: "FileSystemEvent"):
        if event.is_directory or self._should_ignore(event.src_path):
            return
        self._record_change("deleted", event.src_path)
    
    def _record_change(self, action: str, path: str):
        """记录变化"""
        self._recent_changes.append({
            "action": action,
            "path": path,
            "timestamp": datetime.now().isoformat()
        })
        # 只保留最近 50 条
        if len(self._recent_changes) > 50:
            self._recent_changes = self._recent_changes[-50:]
    
    def get_and_clear_changes(self) -> list[dict]:
        """获取并清空变化记录"""
        changes = self._recent_changes.copy()
        self._recent_changes = []
        return changes


class JarvisDaemon:
    """
    Jarvis 心跳进程
    
    🫀 让 Jarvis 真正"活"起来
    """
    
    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig.load()
        self.alive = False
        self._last_self_reflect = datetime.now()
        
        # 初始化组件
        self.notifier = Notifier(NotificationConfig(
            terminal=self.config.notification_terminal,
            macos_notification=self.config.notification_macos,
            min_importance=self.config.notification_min_importance,
        ))
        
        discoveries_path = os.path.join(self.config.jarvis_home, "discoveries.json")
        self.discovery_store = DiscoveryStore(discoveries_path)
        
        # 🆕 Phase 2: 混合记忆系统
        # Markdown 存内容，SQLite 做索引
        memory_path = Path(self.config.jarvis_home) / "memory"
        index_path = Path(self.config.jarvis_home) / "index.db"
        self.memory_writer = MemoryWriter(memory_path)
        self.memory_index = MemoryIndex(index_path)
        
        self.life_signs = LifeSigns()
        self._state_path = os.path.join(self.config.jarvis_home, "state.json")
        
        # Watchdog
        self._observer: Optional[Observer] = None
        self._event_handler: Optional[JarvisEventHandler] = None
        
        # HTTP 客户端
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def start(self):
        """启动心跳"""
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🫀 Jarvis Daemon 启动                     ║
╠══════════════════════════════════════════════════════════════╣
║  状态: 运行中                                                 ║
║  思考间隔: {self.config.think_interval_seconds}s                                              ║
║  监控路径: {len(self.config.watch_paths)} 个                                              ║
║  LLM: {self.config.llm_model[:20]}                                     ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        self.alive = True
        self.life_signs = LifeSigns(status="running", started_at=datetime.now())
        self.life_signs.save(self._state_path)
        
        # 启动文件监控
        self._start_file_watcher()
        
        # 初始化 HTTP 客户端（禁用代理，避免本地请求走代理）
        if HAS_HTTPX:
            self._http_client = httpx.AsyncClient(timeout=60.0, trust_env=False)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # 发送启动通知
        self.notifier.notify(
            title="Jarvis 已醒来",
            message="我已开始监控你的工作目录，有新发现会及时告诉你。",
            importance=2,
            subtitle="心跳进程已启动"
        )
        
        try:
            await self._think_loop()
        finally:
            await self.stop()
    
    async def stop(self):
        """停止心跳"""
        print("\n🛑 Jarvis Daemon 停止中...")
        self.alive = False
        
        # 停止文件监控
        if self._observer:
            self._observer.stop()
            self._observer.join()
        
        # 关闭 HTTP 客户端
        if self._http_client:
            await self._http_client.aclose()
        
        # 更新状态
        self.life_signs.status = "stopped"
        self.life_signs.save(self._state_path)
        
        print("👋 Jarvis 已休眠，随时可以唤醒")
    
    def _handle_signal(self, signum, frame):
        """处理系统信号"""
        self.alive = False
    
    def _start_file_watcher(self):
        """启动文件监控"""
        if not HAS_WATCHDOG:
            return
        
        if not self.config.watch_paths:
            print("[Daemon] 没有配置监控路径")
            return
        
        self._event_handler = JarvisEventHandler(self)
        self._observer = Observer()
        
        for path in self.config.watch_paths:
            if os.path.exists(path):
                self._observer.schedule(self._event_handler, path, recursive=True)
                print(f"[Daemon] 监控: {path}")
            else:
                print(f"[Daemon] 警告: 路径不存在 {path}")
        
        self._observer.start()
    
    async def _think_loop(self):
        """思考循环 - 心跳的核心"""
        while self.alive:
            try:
                # 更新心跳时间
                self.life_signs.last_heartbeat = datetime.now()
                self.life_signs.save(self._state_path)
                
                # 收集文件变化
                changes = []
                if self._event_handler:
                    changes = self._event_handler.get_and_clear_changes()
                
                discovery = None
                
                if changes:
                    # 有变化时进行分析
                    print(f"[Daemon] 检测到 {len(changes)} 个文件变化，开始分析...")
                    discovery = await self._think(changes)
                else:
                    # 检查是否需要自省
                    time_since_reflect = datetime.now() - self._last_self_reflect
                    if time_since_reflect.total_seconds() > self.config.self_reflect_interval_seconds:
                        print("[Daemon] 触发定时自省...")
                        discovery = await self._self_reflect()
                        self._last_self_reflect = datetime.now()
                
                # 处理发现
                if discovery:
                    self._process_discovery(discovery)
                
            except Exception as e:
                print(f"[Daemon] 思考循环错误: {e}")
            
            # 等待下一次心跳
            await asyncio.sleep(self.config.think_interval_seconds)
    
    async def _think(self, changes: list[dict]) -> Optional[Discovery]:
        """
        调用 Claude 分析文件变化
        
        核心：LLM 驱动的智能发现，而非规则触发
        """
        if not HAS_HTTPX or not self._http_client:
            return self._fallback_analysis(changes)
        
        # 格式化变化列表
        changes_text = "\n".join([
            f"- [{c['action']}] {c['path']}"
            for c in changes[:20]  # 最多 20 条
        ])
        
        prompt = f"""你是 Jarvis，Polly 的 AI 助手。你正在监控她的工作目录。

以下是最近检测到的文件变化：

{changes_text}

请分析这些变化，生成一个智能发现。

要求：
1. 不要只是列出"文件被修改了"，而是要推断这意味着什么
2. 如果是代码文件，推测可能在做什么功能
3. 如果是文档，推测可能在写什么内容
4. 给出具体的、可操作的建议

请用以下 JSON 格式回复：
{{
    "title": "简短的发现标题（10字以内）",
    "content": "详细分析（2-3句话，说明这个变化意味着什么，有什么建议）",
    "importance": 1-5 的数字（1=琐碎，3=值得注意，5=非常重要）,
    "suggested_action": "建议的下一步行动（可选）"
}}

只返回 JSON，不要有其他内容。"""

        try:
            response = await self._call_claude(prompt)
            return self._parse_discovery_response(response, changes)
        except Exception as e:
            print(f"[Daemon] Claude 调用失败: {e}")
            return self._fallback_analysis(changes)
    
    async def _self_reflect(self) -> Optional[Discovery]:
        """
        自省思考
        
        当没有文件变化时，Jarvis 也可以主动思考
        """
        if not HAS_HTTPX or not self._http_client:
            return None
        
        prompt = """你是 Jarvis，Polly 的 AI 助手。现在是自省时间。

最近一段时间没有检测到文件变化。请思考：
1. 是否有什么事情需要提醒 Polly？
2. 有没有什么项目可能被遗忘了？
3. 有没有什么建议想给 Polly？

如果没有特别重要的事情，可以返回 null。

如果有，请用以下 JSON 格式回复：
{
    "title": "简短标题",
    "content": "详细内容",
    "importance": 1-5,
    "suggested_action": "建议"
}

只返回 JSON 或 null。"""

        try:
            response = await self._call_claude(prompt)
            if response.strip().lower() == "null":
                return None
            return self._parse_discovery_response(response, [], DiscoveryType.SELF_REFLECT)
        except Exception as e:
            print(f"[Daemon] 自省失败: {e}")
            return None
    
    async def _call_claude(self, prompt: str) -> str:
        """调用 LLM API（支持 OpenAI 和 Anthropic 格式）"""
        if not self._http_client:
            raise RuntimeError("HTTP 客户端未初始化")
        
        if self.config.llm_provider == "openai":
            # OpenAI 格式
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.llm_auth_token}"
            }
            payload = {
                "model": self.config.llm_model,
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            response = await self._http_client.post(
                f"{self.config.llm_base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            # Anthropic 格式
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.config.llm_auth_token,
                "anthropic-version": "2023-06-01"
            }
            payload = {
                "model": self.config.llm_model,
                "max_tokens": 1024,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            response = await self._http_client.post(
                f"{self.config.llm_base_url}/v1/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
    
    def _parse_discovery_response(
        self,
        response: str,
        changes: list[dict],
        discovery_type: DiscoveryType = DiscoveryType.FILE_INSIGHT
    ) -> Optional[Discovery]:
        """解析 Claude 响应"""
        try:
            # 尝试提取 JSON
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            
            data = json.loads(response)
            
            return Discovery(
                type=discovery_type,
                title=data.get("title", "新发现"),
                content=data.get("content", ""),
                importance=data.get("importance", 3),
                source_files=[c["path"] for c in changes] if changes else [],
                suggested_action=data.get("suggested_action")
            )
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Daemon] 解析响应失败: {e}")
            return None
    
    def _fallback_analysis(self, changes: list[dict]) -> Optional[Discovery]:
        """
        后备分析（当 LLM 不可用时）
        
        简单的规则匹配，不如 LLM 智能
        """
        if not changes:
            return None
        
        # 统计变化类型
        modified_count = sum(1 for c in changes if c["action"] == "modified")
        created_count = sum(1 for c in changes if c["action"] == "created")
        deleted_count = sum(1 for c in changes if c["action"] == "deleted")
        
        # 分析文件类型
        extensions = set()
        for c in changes:
            ext = os.path.splitext(c["path"])[1]
            if ext:
                extensions.add(ext)
        
        title = f"检测到 {len(changes)} 个文件变化"
        content = f"修改 {modified_count} 个，新建 {created_count} 个，删除 {deleted_count} 个。"
        if extensions:
            content += f" 文件类型: {', '.join(extensions)}"
        
        return Discovery(
            type=DiscoveryType.FILE_INSIGHT,
            title=title,
            content=content,
            importance=2,
            source_files=[c["path"] for c in changes]
        )
    
    def _process_discovery(self, discovery: Discovery):
        """处理发现"""
        # 1. 保存到 discoveries.json（保持向后兼容）
        self.discovery_store.add(discovery)
        
        # 2. 🆕 写入 Markdown 日志（编年体）
        entry = MemoryEntry(
            timestamp=discovery.timestamp,
            title=discovery.title,
            content=discovery.content,
            importance=discovery.importance,
            entry_type="discovery",
            tags=discovery.source_files[:5] if discovery.source_files else None,
        )
        file_path = self.memory_writer.append_to_daily(entry)
        
        # 3. 🆕 添加到搜索索引
        index_entry = IndexEntry(
            id=discovery.id,
            entry_type="discovery",
            file_path=str(file_path),
            date=discovery.timestamp.date().isoformat(),
            title=discovery.title,
            tags=discovery.source_files[:5] if discovery.source_files else [],
            importance=discovery.importance,
            summary=discovery.content[:200] if discovery.content else ""
        )
        self.memory_index.add(index_entry)
        
        # 4. 更新统计
        self.life_signs.discoveries_today += 1
        if discovery.importance >= 4:
            self.life_signs.important_discoveries_today += 1
        
        # 5. 发送通知
        if discovery.importance >= self.config.notification_min_importance:
            self.notifier.notify(
                title=discovery.title,
                message=discovery.content,
                importance=discovery.importance,
                subtitle=discovery.suggested_action
            )
        
        print(f"[Daemon] 新发现: {discovery.title} (重要性: {discovery.importance})")
        print(f"[Daemon]   └─ 已记录到: {file_path.name}")


async def run_daemon():
    """运行 Daemon 的入口函数"""
    config = DaemonConfig.load()
    daemon = JarvisDaemon(config)
    await daemon.start()


def main():
    """主函数"""
    asyncio.run(run_daemon())


if __name__ == "__main__":
    main()
