"""外部 API Client。"""

from __future__ import annotations

from services.external.http_client import SimpleHttpClient


class ExternalApiClient:
    def __init__(self) -> None:
        self.http = SimpleHttpClient()
