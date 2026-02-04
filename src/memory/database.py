"""
记忆系统 - 数据库操作
"""
import aiosqlite
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from ..config import settings
from .models import Episode, Knowledge, Persona, DEFAULT_PERSONA, PersonaSource


async def get_db():
    """获取数据库连接"""
    # 确保数据目录存在
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return await aiosqlite.connect(settings.database_path)


async def init_database():
    """初始化数据库表"""
    async with await get_db() as db:
        # 创建事件记忆表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                summary TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                importance INTEGER DEFAULT 3
            )
        """)
        
        # 创建知识记忆表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建人格记忆表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS persona (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                source TEXT DEFAULT 'designed'
            )
        """)
        
        await db.commit()
        
        # 初始化默认人格
        await init_default_persona()


async def init_default_persona():
    """初始化默认人格特质"""
    async with await get_db() as db:
        for key, value in DEFAULT_PERSONA.items():
            await db.execute("""
                INSERT OR IGNORE INTO persona (key, value, source)
                VALUES (?, ?, ?)
            """, (key, value, PersonaSource.DESIGNED.value))
        await db.commit()


# ==================== Episodes ====================

async def add_episode(summary: str, tags: List[str] = [], importance: int = 3) -> int:
    """添加事件记忆"""
    async with await get_db() as db:
        cursor = await db.execute("""
            INSERT INTO episodes (summary, tags, importance)
            VALUES (?, ?, ?)
        """, (summary, json.dumps(tags), importance))
        await db.commit()
        return cursor.lastrowid


async def get_recent_episodes(days: int = 7, limit: int = 50) -> List[Episode]:
    """获取最近的事件记忆"""
    since = datetime.now() - timedelta(days=days)
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM episodes
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (since.isoformat(), limit))
        rows = await cursor.fetchall()
        return [
            Episode(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                summary=row["summary"],
                tags=json.loads(row["tags"]),
                importance=row["importance"]
            )
            for row in rows
        ]


async def get_important_episodes(min_importance: int = 4, limit: int = 20) -> List[Episode]:
    """获取重要的事件记忆"""
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM episodes
            WHERE importance >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (min_importance, limit))
        rows = await cursor.fetchall()
        return [
            Episode(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                summary=row["summary"],
                tags=json.loads(row["tags"]),
                importance=row["importance"]
            )
            for row in rows
        ]


# ==================== Knowledge ====================

async def set_knowledge(category: str, key: str, value: any):
    """设置知识记忆"""
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO knowledge (category, key, value, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (category, key, json.dumps(value), datetime.now().isoformat()))
        await db.commit()


async def get_knowledge(key: str) -> Optional[any]:
    """获取知识记忆"""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT value FROM knowledge WHERE key = ?
        """, (key,))
        row = await cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None


async def get_knowledge_by_category(category: str) -> dict:
    """获取某类别的所有知识记忆"""
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT key, value FROM knowledge WHERE category = ?
        """, (category,))
        rows = await cursor.fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}


# ==================== Persona ====================

async def get_persona(key: str) -> Optional[str]:
    """获取人格特质"""
    async with await get_db() as db:
        cursor = await db.execute("""
            SELECT value FROM persona WHERE key = ?
        """, (key,))
        row = await cursor.fetchone()
        return row[0] if row else None


async def update_persona(key: str, value: str, source: str = "learned"):
    """更新人格特质"""
    async with await get_db() as db:
        await db.execute("""
            INSERT INTO persona (key, value, source)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                source = excluded.source
        """, (key, value, source))
        await db.commit()


async def get_all_persona() -> dict:
    """获取所有人格特质"""
    async with await get_db() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT key, value, source FROM persona")
        rows = await cursor.fetchall()
        return {row["key"]: {"value": row["value"], "source": row["source"]} for row in rows}
