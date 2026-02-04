"""
探索器 - 目录扫描器
"""
import re
from pathlib import Path
from typing import List, Optional, Tuple
import logging

from .signatures import PROJECT_SIGNATURES, ProjectSignature, ProjectType
from .context_extractor import extract_project_context

logger = logging.getLogger(__name__)


# 延迟导入以避免循环引用
def _create_project_meta(**kwargs):
    from .models import ProjectMeta
    return ProjectMeta(**kwargs)


def scan_directory(
    root_path: Path,
    max_depth: int = 2,
    ignore_patterns: List[str] = None
) -> List:
    """
    扫描目录，识别项目
    
    Args:
        root_path: 根目录路径
        max_depth: 最大扫描深度
        ignore_patterns: 忽略的目录模式
        
    Returns:
        识别到的项目列表
    """
    from .models import ProjectMeta
    
    if ignore_patterns is None:
        ignore_patterns = [
            "node_modules", "__pycache__", ".git", ".venv", 
            "venv", "dist", "build", ".cache", "public"
        ]
    
    projects: List = []
    visited: set = set()
    
    def should_ignore(path: Path) -> bool:
        return any(pattern in path.parts for pattern in ignore_patterns)
    
    def scan_recursive(current_path: Path, depth: int):
        if depth > max_depth:
            return
        
        if not current_path.is_dir() or should_ignore(current_path):
            return
        
        # 检查当前目录是否匹配某个项目类型
        project = identify_project(current_path)
        
        if project and current_path not in visited:
            visited.add(current_path)
            projects.append(project)
            # 找到项目后不再向下扫描
            return
        
        # 继续扫描子目录
        try:
            for child in current_path.iterdir():
                if child.is_dir():
                    scan_recursive(child, depth + 1)
        except PermissionError:
            pass
    
    scan_recursive(root_path, 0)
    
    # 按置信度排序
    projects.sort(key=lambda p: p.confidence, reverse=True)
    
    return projects


def identify_project(directory: Path):
    """
    识别目录的项目类型
    
    Args:
        directory: 目录路径
        
    Returns:
        项目元数据，如果无法识别则返回 None
    """
    from .models import ProjectMeta
    
    best_match: Optional[Tuple[ProjectSignature, float]] = None
    
    for signature in PROJECT_SIGNATURES:
        confidence = match_signature(directory, signature)
        
        if confidence > 0:
            if best_match is None or (
                confidence > best_match[1] or 
                (confidence == best_match[1] and signature.priority > best_match[0].priority)
            ):
                best_match = (signature, confidence)
    
    if best_match is None:
        return None
    
    signature, confidence = best_match
    
    # 提取项目上下文
    context = extract_project_context(directory)
    
    # 生成项目名称
    name = context.get("name") or directory.name
    
    # 生成状态描述
    status = generate_status(directory, signature, context)
    
    return ProjectMeta(
        name=name,
        path=directory,
        type=signature.type,
        description=signature.description,
        status=status,
        confidence=confidence,
        context=context,
        suggested_skill=signature.skill_template
    )


def match_signature(directory: Path, signature: ProjectSignature) -> float:
    """
    计算目录与签名的匹配度
    
    Args:
        directory: 目录路径
        signature: 项目签名
        
    Returns:
        匹配置信度 (0.0-1.0)
    """
    required_count = len(signature.required_files)
    matched_required = 0
    
    for pattern in signature.required_files:
        if pattern.endswith("/"):
            # 目录模式
            if (directory / pattern.rstrip("/")).is_dir():
                matched_required += 1
        elif "*" in pattern:
            # 通配符模式
            if list(directory.glob(pattern)):
                matched_required += 1
        else:
            # 精确文件匹配
            if (directory / pattern).exists():
                matched_required += 1
    
    # 必须匹配所有必需文件
    if matched_required < required_count:
        return 0.0
    
    # 基础置信度
    confidence = 0.6
    
    # 检查可选文件
    optional_matches = 0
    for pattern in signature.optional_files:
        if pattern.endswith("/"):
            if (directory / pattern.rstrip("/")).is_dir():
                optional_matches += 1
        elif "*" in pattern:
            if list(directory.glob(pattern)):
                optional_matches += 1
        else:
            if (directory / pattern).exists():
                optional_matches += 1
    
    if signature.optional_files:
        confidence += 0.2 * (optional_matches / len(signature.optional_files))
    
    # 检查文件内容模式
    for filename, pattern in signature.pattern_in_file.items():
        file_path = directory / filename
        if file_path.exists():
            try:
                content = file_path.read_text(encoding="utf-8")
                if pattern in content:
                    confidence += 0.2
            except Exception:
                pass
    
    return min(confidence, 1.0)


def generate_status(
    directory: Path, 
    signature: ProjectSignature, 
    context: dict
) -> str:
    """生成项目状态描述"""
    
    if signature.type == ProjectType.ZOLA_BLOG:
        # 查找最新博客文章
        blog_dir = directory / "content" / "blog"
        if blog_dir.exists():
            posts = sorted(
                [d for d in blog_dir.iterdir() if d.is_dir()],
                key=lambda x: x.name,
                reverse=True
            )
            if posts:
                latest = posts[0].name
                match = re.match(r"(\d{8})", latest)
                if match:
                    date_str = match.group(1)
                    return f"上次更新: {date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    elif signature.type == ProjectType.ACADEMIC_PAPER:
        status = context.get("status", "")
        if status:
            return status
        return "论文项目"
    
    elif signature.type == ProjectType.MCP_SERVER:
        # 统计工具数量
        server_file = directory / "src" / "server.py"
        if server_file.exists():
            try:
                content = server_file.read_text(encoding="utf-8")
                tool_count = content.count("@mcp.tool")
                if tool_count:
                    return f"{tool_count} 个工具"
            except Exception:
                pass
    
    return context.get("status", "")
