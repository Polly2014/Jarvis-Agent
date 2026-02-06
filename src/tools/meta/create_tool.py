"""
create_tool — 创建自定义 Tool

Layer 1 元工具。生成标准 Tool 子类代码并保存到 ~/.jarvis/tools/。
"""

import os
import json
from pathlib import Path
from textwrap import dedent

from ..base import Tool, ToolResult


_TOOL_TEMPLATE = '''\
"""
{name} — {description}

Auto-generated Jarvis custom tool.
"""

from src.tools.base import Tool, ToolResult


class {class_name}(Tool):

    @property
    def name(self) -> str:
        return "{name}"

    @property
    def description(self) -> str:
        return """{description}"""

    @property
    def parameters(self) -> dict:
        return {parameters_json}

    async def execute(self, **kwargs) -> ToolResult:
{code}
'''


class CreateToolTool(Tool):

    @property
    def name(self) -> str:
        return "create_tool"

    @property
    def description(self) -> str:
        return (
            "创建一个自定义 Jarvis Tool（Python 脚本）。"
            "生成标准 Tool 子类代码，保存到 ~/.jarvis/tools/。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "工具名称（snake_case，如 count_lines）",
                },
                "description": {
                    "type": "string",
                    "description": "工具描述（给 LLM 看的）",
                },
                "parameters_schema": {
                    "type": "object",
                    "description": "工具参数的 JSON Schema 定义",
                },
                "code": {
                    "type": "string",
                    "description": "execute 方法的函数体代码（Python，缩进 8 空格）",
                },
            },
            "required": ["name", "description", "parameters_schema", "code"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        tool_name = kwargs.get("name", "")
        description = kwargs.get("description", "")
        parameters_schema = kwargs.get("parameters_schema", {})
        code = kwargs.get("code", "")

        if not tool_name or not description or not code:
            return ToolResult(
                success=False, output="",
                error="name, description, code 不能为空"
            )

        # 生成类名
        class_name = "".join(w.capitalize() for w in tool_name.split("_")) + "Tool"

        # 确保代码缩进正确（8 空格）
        code_lines = code.strip().splitlines()
        indented_code = "\n".join(
            f"        {line}" if line.strip() else "" for line in code_lines
        )

        # 生成代码
        parameters_json = json.dumps(parameters_schema, indent=8, ensure_ascii=False)
        tool_code = _TOOL_TEMPLATE.format(
            name=tool_name,
            description=description,
            class_name=class_name,
            parameters_json=parameters_json,
            code=indented_code,
        )

        # 保存
        tools_dir = Path.home() / ".jarvis" / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        tool_path = tools_dir / f"{tool_name}.py"
        tool_path.write_text(tool_code, encoding="utf-8")

        return ToolResult(
            success=True,
            output=f"✅ Tool '{tool_name}' 已创建: {tool_path}\n"
                   f"   类名: {class_name}\n"
                   f"   重启后自动加载，或使用 /tools reload",
            metadata={"tool_name": tool_name, "path": str(tool_path), "class_name": class_name},
        )
