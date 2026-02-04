"""
Polly Agent 配置管理
"""
from pydantic_settings import BaseSettings
from typing import Literal
from pathlib import Path


class Settings(BaseSettings):
    """应用配置"""
    
    # LLM 配置
    claude_api_key: str = ""
    deepseek_api_key: str = ""
    default_llm: Literal["claude", "deepseek"] = "deepseek"
    
    # 企业微信配置
    wechat_corp_id: str = ""
    wechat_agent_id: str = ""
    wechat_secret: str = ""
    wechat_token: str = ""
    wechat_aes_key: str = ""
    wechat_user_id: str = "PollyWang"
    
    # 博客配置
    blog_content_path: Path = Path("../content/blog")
    blog_reminder_threshold_days: int = 3
    blog_reminder_cron_hour: int = 10
    
    # 数据库配置
    database_path: Path = Path("./data/memory.db")
    
    # 服务配置
    host: str = "0.0.0.0"
    port: int = 50207
    debug: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
