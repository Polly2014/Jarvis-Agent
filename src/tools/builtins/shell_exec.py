"""
shell_exec — 执行 Shell 命令

Layer 0 原子工具。带超时保护和危险命令警告。
"""

import asyncio
import os
import shlex

from ..base import Tool, ToolResult


# 需要特别小心的命令前缀
_DANGEROUS_PATTERNS = (
    "rm -rf /", "rm -rf ~", "sudo rm",
    "mkfs", "dd if=", "> /dev/",
    "chmod 777 /", ":(){ :|:& };:",
)


class ShellExecTool(Tool):

    @property
    def name(self) -> str:
        return "shell_exec"

    @property
    def description(self) -> str:
        return "执行 Shell 命令并返回输出。带超时保护，默认 30 秒。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令",
                },
                "workdir": {
                    "type": "string",
                    "description": "工作目录（可选，默认为当前目录）",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认 30",
                    "default": 30,
                },
            },
            "required": ["command"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("command", "")
        workdir = kwargs.get("workdir")
        timeout = kwargs.get("timeout", 30)

        if not command.strip():
            return ToolResult(success=False, output="", error="命令不能为空")

        # 危险命令检查
        cmd_lower = command.lower().strip()
        for pattern in _DANGEROUS_PATTERNS:
            if pattern in cmd_lower:
                return ToolResult(
                    success=False, output="",
                    error=f"⚠️ 危险命令被拦截: 包含 '{pattern}'"
                )

        # 展开工作目录
        if workdir:
            workdir = os.path.expanduser(os.path.expandvars(workdir))
            if not os.path.isdir(workdir):
                return ToolResult(
                    success=False, output="",
                    error=f"工作目录不存在: {workdir}"
                )

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
                env={**os.environ},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False, output="",
                    error=f"命令超时（{timeout}秒）已终止"
                )

            stdout_str = stdout.decode("utf-8", errors="replace").strip()
            stderr_str = stderr.decode("utf-8", errors="replace").strip()
            exit_code = process.returncode

            # 截断过长输出
            if len(stdout_str) > 50_000:
                stdout_str = stdout_str[:50_000] + "\n... (output truncated)"
            if len(stderr_str) > 10_000:
                stderr_str = stderr_str[:10_000] + "\n... (stderr truncated)"

            output_parts = []
            if stdout_str:
                output_parts.append(stdout_str)
            if stderr_str:
                output_parts.append(f"[stderr]\n{stderr_str}")

            output = "\n".join(output_parts) if output_parts else "(no output)"

            return ToolResult(
                success=(exit_code == 0),
                output=output,
                error=f"exit code: {exit_code}" if exit_code != 0 else "",
                metadata={"exit_code": exit_code, "command": command},
            )

        except Exception as e:
            return ToolResult(success=False, output="", error=f"执行失败: {e}")
