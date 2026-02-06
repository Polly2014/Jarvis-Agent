"""
LLM 客户端 — 支持 Streaming + Function Calling

Phase 3: 让 Jarvis 在对话中调用工具
"""

import json
from dataclasses import dataclass, field
from typing import Optional

import httpx

from ..tools.registry import get_registry, ToolRegistry
from ..tools.base import ToolResult


@dataclass
class ToolCall:
    """LLM 请求的工具调用"""
    id: str
    name: str
    arguments: str  # JSON 字符串，需解析


@dataclass
class StreamChunk:
    """流式响应的一个片段"""
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: Optional[str] = None


class JarvisLLMClient:
    """
    Jarvis LLM 客户端

    核心能力:
    1. Streaming 对话（SSE）
    2. Function Calling（工具调用 + 多轮）
    3. 自动工具执行与回传
    """

    SYSTEM_PROMPT = (
        "你是 Jarvis，Polly 的私人 AI 助手。你可以使用工具来帮助完成任务。\n"
        "规则:\n"
        "- 简洁、有帮助、可以用 emoji\n"
        "- 需要读/写文件、执行命令、发 HTTP 请求时，使用对应工具\n"
        "- 不确定时先问用户\n"
        "- 工具执行后，基于结果给用户简明的总结"
    )

    MAX_TOOL_ROUNDS = 10  # 防止无限循环

    def __init__(
        self,
        base_url: str = "http://localhost:23335/api/openai",
        model: str = "claude-sonnet-4",
        auth_token: str = "",
        registry: Optional[ToolRegistry] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.auth_token = auth_token
        self.registry = registry or get_registry()

    async def chat_with_tools(
        self,
        messages: list[dict],
        on_content=None,
        on_tool_start=None,
        on_tool_end=None,
    ) -> str:
        """
        带工具调用的完整对话流程

        1. 发送 messages + tools 给 LLM
        2. 如果 LLM 要调用工具，执行工具并把结果追加到 messages
        3. 重复直到 LLM 给出纯文字回复
        4. 返回最终的完整回复

        Args:
            messages: 对话历史（会被修改——追加 tool calls 和 results）
            on_content: 回调——收到文字片段时调用 (str -> None)
            on_tool_start: 回调——开始执行工具 (tool_name, args -> None)
            on_tool_end: 回调——工具执行完毕 (tool_name, ToolResult -> None)

        Returns:
            最终的助手回复文本
        """
        system_msg = {"role": "system", "content": self.SYSTEM_PROMPT}
        tools_def = self.registry.to_openai_tools() if len(self.registry) > 0 else None

        full_reply = ""

        for _round in range(self.MAX_TOOL_ROUNDS):
            request_messages = [system_msg] + messages[-20:]
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "stream": True,
                "messages": request_messages,
            }
            if tools_def:
                payload["tools"] = tools_def

            content_parts = []
            tool_calls_acc: dict[int, dict] = {}

            async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.auth_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_body = ""
                        async for chunk in response.aiter_text():
                            error_body += chunk
                        raise RuntimeError(
                            f"API 错误 {response.status_code}: {error_body[:500]}"
                        )

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choice = chunk.get("choices", [{}])[0]
                        delta = choice.get("delta", {})

                        # 文字内容
                        if delta.get("content"):
                            text = delta["content"]
                            content_parts.append(text)
                            if on_content:
                                on_content(text)

                        # 工具调用（增量累积）
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_acc:
                                    tool_calls_acc[idx] = {
                                        "id": tc.get("id", f"call_{idx}"),
                                        "name": "",
                                        "arguments": "",
                                    }
                                if tc.get("id"):
                                    tool_calls_acc[idx]["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    tool_calls_acc[idx]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    tool_calls_acc[idx]["arguments"] += tc["function"][
                                        "arguments"
                                    ]

            content_text = "".join(content_parts)

            # Case 1: 纯文字回复 → 完成
            if not tool_calls_acc:
                full_reply += content_text
                messages.append({"role": "assistant", "content": content_text})
                return full_reply

            # Case 2: 有工具调用 → 执行，追加结果，再循环
            assistant_msg: dict = {"role": "assistant", "content": content_text or None}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls_acc.values()
            ]
            messages.append(assistant_msg)

            if content_text:
                full_reply += content_text

            # 执行每个工具
            for tc_info in tool_calls_acc.values():
                tool_name = tc_info["name"]
                tool_id = tc_info["id"]

                try:
                    args = json.loads(tc_info["arguments"]) if tc_info["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}

                if on_tool_start:
                    on_tool_start(tool_name, args)

                result = await self.registry.execute(tool_name, **args)

                if on_tool_end:
                    on_tool_end(tool_name, result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": result.to_message(),
                })

        return full_reply + "\n\n⚠️ 工具调用超过最大轮数，已停止。"

    async def simple_ask(self, question: str) -> str:
        """单次提问（不带历史）"""
        messages: list[dict] = [{"role": "user", "content": question}]
        return await self.chat_with_tools(messages)


__all__ = ["JarvisLLMClient", "ToolCall", "StreamChunk"]
