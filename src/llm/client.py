"""
LLM 客户端
"""
import httpx
import logging
from typing import Optional

from ..config import settings
from ..memory import get_all_persona, get_recent_episodes

logger = logging.getLogger(__name__)


async def get_llm_response(user_message: str, context: Optional[str] = None) -> str:
    """获取 LLM 回复"""
    
    # 构建系统提示
    persona = await get_all_persona()
    recent_episodes = await get_recent_episodes(days=3, limit=5)
    
    system_prompt = build_system_prompt(persona, recent_episodes)
    
    if settings.default_llm == "deepseek":
        return await call_deepseek(system_prompt, user_message)
    else:
        return await call_claude(system_prompt, user_message)


def build_system_prompt(persona: dict, recent_episodes: list) -> str:
    """构建系统提示"""
    
    prompt = """你是 Polly Agent，Polly 的私人数字助手。

## 你的人格特质
"""
    
    for key, info in persona.items():
        prompt += f"- {key}: {info['value']}\n"
    
    if recent_episodes:
        prompt += "\n## 最近的对话记录\n"
        for ep in recent_episodes:
            prompt += f"- [{ep.timestamp.strftime('%m-%d')}] {ep.summary}\n"
    
    prompt += """
## 回复原则
1. 简洁有力，不要啰嗦
2. 对不确定的事情，说"我不确定"
3. 可以适当使用 emoji
4. 始终站在帮助 Polly 的角度思考
"""
    
    return prompt


async def call_deepseek(system_prompt: str, user_message: str) -> str:
    """调用 DeepSeek API"""
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.deepseek_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=30.0
        )
        
        data = resp.json()
        
        if "error" in data:
            logger.error(f"DeepSeek API 错误: {data}")
            return "抱歉，我暂时无法回复，请稍后再试。"
        
        return data["choices"][0]["message"]["content"]


async def call_claude(system_prompt: str, user_message: str) -> str:
    """调用 Claude API"""
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.claude_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_message}
                ]
            },
            timeout=30.0
        )
        
        data = resp.json()
        
        if "error" in data:
            logger.error(f"Claude API 错误: {data}")
            return "抱歉，我暂时无法回复，请稍后再试。"
        
        return data["content"][0]["text"]
