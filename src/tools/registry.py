"""
Tool Registry — 工具注册表

自动发现 builtins/ 和 meta/ 下的工具，统一管理。
"""

import importlib
import pkgutil
from typing import Optional

from .base import Tool, ToolResult


class ToolRegistry:
    """
    工具注册表

    职责:
    1. 注册/注销工具
    2. 自动发现 builtins 和 meta 包下的工具
    3. 按名称查找工具
    4. 导出 OpenAI function calling 格式
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具"""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """注销一个工具"""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        """按名称获取工具"""
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        """列出所有已注册工具"""
        return list(self._tools.values())

    def list_names(self) -> list[str]:
        """列出所有工具名称"""
        return list(self._tools.keys())

    def to_openai_tools(self) -> list[dict]:
        """导出为 OpenAI tools 格式（用于 function calling）"""
        return [tool.to_openai_function() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """执行指定工具

        Args:
            tool_name: 工具名称（用 tool_name 避免与工具参数 name 冲突）
            **kwargs: 工具参数
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' not found. Available: {', '.join(self.list_names())}"
            )
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{tool_name}' execution failed: {e}"
            )

    def discover(self) -> int:
        """
        自动发现并注册工具

        扫描 builtins/ 和 meta/ 包，找到所有 Tool 子类并注册。
        Returns: 新注册的工具数量
        """
        count = 0
        for package_name in ("builtins", "meta"):
            try:
                package = importlib.import_module(f".{package_name}", package="src.tools")
            except ImportError:
                continue

            for _importer, module_name, _is_pkg in pkgutil.iter_modules(package.__path__):
                try:
                    module = importlib.import_module(
                        f".{package_name}.{module_name}", package="src.tools"
                    )
                except ImportError:
                    continue

                # 查找模块中的 Tool 子类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Tool)
                        and attr is not Tool
                        and not getattr(attr, "__abstractmethods__", None)
                    ):
                        try:
                            tool_instance = attr()
                            if tool_instance.name not in self._tools:
                                self.register(tool_instance)
                                count += 1
                        except Exception:
                            continue

        return count

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        return f"<ToolRegistry: {len(self._tools)} tools>"


# ── 全局单例 ──────────────────────────────────────────────

_global_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """获取全局 ToolRegistry 单例（懒初始化 + 自动发现）"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _global_registry.discover()
    return _global_registry
