"""
Skill 注册表与生命周期管理

Phase 4.2: 管理所有 Skill 的发现、加载、启用/禁用、匹配

Skill 存储结构:
~/.jarvis/skills/{name}/
├── SKILL.md          # Skill 定义（YAML frontmatter + Markdown instructions）
└── scripts/          # 可选脚本

SKILL.md frontmatter:
---
name: skill-name
description: 一句话描述
trigger_keywords: ["关键词1", "关键词2"]
enabled: true
version: 1
source: auto | manual | builtin
created_at: 2026-02-08T12:00:00
used_count: 0
---
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class SkillInfo:
    """Skill 完整信息"""

    name: str = ""
    path: Path = field(default_factory=Path)
    description: str = ""
    trigger_keywords: list[str] = field(default_factory=list)
    instructions: str = ""  # SKILL.md 正文
    enabled: bool = True
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    used_count: int = 0
    last_used: Optional[datetime] = None
    source: str = "auto"  # "auto" | "manual" | "builtin"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "description": self.description,
            "trigger_keywords": self.trigger_keywords,
            "enabled": self.enabled,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "used_count": self.used_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "source": self.source,
        }


class SkillRegistry:
    """
    Skill 注册表

    负责:
    1. 从 ~/.jarvis/skills/ 发现并加载 Skill
    2. 按关键词/语义匹配用户输入
    3. 管理 Skill 生命周期（启用/禁用/删除）
    4. 使用统计跟踪
    """

    def __init__(self, jarvis_home: Path):
        self._home = jarvis_home
        self._skills_dir = jarvis_home / "skills"
        self._skills_dir.mkdir(parents=True, exist_ok=True)

        # 缓存
        self._skills: dict[str, SkillInfo] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """延迟加载 — 首次访问时扫描"""
        if not self._loaded:
            self.refresh()
            self._loaded = True

    def refresh(self) -> None:
        """重新扫描 skills 目录"""
        self._skills.clear()
        if not self._skills_dir.exists():
            return

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                info = self._parse_skill_md(skill_md)
                if info:
                    self._skills[info.name] = info

    # ── 读取接口 ──────────────────────────────────────────

    def list_skills(self, include_disabled: bool = False) -> list[SkillInfo]:
        """列出所有 Skill"""
        self._ensure_loaded()
        if include_disabled:
            return list(self._skills.values())
        return [s for s in self._skills.values() if s.enabled]

    def get_skill(self, name: str) -> Optional[SkillInfo]:
        """根据名称获取 Skill"""
        self._ensure_loaded()
        return self._skills.get(name)

    def get_for_context(self, user_input: str) -> Optional[SkillInfo]:
        """根据用户输入匹配最佳 Skill（关键词匹配版）"""
        self._ensure_loaded()
        user_lower = user_input.lower()

        best_match: Optional[SkillInfo] = None
        best_score = 0

        for skill in self._skills.values():
            if not skill.enabled:
                continue

            score = 0
            for keyword in skill.trigger_keywords:
                if keyword.lower() in user_lower:
                    # 更长的关键词匹配权重更高
                    score += len(keyword)

            if score > best_score:
                best_score = score
                best_match = skill

        return best_match

    async def get_for_context_llm(self, user_input: str, llm_call) -> Optional[SkillInfo]:
        """根据用户输入 + LLM 语义匹配 Skill"""
        self._ensure_loaded()

        # 先关键词匹配
        keyword_match = self.get_for_context(user_input)
        if keyword_match:
            return keyword_match

        # 关键词无匹配，用 LLM 语义判断
        skills = self.list_skills()
        if not skills:
            return None

        skill_list = "\n".join(
            f"- {s.name}: {s.description} (关键词: {', '.join(s.trigger_keywords)})"
            for s in skills
        )

        prompt = f"""用户说: "{user_input}"

可用 Skill:
{skill_list}

