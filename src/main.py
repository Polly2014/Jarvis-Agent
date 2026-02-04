"""
Polly Agent - FastAPI 入口
"""
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

from .config import settings
from .memory.database import init_database
from .proactive.scheduler import start_scheduler, stop_scheduler
from .wechat.handlers import router as wechat_router

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 Polly Agent 启动中...")
    
    # 初始化数据库
    await init_database()
    logger.info("✅ 数据库初始化完成")
    
    # 启动调度器
    start_scheduler()
    logger.info("✅ 调度器启动完成")
    
    logger.info(f"🤖 Polly Agent 已就绪，监听 {settings.host}:{settings.port}")
    
    yield
    
    # 关闭时
    logger.info("👋 Polly Agent 关闭中...")
    stop_scheduler()
    logger.info("✅ 调度器已停止")


app = FastAPI(
    title="Polly Agent",
    description="7×24在线的数字助手",
    version="0.1.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(wechat_router, prefix="/wechat", tags=["WeChat"])


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "agent": "Polly Agent v0.1.0"}


@app.get("/status")
async def get_status():
    """获取 Agent 状态"""
    from .memory.database import get_recent_episodes, get_knowledge
    
    episodes = await get_recent_episodes(days=7)
    blog_status = await get_knowledge("blog.last_post_date")
    
    return {
        "status": "online",
        "recent_episodes_count": len(episodes),
        "blog_last_update": blog_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
