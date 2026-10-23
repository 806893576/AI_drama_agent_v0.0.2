"""Embedding 服务。"""

from __future__ import annotations


class SimpleEmbeddingClient:
    """无外部依赖的简易 embedding，占位用于接口联调。"""

    def embed(self, text: str) -> list[float]:
        if not text:
            return [0.0]
        return [sum(ord(char) for char in text) / len(text)]
