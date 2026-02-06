"""
Tool 基类与结果类型

所有工具的抽象基类，定义统一接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: str
    error: str = ""
    metadata: dict = field(default_factory=dict)

    def to_message(self) -> str:
        """转换为给 LLM 的消息文本"""
        if self.success:
            return self.output
        return f"Error: {self.error}\n{self.output}" if self.output else f"Error: {self.error}"


class Tool(ABC):
    """
    工具基类

    所有 Jarvis 工具都继承此类。
    通过 @property 定义名称、描述和参数 schema，
    通过 execute() 实现具体逻辑。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识，snake_case）"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（给 LLM 看的，简洁明了）"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """
        JSON Schema 参数定义

        示例:
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
            },
            "required": ["path"]
        }
        """
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 与 parameters schema 对应的参数

        Returns:
            ToolResult: 执行结果
        """
        ...

    def to_openai_function(self) -> dict:
        """转换为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }

    def __repr__(self) -> str:
        return f"<Tool: {self.name}>"
