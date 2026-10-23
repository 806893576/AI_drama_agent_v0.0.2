"""向量检索服务。"""

from __future__ import annotations

from memory.vector_memory import MemoryDocument, VectorMemory


class VectorClient(VectorMemory):
    def upsert_text(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        self.add(MemoryDocument(doc_id=doc_id, text=text, metadata=metadata or {}))
