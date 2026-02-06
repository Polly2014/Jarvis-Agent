# Phase 3: Tool System 设计文档

> 📅 2026-02-07  
> 🎯 让 Jarvis 拥有"手"——从只会说话到能做事

---

## 1. 核心理念

**"构造实现 tool 的 tool"**——不是给 Jarvis 一把具体的锤子，而是教它怎么打造锤子。

### 两层架构

```
Layer 0 (Atomic)     — 不可再分的原始能力
  file_read            读文件
  file_write           写文件
  shell_exec           执行 shell 命令
  http_request         发 HTTP 请求

Layer 1 (Meta-tools)  — 用 Layer 0 构造新能力
  create_skill         创建 Skill（.claude/skills/ 格式）
  create_tool          创建自定义 Tool（Python 脚本）
  create_mcp           创建 MCP Server 骨架

Layer 2 (Emergent)    — Jarvis 自己通过 Layer 1 创造（Phase 4）
  blog-writer, translator, ...
```

### 设计原则

1. **最小原子集合**：Layer 0 只有 4 个工具，够用就好
2. **OpenAI Function Calling**：兼容 Agent Maestro 已有的 API 格式
3. **安全优先**：shell_exec 需确认，file_write 有路径白名单
4. **注册表驱动**：工具自动发现 + 注册，新增工具零配置

---

## 2. Tool 接口定义

```python
# src/tools/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: str           # 主要输出内容
    error: str = ""       # 错误信息
    metadata: dict = None # 附加元数据

class Tool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称（唯一标识）"""
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（给 LLM 看的）"""
        ...
    
    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON Schema 参数定义"""
        ...
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
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
```

---

## 3. Tool Registry

```python
# src/tools/registry.py

class ToolRegistry:
    """工具注册表——自动发现与管理"""
    
    _tools: dict[str, Tool]  # name -> Tool
    
    def register(tool: Tool)         # 注册单个工具
    def discover()                   # 自动发现 builtins/ 和 meta/ 下的工具
    def get(name: str) -> Tool       # 获取工具
    def list_all() -> list[Tool]     # 列出所有工具
    def to_openai_tools() -> list    # 导出 OpenAI tools 格式
```

---

## 4. Layer 0 原子工具

### file_read
- **参数**: `path` (str), `start_line` (int, optional), `end_line` (int, optional)
- **返回**: 文件内容
- **安全**: 无限制（只读操作）

### file_write
- **参数**: `path` (str), `content` (str), `mode` ("create" | "overwrite" | "append")
- **返回**: 写入确认
- **安全**: 路径检查（不允许写系统文件）

### shell_exec
- **参数**: `command` (str), `workdir` (str, optional), `timeout` (int, default=30)
- **返回**: stdout + stderr + exit_code
- **安全**: 危险命令警告（rm -rf, sudo 等），超时保护

### http_request
- **参数**: `method` (str), `url` (str), `headers` (dict, optional), `body` (str, optional)
- **返回**: status_code + body
- **安全**: 仅 HTTP/HTTPS

---

## 5. Layer 1 元工具

### create_skill
- **参数**: `name` (str), `description` (str), `instructions` (str), `scripts` (list[dict], optional)
- **行为**: 
  1. 创建 `~/.jarvis/skills/{name}/SKILL.md`（遵循 .claude/skills/ 格式）
  2. 如有 scripts，创建 `scripts/` 子目录
- **格式参考**: `.claude/skills/` 的 YAML frontmatter + Markdown body

### create_tool
- **参数**: `name` (str), `description` (str), `parameters_schema` (dict), `code` (str)
- **行为**: 
  1. 创建 `~/.jarvis/tools/{name}.py`
  2. 生成标准 Tool 子类代码
  3. 自动注册到 ToolRegistry

### create_mcp
- **参数**: `name` (str), `description` (str), `tools` (list[dict])
- **行为**: 
  1. 创建 `~/.jarvis/mcp-servers/{name}/` 骨架
  2. 包含 pyproject.toml + server.py (FastMCP)
  3. 参考 Master-Translator-MCP-Server 结构

---

## 6. LLM 集成：Function Calling 流程

```
用户输入
  ↓
chat.py: 构建 messages + tools
  ↓
POST /v1/chat/completions (stream=True, tools=registry.to_openai_tools())
  ↓
解析 SSE 响应
  ├─ delta.content → 直接打印文字
  └─ delta.tool_calls → 收集 tool call
        ↓
      执行 tool → 得到 ToolResult
        ↓
      追加 tool result message → 再次调用 LLM
        ↓
      最终文字回复
```

### 关键修改点

1. **`src/llm/__init__.py`**: 新增 `JarvisLLMClient`，封装 streaming + tool calling
2. **`src/cli/chat.py`**: `run_chat_loop()` 使用新 client，支持多轮 tool 调用
3. **`_do_ask()`**: 单次提问也支持 tool calling

---

## 7. 文件结构

```
src/
├── tools/
│   ├── __init__.py          # 导出 ToolRegistry
│   ├── base.py              # Tool ABC + ToolResult
│   ├── registry.py          # ToolRegistry
│   ├── builtins/            # Layer 0
│   │   ├── __init__.py
│   │   ├── file_read.py
│   │   ├── file_write.py
│   │   ├── shell_exec.py
│   │   └── http_request.py
│   └── meta/                # Layer 1
│       ├── __init__.py
│       ├── create_skill.py
│       ├── create_tool.py
│       └── create_mcp.py
├── llm/
│   └── __init__.py          # JarvisLLMClient (streaming + tool calling)
└── cli/
    ├── chat.py              # 集成 tool calling
    └── tool_cmds.py         # jarvis tools list/run
```

---

## 8. CLI 命令

```
jarvis tools              # 列出所有工具
jarvis tools list          # 同上
jarvis tools run <name>    # 手动执行工具（调试用）
```

聊天中：
```
你> 帮我在 ~/projects 下创建一个 hello-world 项目

Jarvis: 好的，我来帮你创建。
  🔧 file_write: ~/projects/hello-world/main.py
  🔧 file_write: ~/projects/hello-world/README.md
  ✅ 项目已创建！包含 main.py 和 README.md
```
