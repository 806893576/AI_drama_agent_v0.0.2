"""第三方 API 工具基类。"""

from __future__ import annotations


class ExternalApiTool:
    def __init__(self, name: str, base_url: str | None = None) -> None:
        self.name = name
        self.base_url = base_url

    def is_configured(self) -> bool:
        return bool(self.base_url)
