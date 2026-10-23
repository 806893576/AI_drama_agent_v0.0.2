"""简易语义记忆。

当前用关键词重叠模拟检索，保持无外部依赖；以后可以替换为真正向量库。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MemoryDocument:
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)


class VectorMemory:
    def __init__(self) -> None:
        self._docs: dict[str, MemoryDocument] = {}

    def add(self, doc: MemoryDocument) -> None:
        self._docs[doc.doc_id] = doc

    def search(self, query: str, limit: int = 5) -> list[MemoryDocument]:
        normalized_query = query.lower()
        query_terms = set(normalized_query.split()) or set(normalized_query)
        scored = []
        for doc in self._docs.values():
            normalized_text = doc.text.lower()
            if normalized_query in normalized_text:
                score = len(normalized_query) + 10
            else:
                # 中文短语常常没有空格，这里用字符重叠做无依赖兜底。
                score = len(query_terms & (set(normalized_text.split()) | set(normalized_text)))
            if score:
                scored.append((score, doc))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in scored[:limit]]
