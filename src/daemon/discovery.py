"""
Discovery 数据模型

💡 LLM 智能发现的结构化表示
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json
import uuid


class DiscoveryType(Enum):
    """发现类型"""
    FILE_INSIGHT = "file_insight"       # 文件变化洞察
    PROJECT_UPDATE = "project_update"   # 项目状态更新
    REMINDER = "reminder"               # 提醒
    SELF_REFLECT = "self_reflect"       # 自省思考
    SUGGESTION = "suggestion"           # 建议


@dataclass
class Discovery:
    """
    智能发现
    
    由 LLM 分析生成，而非规则触发
    """
    title: str
    content: str
    importance: int  # 1-5
    type: DiscoveryType = DiscoveryType.FILE_INSIGHT
    id: str = field(default_factory=lambda: f"d-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6]}")
    timestamp: datetime = field(default_factory=datetime.now)
    source_files: list[str] = field(default_factory=list)
    suggested_action: Optional[str] = None
    acknowledged: bool = False
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "title": self.title,
            "content": self.content,
            "importance": self.importance,
            "source_files": self.source_files,
            "suggested_action": self.suggested_action,
            "acknowledged": self.acknowledged
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Discovery":
        """从字典创建"""
        return cls(
            id=data.get("id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            type=DiscoveryType(data.get("type", "file_insight")),
            title=data["title"],
            content=data["content"],
            importance=data.get("importance", 3),
            source_files=data.get("source_files", []),
            suggested_action=data.get("suggested_action"),
            acknowledged=data.get("acknowledged", False)
        )
    
    def __str__(self) -> str:
        importance_emoji = "⭐" * self.importance
        return f"[{self.type.value}] {self.title} {importance_emoji}\n{self.content}"


class DiscoveryStore:
    """
    发现存储
    
    持久化保存到 ~/.jarvis/discoveries.json
    """
    
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._discoveries: list[Discovery] = []
        self._load()
    
    def _load(self):
        """加载已有发现"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._discoveries = [
                    Discovery.from_dict(d) for d in data.get("discoveries", [])
                ]
        except FileNotFoundError:
            self._discoveries = []
        except json.JSONDecodeError:
            self._discoveries = []
    
    def _save(self):
        """保存发现"""
        import os
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(
                {"discoveries": [d.to_dict() for d in self._discoveries]},
                f,
                ensure_ascii=False,
                indent=2
            )
    
    def add(self, discovery: Discovery):
        """添加新发现"""
        self._discoveries.insert(0, discovery)  # 最新的在前面
        # 只保留最近 100 条
        if len(self._discoveries) > 100:
            self._discoveries = self._discoveries[:100]
        self._save()
    
    def get_recent(self, count: int = 10) -> list[Discovery]:
        """获取最近的发现"""
        return self._discoveries[:count]
    
    def get_today(self) -> list[Discovery]:
        """获取今日发现"""
        today = datetime.now().date()
        return [d for d in self._discoveries if d.timestamp.date() == today]
    
    def get_unacknowledged(self) -> list[Discovery]:
        """获取未确认的发现"""
        return [d for d in self._discoveries if not d.acknowledged]
    
    def acknowledge(self, discovery_id: str):
        """确认发现"""
        for d in self._discoveries:
            if d.id == discovery_id:
                d.acknowledged = True
                self._save()
                break
    
    def acknowledge_all(self):
        """确认所有发现"""
        for d in self._discoveries:
            d.acknowledged = True
        self._save()
