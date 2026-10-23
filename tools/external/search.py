"""外部搜索工具占位。"""

from __future__ import annotations


def search_web(query: str) -> dict:
    # 生产环境可接搜索 API；当前返回明确的未配置状态。
    return {"query": query, "configured": False, "results": []}
