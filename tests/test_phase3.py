"""
Phase 3 Tool System — 完整测试脚本

测试覆盖:
1. ToolRegistry: 自动发现、注册、获取、OpenAI 格式导出
2. Layer 0 原子工具: file_read, file_write, shell_exec, http_request
3. 安全机制: 危险命令拦截、系统路径写入阻止
4. Layer 1 元工具: create_skill, create_tool, create_mcp
5. LLM 集成: JarvisLLMClient 初始化 + tools 参数
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path


# ── 颜色辅助 ──────────────────────────────────────────────

def green(s): return f"\033[32m{s}\033[0m"
def red(s): return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def cyan(s): return f"\033[36m{s}\033[0m"
def bold(s): return f"\033[1m{s}\033[0m"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, name: str, condition: bool, detail: str = ""):
        if condition:
            print(f"  {green('✅')} {name}")
            self.passed += 1
        else:
            msg = f"  {red('❌')} {name}" + (f" — {detail}" if detail else "")
            print(msg)
            self.failed += 1
            self.errors.append(name)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        if self.failed == 0:
            print(f"{green(bold(f'🎉 ALL PASSED: {total}/{total}'))}")
        else:
            print(f"{red(bold(f'❌ FAILED: {self.failed}/{total}'))}")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*60}\n")
        return self.failed == 0


async def main():
    runner = TestRunner()
    tmp_dir = tempfile.mkdtemp(prefix="jarvis_test_")

    try:
        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 1. ToolRegistry 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.tools.registry import ToolRegistry, get_registry
        from src.tools.base import Tool, ToolResult

        # 1a. 自动发现
        registry = ToolRegistry()
        count = registry.discover()
        runner.check("自动发现工具数量 == 7", count == 7, f"实际: {count}")

        # 1b. 列出所有工具
        names = sorted(registry.list_names())
        expected = sorted([
            "file_read", "file_write", "shell_exec", "http_request",
            "create_skill", "create_tool", "create_mcp",
        ])
        runner.check("工具名称列表正确", names == expected, f"实际: {names}")

        # 1c. 按名获取
        tool = registry.get("file_read")
        runner.check("get('file_read') 返回工具", tool is not None)
        runner.check("get('不存在') 返回 None", registry.get("nonexistent") is None)

        # 1d. OpenAI tools 格式
        openai_tools = registry.to_openai_tools()
        runner.check("to_openai_tools() 返回 7 项", len(openai_tools) == 7)
        first = openai_tools[0]
        runner.check("OpenAI 格式有 type=function", first.get("type") == "function")
        runner.check("OpenAI 格式有 function.name", "name" in first.get("function", {}))
        runner.check("OpenAI 格式有 function.parameters", "parameters" in first.get("function", {}))

        # 1e. 执行不存在的工具
        result = await registry.execute("nonexistent_tool")
        runner.check("执行不存在工具 → success=False", not result.success)

        # 1f. 全局单例
        g1 = get_registry()
        g2 = get_registry()
        runner.check("get_registry() 返回同一实例", g1 is g2)

        # 1g. __contains__ / __len__
        runner.check("'file_read' in registry", "file_read" in registry)
        runner.check("len(registry) == 7", len(registry) == 7)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 2. Layer 0 — file_read 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 准备测试文件
        test_file = os.path.join(tmp_dir, "hello.txt")
        with open(test_file, "w") as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")

        result = await registry.execute("file_read", path=test_file)
        runner.check("读取文件 success=True", result.success)
        runner.check("内容包含 line1", "line1" in result.output)
        runner.check("内容包含 line5", "line5" in result.output)

        # 行范围
        result = await registry.execute("file_read", path=test_file, start_line=2, end_line=3)
        runner.check("行范围 2-3 包含 line2", "line2" in result.output)
        runner.check("行范围 2-3 包含 line3", "line3" in result.output)
        runner.check("行范围 2-3 不含 line1", "line1" not in result.output)

        # 不存在的文件
        result = await registry.execute("file_read", path="/tmp/no_such_file_jarvis_xyz.txt")
        runner.check("读取不存在文件 → success=False", not result.success)
        runner.check("错误信息包含'不存在'", "不存在" in result.error)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 3. Layer 0 — file_write 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 3a. 创建新文件
        new_file = os.path.join(tmp_dir, "subdir", "new.txt")
        result = await registry.execute("file_write", path=new_file, content="hello jarvis", mode="create")
        runner.check("创建新文件 success=True", result.success)
        runner.check("文件确实存在", os.path.exists(new_file))
        runner.check("内容正确", open(new_file).read() == "hello jarvis")

        # 3b. create 模式不允许覆盖
        result = await registry.execute("file_write", path=new_file, content="overwrite", mode="create")
        runner.check("create 模式重复写 → success=False", not result.success)
        runner.check("错误信息包含'已存在'", "已存在" in result.error)

        # 3c. overwrite 模式
        result = await registry.execute("file_write", path=new_file, content="overwritten!", mode="overwrite")
        runner.check("overwrite 模式 success=True", result.success)
        runner.check("内容被覆盖", open(new_file).read() == "overwritten!")

        # 3d. append 模式
        result = await registry.execute("file_write", path=new_file, content="\nappended", mode="append")
        runner.check("append 模式 success=True", result.success)
        runner.check("追加内容存在", "appended" in open(new_file).read())

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 4. Layer 0 — shell_exec 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 4a. 正常命令
        result = await registry.execute("shell_exec", command="echo hello-jarvis")
        runner.check("echo 命令 success=True", result.success)
        runner.check("输出包含 hello-jarvis", "hello-jarvis" in result.output)

        # 4b. 失败命令
        result = await registry.execute("shell_exec", command="ls /nonexistent_dir_xyz")
        runner.check("ls 不存在目录 → success=False", not result.success)

        # 4c. 工作目录
        result = await registry.execute("shell_exec", command="pwd", workdir=tmp_dir)
        runner.check("pwd 在指定目录", tmp_dir in result.output)

        # 4d. 超时
        result = await registry.execute("shell_exec", command="sleep 10", timeout=1)
        runner.check("超时命令 → success=False", not result.success)
        runner.check("超时错误信息", "超时" in result.error)

        # 4e. 空命令
        result = await registry.execute("shell_exec", command="")
        runner.check("空命令 → success=False", not result.success)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 5. Layer 0 — http_request 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 5a. GET 请求
        result = await registry.execute("http_request", method="GET", url="https://httpbin.org/get")
        runner.check("GET httpbin success=True", result.success)
        runner.check("HTTP 200 在输出中", "200" in result.output)

        # 5b. URL 校验
        result = await registry.execute("http_request", method="GET", url="ftp://evil.com")
        runner.check("非 http/https URL → success=False", not result.success)
        runner.check("错误信息包含 http", "http" in result.error.lower())

        # 5c. 超时
        result = await registry.execute("http_request", method="GET", url="https://httpbin.org/delay/10", timeout=2)
        runner.check("HTTP 超时 → success=False", not result.success)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 6. 安全机制测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 6a. 危险 shell 命令
        result = await registry.execute("shell_exec", command="rm -rf /")
        runner.check("rm -rf / 被拦截", not result.success)
        runner.check("拦截信息包含'危险'", "危险" in result.error)

        result = await registry.execute("shell_exec", command="sudo rm -rf /home")
        runner.check("sudo rm 被拦截", not result.success)

        result = await registry.execute("shell_exec", command="dd if=/dev/zero of=/dev/sda")
        runner.check("dd 命令被拦截", not result.success)

        # 6b. 系统路径写入
        result = await registry.execute("file_write", path="/System/evil.txt", content="bad")
        runner.check("写入 /System 被阻止", not result.success)
        runner.check("错误信息包含'安全'", "安全" in result.error)

        result = await registry.execute("file_write", path="/usr/bin/evil", content="bad")
        runner.check("写入 /usr 被阻止", not result.success)

        result = await registry.execute("file_write", path="/etc/passwd", content="bad")
        runner.check("写入 /etc 被阻止", not result.success)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 7. Layer 1 — create_skill 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        # 清理测试 skill
        test_skill_dir = Path.home() / ".jarvis" / "skills" / "test-greeting"
        if test_skill_dir.exists():
            shutil.rmtree(test_skill_dir)

        result = await registry.execute(
            "create_skill",
            name="test-greeting",
            description="A test skill for greeting users",
            instructions="## 工作流\n\n1. 问候用户\n2. 询问需求",
            scripts=[{"filename": "greet.py", "content": "print('Hello!')"}],
        )
        runner.check("create_skill success=True", result.success)

        # 验证文件
        skill_md = test_skill_dir / "SKILL.md"
        runner.check("SKILL.md 已创建", skill_md.exists())
        content = skill_md.read_text()
        runner.check("SKILL.md 包含 name", "name: test-greeting" in content)
        runner.check("SKILL.md 包含 description", "A test skill" in content)
        runner.check("SKILL.md 包含 instructions", "工作流" in content)

        script_file = test_skill_dir / "scripts" / "greet.py"
        runner.check("脚本文件已创建", script_file.exists())
        runner.check("脚本有可执行权限", os.access(script_file, os.X_OK))

        # 清理
        shutil.rmtree(test_skill_dir)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 8. Layer 1 — create_tool 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        test_tool_path = Path.home() / ".jarvis" / "tools" / "test_counter.py"
        if test_tool_path.exists():
            test_tool_path.unlink()

        result = await registry.execute(
            "create_tool",
            name="test_counter",
            description="Count words in text",
            parameters_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Input text"},
                },
                "required": ["text"],
            },
            code='count = len(kwargs.get("text", "").split())\nreturn ToolResult(success=True, output=f"Word count: {count}")',
        )
        runner.check("create_tool success=True", result.success)
        runner.check("工具文件已创建", test_tool_path.exists())

        content = test_tool_path.read_text()
        runner.check("包含 class TestCounterTool", "TestCounterTool" in content)
        runner.check("包含 Tool 基类", "class TestCounterTool(Tool)" in content)
        runner.check("包含 execute 方法", "async def execute" in content)

        # 清理
        test_tool_path.unlink()

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 9. Layer 1 — create_mcp 测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        test_mcp_dir = Path.home() / ".jarvis" / "mcp-servers" / "test-weather"
        if test_mcp_dir.exists():
            shutil.rmtree(test_mcp_dir)

        result = await registry.execute(
            "create_mcp",
            name="test-weather",
            description="Weather information MCP server",
            tools=[
                {
                    "name": "get_weather",
                    "description": "Get weather for a city",
                    "parameters": [
                        {"name": "city", "type": "str", "description": "City name"},
                    ],
                },
                {
                    "name": "get_forecast",
                    "description": "Get 7-day forecast",
                    "parameters": [
                        {"name": "city", "type": "str"},
                        {"name": "days", "type": "int"},
                    ],
                },
            ],
        )
        runner.check("create_mcp success=True", result.success)

        # 验证文件
        pyproject = test_mcp_dir / "pyproject.toml"
        runner.check("pyproject.toml 已创建", pyproject.exists())
        runner.check("pyproject 包含 name", "test-weather" in pyproject.read_text())

        server_py = test_mcp_dir / "src" / "server.py"
        runner.check("server.py 已创建", server_py.exists())
        server_content = server_py.read_text()
        runner.check("server.py 包含 FastMCP", "FastMCP" in server_content)
        runner.check("server.py 包含 get_weather", "get_weather" in server_content)
        runner.check("server.py 包含 get_forecast", "get_forecast" in server_content)
        runner.check("server.py 包含 @mcp.tool()", "@mcp.tool()" in server_content)

        init_py = test_mcp_dir / "src" / "__init__.py"
        runner.check("src/__init__.py 已创建", init_py.exists())

        # 清理
        shutil.rmtree(test_mcp_dir)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 10. LLM Client 初始化测试 ═══'))}\n")
        # ════════════════════════════════════════════════════

        from src.llm import JarvisLLMClient

        client = JarvisLLMClient(
            base_url="http://localhost:23335/api/openai",
            model="claude-sonnet-4",
            auth_token="test",
        )
        runner.check("JarvisLLMClient 初始化成功", client is not None)
        runner.check("client.registry 已加载工具", len(client.registry) == 7)
        runner.check("client.model 正确", client.model == "claude-sonnet-4")
        runner.check("SYSTEM_PROMPT 包含工具指引", "工具" in client.SYSTEM_PROMPT)
        runner.check("MAX_TOOL_ROUNDS > 0", client.MAX_TOOL_ROUNDS > 0)

        # 验证 openai tools 格式完整性
        tools_json = client.registry.to_openai_tools()
        for t in tools_json:
            func = t.get("function", {})
            has_all = all(k in func for k in ("name", "description", "parameters"))
            if not has_all:
                runner.check(f"工具 {func.get('name', '?')} 格式完整", False)
                break
        else:
            runner.check("所有工具 OpenAI 格式完整", True)

        # ════════════════════════════════════════════════════
        print(f"\n{bold(cyan('═══ 11. Tool.to_openai_function() 格式验证 ═══'))}\n")
        # ════════════════════════════════════════════════════

        for tool in registry.list_all():
            fn = tool.to_openai_function()
            runner.check(
                f"{tool.name}: type=function",
                fn.get("type") == "function",
            )
            func = fn.get("function", {})
            runner.check(
                f"{tool.name}: has parameters.type=object",
                func.get("parameters", {}).get("type") == "object",
            )

    finally:
        # 清理临时目录
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # 最终汇总
    return runner.summary()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
