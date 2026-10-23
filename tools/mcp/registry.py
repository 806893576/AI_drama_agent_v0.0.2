"""MCP 服务注册中心。"""

from __future__ import annotations


class MCPRegistry:
    def __init__(self) -> None:
        self._servers: dict[str, dict] = {}

    def register(self, name: str, config: dict) -> None:
        self._servers[name] = config

    def list_servers(self) -> list[str]:
        return list(self._servers)
