"""
企业微信模块
"""
from .client import wechat_client, WeChatClient
from .handlers import router

__all__ = ["wechat_client", "WeChatClient", "router"]
