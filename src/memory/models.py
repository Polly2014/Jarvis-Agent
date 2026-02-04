"""
记忆系统 - 数据模型
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class MemoryCategory(str, Enum):
    """知识记忆分类"""
    PROJECT = "project"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"


class PersonaSource(str, Enum):
    """人格记忆来源"""
    DESIGNED = "designed"  # 人工设计
    LEARNED = "learned"    # 从交互中学习


class Episode(BaseModel):
    """事件记忆"""
    id: Optional[int] = None
    timestamp: datetime = datetime.now()
    summary: str
    tags: List[str] = []
    importance: int = 3  # 1-5，5最重要
    
    class Config:
        from_attributes = True


class Knowledge(BaseModel):
    """知识记忆"""
    id: Optional[int] = None
    category: MemoryCategory
    key: str
    value: str  # JSON 字符串
    updated_at: datetime = datetime.now()
    
    class Config:
        from_attributes = True


class Persona(BaseModel):
    """人格记忆"""
    key: str
    value: str
    source: PersonaSource = PersonaSource.DESIGNED
    
    class Config:
        from_attributes = True


# 预设的人格特质
DEFAULT_PERSONA = {
    "style.emoji_usage": "moderate",  # low | moderate | high
    "style.formality": "casual",      # formal | casual | playful
    "style.verbosity": "concise",     # concise | detailed | verbose
    "value.honesty": "always admit when unsure",
    "value.privacy": "never reveal user's private info",
    "redline.harmful_content": "refuse harmful, illegal, or unethical requests",
}
