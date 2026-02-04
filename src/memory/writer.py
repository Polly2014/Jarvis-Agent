"""
记忆系统 - Markdown 写入器

LLM-native 的记忆存储：
- 📅 daily/ 编年体日志
- 📂 topics/ 纪传体主题
- 🎭 persona.md 人格定义
"""
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class MemoryEntry:
    """记忆条目"""
    timestamp: datetime
    title: str
    content: str
    importance: int = 3  # 1-5
    tags: List[str] = None
    entry_type: str = "discovery"  # discovery, dialogue, decision, milestone
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryWriter:
    """
    Markdown 记忆写入器
    
    目录结构：
    ~/.jarvis/memory/
    ├── daily/           # 编年体
    │   └── 2026-02-05.md
    ├── topics/          # 纪传体
    │   └── project-jarvis.md
    └── persona.md       # 人格
    """
    
    def __init__(self, memory_root: Path):
        self.memory_root = memory_root
        self.daily_dir = memory_root / "daily"
        self.topics_dir = memory_root / "topics"
        self.persona_path = memory_root / "persona.md"
        
        # 确保目录存在
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保目录结构存在"""
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.topics_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== Daily (编年体) ====================
    
    def get_daily_path(self, d: date = None) -> Path:
        """获取日志文件路径"""
        if d is None:
            d = date.today()
        return self.daily_dir / f"{d.isoformat()}.md"
    
    def append_to_daily(self, entry: MemoryEntry) -> Path:
        """
        追加条目到当日日志
        
        格式：
        ## 发现
        - 10:23 ⭐⭐⭐ 标题
          内容...
        """
        daily_path = self.get_daily_path(entry.timestamp.date())
        
        # 如果文件不存在，创建带标题的新文件
        if not daily_path.exists():
            self._create_daily_file(daily_path, entry.timestamp.date())
        
        # 格式化条目
        time_str = entry.timestamp.strftime("%H:%M")
        stars = "⭐" * min(entry.importance, 5)
        tags_str = " ".join(f"`{t}`" for t in entry.tags) if entry.tags else ""
        
        # 构建条目文本
        entry_text = f"- {time_str} {stars} **{entry.title}**"
        if tags_str:
            entry_text += f" {tags_str}"
        entry_text += "\n"
        if entry.content:
            # 缩进内容
            indented = "\n".join(f"  {line}" for line in entry.content.split("\n"))
            entry_text += f"{indented}\n"
        entry_text += "\n"
        
        # 追加到对应 section
        self._append_to_section(daily_path, entry.entry_type, entry_text)
        
        return daily_path
    
    def _create_daily_file(self, path: Path, d: date):
        """创建新的日志文件"""
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        weekday = weekday_names[d.weekday()]
        
        template = f"""# {d.isoformat()} {weekday}

## 发现

## 对话

## 决策

## 里程碑

"""
        path.write_text(template, encoding="utf-8")
    
    def _append_to_section(self, path: Path, entry_type: str, text: str):
        """追加内容到指定 section"""
        section_map = {
            "discovery": "## 发现",
            "dialogue": "## 对话",
            "decision": "## 决策",
            "milestone": "## 里程碑",
        }
        section_header = section_map.get(entry_type, "## 发现")
        
        content = path.read_text(encoding="utf-8")
        
        # 找到 section 位置，在其后追加
        lines = content.split("\n")
        insert_idx = None
        
        for i, line in enumerate(lines):
            if line.strip() == section_header:
                insert_idx = i + 1
                # 跳过空行
                while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                    insert_idx += 1
                break
        
        if insert_idx is not None:
            # 在 section 后插入
            lines.insert(insert_idx, text)
            path.write_text("\n".join(lines), encoding="utf-8")
        else:
            # section 不存在，追加到文件末尾
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n{section_header}\n\n{text}")
    
    def read_daily(self, d: date = None) -> Optional[str]:
        """读取当日日志"""
        path = self.get_daily_path(d)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None
    
    def read_recent_dailies(self, days: int = 7) -> List[tuple[date, str]]:
        """读取最近 N 天的日志"""
        result = []
        today = date.today()
        
        for i in range(days):
            d = date.fromordinal(today.toordinal() - i)
            content = self.read_daily(d)
            if content:
                result.append((d, content))
        
        return result
    
    # ==================== Topics (纪传体) ====================
    
    def get_topic_path(self, topic_name: str) -> Path:
        """获取主题文件路径"""
        # 规范化文件名
        safe_name = topic_name.lower().replace(" ", "-").replace("/", "-")
        return self.topics_dir / f"{safe_name}.md"
    
    def update_topic(self, topic_name: str, section: str, content: str):
        """
        更新主题文件的指定 section
        
        Args:
            topic_name: 主题名称 (如 "project-jarvis")
            section: section 标题 (如 "里程碑")
            content: 要追加的内容
        """
        path = self.get_topic_path(topic_name)
        
        if not path.exists():
            self._create_topic_file(path, topic_name)
        
        self._append_to_section(path, section.lower(), content)
    
    def _create_topic_file(self, path: Path, topic_name: str):
        """创建新的主题文件"""
        template = f"""# {topic_name}

## 基本信息

- 创建时间: {datetime.now().isoformat()}

## 里程碑

## 待办

## 笔记

"""
        path.write_text(template, encoding="utf-8")
    
    def read_topic(self, topic_name: str) -> Optional[str]:
        """读取主题文件"""
        path = self.get_topic_path(topic_name)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return None
    
    def list_topics(self) -> List[str]:
        """列出所有主题"""
        return [p.stem for p in self.topics_dir.glob("*.md")]
    
    # ==================== Persona (人格) ====================
    
    def read_persona(self) -> Optional[str]:
        """读取人格定义"""
        if self.persona_path.exists():
            return self.persona_path.read_text(encoding="utf-8")
        return None
    
    def init_persona(self, traits: dict):
        """初始化人格定义"""
        if self.persona_path.exists():
            return  # 已存在则不覆盖
        
        template = f"""# 🎭 Jarvis Persona

> 定义 Jarvis 的人格特质

## 骨架（设计）

这些是核心价值观，不会改变：

- **名字**: {traits.get('name', 'Jarvis')}
- **角色**: {traits.get('role', 'AI 助手')}
- **风格**: {traits.get('style', 'helpful, friendly, slightly playful')}
- **底线**: 诚实、不泄露隐私、承认不知道

## 肌肉（涌现）

这些从交互中学习，会逐渐生长：

### 用户偏好

（自动记录）

### 沟通习惯

（自动记录）

### 领域知识

（自动记录）

---

*最后更新: {datetime.now().isoformat()}*
"""
        self.persona_path.write_text(template, encoding="utf-8")
    
    def append_to_persona(self, section: str, content: str):
        """追加内容到人格文件的指定 section"""
        if not self.persona_path.exists():
            self.init_persona({})
        
        # 简单追加到文件末尾（可以优化为精确插入）
        with open(self.persona_path, "a", encoding="utf-8") as f:
            f.write(f"\n### {section}\n\n{content}\n")
