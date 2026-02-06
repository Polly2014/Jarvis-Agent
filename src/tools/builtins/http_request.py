"""
http_request — 发送 HTTP 请求

Layer 0 原子工具。支持 GET/POST/PUT/DELETE 等方法。
"""

import json as json_module

from ..base import Tool, ToolResult

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class HttpRequestTool(Tool):

    @property
    def name(self) -> str:
        return "http_request"

    @property
    def description(self) -> str:
        return "发送 HTTP 请求。支持 GET、POST、PUT、DELETE 等方法。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"],
                    "description": "HTTP 方法",
                },
                "url": {
                    "type": "string",
                    "description": "请求 URL（必须以 http:// 或 https:// 开头）",
                },
                "headers": {
                    "type": "object",
                    "description": "请求头（可选）",
                    "additionalProperties": {"type": "string"},
                },
                "body": {
                    "type": "string",
                    "description": "请求体（可选，JSON 字符串或纯文本）",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认 30",
                    "default": 30,
                },
            },
            "required": ["method", "url"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        if not HAS_HTTPX:
            return ToolResult(
                success=False, output="",
                error="httpx 未安装，无法发送 HTTP 请求"
            )

        method = kwargs.get("method", "GET").upper()
        url = kwargs.get("url", "")
        headers = kwargs.get("headers") or {}
        body = kwargs.get("body")
        timeout = kwargs.get("timeout", 30)

        # URL 校验
        if not url.startswith(("http://", "https://")):
            return ToolResult(
                success=False, output="",
                error="URL 必须以 http:// 或 https:// 开头"
            )

        try:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                request_kwargs = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                }

                if body and method in ("POST", "PUT", "PATCH"):
                    # 尝试解析为 JSON
                    try:
                        json_body = json_module.loads(body)
                        request_kwargs["json"] = json_body
                    except (json_module.JSONDecodeError, TypeError):
                        request_kwargs["content"] = body

                response = await client.request(**request_kwargs)

            # 构造输出
            body_text = response.text
            if len(body_text) > 50_000:
                body_text = body_text[:50_000] + "\n... (truncated)"

            output = f"HTTP {response.status_code}\n\n{body_text}"

            return ToolResult(
                success=(200 <= response.status_code < 400),
                output=output,
                error="" if response.status_code < 400 else f"HTTP {response.status_code}",
                metadata={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                },
            )

        except httpx.TimeoutException:
            return ToolResult(
                success=False, output="",
                error=f"请求超时（{timeout}秒）"
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=f"请求失败: {e}")
