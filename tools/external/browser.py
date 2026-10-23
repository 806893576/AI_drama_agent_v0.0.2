"""浏览器工具占位。"""

from __future__ import annotations


def fetch_page(url: str) -> dict:
    return {"url": url, "configured": False, "content": None}
