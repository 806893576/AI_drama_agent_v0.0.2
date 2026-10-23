"""工具权限控制。"""

from __future__ import annotations


class ToolPermissionGuard:
    def __init__(self, allowed_tools: set[str] | None = None) -> None:
        self.allowed_tools = allowed_tools or set()

    def assert_allowed(self, tool_name: str) -> None:
        if self.allowed_tools and tool_name not in self.allowed_tools:
            raise PermissionError(f"Tool is not allowed: {tool_name}")
