"""
探索器 - 上下文提取器
"""
import re
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def extract_project_context(directory: Path) -> Dict[str, Any]:
    """
    从项目目录提取上下文信息
    
    优先读取：
    1. CLAUDE.md
    2. README.md
    3. pyproject.toml / package.json
    
    Args:
        directory: 项目目录
        
    Returns:
        提取的上下文信息
    """
    context: Dict[str, Any] = {}
    
    # 尝试读取 CLAUDE.md
    claude_md = directory / "CLAUDE.md"
    if claude_md.exists():
        context.update(parse_claude_md(claude_md))
    
    # 尝试读取 README.md
    readme_md = directory / "README.md"
    if readme_md.exists() and "description" not in context:
        context.update(parse_readme(readme_md))
    
    # 尝试读取 pyproject.toml
    pyproject = directory / "pyproject.toml"
    if pyproject.exists():
        context.update(parse_pyproject(pyproject))
    
    # 尝试读取 package.json
    package_json = directory / "package.json"
    if package_json.exists():
        context.update(parse_package_json(package_json))
    
    return context


def parse_claude_md(file_path: Path) -> Dict[str, Any]:
    """解析 CLAUDE.md 文件"""
    try:
        content = file_path.read_text(encoding="utf-8")
        context = {}
        
        # 提取标题作为名称
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            context["name"] = title_match.group(1).strip()
        
        # 提取项目概述/愿景
        overview_patterns = [
            r"##\s*项目概述\s*\n+([\s\S]*?)(?=\n##|\Z)",
            r"##\s*Project Overview\s*\n+([\s\S]*?)(?=\n##|\Z)",
            r"##\s*项目愿景\s*\n+([\s\S]*?)(?=\n##|\Z)",
        ]
        for pattern in overview_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                description = match.group(1).strip()
                # 取第一段
                first_para = description.split("\n\n")[0]
                context["description"] = first_para[:200]
                break
        
        # 提取状态（如果有）
        status_match = re.search(r"状态[：:]\s*(.+)", content)
        if status_match:
            context["status"] = status_match.group(1).strip()
        
        return context
        
    except Exception as e:
        logger.warning(f"解析 CLAUDE.md 失败: {e}")
        return {}


def parse_readme(file_path: Path) -> Dict[str, Any]:
    """解析 README.md 文件"""
    try:
        content = file_path.read_text(encoding="utf-8")
        context = {}
        
        # 提取标题
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            context["name"] = title_match.group(1).strip()
        
        # 提取第一段作为描述
        # 跳过标题和徽章
        lines = content.split("\n")
        description_lines = []
        in_description = False
        
        for line in lines:
            # 跳过标题
            if line.startswith("#"):
                if in_description:
                    break
                continue
            # 跳过徽章和空行
            if line.startswith("![") or line.startswith("[![") or not line.strip():
                if in_description:
                    break
                continue
            # 开始收集描述
            in_description = True
            description_lines.append(line)
            if len(" ".join(description_lines)) > 200:
                break
        
        if description_lines:
            context["description"] = " ".join(description_lines)[:200]
        
        return context
        
    except Exception as e:
        logger.warning(f"解析 README.md 失败: {e}")
        return {}


def parse_pyproject(file_path: Path) -> Dict[str, Any]:
    """解析 pyproject.toml 文件"""
    try:
        content = file_path.read_text(encoding="utf-8")
        context = {}
        
        # 提取 name
        name_match = re.search(r'^name\s*=\s*["\'](.+)["\']', content, re.MULTILINE)
        if name_match:
            context["package_name"] = name_match.group(1)
        
        # 提取 description
        desc_match = re.search(r'^description\s*=\s*["\'](.+)["\']', content, re.MULTILINE)
        if desc_match:
            context["description"] = desc_match.group(1)
        
        # 提取 version
        version_match = re.search(r'^version\s*=\s*["\'](.+)["\']', content, re.MULTILINE)
        if version_match:
            context["version"] = version_match.group(1)
        
        return context
        
    except Exception as e:
        logger.warning(f"解析 pyproject.toml 失败: {e}")
        return {}


def parse_package_json(file_path: Path) -> Dict[str, Any]:
    """解析 package.json 文件"""
    try:
        import json
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
        
        context = {}
        
        if "name" in data:
            context["package_name"] = data["name"]
        if "description" in data:
            context["description"] = data["description"]
        if "version" in data:
            context["version"] = data["version"]
        
        return context
        
    except Exception as e:
        logger.warning(f"解析 package.json 失败: {e}")
        return {}
