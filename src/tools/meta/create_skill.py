"""
create_skill — 创建 Skill

Layer 1 元工具。遵循 .claude/skills/ 格式创建 SKILL.md + 可选脚本。
Skills 存放在 ~/.jarvis/skills/{name}/
"""

import os
from pathlib import Path

from ..base import Tool, ToolResult


_SKILL_TEMPLATE = """\
---
name: {name}
description: {description}
---

# {display_name}

{instructions}
"""


class CreateSkillTool(Tool):

    @property
    def name(self) -> str:
        return "create_skill"

    @property
    def description(self) -> str:
        return (
            "创建一个 Jarvis Skill（技能包）。"
            "Skill 包含 SKILL.md 指令文件和可选的脚本。"
            "格式兼容 .claude/skills/ 规范。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Skill 名称（英文、小写、连字符，如 blog-writer）",
                },
                "description": {
                    "type": "string",
                    "description": "Skill 描述（一句话说明用途和触发条件）",
                },
                "instructions": {
                    "type": "string",
                    "description": "Skill 的详细指令（Markdown 格式，包含工作流程、规则等）",
                },
                "scripts": {
                    "type": "array",
                    "description": "可选的脚本文件列表",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "description": "脚本文件名"},
                            "content": {"type": "string", "description": "脚本内容"},
                        },
                        "required": ["filename", "content"],
                    },
                },
            },
            "required": ["name", "description", "instructions"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        skill_name = kwargs.get("name", "")
        skill_desc = kwargs.get("description", "")
        instructions = kwargs.get("instructions", "")
        scripts = kwargs.get("scripts", [])

        if not skill_name or not skill_desc:
            return ToolResult(success=False, output="", error="name 和 description 不能为空")

        # Skill 目录
        jarvis_home = Path.home() / ".jarvis"
        skill_dir = jarvis_home / "skills" / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 生成 display name
        display_name = skill_name.replace("-", " ").title()

        # 写入 SKILL.md
        skill_md = _SKILL_TEMPLATE.format(
            name=skill_name,
            description=skill_desc,
            display_name=display_name,
            instructions=instructions,
        )
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(skill_md, encoding="utf-8")

        created_files = [str(skill_path)]

        # 写入脚本
        if scripts:
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            for script in scripts:
                filename = script.get("filename", "")
                content = script.get("content", "")
                if filename and content:
                    script_path = scripts_dir / filename
                    script_path.write_text(content, encoding="utf-8")
                    # Python/Bash 脚本自动加可执行权限
                    if filename.endswith((".py", ".sh")):
                        os.chmod(script_path, 0o755)
                    created_files.append(str(script_path))

        files_list = "\n".join(f"  📄 {f}" for f in created_files)
        return ToolResult(
            success=True,
            output=f"✅ Skill '{skill_name}' 已创建:\n{files_list}",
            metadata={"skill_name": skill_name, "path": str(skill_dir), "files": created_files},
        )
