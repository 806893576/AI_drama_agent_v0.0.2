"""HTTP Client。"""

from __future__ import annotations

import urllib.request


class SimpleHttpClient:
    def get_text(self, url: str, timeout: float = 10.0) -> str:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read().decode("utf-8")
