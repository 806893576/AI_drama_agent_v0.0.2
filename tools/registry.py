"""工具注册中心。"""

from __future__ import annotations

from tools.decorator import ToolSpec


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def register_function(self, func) -> None:
        spec = getattr(func, "_drama_tool_spec", None)
        if spec is None:
            raise ValueError("function is not decorated by @drama_tool")
        self.register(spec)

    def get(self, name: str) -> ToolSpec:
        return self._tools[name]

    def list(self) -> list[ToolSpec]:
        return list(self._tools.values())


tool_registry = ToolRegistry()
