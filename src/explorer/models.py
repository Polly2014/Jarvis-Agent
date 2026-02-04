"""
探索器 - 项目数据模型
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
from enum import Enum
from rich.table import Table
from rich.panel import Panel


class ProjectType(str, Enum):
    """项目类型"""
    ZOLA_BLOG = "zola_blog"
    ACADEMIC_PAPER = "academic_paper"
    MCP_SERVER = "mcp_server"
    VSCODE_EXTENSION = "vscode_extension"
    PYTHON_PROJECT = "python_project"
    BOOK_TRANSLATION = "book_translation"
    UNKNOWN = "unknown"


@dataclass
class ProjectMeta:
    """项目元数据"""
    name: str
    path: Path
    type: ProjectType
    description: str = ""
    status: str = ""
    confidence: float = 0.0
    context: dict = field(default_factory=dict)
    suggested_skill: str = ""
    
    @property
    def icon(self) -> str:
        """返回项目类型对应的图标"""
        icons = {
            ProjectType.ZOLA_BLOG: "✍️",
            ProjectType.ACADEMIC_PAPER: "📄",
            ProjectType.MCP_SERVER: "📦",
            ProjectType.VSCODE_EXTENSION: "🧩",
            ProjectType.PYTHON_PROJECT: "🐍",
            ProjectType.BOOK_TRANSLATION: "📚",
            ProjectType.UNKNOWN: "❓"
        }
        return icons.get(self.type, "📁")


def format_discovery_report(projects: List[ProjectMeta]) -> Panel:
    """格式化项目发现报告"""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("类型", width=8)
    table.add_column("项目名称", width=25)
    table.add_column("状态", width=20)
    table.add_column("建议", width=30)
    
    for i, project in enumerate(projects, 1):
        table.add_row(
            str(i),
            project.icon,
            project.name,
            project.status or "[dim]未知[/dim]",
            f"创建 {project.suggested_skill} skill" if project.suggested_skill else "[dim]无[/dim]"
        )
    
    return Panel(
        table,
        title=f"🔍 发现 {len(projects)} 个项目",
        border_style="green"
    )
