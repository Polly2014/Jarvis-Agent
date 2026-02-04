"""
主动能力 - 博客催更
"""
import os
import re
import logging
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..memory import get_recent_episodes, set_knowledge
from ..wechat import wechat_client
from .scheduler import is_muted

logger = logging.getLogger(__name__)


# 消息模板
TEMPLATES = {
    "light": """📝 写作小提醒

距离上次更新已经 {days} 天了~
最近有什么想记录的吗？

💡 快捷回复：
• 回复「忙」→ 我3天后再提醒
• 回复任意想法 → 我帮你整理成大纲""",
    
    "strong": """📝 博客更新提醒

你已经 {days} 天没更新博客了！

上次文章：《{last_title}》({last_date})

{recent_activities}

要不要把这些整理成一篇？

💡 回复想法，我帮你起草"""
}


async def check_blog_update():
    """检查博客更新状态"""
    logger.info("🔍 开始检查博客更新状态...")
    
    # 检查是否在静默期
    if await is_muted("blog"):
        logger.info("📴 博客提醒在静默期，跳过")
        return
    
    # 扫描博客目录
    blog_path = settings.blog_content_path
    if not blog_path.exists():
        logger.warning(f"博客目录不存在: {blog_path}")
        return
    
    # 获取最新文章信息
    latest_date, latest_title = get_latest_post(blog_path)
    
    if not latest_date:
        logger.info("未找到博客文章")
        return
    
    # 更新知识库
    await set_knowledge("project", "blog.last_post_date", latest_date.isoformat())
    await set_knowledge("project", "blog.last_post_title", latest_title)
    
    # 计算天数
    days_since = (datetime.now() - latest_date).days
    logger.info(f"📊 最新文章: {latest_title}, {days_since} 天前更新")
    
    # 决定是否提醒
    if days_since <= settings.blog_reminder_threshold_days:
        logger.info(f"✅ 博客更新正常 ({days_since} 天内)")
        return
    
    # 生成并发送提醒
    await send_reminder(days_since, latest_title, latest_date)


def get_latest_post(blog_path: Path) -> tuple[datetime | None, str | None]:
    """获取最新的博客文章"""
    latest_date = None
    latest_title = None
    
    # 遍历博客目录
    for item in blog_path.iterdir():
        if not item.is_dir():
            continue
        
        # 尝试从目录名解析日期 (格式: YYYYMMDD-xxx)
        match = re.match(r"(\d{8})-", item.name)
        if not match:
            continue
        
        try:
            date = datetime.strptime(match.group(1), "%Y%m%d")
        except ValueError:
            continue
        
        # 尝试读取标题
        index_file = item / "index.md"
        title = item.name
        
        if index_file.exists():
            title = extract_title(index_file) or title
        
        if latest_date is None or date > latest_date:
            latest_date = date
            latest_title = title
    
    return latest_date, latest_title


def extract_title(md_file: Path) -> str | None:
    """从 markdown 文件提取标题"""
    try:
        content = md_file.read_text(encoding="utf-8")
        
        # 尝试从 frontmatter 提取
        match = re.search(r'title\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
        
        # 尝试从 H1 提取
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1)
        
    except Exception as e:
        logger.warning(f"读取文件失败 {md_file}: {e}")
    
    return None


async def send_reminder(days: int, last_title: str, last_date: datetime):
    """发送博客催更提醒"""
    
    # 选择模板
    template_key = "light" if days <= 7 else "strong"
    
    # 获取最近活动（如果是强提醒）
    recent_activities = ""
    if template_key == "strong":
        episodes = await get_recent_episodes(days=7, limit=5)
        if episodes:
            recent_activities = "我注意到这周你在做：\n"
            for ep in episodes:
                recent_activities += f"• {ep.summary[:30]}...\n"
    
    # 格式化消息
    message = TEMPLATES[template_key].format(
        days=days,
        last_title=last_title,
        last_date=last_date.strftime("%Y-%m-%d"),
        recent_activities=recent_activities
    )
    
    # 发送消息
    success = await wechat_client.send_text_message(message)
    
    if success:
        logger.info(f"✅ 博客催更提醒已发送 (模板: {template_key})")
    else:
        logger.error("❌ 博客催更提醒发送失败")
