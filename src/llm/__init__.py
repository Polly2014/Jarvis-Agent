"""
LLM 客户端 — 支持 Streaming + Function Calling + Context Window Management

Phase 3: 让 Jarvis 在对话中调用工具
Phase 4.5: 三层防御 — token-aware 窗口 + LLM 压缩 + graceful fallback
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from ..skills.loader import discover_skills, format_skills_prompt
from ..tools.registry import get_registry, ToolRegistry
from ..tools.base import ToolResult

logger = logging.getLogger(__name__)


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

    # ── Phase 4.5: Context Window Management ──
    MODEL_CONTEXT = {
        "claude-sonnet-4": 200_000,
        "claude-sonnet-4.5": 200_000,
        "claude-haiku-3.5": 200_000,
        "gpt-4o": 128_000,
        "o3-mini": 128_000,
        "gemini-2.0-flash": 1_000_000,
    }
    DEFAULT_CONTEXT_LIMIT = 128_000  # 未知模型的保守默认值
    RESPONSE_RESERVE = 4096  # 预留给回复的 token
    SYSTEM_RESERVE = 8000  # 预留给 system prompt + tools schema

    COMPACTION_SUMMARY_PROMPT = (
        "请用 2-3 句话总结以下对话的关键内容和决策，"
        "保留重要的事实、数字和结论：\n\n{conversation}"
    )

    # 技能缓存（启动时发现一次，整个生命周期复用）
    _skills_prompt_cache: Optional[str] = None

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
        self._system_prompt: Optional[str] = None  # 延迟构建

    def reload_skills(self) -> None:
        """清除缓存，下次调用时重新发现技能。支持热加载。"""
        self._system_prompt = None
        logger.info("技能缓存已清除，下次调用时重新发现")

    def _build_system_prompt(self) -> str:
        """动态构建 system prompt，包含已发现的技能列表。"""
        if self._system_prompt is not None:
            return self._system_prompt

        prompt = self.SYSTEM_PROMPT

        # 技能发现 + prompt 注入
        try:
            skills = discover_skills()
            skills_section = format_skills_prompt(skills)
            if skills_section:
                prompt += skills_section
                logger.info("已注入 %d 个技能到 system prompt", len(skills))
        except Exception as e:
            logger.warning("技能发现失败，跳过: %s", e)

        self._system_prompt = prompt
        return prompt

    # ── Phase 4.5: Context Window Management ──

    def _estimate_tokens(self, text: str) -> int:
        """
        保守估算 token 数。
        中文字符按 1 token，ASCII 字符按 0.25 token。
        """
        if not text:
            return 0
        cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        ascii_chars = len(text) - cjk
        return cjk + ascii_chars // 4

    def _get_context_limit(self) -> int:
        """获取当前模型的 context window 大小"""
        return self.MODEL_CONTEXT.get(self.model, self.DEFAULT_CONTEXT_LIMIT)

    def _fit_messages_to_window(
        self,
        messages: list[dict],
        max_tokens: int,
    ) -> list[dict]:
        """
        按 token 预算从后往前填充消息。
        替代 messages[-20:] 硬截断。
        """
        budget = max_tokens - self.RESPONSE_RESERVE - self.SYSTEM_RESERVE

        fitted: list[dict] = []
        used = 0

        for msg in reversed(messages):
            content = msg.get("content", "") or ""
            msg_tokens = self._estimate_tokens(content)

            if used + msg_tokens > budget:
                break

            fitted.insert(0, msg)
            used += msg_tokens

        # 至少保留最近 2 条消息（一问一答），即使超预算
        if len(fitted) < 2 and len(messages) >= 2:
            fitted = messages[-2:]

        logger.debug(
            "Context window: %d messages fitted, ~%d tokens used (budget: %d)",
            len(fitted), used, budget,
        )
        return fitted

    async def _compact_messages(
        self,
        messages: list[dict],
        keep_recent: int = 6,
    ) -> tuple[list[dict], bool]:
        """
        压缩早期消息为摘要。

        保留最近 keep_recent 条原始消息，
        前面的压缩为一条 system message。

        Returns:
            (压缩后的消息列表, 是否执行了压缩)
        """
        if len(messages) <= keep_recent:
            return messages, False

        old_messages = messages[:-keep_recent]
        recent_messages = messages[-keep_recent:]

        # 只提取 user/assistant 的内容（跳过 tool results 等）
        conversation = "\n".join(
            f"[{m['role']}]: {(m.get('content') or '')[:500]}"
            for m in old_messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        )

        if not conversation.strip():
            return recent_messages, True

        try:
            summary = await self._compact_summarize(
                self.COMPACTION_SUMMARY_PROMPT.format(conversation=conversation)
            )
        except Exception as e:
            logger.warning("Compaction 摘要生成失败: %s，回退到截断", e)
            return recent_messages, True

        summary_msg = {
            "role": "system",
            "content": f"[对话摘要] {summary}",
        }

        logger.info(
            "对话已压缩: %d → %d 条 (摘要 %d chars)",
            len(messages), len(recent_messages) + 1, len(summary),
        )
        return [summary_msg] + recent_messages, True

    async def _compact_summarize(self, prompt: str) -> str:
        """
        独立的摘要 LLM 调用。
        不走 chat_with_tools，避免递归触发 compaction。
        """
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"Compaction API 错误: {response.status_code}")
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat_with_tools(
        self,
        messages: list[dict],
        on_content=None,
        on_tool_start=None,
        on_tool_end=None,
        on_compaction=None,
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
            on_compaction: 回调——对话被压缩时调用 (None -> None)

        Returns:
            最终的助手回复文本
        """
        system_msg = {"role": "system", "content": self._build_system_prompt()}
        tools_def = self.registry.to_openai_tools() if len(self.registry) > 0 else None

        full_reply = ""
        compacted = False  # 标记是否曾压缩（供 CLI 显示提示）

        for _round in range(self.MAX_TOOL_ROUNDS):
            # Phase 4.5: 主动压缩 — 消息过多时先压缩再发送
            total_tokens = sum(
                self._estimate_tokens(m.get("content", "") or "")
                for m in messages
            )
            if total_tokens > self._get_context_limit() * 0.7:
                logger.info("主动压缩: ~%d tokens 超过 70%% 限制", total_tokens)
                messages[:], was_compacted = await self._compact_messages(messages)
                if was_compacted and on_compaction:
                    on_compaction()

            # Phase 4.5: Token-aware 窗口替代 messages[-20:]
            context_limit = self._get_context_limit()
            fitted_messages = self._fit_messages_to_window(messages, context_limit)
            request_messages = [system_msg] + fitted_messages
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

            # base_url 约定不含 /v1，代码中拼接完整路径
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

                        # Phase 4.5: Context window 爆了 → 压缩后重试
                        error_lower = error_body.lower()
                        if response.status_code == 400 and (
                            "context" in error_lower
                            or "token" in error_lower
                            or "too long" in error_lower
                            or "maximum" in error_lower
                        ):
                            logger.warning(
                                "Context window exceeded (status=%d), compacting...",
                                response.status_code,
                            )
                            messages[:], compacted = await self._compact_messages(messages)
                            if compacted and on_compaction:
                                on_compaction()
                            continue  # 重试当前 round

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
