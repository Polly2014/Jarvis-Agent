"""
记忆系统 - 轻量索引

SQLite 索引用于快速检索，内容存储在 Markdown 文件中
"""
import sqlite3
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class IndexEntry:
    """索引条目"""
    id: str
    entry_type: str           # 'daily' | 'topic' | 'discovery'
    file_path: str            # 指向 .md 文件
    date: str                 # ISO 日期
    title: str
    tags: List[str]
    importance: int
    summary: str              # 简短摘要
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class MemoryIndex:
    """
    轻量级 SQLite 索引
    
    只存元数据，不存内容。用于：
    - 按日期范围检索
    - 按标签过滤
    - 按重要性排序
    - 关键词搜索（标题和摘要）
    """
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_index (
                    id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    date TEXT NOT NULL,
                    title TEXT NOT NULL,
                    tags TEXT DEFAULT '[]',
                    importance INTEGER DEFAULT 3,
                    summary TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_date ON memory_index(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memory_index(entry_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memory_index(importance)")
            
            # 创建全文搜索虚拟表 (FTS5)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    id,
                    title,
                    summary,
                    tags,
                    content='memory_index',
                    content_rowid='rowid'
                )
            """)
            
            # 创建触发器保持 FTS 同步
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory_index BEGIN
                    INSERT INTO memory_fts(rowid, id, title, summary, tags)
                    VALUES (new.rowid, new.id, new.title, new.summary, new.tags);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory_index BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, id, title, summary, tags)
                    VALUES ('delete', old.rowid, old.id, old.title, old.summary, old.tags);
                END
            """)
            
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory_index BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, id, title, summary, tags)
                    VALUES ('delete', old.rowid, old.id, old.title, old.summary, old.tags);
                    INSERT INTO memory_fts(rowid, id, title, summary, tags)
                    VALUES (new.rowid, new.id, new.title, new.summary, new.tags);
                END
            """)
            
            conn.commit()
    
    # ==================== 写入 ====================
    
    def add(self, entry: IndexEntry) -> str:
        """添加索引条目"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_index 
                (id, entry_type, file_path, date, title, tags, importance, summary, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.entry_type,
                entry.file_path,
                entry.date,
                entry.title,
                json.dumps(entry.tags),
                entry.importance,
                entry.summary,
                entry.created_at.isoformat()
            ))
            conn.commit()
        return entry.id
    
    def delete(self, entry_id: str):
        """删除索引条目"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory_index WHERE id = ?", (entry_id,))
            conn.commit()
    
    # ==================== 查询 ====================
    
    def search(
        self,
        query: str = None,
        entry_type: str = None,
        date_from: date = None,
        date_to: date = None,
        min_importance: int = None,
        tags: List[str] = None,
        limit: int = 50
    ) -> List[IndexEntry]:
        """
        综合搜索
        
        Args:
            query: 全文搜索关键词
            entry_type: 条目类型过滤
            date_from: 开始日期
            date_to: 结束日期
            min_importance: 最小重要性
            tags: 标签过滤（任一匹配）
            limit: 返回数量限制
        """
        conditions = []
        params = []
        
        # 全文搜索
        if query:
            # 使用 FTS5 搜索，添加 * 通配符支持前缀匹配
            # 将每个词后面加上 * 以支持部分匹配
            fts_query = " ".join(f"{word}*" for word in query.split())
            conditions.append("""
                id IN (SELECT id FROM memory_fts WHERE memory_fts MATCH ?)
            """)
            params.append(fts_query)
        
        # 类型过滤
        if entry_type:
            conditions.append("entry_type = ?")
            params.append(entry_type)
        
        # 日期范围
        if date_from:
            conditions.append("date >= ?")
            params.append(date_from.isoformat())
        if date_to:
            conditions.append("date <= ?")
            params.append(date_to.isoformat())
        
        # 重要性过滤
        if min_importance:
            conditions.append("importance >= ?")
            params.append(min_importance)
        
        # 标签过滤（JSON 数组搜索）
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            conditions.append(f"({' OR '.join(tag_conditions)})")
        
        # 构建查询
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"""
                SELECT * FROM memory_index
                WHERE {where_clause}
                ORDER BY date DESC, importance DESC
                LIMIT ?
            """, params + [limit])
            
            rows = cursor.fetchall()
        
        return [self._row_to_entry(row) for row in rows]
    
    def get_by_date(self, d: date) -> List[IndexEntry]:
        """获取指定日期的所有条目"""
        return self.search(date_from=d, date_to=d)
    
    def get_recent(self, days: int = 7, limit: int = 50) -> List[IndexEntry]:
        """获取最近 N 天的条目"""
        from datetime import timedelta
        date_from = date.today() - timedelta(days=days)
        return self.search(date_from=date_from, limit=limit)
    
    def get_important(self, min_importance: int = 4, limit: int = 20) -> List[IndexEntry]:
        """获取重要条目"""
        return self.search(min_importance=min_importance, limit=limit)
    
    def recall(self, keyword: str, limit: int = 20) -> List[IndexEntry]:
        """
        回忆：根据关键词搜索记忆
        
        这是给用户用的主要接口
        """
        return self.search(query=keyword, limit=limit)
    
    def _row_to_entry(self, row: sqlite3.Row) -> IndexEntry:
        """将数据库行转换为 IndexEntry"""
        return IndexEntry(
            id=row["id"],
            entry_type=row["entry_type"],
            file_path=row["file_path"],
            date=row["date"],
            title=row["title"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            importance=row["importance"],
            summary=row["summary"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None
        )
    
    # ==================== 统计 ====================
    
    def count(self, entry_type: str = None) -> int:
        """统计条目数量"""
        with sqlite3.connect(self.db_path) as conn:
            if entry_type:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM memory_index WHERE entry_type = ?",
                    (entry_type,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM memory_index")
            return cursor.fetchone()[0]
    
    def get_all_tags(self) -> List[str]:
        """获取所有使用过的标签"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT DISTINCT tags FROM memory_index")
            all_tags = set()
            for row in cursor.fetchall():
                if row[0]:
                    tags = json.loads(row[0])
                    all_tags.update(tags)
            return sorted(all_tags)
