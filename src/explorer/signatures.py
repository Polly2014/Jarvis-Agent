"""
探索器 - 特征指纹库
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


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
class ProjectSignature:
    """项目特征签名"""
    type: ProjectType
    description: str
    required_files: List[str]  # 必须存在的文件/目录
    optional_files: List[str] = field(default_factory=list)  # 可选的文件/目录
    pattern_in_file: Dict[str, str] = field(default_factory=dict)  # 文件内必须包含的模式
    skill_template: str = ""  # 对应的 skill 模板
    priority: int = 0  # 匹配优先级（越高越优先）


# 项目特征指纹库
PROJECT_SIGNATURES: List[ProjectSignature] = [
    ProjectSignature(
        type=ProjectType.ZOLA_BLOG,
        description="Zola 静态博客",
        required_files=["config.toml", "content/", "templates/"],
        optional_files=["static/", "CNAME", "sass/"],
        skill_template="blog-tracker",
        priority=10
    ),
    ProjectSignature(
        type=ProjectType.ACADEMIC_PAPER,
        description="学术论文",
        required_files=["*.tex"],
        optional_files=["*.bib", "figures/", "latex/", "images/"],
        skill_template="paper-tracker",
        priority=8
    ),
    ProjectSignature(
        type=ProjectType.MCP_SERVER,
        description="MCP 服务器",
        required_files=["pyproject.toml"],
        pattern_in_file={"pyproject.toml": "fastmcp"},
        skill_template="mcp-monitor",
        priority=9
    ),
    ProjectSignature(
        type=ProjectType.VSCODE_EXTENSION,
        description="VS Code 扩展",
        required_files=["package.json", "src/extension.ts"],
        optional_files=["tsconfig.json", ".vscodeignore"],
        skill_template="extension-tracker",
        priority=9
    ),
    ProjectSignature(
        type=ProjectType.PYTHON_PROJECT,
        description="Python 项目",
        required_files=["pyproject.toml"],
        optional_files=["src/", "tests/", "setup.py"],
        skill_template="project-tracker",
        priority=5  # 较低优先级，作为兜底
    ),
    ProjectSignature(
        type=ProjectType.BOOK_TRANSLATION,
        description="书籍翻译项目",
        required_files=["*.md"],
        optional_files=["terminology*.json", "output/", "translation/"],
        skill_template="translation-tracker",
        priority=3
    ),
]


def get_signature_by_type(project_type: ProjectType) -> Optional[ProjectSignature]:
    """根据类型获取签名"""
    for sig in PROJECT_SIGNATURES:
        if sig.type == project_type:
            return sig
    return None
