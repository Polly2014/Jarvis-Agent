"""
file_write — 写入文件内容

Layer 0 原子工具。支持创建、覆盖、追加三种模式。
"""

import os
from pathlib import Path

from ..base import Tool, ToolResult


# 禁止写入的路径前缀
_BLOCKED_PREFIXES = (
    "/System", "/usr", "/bin", "/sbin",
    "/etc", "/var/root",
    "/private/var/root",
)

# macOS /var → /private/var 是 symlink
# /private/var/folders 是用户临时目录，不应阻止
# 仅阻止 /private/var/root 等真正的系统路径


class FileWriteTool(Tool):

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "写入文件内容。支持创建新文件、覆盖已有文件或追加内容。自动创建不存在的父目录。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件的绝对或相对路径",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的内容",
                },
                "mode": {
                    "type": "string",
                    "enum": ["create", "overwrite", "append"],
                    "description": "写入模式: create=仅创建新文件, overwrite=覆盖, append=追加",
                    "default": "overwrite",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "overwrite")

        # 展开 ~ 和环境变量
        path = os.path.expanduser(os.path.expandvars(path))
        file_path = Path(path).resolve()

        # 安全检查
        path_str = str(file_path)
        for prefix in _BLOCKED_PREFIXES:
            if path_str.startswith(prefix):
                return ToolResult(
                    success=False, output="",
                    error=f"安全限制: 不允许写入系统路径 {prefix}"
                )

        # create 模式不允许覆盖
        if mode == "create" and file_path.exists():
            return ToolResult(
                success=False, output="",
                error=f"文件已存在: {path}（使用 overwrite 模式可覆盖）"
            )

        # 自动创建父目录
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return ToolResult(success=False, output="", error=f"创建目录失败: {e}")

        # 写入
        try:
            if mode == "append":
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(content)
                action = "追加"
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                action = "创建" if mode == "create" else "写入"
        except Exception as e:
            return ToolResult(success=False, output="", error=f"写入失败: {e}")

        return ToolResult(
            success=True,
            output=f"✅ 已{action}文件: {file_path} ({len(content)} 字符)",
            metadata={"path": str(file_path), "size": len(content), "mode": mode},
        )
