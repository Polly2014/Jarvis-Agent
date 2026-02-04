"""
企业微信 API 客户端
"""
import httpx
import logging
from typing import Optional
from datetime import datetime, timedelta

from ..config import settings

logger = logging.getLogger(__name__)


class WeChatClient:
    """企业微信 API 客户端"""
    
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    async def get_access_token(self) -> str:
        """获取 access_token（自动缓存）"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/gettoken",
                params={
                    "corpid": settings.wechat_corp_id,
                    "corpsecret": settings.wechat_secret
                }
            )
            data = resp.json()
            
            if data.get("errcode") != 0:
                logger.error(f"获取 access_token 失败: {data}")
                raise Exception(f"WeChat API Error: {data.get('errmsg')}")
            
            self.access_token = data["access_token"]
            self.token_expires_at = datetime.now() + timedelta(seconds=data["expires_in"] - 300)
            
            return self.access_token
    
    async def send_text_message(self, content: str, to_user: Optional[str] = None) -> bool:
        """发送文本消息"""
        token = await self.get_access_token()
        
        payload = {
            "touser": to_user or settings.wechat_user_id,
            "msgtype": "text",
            "agentid": settings.wechat_agent_id,
            "text": {"content": content}
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/message/send",
                params={"access_token": token},
                json=payload
            )
            data = resp.json()
            
            if data.get("errcode") != 0:
                logger.error(f"发送消息失败: {data}")
                return False
            
            logger.info(f"消息发送成功: {content[:50]}...")
            return True
    
    async def send_markdown_message(self, content: str, to_user: Optional[str] = None) -> bool:
        """发送 Markdown 消息"""
        token = await self.get_access_token()
        
        payload = {
            "touser": to_user or settings.wechat_user_id,
            "msgtype": "markdown",
            "agentid": settings.wechat_agent_id,
            "markdown": {"content": content}
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/message/send",
                params={"access_token": token},
                json=payload
            )
            data = resp.json()
            
            if data.get("errcode") != 0:
                logger.error(f"发送消息失败: {data}")
                return False
            
            return True
    
    async def send_textcard_message(
        self, 
        title: str, 
        description: str, 
        url: str,
        btn_txt: str = "详情",
        to_user: Optional[str] = None
    ) -> bool:
        """发送文本卡片消息"""
        token = await self.get_access_token()
        
        payload = {
            "touser": to_user or settings.wechat_user_id,
            "msgtype": "textcard",
            "agentid": settings.wechat_agent_id,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btn_txt
            }
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/message/send",
                params={"access_token": token},
                json=payload
            )
            data = resp.json()
            
            if data.get("errcode") != 0:
                logger.error(f"发送消息失败: {data}")
                return False
            
            return True


# 全局客户端实例
wechat_client = WeChatClient()
