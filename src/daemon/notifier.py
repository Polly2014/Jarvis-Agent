"""
Notifier 通知模块

📢 支持终端输出和 macOS 系统通知
"""
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class NotificationConfig:
    """通知配置"""
    terminal: bool = True
    macos_notification: bool = True
    min_importance: int = 3
    sound: bool = True


class Notifier:
    """
    通知管理器
    
    支持：
    - 终端输出（带颜色）
    - macOS 系统通知（osascript）
    """
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
    
    def notify(
        self,
        title: str,
        message: str,
        importance: int = 3,
        subtitle: Optional[str] = None
    ):
        """
        发送通知
        
        Args:
            title: 通知标题
            message: 通知内容
            importance: 重要性 1-5
            subtitle: 副标题（可选）
        """
        # 检查重要性阈值
        if importance < self.config.min_importance:
            return
        
        # 终端输出
        if self.config.terminal:
            self._terminal_notify(title, message, importance, subtitle)
        
        # macOS 系统通知
        if self.config.macos_notification and sys.platform == "darwin":
            self._macos_notify(title, message, subtitle)
    
    def _terminal_notify(
        self,
        title: str,
        message: str,
        importance: int,
        subtitle: Optional[str] = None
    ):
        """终端输出"""
        # 重要性颜色映射
        colors = {
            1: "\033[90m",   # 灰色
            2: "\033[37m",   # 白色
            3: "\033[33m",   # 黄色
            4: "\033[35m",   # 紫色
            5: "\033[31m",   # 红色
        }
        reset = "\033[0m"
        color = colors.get(importance, "\033[37m")
        
        importance_stars = "⭐" * importance
        
        print(f"\n{color}{'='*60}{reset}")
        print(f"{color}💡 Jarvis 发现 {importance_stars}{reset}")
        print(f"{color}{'='*60}{reset}")
        print(f"\033[1m{title}\033[0m")
        if subtitle:
            print(f"\033[90m{subtitle}\033[0m")
        print()
        print(message)
        print(f"{color}{'='*60}{reset}\n")
    
    def _macos_notify(
        self,
        title: str,
        message: str,
        subtitle: Optional[str] = None
    ):
        """macOS 系统通知"""
        # 构建 AppleScript
        script_parts = [f'display notification "{self._escape_applescript(message)}"']
        script_parts.append(f'with title "Jarvis: {self._escape_applescript(title)}"')
        
        if subtitle:
            script_parts.append(f'subtitle "{self._escape_applescript(subtitle)}"')
        
        if self.config.sound:
            script_parts.append('sound name "Ping"')
        
        script = " ".join(script_parts)
        
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            print(f"[Notifier] macOS 通知失败: {e}")
        except FileNotFoundError:
            # osascript 不存在（非 macOS）
            pass
    
    def _escape_applescript(self, text: str) -> str:
        """转义 AppleScript 特殊字符"""
        return text.replace("\\", "\\\\").replace('"', '\\"')
    
    def test(self):
        """测试通知"""
        self.notify(
            title="测试通知",
            message="如果你看到这条消息，说明通知系统工作正常！",
            importance=3,
            subtitle="Jarvis Daemon"
        )


if __name__ == "__main__":
    # 测试通知
    notifier = Notifier()
    notifier.test()
