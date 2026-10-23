"""MCP 结果适配器。"""

from __future__ import annotations


def normalize_mcp_result(result: dict) -> dict:
    return {"content": result, "source": "mcp"}
