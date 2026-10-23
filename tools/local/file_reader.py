"""文件读取工具。"""

from __future__ import annotations

from pathlib import Path

from tools.decorator import drama_tool


@drama_tool(name="read_text_file", description="读取 UTF-8 文本文件")
def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")