这个用户输入最匹配哪个 Skill？如果都不匹配返回 "none"。
只返回 Skill 名称或 "none"。"""

        try:
            result = (await llm_call(prompt)).strip().lower()
            if result != "none":
                return self._skills.get(result)
        except Exception:
            pass

        return None

    # ── 写入接口 ──────────────────────────────────────────

    def enable(self, name: str) -> bool:
        """启用 Skill"""
        return self._update_enabled(name, True)

    def disable(self, name: str) -> bool:
        """禁用 Skill"""
        return self._update_enabled(name, False)

    def _update_enabled(self, name: str, enabled: bool) -> bool:
        """更新 Skill 的 enabled 状态"""
        self._ensure_loaded()
        skill = self._skills.get(name)
        if not skill:
            return False

        skill.enabled = enabled
        self._update_frontmatter(skill.path / "SKILL.md", {"enabled": enabled})
        return True

    def delete(self, name: str) -> bool:
        """删除 Skill（移到 .trash）"""
        self._ensure_loaded()
        skill = self._skills.get(name)
        if not skill:
            return False

        import shutil
        trash_dir = self._home / ".trash" / "skills"
        trash_dir.mkdir(parents=True, exist_ok=True)

        dest = trash_dir / f"{name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.move(str(skill.path), str(dest))

        del self._skills[name]
        return True

    def record_usage(self, name: str) -> None:
        """记录 Skill 使用"""
        self._ensure_loaded()
        skill = self._skills.get(name)
        if not skill:
            return

        skill.used_count += 1
        skill.last_used = datetime.now()
        self._update_frontmatter(
            skill.path / "SKILL.md",
            {"used_count": skill.used_count, "last_used": skill.last_used.isoformat()},
        )

    # ── 解析 SKILL.md ────────────────────────────────────

    def _parse_skill_md(self, path: Path) -> Optional[SkillInfo]:
        """解析 SKILL.md 文件"""
        try:
            content = path.read_text(encoding="utf-8")
        except IOError:
            return None

        # 提取 YAML frontmatter
        frontmatter, body = self._split_frontmatter(content)
        if not frontmatter:
            return None

        # 解析 trigger_keywords
        keywords = frontmatter.get("trigger_keywords", [])
        if isinstance(keywords, str):
            # 兼容 YAML 列表的字符串形式
            try:
                keywords = json.loads(keywords)
            except json.JSONDecodeError:
                keywords = [k.strip() for k in keywords.split(",")]

        # 解析时间
        created_at = frontmatter.get("created_at", "")
        if isinstance(created_at, str) and created_at:
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                created_at = datetime.now()
        else:
            created_at = datetime.now()

        last_used = frontmatter.get("last_used")
        if isinstance(last_used, str) and last_used:
            try:
                last_used = datetime.fromisoformat(last_used)
            except ValueError:
                last_used = None

        return SkillInfo(
            name=frontmatter.get("name", path.parent.name),
            path=path.parent,
            description=frontmatter.get("description", ""),
            trigger_keywords=keywords,
            instructions=body.strip(),
            enabled=frontmatter.get("enabled", True),
            version=frontmatter.get("version", 1),
            created_at=created_at,
            used_count=frontmatter.get("used_count", 0),
            last_used=last_used,
            source=frontmatter.get("source", "auto"),
        )

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[Optional[dict], str]:
        """
        分割 YAML frontmatter 和 Markdown 正文

        使用简单的正则解析（避免依赖 PyYAML）
        """
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            return None, content

        yaml_str = match.group(1)
        body = match.group(2)

        # 简单 YAML 解析（只处理 key: value 和 key: [list]）
        frontmatter = {}
        for line in yaml_str.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ": " in line:
                key, value = line.split(": ", 1)
                key = key.strip()
                value = value.strip()

                # 解析值类型
                if value.lower() in ("true", "yes"):
                    frontmatter[key] = True
                elif value.lower() in ("false", "no"):
                    frontmatter[key] = False
                elif value.isdigit():
                    frontmatter[key] = int(value)
                elif value.startswith("[") and value.endswith("]"):
                    # JSON 数组
                    try:
                        frontmatter[key] = json.loads(value)
                    except json.JSONDecodeError:
                        frontmatter[key] = value
                elif value.startswith('"') and value.endswith('"'):
                    frontmatter[key] = value[1:-1]
                elif value == "null" or value == "~":
                    frontmatter[key] = None
                else:
                    frontmatter[key] = value

        return frontmatter, body

    @staticmethod
    def _update_frontmatter(path: Path, updates: dict) -> None:
        """更新 SKILL.md 的 frontmatter 字段"""
        try:
            content = path.read_text(encoding="utf-8")
        except IOError:
            return

        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)
        if not match:
            return

        yaml_str = match.group(1)
        body = match.group(2)

        # 更新或添加字段
        lines = yaml_str.split("\n")
        updated_keys = set()

        for i, line in enumerate(lines):
            if ": " in line:
                key = line.split(": ", 1)[0].strip()
                if key in updates:
                    value = updates[key]
                    if isinstance(value, bool):
                        lines[i] = f"{key}: {str(value).lower()}"
                    elif isinstance(value, list):
                        lines[i] = f"{key}: {json.dumps(value, ensure_ascii=False)}"
                    elif value is None:
                        lines[i] = f"{key}: null"
                    else:
                        lines[i] = f"{key}: {value}"
                    updated_keys.add(key)

        # 添加新字段
        for key, value in updates.items():
            if key not in updated_keys:
                if isinstance(value, bool):
                    lines.append(f"{key}: {str(value).lower()}")
                elif isinstance(value, list):
                    lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
                elif value is None:
                    lines.append(f"{key}: null")
                else:
                    lines.append(f"{key}: {value}")

        new_content = f"---\n{chr(10).join(lines)}\n---\n{body}"
        path.write_text(new_content, encoding="utf-8")
