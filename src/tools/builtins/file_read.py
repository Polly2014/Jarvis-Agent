"""
file_read — 读取文件内容

Layer 0 原子工具。支持全文或按行范围读取。
"""

import os
from pathlib import Path

from ..base import Tool, ToolResult


class FileReadTool(Tool):

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "读取文件内容。支持全文读取或指定行范围。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件的绝对或相对路径",
                },
                "start_line": {
                    "type": "integer",
                    "description": "起始行号（1-based，可选）",
                },
                "end_line": {
                    "type": "integer",
                    "description": "结束行号（1-based，包含，可选）",
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")

        # 展开 ~ 和环境变量
        path = os.path.expanduser(os.path.expandvars(path))
        file_path = Path(path)

        if not file_path.exists():
            return ToolResult(success=False, output="", error=f"文件不存在: {path}")

        if not file_path.is_file():
            return ToolResult(success=False, output="", error=f"不是文件: {path}")

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # 尝试 latin-1 兜底
            try:
                content = file_path.read_bytes().decode("latin-1")
            except Exception as e:
                return ToolResult(success=False, output="", error=f"读取失败: {e}")
        except Exception as e:
            return ToolResult(success=False, output="", error=f"读取失败: {e}")

        # 按行范围截取
        if start_line is not None or end_line is not None:
            lines = content.splitlines(keepends=True)
            total = len(lines)
            s = max(1, start_line or 1) - 1  # 转 0-based
            e = min(total, end_line or total)
            content = "".join(lines[s:e])
            meta = {"total_lines": total, "returned_lines": f"{s+1}-{e}"}
        else:
            meta = {"total_lines": content.count("\n") + 1}

        # 防止输出过大
        if len(content) > 100_000:
            content = content[:100_000] + f"\n\n... (truncated, total {len(content)} chars)"

        return ToolResult(success=True, output=content, metadata=meta)
