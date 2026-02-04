"""
企业微信消息处理
"""
from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
import logging
import hashlib

from ..config import settings
from ..llm.client import get_llm_response
from ..memory import add_episode

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_signature(signature: str, timestamp: str, nonce: str) -> bool:
    """验证企业微信回调签名"""
    params = sorted([settings.wechat_token, timestamp, nonce])
    check_str = "".join(params)
    check_signature = hashlib.sha1(check_str.encode()).hexdigest()
    return check_signature == signature


@router.get("/callback")
async def verify_callback(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """企业微信回调验证"""
    # TODO: 实现完整的加密验证
    # 这里简化处理，实际需要使用 WXBizMsgCrypt
    logger.info("收到企业微信回调验证请求")
    return PlainTextResponse(echostr)


@router.post("/callback")
async def handle_message(request: Request):
    """处理企业微信消息"""
    # TODO: 实现完整的消息解密和处理
    # 这里是简化的框架代码
    
    body = await request.body()
    logger.info(f"收到企业微信消息: {body[:200]}")
    
    # 解析消息（需要解密）
    # message = decrypt_message(body)
    
    # 处理不同类型的消息
    # if message.type == "text":
    #     response = await handle_text_message(message.content)
    #     return response
    
    return PlainTextResponse("success")


async def handle_text_message(content: str, from_user: str) -> str:
    """处理文本消息"""
    logger.info(f"处理文本消息: {content}")
    
    # 快捷命令处理
    if content == "状态":
        return await get_status_summary()
    
    if content == "最近":
        return await get_recent_summary()
    
    if content.startswith("记住"):
        memory_content = content[2:].strip()
        await add_episode(
            summary=f"用户要求记住: {memory_content}",
            tags=["user_request", "memory"],
            importance=5
        )
        return f"✅ 已记住: {memory_content}"
    
    if content == "忙":
        from ..proactive.scheduler import mute_reminder
        await mute_reminder("blog", days=3)
        return "好的，我 3 天内不会再提醒博客更新了 👍"
    
    # 通用对话：调用 LLM
    response = await get_llm_response(content)
    
    # 记录这次对话
    await add_episode(
        summary=f"微信对话 - 用户: {content[:50]}... Agent: {response[:50]}...",
        tags=["wechat", "conversation"],
        importance=2
    )
    
    return response


async def get_status_summary() -> str:
    """获取状态摘要"""
    from ..memory import get_knowledge
    
    blog_date = await get_knowledge("blog.last_post_date")
    
    status = "📊 Polly Agent 状态\n\n"
    status += f"🌐 服务状态: 在线\n"
    
    if blog_date:
        status += f"📝 博客最后更新: {blog_date}\n"
    
    # TODO: 添加更多状态信息
    
    return status


async def get_recent_summary() -> str:
    """获取最近摘要"""
    from ..memory import get_recent_episodes
    
    episodes = await get_recent_episodes(days=7, limit=10)
    
    if not episodes:
        return "📅 最近 7 天没有记录"
    
    summary = "📅 最近 7 天的记录\n\n"
    for ep in episodes:
        date_str = ep.timestamp.strftime("%m-%d")
        importance_emoji = "⭐" if ep.importance >= 4 else "•"
        summary += f"{importance_emoji} [{date_str}] {ep.summary[:40]}...\n"
    
    return summary
