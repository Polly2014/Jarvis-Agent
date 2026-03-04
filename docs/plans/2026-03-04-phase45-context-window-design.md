# Phase 4.5: Context Window Management

> **里程碑**：对话超长时自动压缩而非崩溃，像 Claude/Copilot 一样优雅处理

## 问题

`src/llm/__init__.py` 中 `messages[-20:]` 硬截断：

1. **20 条消息不感知 token 数** — 如果 tool result 返回大文件，20 条就可能爆
2. **无损截断** — 前面的对话直接丢弃，没有压缩/摘要
3. **API 报错 → 崩溃** — 没有 fallback 处理

## 三层防御策略

```
Layer 1: Token-aware 窗口    — 按 token 预算从后往前填充
Layer 2: Compaction（压缩）   — 超限时 LLM 摘要早期对话
Layer 3: Graceful fallback   — API 报 context 错误时自动压缩重试
```

## 详细设计

### Layer 1: Token-aware 窗口

替代 `messages[-20:]`，按 token 预算动态截取：

```python
MODEL_CONTEXT = {
    "claude-sonnet-4": 200_000,
    "claude-haiku-3.5": 200_000,
    "gpt-4o": 128_000,
}
RESPONSE_RESERVE = 4096
SYSTEM_RESERVE = 4000

def _estimate_tokens(self, text: str) -> int:
    """保守估算 token 数
    中文字符按 1 token，ASCII 按 0.25 token
    """
    cjk = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    ascii_chars = len(text) - cjk
    return cjk + ascii_chars // 4

def _fit_messages_to_window(self, system_msg, messages, max_tokens):
    """按 token 预算从后往前填充"""
    budget = max_tokens - self.RESPONSE_RESERVE - self.SYSTEM_RESERVE
    fitted = []
    used = 0
    for msg in reversed(messages):
        content = msg.get("content", "") or ""
        msg_tokens = self._estimate_tokens(content)
        if used + msg_tokens > budget:
            break
        fitted.insert(0, msg)
        used += msg_tokens
    return fitted
```

### Layer 2: Compaction — LLM 摘要压缩

当消息数超过阈值时，用 LLM 将早期对话压缩为一条摘要：

```python
COMPACTION_SUMMARY_PROMPT = (
    "请用 2-3 句话总结以下对话的关键内容和决策，"
    "保留重要的事实、数字和结论：\n\n{conversation}"
)

async def _compact_messages(self, messages, keep_recent=6):
    """保留最近 keep_recent 条原始消息，前面的压缩为摘要"""
    if len(messages) <= keep_recent:
        return messages
    
    old = messages[:-keep_recent]
    recent = messages[-keep_recent:]
    
    conversation = "\n".join(
        f"[{m['role']}]: {(m.get('content') or '')[:500]}"
        for m in old
        if m.get("role") in ("user", "assistant") and m.get("content")
    )
    
    summary = await self._compact_summarize(
        self.COMPACTION_SUMMARY_PROMPT.format(conversation=conversation)
    )
    
    return [{"role": "system", "content": f"[对话摘要] {summary}"}] + recent

async def _compact_summarize(self, prompt: str) -> str:
    """独立的摘要调用，不走 chat_with_tools，避免递归”””
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        response = await client.post(
            f"{self.base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.auth_token}"},
            json={
                "model": self.model,
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
```

### Layer 3: Graceful Fallback

API 返回 context_length_exceeded 时，自动压缩重试：

```python
# 在 chat_with_tools() 中
if response.status_code == 400:
    error_body = await response.aread()
    if "context" in error_body.lower() or "token" in error_body.lower():
        logger.warning("Context window exceeded, compacting...")
        messages[:] = await self._compact_messages(messages)
        continue  # 重试
```

## 改动清单

| 文件 | 改动 | 优先级 |
|------|------|--------|
| `src/llm/__init__.py` | 三层防御核心 + `_compact_summarize` 独立调用(避免递归) | 必须 |
| `src/cli/chat.py` | compaction 时显示 `📦 对话已压缩` 提示 | nice-to-have |

## 验收标准

- [ ] 连续对话 50+ 轮不崩溃
- [ ] 超出 context window 时自动压缩并显示 `[对话摘要]`
- [ ] API 返回 400/context error 时自动重试而非崩溃
- [ ] Phase 4 的 79/79 单元测试无回归
- [ ] tool result 包含大文件内容时仍能正常对话

## 预估

**1-2 天**。改动集中在 `llm/__init__.py` 一个文件，核心逻辑 ~80 行。
