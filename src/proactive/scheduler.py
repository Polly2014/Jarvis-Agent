"""
主动能力 - 任务调度器
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime, timedelta
from typing import Optional

from ..config import settings
from ..memory import get_knowledge, set_knowledge

logger = logging.getLogger(__name__)

# 全局调度器
scheduler = AsyncIOScheduler()

# 静默状态存储
_mute_until: dict[str, datetime] = {}


def start_scheduler():
    """启动调度器"""
    from .blog_reminder import check_blog_update
    
    # 添加博客催更任务
    scheduler.add_job(
        check_blog_update,
        trigger=CronTrigger(hour=settings.blog_reminder_cron_hour, minute=0),
        id="blog_reminder",
        name="博客催更检查",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("📅 调度器已启动，已注册任务:")
    for job in scheduler.get_jobs():
        logger.info(f"  - {job.name} ({job.id})")


def stop_scheduler():
    """停止调度器"""
    scheduler.shutdown()


async def mute_reminder(reminder_type: str, days: int = 3):
    """静默某类提醒"""
    until = datetime.now() + timedelta(days=days)
    _mute_until[reminder_type] = until
    
    # 同时持久化到数据库
    await set_knowledge(
        "system", 
        f"mute.{reminder_type}", 
        until.isoformat()
    )
    
    logger.info(f"🔇 {reminder_type} 提醒已静默至 {until}")


async def is_muted(reminder_type: str) -> bool:
    """检查是否在静默期"""
    # 先检查内存缓存
    if reminder_type in _mute_until:
        if datetime.now() < _mute_until[reminder_type]:
            return True
        else:
            del _mute_until[reminder_type]
    
    # 检查数据库
    mute_until_str = await get_knowledge(f"mute.{reminder_type}")
    if mute_until_str:
        mute_until = datetime.fromisoformat(mute_until_str)
        if datetime.now() < mute_until:
            _mute_until[reminder_type] = mute_until
            return True
    
    return False
