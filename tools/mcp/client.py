"""MCP Client 占位实现。"""

from __future__ import annotations


class MCPClient:
    def __init__(self, server_name: str) -> None:
        self.server_name = server_name

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        return {"server": self.server_name, "tool": tool_name, "arguments": arguments, "configured": False}
