"""
记忆系统模块

Phase 2: 混合存储架构
- Markdown: 存储内容（LLM 友好、人类可读）
- SQLite: 轻量索引（快速检索）
"""
from .database import (
    init_database,
    add_episode,
    get_recent_episodes,
    get_important_episodes,
    set_knowledge,
    get_knowledge,
    get_knowledge_by_category,
    get_persona,
    update_persona,
    get_all_persona,
)
from .models import Episode, Knowledge, Persona, MemoryCategory, PersonaSource
from .writer import MemoryWriter, MemoryEntry
from .index import MemoryIndex, IndexEntry

__all__ = [
    # Legacy SQLite (保持兼容)
    "init_database",
    "add_episode",
    "get_recent_episodes",
    "get_important_episodes",
    "set_knowledge",
    "get_knowledge",
    "get_knowledge_by_category",
    "get_persona",
    "update_persona",
    "get_all_persona",
    "Episode",
    "Knowledge",
    "Persona",
    "MemoryCategory",
    "PersonaSource",
    # Phase 2: Markdown + Index
    "MemoryWriter",
    "MemoryEntry",
    "MemoryIndex",
    "IndexEntry",
]
