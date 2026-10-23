"""工具装饰器。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    func: Callable


def drama_tool(name: str, description: str):
    def wrapper(func: Callable) -> Callable:
        setattr(func, "_drama_tool_spec", ToolSpec(name=name, description=description, func=func))
        return func

    return wrapper
