"""
Jarvis Tool System

Phase 3: 让 Jarvis 拥有"手"——从只会说话到能做事

两层架构:
- Layer 0 (Atomic): file_read, file_write, shell_exec, http_request
- Layer 1 (Meta-tools): create_skill, create_tool, create_mcp
"""

from .base import Tool, ToolResult
from .registry import ToolRegistry

__all__ = ["Tool", "ToolResult", "ToolRegistry"]
